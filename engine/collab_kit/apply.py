"""Applying returns: whole or not at all, at most once, with a ledger that makes undo possible.

    plan  ->  every change is checked against the unit as it is (item numbers, title checks,
              paths) and turned into file effects, in memory. Any problem rejects the whole return.
    run   ->  the ledger is written first (state "applying", with every effect's before and after
              text), then the effects, then the ledger is marked "done" and the return moves to
              _returns/applied/. A run that stops half way is finished by the next one: effects
              already in place are skipped, so nothing is applied twice.

The ledger (`_returns/applied/<id>.ledger.json`) lives with the effects, in the unit itself.
Undo is another return (`undo <id>`): it restores each file the earlier return wrote, provided
nothing has changed it since; otherwise the undo is refused and says which file moved on.
"""
from __future__ import annotations

import dataclasses
import json
import re

from . import returns as R
from .store import Entry, StoreError
from .text import (FENCE_NOTE, check_project_name, fold, one_line, safe_relpath, sha, stamp, today,
                   utcnow, PLAIN_SUFFIXES)
from .unit import (AGENDA, APPLIED, FAILED, GENERATED_KNOWLEDGE, GENERATED_KNOWLEDGE_DIRS, KNOWLEDGE,
                   RETURNS, START, STRAYS, VERSIONS, WIP, Item, Unit, edit_item_text, render_item,
                   retire, write_versioned)
from .text import slug, split_front_matter

MAX_RETURN_BYTES = 256 * 1024
MAX_CHANGES = 200
SETTLE_SECONDS = 120              # a return younger than this may still be syncing
NEW_PROJECTS_PER_DAY = 3
STATUS_FILE = f"{KNOWLEDGE}/status.md"


class Reject(Exception):
    """The return cannot be applied as written."""


@dataclasses.dataclass
class Effect:
    op: str               # "write" or "move"
    path: str             # relative to the effect's unit
    before: str | None = None
    after: str | None = None
    dest: str | None = None   # for "move"
    unit: str = "self"        # "self" or "top" (only project/new-project changes touch the top)


@dataclasses.dataclass
class Outcome:
    status: str           # applied | recorded | failed | stray | waiting | already | undone
    rid: str
    message: str = ""
    minted: list = dataclasses.field(default_factory=list)
    push_requests: list = dataclasses.field(default_factory=list)


# ----------------------------------------------------------------------- the overlay --

class Overlay:
    """The unit as it will be once the return is applied, built up change by change."""

    def __init__(self, unit: Unit, top: Unit | None):
        self.units = {"self": unit, "top": top}
        self.files: dict[tuple[str, str], str | None] = {}
        self.original: dict[tuple[str, str], str | None] = {}
        self.order: list[tuple[str, str]] = []

    def read(self, path: str, where: str = "self") -> str | None:
        key = (where, path)
        if key in self.files:
            return self.files[key]
        u = self.units[where]
        if u is None:
            raise Reject("this change needs the top level, which is not available here")
        text = u.store.read(path)
        self.original[key] = text
        return text

    def write(self, path: str, text: str, where: str = "self") -> None:
        key = (where, path)
        if key not in self.original:
            self.read(path, where)
        if key not in self.order:
            self.order.append(key)
        self.files[key] = text

    def effects(self) -> list[Effect]:
        out = []
        for where, path in self.order:
            before, after = self.original.get((where, path)), self.files[(where, path)]
            if before != after:
                out.append(Effect("write", path, before, after, unit=where))
        return out


# ------------------------------------------------------------------------- planning --

def _item_from_text(path: str, text: str) -> Item:
    fields, raw, body = split_front_matter(text)
    num = int(re.match(r"^agenda/W-(\d+)", path).group(1))
    return Item(f"W-{num:03d}", num, path, fields, raw, body, text)


class Planner:
    def __init__(self, unit: Unit, ret: R.Return, top: Unit | None, now=None):
        self.unit, self.ret, self.top = unit, ret, top
        self.ov = Overlay(unit, top)
        self.handles: dict[str, str] = {}       # @handle -> agenda path
        self.minted: list[str] = []
        self.push_requests: list[dict] = []
        self.now = now or utcnow()
        self._next = None
        self.sender = one_line(ret.fields.get("from", "") or "unknown", 60)

    # --- items
    def next_number(self) -> int:
        if self._next is None:
            used = self.unit.used_numbers()
            self._next = max((max(used) if used else 0) + 1, read_counter(self.unit))
        n = self._next
        self._next += 1
        return n

    def resolve(self, ch: R.Change) -> Item:
        ref = ch.ref
        if ref.startswith("@"):
            if ref not in self.handles:
                raise Reject(f"line {ch.line}: {ref} is not defined by an earlier new-item in this return")
            path = self.handles[ref]
            return _item_from_text(path, self.ov.read(path))
        found = [i for i in self.unit.items() if i.id == ref]
        if not found:
            raise Reject(f"line {ch.line}: there is no item {ref} in {self.unit.name}")
        if len(found) > 1:
            raise Reject(f"line {ch.line}: two files claim {ref}; renumber one first")
        item = found[0]
        text = self.ov.read(item.path)
        item = _item_from_text(item.path, text)
        if ch.check is not None and fold(ch.check) not in fold(item.title):
            raise Reject(f"line {ch.line}: title check failed: {ref} is \"{one_line(item.title, 100)}\", "
                         f"and \"{one_line(ch.check, 60)}\" is not part of that title")
        return item

    def tag(self) -> str:
        return f"(return {self.ret.id}, from {self.sender})"

    def plan(self) -> list[Effect]:
        for ch in self.ret.changes:
            getattr(self, "op_" + ch.op.replace("-", "_"))(ch)
        return self.ov.effects()

    def op_new_item(self, ch: R.Change):
        a = ch.args
        if self.unit.top is False and a.get("project") and a["project"] != self.unit.name:
            raise Reject(f"line {ch.line}: a project's inbox can only add items to that project")
        if ch.ref and ch.ref in self.handles:
            raise Reject(f"line {ch.line}: {ch.ref} is used twice")
        num = self.next_number()
        wid = f"W-{num:03d}"
        path = f"{AGENDA}/{wid}-{slug(a['title'], 40)}.md"
        text = render_item(wid, a["title"], kind=a.get("kind", "task"), importance=a.get("importance", 3),
                           status=a.get("status", "open"), due=a.get("due", ""), project=a.get("project", ""),
                           body=ch.body, log=[f"created {self.tag()}"])
        self.ov.write(path, text)
        if ch.ref:
            self.handles[ch.ref] = path
        self.minted.append(wid)

    def _edit(self, ch: R.Change, fields: dict, log: str):
        item = self.resolve(ch)
        self.ov.write(item.path, edit_item_text(item, fields, f"{log} {self.tag()}"))

    def op_set(self, ch: R.Change):
        if self.unit.top is False and ch.args.get("project") not in (None, "", self.unit.name):
            raise Reject(f"line {ch.line}: a project's inbox cannot move items to another project")
        desc = ", ".join(f"{k} to {v if v != '' else '(none)'}" for k, v in ch.args.items())
        self._edit(ch, dict(ch.args), f"set {desc}")

    def op_log(self, ch: R.Change):
        text = ch.text or ch.body
        if not text or not text.strip():
            raise Reject(f"line {ch.line}: log needs its text (quoted, or a fenced body)")
        item = self.resolve(ch)
        self.ov.write(item.path, edit_item_text(item, {}, f"{text.strip()} {self.tag()}"))

    def op_settle(self, ch: R.Change):
        self._edit(ch, {"status": "settled", "outcome": ch.args["outcome"]}, f"settled: {ch.args['outcome']}")

    def op_snooze(self, ch: R.Change):
        self._edit(ch, {"snoozed_until": ch.args["until"]}, f"snoozed until {ch.args['until']}")

    def op_withdraw(self, ch: R.Change):
        why = ch.args.get("reason", "")
        self._edit(ch, {"status": "dropped"}, f"withdrawn{': ' + why if why else ''}")

    def op_reopen(self, ch: R.Change):
        why = ch.args.get("reason", "")
        self._edit(ch, {"status": "open", "outcome": ""}, f"reopened{': ' + why if why else ''}")

    def op_status(self, ch: R.Change):
        text = (ch.text or ch.body or "").strip()
        if not text:
            raise Reject(f"line {ch.line}: status needs its text (quoted, or a fenced body)")
        self.ov.write(STATUS_FILE, add_status_entry(self.ov.read(STATUS_FILE), self.unit.name,
                                                    self.sender, self.ret.topic, text, self.now))

    def op_knowledge(self, ch: R.Change):
        rel = safe_relpath(ch.ref)
        if not rel:
            raise Reject(f"line {ch.line}: '{ch.ref}' is not a path inside knowledge/")
        if "." + rel.rsplit(".", 1)[-1].lower() not in PLAIN_SUFFIXES or "." not in rel:
            raise Reject(f"line {ch.line}: knowledge files are plain files ({', '.join(sorted(PLAIN_SUFFIXES))})")
        if self.unit.home == "repo" and (rel in GENERATED_KNOWLEDGE or rel.split("/")[0] in GENERATED_KNOWLEDGE_DIRS):
            raise Reject(f"line {ch.line}: knowledge/{rel} is generated by the build; change its source instead")
        if ch.body is None:
            raise Reject(f"line {ch.line}: knowledge needs the file's content as a fenced body")
        self.ov.write(f"{KNOWLEDGE}/{rel}", ch.body.rstrip("\n") + "\n")

    def op_project(self, ch: R.Change):
        if self.top is None:
            raise Reject(f"line {ch.line}: 'project' changes the top level's project list, which is not reachable here")
        name = ch.ref or ("" if self.unit.top else self.unit.name)
        if not self.unit.top and name != self.unit.name:
            raise Reject(f"line {ch.line}: a project's inbox can only change its own entry")
        if not name:
            raise Reject(f"line {ch.line}: 'project' from the top-level inbox names the project")
        changed = False
        for path in (f"{KNOWLEDGE}/projects.md", START):
            text = self.ov.read(path, "top")
            if text is None:
                continue
            new = edit_project_row(text, name, ch.args)
            if new != text:
                self.ov.write(path, new, "top")
                changed = True
        if not changed:
            raise Reject(f"line {ch.line}: no row for '{name}' in the top level's project tables")

    def op_new_project(self, ch: R.Change):
        if not self.unit.top:
            raise Reject(f"line {ch.line}: projects are started only from the top-level inbox")
        a = ch.args
        name = a["name"].strip()
        if ch.check is None:
            raise Reject(f"line {ch.line}: new-project must repeat part of the idea's title in quotes, as a check")
        idea = self.resolve(R.Change("set", ch.line, ref=a["from"], check=ch.check))
        if idea.kind != "project" or not idea.is_open:
            raise Reject(f"line {ch.line}: {idea.id} is not an open idea of kind project")
        taken = existing_projects(self.unit) | listed_repositories(self.unit)
        why = check_project_name(name, taken)
        if why:
            raise Reject(f"line {ch.line}: {why}")
        if recent_new_projects(self.unit, self.now) >= NEW_PROJECTS_PER_DAY:
            raise Reject(f"line {ch.line}: at most {NEW_PROJECTS_PER_DAY} projects start in one day")
        base = f"projects/{name}/collab-kit"
        about = a.get("about") or idea.title
        spoken = a.get("spoken", "")
        from .templates import project_start_file, returns_readme
        self.ov.write(f"{base}/{START}", project_start_file(name, about, spoken, home="cloud"))
        self.ov.write(f"{base}/{RETURNS}/README.md", returns_readme(name))
        self.ov.write(f"{base}/{KNOWLEDGE}/README.md", f"# {name}\n\n{about}\n")
        self.ov.write(f"{base}/{WIP}/README.md", "# WIP\n\nCheckpoint notes between saves. See the top-level start file.\n")
        body = idea.body.split("\n<!-- ", 1)[0]
        first = render_item("W-001", idea.title, kind="work-out", importance=idea.importance, due=idea.due,
                            body=re.sub(r"(?ms)^## Log\s*$.*", "", body).strip() or idea.title,
                            log=[f"carried over from the top level's {idea.id} {self.tag()}"])
        self.ov.write(f"{base}/{AGENDA}/W-001-{slug(idea.title, 40)}.md", first)
        self.ov.write(idea.path, edit_item_text(idea, {"status": "settled", "outcome": f"started as project {name}"},
                                                f"settled: started as project {name} (its W-001) {self.tag()}"))
        row = {"folder": name, "say": spoken, "what": about, "home": "cloud folder (no repository)"}
        for path in (f"{KNOWLEDGE}/projects.md", START):
            text = self.ov.read(path)
            if text is not None:
                self.ov.write(path, add_project_row(text, row))
        self.minted.append(f"project:{name}")

    def op_undo(self, ch: R.Change):
        target = ch.ref
        led = read_ledger(self.unit, target)
        if not led or led.get("state") != "done":
            raise Reject(f"line {ch.line}: there is no applied return '{target}' here to undo")
        if led.get("undone_by"):
            raise Reject(f"line {ch.line}: '{target}' was already undone by {led['undone_by']}")
        for eff in reversed(led.get("effects", [])):
            where = eff.get("unit", "self")
            check_effect_path(str(eff.get("path", "")), where)
            if not isinstance(eff.get("before"), (str, type(None))):
                raise Reject(f"line {ch.line}: the ledger of '{target}' is malformed")
            cur = self.ov.read(eff["path"], where)
            if sha_or_none(cur) != eff.get("after_sha"):
                raise Reject(f"line {ch.line}: cannot undo '{target}': {eff['path']} has changed since")
            if eff.get("before") is None:
                self.ov.write(eff["path"], None, where)        # retire (moved to _versions/)
            else:
                self.ov.write(eff["path"], eff["before"], where)
        self.undo_target = target

    def op_push_request(self, ch: R.Change):
        """An approved push becomes a task on the agenda, carrying the approval verbatim, until a
        back end (or a session) carries it out and settles it."""
        repo, branch = ch.args["repo"].strip(), ch.args.get("branch", "").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", repo) or (branch and not re.fullmatch(r"[A-Za-z0-9._/-]{1,200}", branch)):
            raise Reject(f"line {ch.line}: push-request names a repository (and branch) by name only")
        what = f"{repo}" + (f" ({branch})" if branch else "")
        self.push_requests.append({"repo": repo, "branch": branch, "approval": ch.args["approval"], "line": ch.line})
        num = self.next_number()
        wid = f"W-{num:03d}"
        title = f"Push {what} to GitHub (approved)"
        body = (f"## What's needed\nPush {what}, as approved.\n\n## What we know so far\n"
                f"Approval, verbatim: \"{one_line(ch.args['approval'], 400)}\" (from {self.sender}).\n\n"
                f"## Done when\nThe push is done and this item is settled with what was pushed.\n")
        self.ov.write(f"{AGENDA}/{wid}-{slug(title, 40)}.md",
                      render_item(wid, title, kind="task", importance=2, body=body, log=[f"created {self.tag()}"]))
        self.minted.append(wid)


def sha_or_none(text):
    return None if text is None else sha(text)


_PROJECT_PATH = re.compile(r"^projects/[a-z][a-z0-9-]{0,39}/collab-kit/(?:00-START-HERE\.md|(?:agenda|knowledge|_returns|WIP)/.+)$")


def check_effect_path(path: str, where: str) -> None:
    """Every file a ledger names must be one a return could have written: inside the unit's agenda/
    or knowledge/, its start file, or (top level only) a new project's folder. A ledger is a file in
    the shared folder, so it is checked like any other text from outside before it is trusted."""
    if where not in ("self", "top"):
        raise Reject(f"a ledger names an unknown unit {where!r}")
    from .store import StoreError, check_rel
    try:
        check_rel(path)
    except StoreError as e:
        raise Reject(str(e)) from None
    parts = path.split("/")
    if any(p.startswith(".") or p == VERSIONS for p in parts):
        raise Reject(f"a ledger names a path a return never writes: {path!r}")
    if path == START or path.startswith((f"{AGENDA}/", f"{KNOWLEDGE}/")) or _PROJECT_PATH.match(path):
        return
    raise Reject(f"a ledger names a path a return never writes: {path!r}")


# --------------------------------------------------------------- tables and status --

def add_status_entry(current: str | None, unit_name: str, sender: str, topic: str, text: str, now) -> str:
    head = f"## {now.strftime('%Y-%m-%d %H:%M')} UTC, {sender}" + (f": {one_line(topic, 100)}" if topic else "")
    entry = f"{head}\n\n{text.strip()}\n"
    if not current:
        title = "the top level" if unit_name == "top" else unit_name
        current = (f"# What is going on ({title})\n\nWritten by work running outside conversations "
                   f"(the back end, Claude Code sessions, research runs). Newest first.\n")
    m = re.search(r"^## ", current, re.M)
    out = current[: m.start()] + entry + "\n" + current[m.start():] if m else current.rstrip("\n") + "\n\n" + entry
    return re.sub(r"Last updated [^.\n]*\.", f"Last updated {now.strftime('%Y-%m-%d %H:%M')} UTC.", out, count=1)


def _table_rows(text: str):
    """(header cells, row index list) of the first table whose header has a Folder column."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and "folder" in line.lower() and i + 1 < len(lines) and re.match(r"^\s*\|[-:| ]+\|\s*$", lines[i + 1]):
            cells = [c.strip().lower() for c in line.strip().strip("|").split("|")]
            j = i + 2
            rows = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(j)
                j += 1
            return lines, i, cells, rows
    return lines, None, [], []


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _col(cells: list[str], *names: str) -> int | None:
    for n in names:
        for k, c in enumerate(cells):
            if c.startswith(n):
                return k
    return None


def edit_project_row(text: str, name: str, args: dict) -> str:
    lines, hi, cells, rows = _table_rows(text)
    if hi is None:
        return text
    fcol, scol, wcol = _col(cells, "folder"), _col(cells, "say"), _col(cells, "what")
    for j in rows:
        row = _cells(lines[j])
        if fcol is None or fcol >= len(row) or row[fcol].strip("`") != name:
            continue
        if "spoken" in args and scol is not None:
            row[scol] = ", ".join(f"\"{s.strip()}\"" for s in args["spoken"].split(",") if s.strip())
        if "about" in args and wcol is not None:
            row[wcol] = one_line(args["about"], 200)
        if "active" in args and wcol is not None:
            row[wcol] = row[wcol].replace(" (inactive)", "") + ("" if args["active"] else " (inactive)")
        lines[j] = "| " + " | ".join(row) + " |"
    return "\n".join(lines)


def add_project_row(text: str, row: dict) -> str:
    lines, hi, cells, rows = _table_rows(text)
    if hi is None:
        return text
    vals = []
    for c in cells:
        if c.startswith("folder"):
            vals.append(f"`{row['folder']}`")
        elif c.startswith("say"):
            vals.append(", ".join(f"\"{s.strip()}\"" for s in row["say"].split(",") if s.strip()))
        elif c.startswith("what"):
            vals.append(one_line(row["what"], 200))
        elif c.startswith("home") or c.startswith("here"):
            vals.append(row["home"])
        else:
            vals.append("")
    at = (rows[-1] if rows else hi + 1) + 1
    lines.insert(at, "| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def existing_projects(top: Unit) -> set[str]:
    return {e.name for e in top.store.dirs("projects")}


def listed_repositories(top: Unit) -> set[str]:
    """Every name in a Repository/Folder column of the top level's knowledge (repositories are names too)."""
    out = set()
    for name in ("projects.md", "repositories.md"):
        text = top.store.read(f"{KNOWLEDGE}/{name}") or ""
        for line in text.split("\n"):
            m = re.match(r"^\s*\|\s*`([A-Za-z0-9._-]+)`\s*\|", line)
            if m:
                out.add(m.group(1))
    return out


def recent_new_projects(top: Unit, now) -> int:
    n = 0
    for e in top.store.files(APPLIED):
        if not e.name.endswith(".ledger.json"):
            continue
        led = json.loads(top.store.read(f"{APPLIED}/{e.name}") or "{}")
        if any(m.startswith("project:") for m in led.get("minted", [])):
            at = led.get("applied_at", "")
            if at[:10] == now.date().isoformat():
                n += 1
    return n


# --------------------------------------------------------------------------- ledger --

COUNTER = f"{APPLIED}/next-item.json"


def read_counter(unit: Unit) -> int:
    """The next item number never yet used in this unit (numbers are never reused, even after an
    undo and the trimming of old versions)."""
    try:
        return int(json.loads(unit.store.read(COUNTER) or "{}").get("next", 1))
    except (ValueError, TypeError, AttributeError):
        return 1


def bump_counter(unit: Unit, minted: list[str]) -> None:
    nums = [int(m[2:]) for m in minted if re.fullmatch(r"W-\d+", m)]
    if nums and max(nums) + 1 > read_counter(unit):
        unit.store.write(COUNTER, json.dumps({"next": max(nums) + 1}) + "\n")


def ledger_path(rid: str) -> str:
    return f"{APPLIED}/{rid}.ledger.json"


def read_ledger(unit: Unit, rid: str) -> dict | None:
    text = unit.store.read(ledger_path(rid))
    return json.loads(text) if text else None


def write_ledger(unit: Unit, led: dict) -> None:
    unit.store.write(ledger_path(led["id"]), json.dumps(led, indent=1, ensure_ascii=False) + "\n")


def _unit_for(where: str, unit: Unit, top: Unit | None) -> Unit:
    return unit if where == "self" else top


def _run_effects(led: dict, unit: Unit, top: Unit | None) -> None:
    for eff in led["effects"]:
        check_effect_path(eff["path"], eff.get("unit", "self"))
        u = _unit_for(eff.get("unit", "self"), unit, top)
        cur = u.store.read(eff["path"])
        if sha_or_none(cur) == eff["after_sha"]:
            continue                                   # already in place (a resumed run)
        if sha_or_none(cur) != eff["before_sha"]:
            raise StoreError(f"{eff['path']} changed while the return was being applied")
        if eff["after"] is None:
            eff["retired_to"] = retire(u, eff["path"])
        else:
            v = write_versioned(u, eff["path"], eff["after"])
            if v:
                eff["version"] = v


# ----------------------------------------------------------------------------- entry --

def apply_file(unit: Unit, entry: Entry, *, top: Unit | None = None, now=None, force_settled=False) -> Outcome:
    """Apply one file from the unit's _returns/. Moves it to applied/, failed/, or strays/ (never
    deletes), and raises an agenda item for anything that needs a person."""
    now = now or utcnow()
    name = entry.name
    if entry.native:
        return _set_aside(unit, entry, STRAYS, "saved in a Google format, which Collab Kit never processes; "
                          "save it again as a plain .md file", now, top)
    if not name.lower().endswith((".md", ".txt")):
        return _set_aside(unit, entry, STRAYS, "not a plain .md or .txt file", now, top)
    if entry.size > MAX_RETURN_BYTES:
        return _set_aside(unit, entry, FAILED, f"larger than {MAX_RETURN_BYTES // 1024} KB", now, top)
    if not force_settled and entry.mtime and now.timestamp() - entry.mtime < SETTLE_SECONDS:
        return Outcome("waiting", name, "still settling")
    text = unit.store.read(f"{RETURNS}/{name}") or ""
    try:
        ret = R.parse(text, name)
    except R.ReturnError as e:
        return _set_aside(unit, entry, FAILED, str(e), now, top)
    if not ret.complete:
        age = now.timestamp() - entry.mtime if entry.mtime else 0
        if age < 24 * 3600 and not force_settled:
            return Outcome("waiting", ret.id, "no End. yet (still being written?)")
        return _set_aside(unit, entry, FAILED, "it never ended with 'End.'", now, top)
    if fold(ret.project) != fold(unit.name) and not (unit.top and fold(ret.project) in ("top", "collab kit", "")):
        return _set_aside(unit, entry, STRAYS, f"it is addressed to '{one_line(ret.project, 60)}', not '{unit.name}'", now, top)
    if len(ret.changes) > MAX_CHANGES:
        return _set_aside(unit, entry, FAILED, f"more than {MAX_CHANGES} changes", now, top)
    return apply_return(unit, ret, name, top=top, now=now)


def apply_return(unit: Unit, ret: R.Return, filename: str | None, *, top: Unit | None = None, now=None) -> Outcome:
    now = now or utcnow()
    led = read_ledger(unit, ret.id)
    if led and led.get("state") == "done":
        if filename:
            _archive(unit, filename, ret.id)
        return Outcome("already", ret.id, "applied before; filed away")
    if not led:
        planner = Planner(unit, ret, top, now)
        try:
            effects = planner.plan()
        except Reject as e:
            if filename:
                return _set_aside(unit, Entry(filename, filename, False), FAILED, str(e), now, top)
            return Outcome("failed", ret.id, str(e))
        led = {"id": ret.id, "unit": unit.name, "grammar": R.GRAMMAR, "state": "applying",
               "applied_at": now.isoformat(), "from": planner.sender, "topic": one_line(ret.topic, 200),
               "type": one_line(ret.type, 40), "minted": planner.minted,
               "push_requests": planner.push_requests,
               "undo_of": getattr(planner, "undo_target", None),
               "effects": [{"path": e.path, "unit": e.unit, "before": e.before, "after": e.after,
                            "before_sha": sha_or_none(e.before), "after_sha": sha_or_none(e.after)}
                           for e in effects]}
        write_ledger(unit, led)
    _run_effects(led, unit, top)
    bump_counter(unit, led.get("minted", []))
    led["state"] = "done"
    write_ledger(unit, led)
    if led.get("undo_of"):
        old = read_ledger(unit, led["undo_of"])
        if old:
            old["undone_by"] = ret.id
            write_ledger(unit, old)
    if filename:
        _archive(unit, filename, ret.id)
    status = "undone" if led.get("undo_of") else ("applied" if led["effects"] or led["push_requests"] else "recorded")
    return Outcome(status, ret.id, f"{len(led['effects'])} file(s) changed", led["minted"], led["push_requests"])


def unique_dest(unit: Unit, folder: str, name: str) -> str:
    dst = f"{folder}/{name}"
    n = 1
    while unit.store.exists(dst):
        n += 1
        dst = f"{folder}/{stamp()}-{n}-{name}"
    return dst


def _archive(unit: Unit, filename: str, rid: str) -> None:
    src = f"{RETURNS}/{filename}"
    if not unit.store.exists(src):
        return
    unit.store.mkdir(APPLIED)
    unit.store.move(src, unique_dest(unit, APPLIED, filename))


def _set_aside(unit: Unit, entry: Entry, where: str, why: str, now, top) -> Outcome:
    """Move a return that cannot be applied out of the inbox, and put it on the unit's agenda."""
    name = entry.name
    src = f"{RETURNS}/{name}"
    dst = unique_dest(unit, where, name)
    unit.store.mkdir(where)
    unit.store.move(src, dst)
    label = "could not be filed" if where == FAILED else "was set aside"
    out = raise_item(unit, f"A return {label}: {one_line(name, 60)}",
                     f"The file `{dst}` {label}: {one_line(why, 300)}.\n\nRead it, fix it (or file what it meant "
                     f"again), and move it back into `_returns/`; or settle this item if it should be dropped.",
                     top=top, now=now)
    status = "failed" if where == FAILED else "stray"
    return Outcome(status, name, why, out.minted)


def raise_item(unit: Unit, title: str, needed: str, *, top: Unit | None = None, now=None, importance: int = 2) -> Outcome:
    """The back end puts something on a unit's agenda (through a return of its own, with a ledger)."""
    now = now or utcnow()
    rid = f"{stamp(now)}-backend-{slug(title, 40)}-{sha(title + now.isoformat())[:6]}"
    body = f"## What's needed\n{needed}\n\n## Done when\nSomeone has looked at it and settled this item.\n"
    ret = R.Return(rid, unit.name, {"from": "the back end", "topic": title}, [
        R.Change("new-item", 0, args={"title": title, "kind": "task", "importance": importance}, body=body)],
        True, True, "")
    return apply_return(unit, ret, None, top=top, now=now)


def heal_duplicates(unit: Unit) -> list[tuple[str, str]]:
    """Two files with one item number (two conversations took the same number at the same time):
    the older file keeps it; each later one takes the next free number, with a log line saying so,
    and its old file goes to _versions/ (DESIGN-0.5 section 16, level 1)."""
    from .unit import ITEM_FILE_RE
    files = [e for e in unit.store.files(AGENDA) if ITEM_FILE_RE.match(e.name)]
    by_num: dict[int, list] = {}
    for e in files:
        by_num.setdefault(int(ITEM_FILE_RE.match(e.name).group(1)), []).append(e)
    healed = []
    alias = re.compile(r" \(\d{1,3}\)(?=\.[^.]+$)")
    for num, group in sorted(by_num.items()):
        if len(group) < 2:
            continue
        group.sort(key=lambda e: (e.mtime, e.name))
        # The same file twice (Drive for desktop's "name (1).md" while a conversation edits by
        # versioning): the newer is current, the older goes to _versions/. Not two items.
        same: dict[str, list] = {}
        for e in group:
            same.setdefault(alias.sub("", e.name), []).append(e)
        group = []
        for copies in same.values():
            copies.sort(key=lambda e: e.mtime)
            for old in copies[:-1]:
                retire(unit, f"{AGENDA}/{old.name}")
            group.append(copies[-1])
        group.sort(key=lambda e: (e.mtime, e.name))
        for e in group[1:]:
            used = unit.used_numbers()
            new = max(used) + 1
            old_id, new_id = f"W-{num:03d}", f"W-{new:03d}"
            path = f"{AGENDA}/{e.name}"
            text = unit.store.read(path) or ""
            fields, raw, body = split_front_matter(text)
            item = Item(old_id, num, path, fields, raw, body, text)
            fixed = edit_item_text(item, {"id": new_id},
                                   f"renumbered from {old_id}: another item took that number at the same time")
            new_path = f"{AGENDA}/{new_id}{alias.sub('', e.name)[len(old_id):]}"
            unit.store.write(new_path, fixed)
            retire(unit, path)
            bump_counter(unit, [new_id])
            healed.append((old_id, new_id))
    return healed

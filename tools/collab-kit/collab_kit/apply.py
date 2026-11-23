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
MAX_TITLE = 200                   # an idea's title, when a new-project return carries the idea itself
NO_REPOSITORY = "its Collab Kit folder (no repository)"   # where a project lives when new-project made it
KIT_STATES = ("not set up", "requested", "live")      # the projects list's Collab Kit column
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
        self.check_blocks(ch)
        num = self.next_number()
        wid = f"W-{num:03d}"
        path = f"{AGENDA}/{wid}-{slug(a['title'], 40)}.md"
        text = render_item(wid, a["title"], kind=a.get("kind", "task"), importance=a.get("importance", 3),
                           status=a.get("status", "open"), due=a.get("due", ""), project=a.get("project", ""),
                           body=ch.body, log=[f"created {self.tag()}"], blocks=a.get("blocks", ""))
        self.ov.write(path, text)
        if ch.ref:
            self.handles[ch.ref] = path
        self.minted.append(wid)

    def check_blocks(self, ch: R.Change, own: str = "") -> None:
        """blocks= names an item of this unit (one that exists, or one this return made earlier)."""
        wid = ch.args.get("blocks")
        if not wid:
            return
        if wid == own:
            raise Reject(f"line {ch.line}: an item cannot block itself")
        if wid not in self.minted and not any(i.id == wid for i in self.unit.items()):
            raise Reject(f"line {ch.line}: blocks= names {wid}, and there is no item {wid} in {self.unit.name}")

    def _edit(self, ch: R.Change, fields: dict, log: str) -> Item:
        item = self.resolve(ch)
        self.ov.write(item.path, edit_item_text(item, fields, f"{log} {self.tag()}"))
        return item

    def tell_blocked(self, item: Item, what: str) -> None:
        """A question that blocked an item is closed: write the answer on that item's log too, so the
        session that works on it next finds it there. The text is the person's answer, quoted: data."""
        found = [i for i in self.unit.items() if i.id == item.blocks] if item.blocks else []
        if len(found) != 1 or found[0].path == item.path:
            return
        text = self.ov.read(found[0].path)
        if text is None:
            return
        waiting = _item_from_text(found[0].path, text)
        if waiting.is_open:
            self.ov.write(waiting.path, edit_item_text(
                waiting, {}, f"{item.id} (\"{one_line(item.title, 80)}\"), which this item waited on, {what} {self.tag()}"))

    def op_set(self, ch: R.Change):
        if self.unit.top is False and ch.args.get("project") not in (None, "", self.unit.name):
            raise Reject(f"line {ch.line}: a project's inbox cannot move items to another project")
        desc = ", ".join(f"{k} to {v if v != '' else '(none)'}" for k, v in ch.args.items())
        if ch.args.get("blocks"):
            self.check_blocks(ch, own=self.resolve(ch).id)
        self._edit(ch, dict(ch.args), f"set {desc}")

    def op_log(self, ch: R.Change):
        text = ch.text or ch.body
        if not text or not text.strip():
            raise Reject(f"line {ch.line}: log needs its text (quoted, or a fenced body)")
        item = self.resolve(ch)
        self.ov.write(item.path, edit_item_text(item, {}, f"{text.strip()} {self.tag()}"))

    def op_settle(self, ch: R.Change):
        item = self._edit(ch, {"status": "settled", "outcome": ch.args["outcome"]}, f"settled: {ch.args['outcome']}")
        self.tell_blocked(item, f"was settled: {ch.args['outcome']}")

    def op_snooze(self, ch: R.Change):
        self._edit(ch, {"snoozed_until": ch.args["until"]}, f"snoozed until {ch.args['until']}")

    def op_withdraw(self, ch: R.Change):
        why = ch.args.get("reason", "")
        item = self._edit(ch, {"status": "dropped"}, f"withdrawn{': ' + why if why else ''}")
        self.tell_blocked(item, f"was dropped{': ' + why if why else ''}")

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
        where = "self" if self.unit.top else "top"       # filed at the top level, the list is its own
        if where == "top" and self.top is None:
            raise Reject(f"line {ch.line}: 'project' changes the top level's project list, which is not reachable here")
        name = ch.ref or ("" if self.unit.top else self.unit.name)
        if not self.unit.top and name != self.unit.name:
            raise Reject(f"line {ch.line}: a project's inbox can only change its own entry")
        if not name:
            raise Reject(f"line {ch.line}: 'project' from the top-level inbox names the project")
        if "collab-kit" in ch.args and ch.args["collab-kit"].strip().lower() not in KIT_STATES:
            raise Reject(f"line {ch.line}: collab-kit= is one of {', '.join(repr(s) for s in KIT_STATES)}")
        path = f"{KNOWLEDGE}/projects.md"              # the one list of projects (the start file has none)
        text = self.ov.read(path, where)
        if text is None or _table_rows(text)[1] is None:
            raise Reject(f"line {ch.line}: the top level has no projects table in knowledge/projects.md")
        if "collab-kit" in ch.args and _col(_table_rows(text)[2], "collab kit", "collab-kit") is None:
            raise Reject(f"line {ch.line}: the projects list has no Collab Kit column to set "
                         "(add one: | Folder | Say | What it is | Where | Status | Collab Kit |)")
        if not has_project_row(text, name):           # a row is added only with what it is: a typo adds nothing
            if not ch.args.get("about", "").strip():
                raise Reject(f"line {ch.line}: no row for '{name}' in the top level's knowledge/projects.md "
                             "(to add one, say what it is: about=\"...\")")
            why = check_project_name(name, set())
            if why:
                raise Reject(f"line {ch.line}: {why}")
            text = add_project_row(text, {"folder": name, "say": ch.args.get("spoken", ""), "what": ch.args["about"],
                                          "home": _cell(ch.args.get("where", "")), "status": "active",
                                          "kit": ch.args.get("collab-kit", "live").strip().lower()})
            self.ov.write(path, text, where)
            return
        new = edit_project_row(text, name, ch.args)   # already as asked is fine (a pass redone after a failed push)
        if new != text:
            self.ov.write(path, new, where)

    def op_new_project(self, ch: R.Change):
        """Start a project from an idea: one already on the top level's agenda (from=W-012, with part
        of its title as a check), or one the return carries itself (its title in quotes, what was
        worked out in a fenced body), so a brainstorm becomes a project in one step (DESIGN-0.5
        section 25)."""
        if not self.unit.top:
            raise Reject(f"line {ch.line}: projects are started only from the top-level inbox")
        a = ch.args
        name = a["name"].strip()
        if ch.check is None:
            raise Reject(f"line {ch.line}: new-project must repeat part of the idea's title in quotes, as a check")
        idea = None
        if a.get("from"):
            idea = self.resolve(R.Change("set", ch.line, ref=a["from"], check=ch.check))
            if idea.kind != "project" or not idea.is_open:
                raise Reject(f"line {ch.line}: {idea.id} is not an open idea of kind project")
            title = idea.title
        else:
            title = " ".join(ch.check.split())
            if not title or len(title) > MAX_TITLE:
                raise Reject(f"line {ch.line}: new-project needs the idea's title in quotes, one line of at most "
                             f"{MAX_TITLE} characters (what was worked out goes in a fenced body under it)")
        taken = existing_projects(self.unit) | listed_repositories(self.unit)
        why = check_project_name(name, taken)
        if why:
            raise Reject(f"line {ch.line}: {why}")
        if recent_new_projects(self.unit, self.now) >= NEW_PROJECTS_PER_DAY:
            raise Reject(f"line {ch.line}: at most {NEW_PROJECTS_PER_DAY} projects start in one day")
        base = f"projects/{name}/collab-kit"
        about = a.get("about") or title
        spoken = a.get("spoken", "")
        from .templates import project_start_file, returns_readme
        self.ov.write(f"{base}/{START}", project_start_file(name, about, spoken, home="cloud"))
        self.ov.write(f"{base}/{RETURNS}/README.md", returns_readme(name))
        self.ov.write(f"{base}/{KNOWLEDGE}/README.md", f"# {name}\n\n{about}\n")
        self.ov.write(f"{base}/{WIP}/README.md", "# WIP\n\nCheckpoint notes between saves. See the top-level start file.\n")
        if idea:
            body = idea.body.split("\n<!-- ", 1)[0]
            first = render_item("W-001", title, kind="work-out", importance=idea.importance, due=idea.due,
                                body=re.sub(r"(?ms)^## Log\s*$.*", "", body).strip() or title,
                                log=[f"carried over from the top level's {idea.id} {self.tag()}"])
        else:
            first = render_item("W-001", title, kind="work-out", body=idea_body(about, ch.body),
                                log=[f"started from a conversation {self.tag()}"])
        self.ov.write(f"{base}/{AGENDA}/W-001-{slug(title, 40)}.md", first)
        if idea:
            self.ov.write(idea.path, edit_item_text(idea, {"status": "settled", "outcome": f"started as project {name}"},
                                                    f"settled: started as project {name} (its W-001) {self.tag()}"))
        else:                                          # no item to settle: the top level's status says it started
            self.ov.write(STATUS_FILE, add_status_entry(
                self.ov.read(STATUS_FILE), self.unit.name, self.sender, f"project {name} started",
                f"Project {name} started: {one_line(about, 200)}. Its first agenda item, W-001, carries the idea.", self.now))
        row = {"folder": name, "say": spoken, "what": about, "home": NO_REPOSITORY,
               "kit": "live", "status": f"active, started {self.now.strftime('%Y-%m-%d')}"}
        text = self.ov.read(f"{KNOWLEDGE}/projects.md")
        if text is not None:
            self.ov.write(f"{KNOWLEDGE}/projects.md", add_project_row(text, row))
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
            if not isinstance(eff.get("before"), (str, type(None))):
                raise Reject(f"line {ch.line}: the ledger of '{target}' is malformed")
            check_effect_path(str(eff.get("path", "")), where, before=eff.get("before"), top_unit=self.unit.top)
            cur = self.ov.read(eff["path"], where)
            if where == "top" and not self.unit.top and not only_own_row(eff.get("before"), cur, self.unit.name):
                raise Reject(f"line {ch.line}: cannot undo '{target}': it would change more of the projects list "
                             f"than {self.unit.name}'s own row")
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


def idea_body(about: str, worked_out: str | None) -> str:
    """The first item of a project started from a conversation. Text with its own `## ` headings is
    kept as written; plain text becomes what is known so far, under what the project is about."""
    text = (worked_out or "").strip()
    if not text:
        return about
    if re.search(r"^## ", text, re.M):
        return text
    return f"## What's needed\n{about}\n\n## What we know so far\n{text}\n\n## Done when\n"


def sha_or_none(text):
    return None if text is None else sha(text)


_PROJECT_PATH = re.compile(r"^projects/[a-z][a-z0-9-]{0,39}/collab-kit/(?:00-START-HERE\.md|(?:agenda|knowledge|_returns|WIP)/.+)$")


def check_effect_path(path: str, where: str, *, before=None, top_unit: bool = False, removes: bool = False) -> None:
    """Every file a ledger names must be one a return could have written. A ledger is a file in the
    shared folder (and, for a repository-homed project, in git), so it is checked like any other text
    from outside before it is trusted:

    - inside the unit's own agenda/ or knowledge/;
    - from a project, at the top level: only knowledge/projects.md (its own row: checked in op_undo);
    - at the top level, a new project's folder: only to create a file there (`before` is None, what
      new-project does) or to take one away again (`removes`, what its undo does), never to change one.

    No return writes a start file, so no ledger may restore one."""
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
    if where == "top" and not top_unit:
        if path == f"{KNOWLEDGE}/projects.md":
            return
        raise Reject(f"a project's ledger names a top-level path other than its row in the projects list: {path!r}")
    if path.startswith((f"{AGENDA}/", f"{KNOWLEDGE}/")):
        return
    if _PROJECT_PATH.match(path) and (before is None or removes):
        return                                           # a new project's files: created, or taken away by its undo
    raise Reject(f"a ledger names a path a return never writes: {path!r}")


def only_own_row(before: str | None, current: str | None, name: str) -> bool:
    """True if two versions of the projects list differ only in lines that name this project."""
    if before is None or current is None:
        return False
    keep = lambda text: [ln for ln in text.splitlines() if f"`{name}`" not in ln]   # noqa: E731
    return keep(before) == keep(current)


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


def _cell(text: str) -> str:
    """A value for a table cell: one line, and no | (which would shift the columns)."""
    return one_line(str(text), 200).replace("|", "/")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _col(cells: list[str], *names: str) -> int | None:
    for n in names:
        for k, c in enumerate(cells):
            if c.startswith(n):
                return k
    return None


def has_project_row(text: str, name: str) -> bool:
    lines, hi, cells, rows = _table_rows(text)
    fcol = _col(cells, "folder")
    return hi is not None and fcol is not None and any(
        fcol < len(_cells(lines[j])) and _cells(lines[j])[fcol].strip("`") == name for j in rows)


def edit_project_row(text: str, name: str, args: dict) -> str:
    lines, hi, cells, rows = _table_rows(text)
    if hi is None:
        return text
    fcol, scol, wcol = _col(cells, "folder"), _col(cells, "say"), _col(cells, "what")
    kcol = _col(cells, "collab kit", "collab-kit")
    for j in rows:
        row = _cells(lines[j])
        if fcol is None or fcol >= len(row) or row[fcol].strip("`") != name:
            continue
        row += [""] * (len(cells) - len(row))          # a row older than a column added later
        if "spoken" in args and scol is not None:
            row[scol] = _cell(", ".join(f"\"{s.strip()}\"" for s in args["spoken"].split(",") if s.strip()))
        if "about" in args and wcol is not None:
            row[wcol] = _cell(args["about"])
        if "collab-kit" in args and kcol is not None:
            row[kcol] = args["collab-kit"].strip().lower()
        hcol = _col(cells, "where", "home", "here")
        if "where" in args and hcol is not None:
            row[hcol] = _cell(args["where"])
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
            vals.append(_cell(", ".join(f"\"{s.strip()}\"" for s in row["say"].split(",") if s.strip())))
        elif c.startswith("what"):
            vals.append(_cell(row["what"]))
        elif c.startswith("home") or c.startswith("here") or c.startswith("where"):
            vals.append(row["home"])
        elif c.startswith("collab kit") or c.startswith("collab-kit"):
            vals.append(row.get("kit", "live"))
        elif c.startswith("status"):
            vals.append(row.get("status", "active"))
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
        try:
            led = json.loads(top.store.read(f"{APPLIED}/{e.name}") or "{}")
        except ValueError:
            continue                                   # not a ledger: it counts for nothing, and stops nothing
        minted = led.get("minted") if isinstance(led, dict) else None
        if any(isinstance(m, str) and m.startswith("project:") for m in (minted if isinstance(minted, list) else [])):
            if str(led.get("applied_at", ""))[:10] == now.date().isoformat():
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
        where = eff.get("unit", "self")
        check_effect_path(eff["path"], where, before=eff.get("before"), top_unit=unit.top,
                          removes=eff.get("after") is None)
        u = _unit_for(where, unit, top)
        cur = u.store.read(eff["path"])
        if where == "top" and not unit.top and not only_own_row(eff.get("after"), cur, unit.name):
            raise StoreError(f"a ledger would change more of the projects list than {unit.name}'s own row")
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

def changed_since_listed(unit: Unit, rel: str, entry: Entry) -> bool:
    """Did the file just read differ from the listing `entry` came from? A store that answers from a
    listing taken earlier (DESIGN-0.5 section 22) downloads a file's current bytes when its copy is
    missing: if those are not what was listed, the file changed since, and its settling starts again."""
    if not getattr(entry, "md5", None):
        return False
    now_e = unit.store.entry(rel)
    return bool(now_e and now_e.md5 and now_e.md5 != entry.md5)


def moved_on(effects: list, unit: Unit, top: Unit | None) -> list[str]:
    """The existing files a plan changes that are no longer what the plan read, each read as it is
    now. A store answering from a listing taken earlier (DESIGN-0.5 section 22) reads as of that
    listing; reading a file afresh also brings the store's copy up to date, so a second plan sees the
    change rather than overwriting it."""
    out = []
    for e in effects:
        if e.before is not None and sha_or_none(_unit_for(e.unit, unit, top).store.read_fresh(e.path)) != sha_or_none(e.before):
            out.append(e.path)
    return out


def apply_file(unit: Unit, entry: Entry, *, top: Unit | None = None, now=None, force_settled=False) -> Outcome:
    """Apply one file from the unit's _returns/. Moves it to applied/, failed/, or strays/ (never
    deletes), and raises an agenda item for anything that needs a person."""
    now = now or utcnow()
    name = entry.name
    if not force_settled and entry.mtime and now.timestamp() - entry.mtime < SETTLE_SECONDS:
        return Outcome("waiting", name, "still settling")          # first: a conversation may still move it
    if entry.native:
        return _set_aside(unit, entry, STRAYS, "saved in a Google format, which Collab Kit never processes; "
                          "save it again as a plain .md file", now, top)
    if not name.lower().endswith((".md", ".txt")):
        return _set_aside(unit, entry, STRAYS, "not a plain .md or .txt file", now, top)
    if entry.size > MAX_RETURN_BYTES:
        return _set_aside(unit, entry, FAILED, f"larger than {MAX_RETURN_BYTES // 1024} KB", now, top)
    text = unit.store.read(f"{RETURNS}/{name}") or ""
    if changed_since_listed(unit, f"{RETURNS}/{name}", entry) and not force_settled:
        return Outcome("waiting", name, "it changed after the folder was listed (still being written?)")
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
        for _ in range(2):                             # a file edited after it was read: plan once more
            planner = Planner(unit, ret, top, now)
            try:
                try:
                    effects = planner.plan()
                except (ValueError, StoreError) as e:  # e.g. an item file whose front matter is broken
                    raise Reject(f"{type(e).__name__}: {e}") from None
            except Reject as e:
                if filename:
                    return _set_aside(unit, Entry(filename, filename, False), FAILED, str(e), now, top)
                return Outcome("failed", ret.id, str(e))
            moved = moved_on(effects, unit, top)
            if not moved:
                break
        else:
            return Outcome("waiting", ret.id, f"{moved[0]} kept changing while this return was applied; it is "
                                              f"applied again on the next pass")
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
    out = raise_item(unit, f"A return {label}",                 # a neutral title: the file's name is outside text
                     f"The file `{one_line(dst, 160)}` {label}: {one_line(why, 300)}.\n\nRead it, fix it (or file what it meant "
                     f"again), and move it back into `_returns/`; or settle this item if it should be dropped.",
                     top=top, now=now)
    status = "failed" if where == FAILED else "stray"
    return Outcome(status, name, why, out.minted)


def raise_item(unit: Unit, title: str, needed: str, *, top: Unit | None = None, now=None, importance: int = 1) -> Outcome:
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
            new = max(max(used) + 1, read_counter(unit))
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

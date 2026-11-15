"""The back end: one pass, run on a schedule by one runner at a time. Scripts only, no AI.

    lease        _backend/lease.json in the Collab Kit folder: any other runner exits.
    top level    apply its inbox (new projects are created here).
    each project home = cloud: apply its inbox in the folder (versioning by name).
                 home = repo:  pull the back end's own clone; bring the cloud inbox in; apply it
                               (and any returns that arrived through the repository); build the
                               knowledge if the project has the 0.4 knowledge build; commit
                               collab-kit/ only; push it (the standing authorization covers
                               collab-kit/ only, and only to a private repository unless the
                               project says otherwise); mirror knowledge/, agenda/, and the start
                               file to the cloud (copy, never sync; an edit made in the cloud is
                               saved as a return before it is overwritten).
    views        agenda/00-PRESSING.md at the top level (every unit, deadlines first); the top-level
                 start file's health and due-soon blocks (rewritten only when they change).
    heartbeat    _backend/heartbeat.json: when it ran, what failed.

Config (TOML, `ck backend run --config FILE`; default <config dir>/backend.toml):

    [backend]
    cloud = "rclone:gdrive:Collab Kit"   # or a folder path
    work = "~/.local/share/collab-kit/backend"   # the back end's own clones (never inside ~/dev or the cloud folder)
    interval_minutes = 60
    human = "Sam"
    local_roots = ["~/dev", "~/projects"]  # folder names there count as taken project names
    deny = ["secret-codename"]            # never push a diff that mentions these (regexes)

    [[project]]                           # only projects whose home is a repository
    name = "garden-planner"
    repo = "git@github.com:sam/garden-planner.git"   # or a local path
    branch = "main"
    push = true
    allow_public = false                  # push collab-kit/ to a public repository only if true
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

from . import config as C
from .apply import Outcome, apply_file
from .store import FolderStore, Store, StoreError, SubStore, open_store
from .templates import get_block, replace_block, set_human
from .text import one_line, sha, stamp, utcnow
from .unit import AGENDA, KNOWLEDGE, RETURNS, START, VERSIONS, Unit, write_versioned

LEASE = "_backend/lease.json"
HEARTBEAT = "_backend/heartbeat.json"
MIRROR_STATE = "_backend/mirror"
PRESSING = f"{AGENDA}/00-PRESSING.md"


class Problem(Exception):
    pass


def git(cwd: Path, *args, check=True, timeout=300) -> str:
    res = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8",
                         errors="replace", timeout=timeout)
    if check and res.returncode != 0:
        raise Problem(f"git {' '.join(args[:2])} failed in {cwd.name}: {res.stderr.strip()[:300]}")
    return res.stdout


# ------------------------------------------------------------------------------ lease --

def take_lease(cloud: Store, me: str, minutes: int) -> bool:
    now = utcnow()
    raw = cloud.read(LEASE)
    if raw:
        try:
            cur = json.loads(raw)
            if cur.get("holder") != me and dt.datetime.fromisoformat(cur["expires"]) > now:
                return False
        except (ValueError, KeyError):
            pass
    cloud.write(LEASE, json.dumps({"holder": me, "expires": (now + dt.timedelta(minutes=minutes)).isoformat(),
                                   "taken": now.isoformat()}))
    try:
        return json.loads(cloud.read(LEASE) or "{}").get("holder") == me
    except ValueError:
        return False


def drop_lease(cloud: Store, me: str) -> None:
    try:
        cur = json.loads(cloud.read(LEASE) or "{}")
        if cur.get("holder") == me:
            cur["expires"] = utcnow().isoformat()
            cloud.write(LEASE, json.dumps(cur))
    except (ValueError, StoreError):
        pass


# ----------------------------------------------------------------------- one pass --

class Pass:
    def __init__(self, cfg: dict, dry_run: bool = False):
        b = cfg.get("backend", {})
        self.cfg = cfg
        self.cloud = open_store(C.expand(b["cloud"]))
        self.work = Path(C.expand(b.get("work", str(C.state_dir().parent / "backend"))))
        self.interval = int(b.get("interval_minutes", 60))
        self.human = b.get("human", "the owner")
        self.local_roots = [Path(C.expand(p)) for p in b.get("local_roots", [])]
        self.deny = [re.compile(x, re.I) for x in b.get("deny", [])]
        self.repos = {p["name"]: p for p in cfg.get("project", [])}
        self.me = f"{socket.gethostname()}:{os.getpid()}"
        self.dry = dry_run
        self.problems: list[str] = []
        self.log: list[str] = []
        self.top = Unit(self.cloud, "top", home="cloud", top=True)
        set_human(self.human)

    def note(self, msg: str) -> None:
        self.log.append(msg)

    def problem(self, msg: str) -> None:
        self.problems.append(one_line(msg, 300))

    # ---- inboxes
    def apply_inbox(self, unit: Unit, top: Unit | None) -> list[Outcome]:
        outs = []
        for e in unit.pending_returns():
            if self.dry:
                self.note(f"would apply {unit.name}/{e.name}")
                continue
            try:
                out = apply_file(unit, e, top=top)
            except (StoreError, OSError) as ex:
                self.problem(f"{unit.name}: {e.name}: {ex}")
                continue
            outs.append(out)
            self.note(f"{unit.name}: {out.status} {out.rid} {out.message}")
            if out.status in ("failed", "stray"):
                self.problem(f"{unit.name}: a return {('could not be filed' if out.status == 'failed' else 'was set aside')}: "
                             f"{e.name} ({out.message})")
        return outs

    # ---- repositories
    def clone(self, spec: dict) -> Path:
        d = self.work / spec["name"]
        if not (d / ".git").is_dir():
            self.work.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "-q", "--branch", spec.get("branch", "main"), C.expand(spec["repo"]), str(d)],
                           check=True, capture_output=True, timeout=600)
        git(d, "fetch", "-q", "origin")
        git(d, "checkout", "-q", spec.get("branch", "main"))
        git(d, "merge", "-q", "--ff-only", f"origin/{spec.get('branch', 'main')}")
        return d

    def repo_project(self, name: str, spec: dict) -> None:
        d = self.clone(spec)
        repo_unit = Unit(FolderStore(d / "collab-kit"), name, home="repo")
        cloud_unit = Unit(SubStore(self.cloud, f"projects/{name}/collab-kit"), name, home="repo")
        # bring the cloud inbox in
        from_cloud: set[str] = set()
        for e in cloud_unit.pending_returns():
            text = cloud_unit.read(f"{RETURNS}/{e.name}")
            if text is None:
                continue
            dest = d / "collab-kit" / RETURNS / e.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_text(text, encoding="utf-8")
                os.utime(dest, (e.mtime or 0, e.mtime or 0))
                from_cloud.add(e.name)
            out = apply_file(repo_unit, repo_unit.store.entry(f"{RETURNS}/{e.name}"), top=self.top)
            if out.status == "waiting":
                dest.unlink(missing_ok=True)          # our own clone; it comes in on a later pass
                continue
            folder = {"failed": "failed", "stray": "strays"}.get(out.status, "applied")
            cloud_unit.store.mkdir(f"{RETURNS}/{folder}")
            target = f"{RETURNS}/{folder}/{e.name}"
            if cloud_unit.store.exists(target):
                target = f"{RETURNS}/{folder}/{stamp()}-{e.name}"
            cloud_unit.store.move(f"{RETURNS}/{e.name}", target)
            self.note(f"{name}: {out.status} {out.rid}")
            if out.status in ("failed", "stray"):
                self.problem(f"{name}: a return could not be filed: {e.name} ({out.message})")
        # returns that came in through the repository (merged with someone's work)
        self.apply_inbox(repo_unit, self.top)
        if not spec.get("returns_in_git", False):
            # Returns from the cloud keep their text there (_returns/applied/ etc.); the repository
            # gets only their ledgers. Returns that arrived through the repository stay as they came.
            for p in (d / "collab-kit" / RETURNS).rglob("*"):
                if p.is_file() and p.name in from_cloud and not git(d, "ls-files", "--", str(p), check=False).strip():
                    p.unlink()
        # the 0.4 knowledge build, when the project has it
        if (d / "tools" / "kb" / "kb.py").is_file():
            res = subprocess.run([sys.executable, "tools/kb/kb.py", "build"], cwd=d, capture_output=True, text=True, timeout=600)
            if res.returncode != 0:
                self.problem(f"{name}: the knowledge build failed: {res.stderr.strip()[:200]}")
        self.commit_and_push(name, spec, d)
        self.mirror(name, d / "collab-kit", cloud_unit)

    def commit_and_push(self, name: str, spec: dict, d: Path) -> None:
        git(d, "add", "-A", "--", "collab-kit")
        if not git(d, "diff", "--cached", "--name-only").strip():
            return
        others = [p for p in git(d, "diff", "--cached", "--name-only").split() if not p.startswith("collab-kit/")]
        if others:
            git(d, "reset", "-q")
            raise Problem(f"{name}: refusing to commit outside collab-kit/: {others[:3]}")
        git(d, "-c", "user.name=Collab Kit back end", "-c", "user.email=collab-kit@users.noreply.github.com",
            "commit", "-q", "-m", f"collab-kit: apply returns ({utcnow().strftime('%Y-%m-%d %H:%M')} UTC)")
        if not spec.get("push", False):
            return
        diff = git(d, "show", "--format=", "HEAD")
        for rx in self.deny:
            if rx.search(diff):
                raise Problem(f"{name}: not pushed: the change mentions a denied word ({rx.pattern})")
        if not spec.get("allow_public", False) and self.is_public(spec):
            raise Problem(f"{name}: not pushed: the repository is public and allow_public is not set")
        git(d, "push", "-q", "origin", f"HEAD:{spec.get('branch', 'main')}")

    def is_public(self, spec: dict) -> bool:
        m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", spec.get("repo", ""))
        if not m:
            return False
        try:
            res = subprocess.run(["gh", "repo", "view", m.group(1), "--json", "visibility", "-q", ".visibility"],
                                 capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return True                                 # unknown: treat as public
        return res.returncode != 0 or res.stdout.strip().upper() != "PRIVATE"

    def mirror(self, name: str, src: Path, cloud_unit: Unit) -> None:
        """Copy the repository's channels out. Never sync, never delete: a file the repository no
        longer has is moved to _versions/ in the cloud; a cloud file edited since the last copy is
        saved as a return first."""
        state_path = f"{MIRROR_STATE}/{name}.json"
        try:
            written = json.loads(self.cloud.read(state_path) or "{}")
        except ValueError:
            written = {}
        want: dict[str, str] = {}
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src).as_posix()
            if not p.is_file() or not (rel == START or rel.startswith((f"{KNOWLEDGE}/", f"{AGENDA}/"))):
                continue
            if f"/{VERSIONS}/" in f"/{rel}" or any(part.startswith(".") for part in rel.split("/")):
                continue
            want[rel] = p.read_text(encoding="utf-8", errors="replace")
        new_state = {}
        for rel, text in want.items():
            cur = cloud_unit.store.read(rel)
            if cur is not None and cur != text and sha(cur) != written.get(rel):
                self.save_cloud_edit(name, rel, cur, cloud_unit)
            if cur != text:
                cloud_unit.store.write(rel, text)
            new_state[rel] = sha(text)
        for rel, h in written.items():
            if rel not in want and cloud_unit.store.exists(rel):
                cur = cloud_unit.store.read(rel)
                if cur is not None and sha(cur) != h:
                    self.save_cloud_edit(name, rel, cur, cloud_unit)
                folder, _, base = rel.rpartition("/")
                dst = f"{folder}/{VERSIONS}/{base}" if folder else f"{VERSIONS}/{base}"
                if cloud_unit.store.exists(dst):
                    dst = dst.replace(base, f"{stamp()}-{base}")
                cloud_unit.store.move(rel, dst)
        self.cloud.write(state_path, json.dumps(new_state, indent=0, sort_keys=True))

    def save_cloud_edit(self, name: str, rel: str, text: str, cloud_unit: Unit) -> None:
        rid = f"{stamp()}-edited-in-the-folder-{re.sub(r'[^a-z0-9]+', '-', rel.lower())[:40]}"
        body = "\n".join("  " + line for line in text.splitlines())
        ret = (f"Project: {name}\nId: {rid}\nFrom: the back end\nType: note\n"
               f"Topic: {rel} was edited in the Collab Kit folder, where it is a copy; this saves that version\n"
               f"What was worked out: the repository's version replaced it. The edited text follows; "
               f"file what it meant as changes if it is still wanted.\nVerbatim:\n{body}\nEnd.\n")
        cloud_unit.store.write(f"{RETURNS}/{rid}.md", ret)
        self.problem(f"{name}: {rel} was edited in the folder (a copy); saved as a return and replaced")

    # ---- views
    def all_units(self) -> list[tuple[str, Unit]]:
        """The top level, then every project: each folder with a collab-kit/ in the cloud, and every
        repository-homed project in the config (its cloud copy is created by the first mirror)."""
        out = [("top", self.top)]
        names = {e.name for e in self.cloud.dirs("projects") if self.cloud.exists(f"projects/{e.name}/collab-kit")}
        for name in sorted(names | set(self.repos)):
            home = "repo" if name in self.repos else "cloud"
            out.append((name, Unit(SubStore(self.cloud, f"projects/{name}/collab-kit"), name, home=home)))
        return out

    def views(self) -> None:
        today = utcnow().date()
        inactive = self.inactive_projects()
        rows = []
        for name, unit in self.all_units():
            for it in unit.items():
                if not it.is_open:
                    continue
                if str(it.fields.get("snoozed_until", "")) > today.isoformat():
                    continue
                rows.append((name, it))

        def due(it):
            try:
                return dt.date.fromisoformat(it.due)
            except ValueError:
                return None
        dated = sorted((r for r in rows if due(r[1]) and due(r[1]) <= today + dt.timedelta(days=14)),
                       key=lambda r: due(r[1]))
        busy = [r for r in rows if r not in dated and r[1].status == "in-progress" and r[0] not in inactive]
        top = sorted((r for r in rows if r not in dated and r not in busy and r[1].importance <= 2 and r[0] not in inactive),
                     key=lambda r: (r[1].importance, r[0], r[1].num))

        def line(r):
            name, it = r
            where = "top level" if name == "top" else name
            d = f"due {it.due}{' (OVERDUE)' if due(it) and due(it) < today else ''}; " if it.due else ""
            return f"- **{one_line(it.title, 100)}** ({where} {it.id}; {d}{it.kind}, importance {it.importance})"
        parts = [f"# What is pressing, across everything\n\nGenerated by the back end on {today.isoformat()} from every "
                 f"agenda; never edit it (change items with returns). Deadlines first, then work in progress, "
                 f"then the most important open items. Read the top three or four aloud, then say how many more.\n"]
        if dated:
            parts.append("## Due in the next two weeks\n\n" + "\n".join(line(r) for r in dated) + "\n")
        if busy:
            parts.append("## In progress\n\n" + "\n".join(line(r) for r in busy[:15]) + "\n")
        if top:
            parts.append("## Most important open\n\n" + "\n".join(line(r) for r in top[:15])
                         + (f"\n- ... and {len(top) - 15} more" if len(top) > 15 else "") + "\n")
        if inactive:
            counts = {n: sum(1 for r in rows if r[0] == n) for n in inactive}
            parts.append("## Inactive projects\n\n" + "\n".join(f"- {n}: {c} open item(s)" for n, c in sorted(counts.items())) + "\n")
        if not (dated or busy or top):
            parts.append("Nothing is due, in progress, or marked most important.\n")
        if not self.dry:
            self.write_if_changed(self.top, PRESSING, "\n".join(parts))
            self.start_file_blocks(dated, today, due)

    def inactive_projects(self) -> set[str]:
        text = self.cloud.read(f"{KNOWLEDGE}/projects.md") or ""
        return {m.group(1) for m in re.finditer(r"^\|\s*`([a-z0-9-]+)`\s*\|.*\(inactive\)", text, re.M)}

    def write_if_changed(self, unit: Unit, rel: str, text: str) -> None:
        if unit.store.read(rel) != text:
            write_versioned(unit, rel, text)

    def start_file_blocks(self, dated, today, due) -> None:
        text = self.cloud.read(START)
        if not text:
            return
        soon = [r for r in dated if due(r[1]) <= today + dt.timedelta(days=7)]
        due_md = "\n".join(f"- {r[1].due}: {one_line(r[1].title, 100)} ({'top level' if r[0] == 'top' else r[0]} {r[1].id})"
                           for r in soon) or "Nothing due in the next week."
        when = today.isoformat()
        if self.problems:
            probs = "\n".join(f"  - {p}" for p in self.problems[:8])
            health = (f"**A back end runs for this folder** (every {self.interval} minutes; checked {when}). **File "
                      f"returns; do not edit agendas or knowledge yourself**: it applies them.\n\n**Raise these with "
                      f"{self.human} first (the back end could not handle them):**\n{probs}")
        else:
            health = (f"**A back end runs for this folder** (every {self.interval} minutes; healthy on {when}). **File "
                      f"returns; do not edit agendas or knowledge yourself**: it applies them, usually within the "
                      f"hour, and reports anything it could not file on the agenda. If this date is more than a day "
                      f"old, the back end has stopped: tell {self.human}.\n\nWhat is pressing across every project: "
                      f"`agenda/00-PRESSING.md`.")
        new = text
        for name, body in (("health", health), ("due", due_md)):
            out = replace_block(new, name, body)
            if out is not None:
                new = out
            elif get_block(new, name) is None and name == "health":
                self.problem("the top-level start file has no health block; add <!-- collab-kit:begin health --> markers")
        if new != text:
            write_versioned(self.top, START, new)

    def repositories(self) -> None:
        """knowledge/repositories.md: every name already taken (GitHub, and local project folders)."""
        names: dict[str, str] = {}
        try:
            res = subprocess.run(["gh", "repo", "list", "--limit", "500", "--json", "name,visibility"],
                                 capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                for r in json.loads(res.stdout):
                    names[r["name"]] = f"GitHub, {r['visibility'].lower()}"
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        for root in self.local_roots:
            if root.is_dir():
                for d in root.iterdir():
                    if d.is_dir() and not d.name.startswith("."):
                        names.setdefault(d.name, f"folder in {root.name}")
        if not names:
            return
        body = ("# Names already taken\n\nGenerated by the back end; a new project's name must differ from "
                "every name here (compared without case).\n\n| Name | Where |\n|---|---|\n"
                + "\n".join(f"| `{n}` | {w} |" for n, w in sorted(names.items(), key=lambda x: x[0].lower())) + "\n")
        if not self.dry:
            self.write_if_changed(self.top, f"{KNOWLEDGE}/repositories.md", body)

    # ---- the pass
    def run(self) -> int:
        if not self.dry and not take_lease(self.cloud, self.me, max(self.interval - 5, 10)):
            print("collab-kit back end: another runner holds the lease; exiting")
            return 0
        try:
            try:
                self.repositories()
                self.apply_inbox(self.top, None)
                for name, unit in self.all_units()[1:]:
                    try:
                        if name in self.repos:
                            if not self.dry:
                                self.repo_project(name, self.repos[name])
                        else:
                            self.apply_inbox(unit, self.top)
                    except (Problem, StoreError, OSError, subprocess.SubprocessError) as ex:
                        self.problem(f"{name}: {ex}")
                self.views()
            except (StoreError, OSError) as ex:
                self.problem(f"the pass stopped: {ex}")
            if not self.dry:
                self.cloud.write(HEARTBEAT, json.dumps({
                    "last_run": utcnow().isoformat(), "interval_minutes": self.interval, "host": socket.gethostname(),
                    "problems": self.problems, "applied": len(self.log)}, indent=1))
        finally:
            if not self.dry:
                drop_lease(self.cloud, self.me)
        for line in self.log:
            print(line)
        for p in self.problems:
            print(f"PROBLEM: {p}")
        return 1 if self.problems else 0


def load_config(path: str | None) -> dict:
    p = Path(C.expand(path)) if path else C.config_dir() / "backend.toml"
    cfg = C.load_toml(p)
    if not cfg.get("backend", {}).get("cloud"):
        raise SystemExit(f"collab-kit back end: no [backend].cloud in {p}")
    return cfg


def run(path: str | None, once: bool = True, dry_run: bool = False) -> int:
    return Pass(load_config(path), dry_run=dry_run).run()

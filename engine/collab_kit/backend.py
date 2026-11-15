"""The back end: one pass, run on a schedule by one runner at a time. Scripts only, no AI.

    account      every run first checks the folder belongs to the configured Google account.
    lease        _backend/lease.json in the Collab Kit folder (written, settled, read back, renewed
                 per unit): any other runner exits.
    top level    apply its inbox (new projects are created here).
    each project home = cloud: apply its inbox in the folder (versioning by name).
                 home = repo:  start the back end's own clone from the remote's state; bring the
                               cloud inbox in one return at a time, one commit per return; apply
                               returns that arrived through the repository; build the knowledge
                               (the 0.4 knowledge build, if the project has it); before any push,
                               check every unpushed commit (collab-kit/ only; nothing on the
                               deny-list; a private repository unless the project allows public);
                               push; only then file the cloud returns away and mirror the
                               repository's channels to the cloud (copy, never sync, by hash; a
                               cloud edit to a copy is saved first; the first mirror keeps what it
                               replaces).
    views        agenda/00-PRESSING.md at the top level (every unit, deadlines first); the top-level
                 start file's health and due-soon blocks (rewritten only when they change).
    heartbeat    _backend/heartbeat.json: when it ran, what failed. Written whatever happened.

If a push fails, nothing is lost: the cloud returns stay in the inbox and the next pass starts again
from the remote and applies them again. Problems are recomputed every pass, so a standing problem is
reported until it is gone.

Config (TOML, `ck backend run --config FILE`; default <config dir>/backend.toml):

    [backend]
    cloud = "rclone:gdrive:Collab Kit"   # or a folder path
    work = "~/.local/share/collab-kit/backend"   # the back end's own clones (never inside ~/dev or the cloud folder)
    interval_minutes = 60
    human = "Sam"
    account = "sam@example.com"           # the Google account the folder must belong to (checked every run)
    local_roots = ["~/dev", "~/projects"]  # folder names there count as taken project names
    deny = ["secret-codename"]            # never push a change that contains these (regexes)
    lease_settle_seconds = 20             # wait before trusting the lease (a synced folder is eventually consistent)

    [[project]]                           # only projects whose home is a repository
    name = "garden-planner"
    repo = "git@github.com:sam/garden-planner.git"   # or a local path
    branch = "main"
    push = true
    allow_public = false                  # push collab-kit/ to a public repository only if true
    returns_in_git = false                # keep the text of returns from the cloud out of git
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
import tempfile
import time
from pathlib import Path

from . import config as C
from .apply import Outcome, apply_file, heal_duplicates, raise_item
from .store import FolderStore, Store, StoreError, SubStore, open_store
from .templates import get_block, replace_block, set_human
from .text import one_line, sha, stamp, utcnow
from .unit import AGENDA, APPLIED, FAILED, KNOWLEDGE, RETURNS, START, STRAYS, VERSIONS, Unit, write_versioned

LEASE = "_backend/lease.json"
HEARTBEAT = "_backend/heartbeat.json"
MIRROR_STATE = "_backend/mirror"
PRESSING = f"{AGENDA}/00-PRESSING.md"
TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json", ".html", ".toml", ".tsv", ".svg", ".yml", ".yaml"}
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}


class Problem(Exception):
    pass


def git(cwd: Path, *args, check=True, timeout=300) -> str:
    res = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8",
                         errors="replace", timeout=timeout, env={**os.environ, **GIT_ENV})
    if check and res.returncode != 0:
        raise Problem(f"git {' '.join(args[:2])} failed in {cwd.name}: {res.stderr.strip()[:300]}")
    return res.stdout


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# ------------------------------------------------------------------------------ lease --

def take_lease(cloud: Store, me: str, minutes: int, settle: float = 0) -> bool:
    """Write the lease, wait for a synced folder to settle, and read it back: the runner whose name
    is there owns this pass."""
    now = utcnow()
    raw = cloud.read(LEASE)
    if raw:
        try:
            cur = json.loads(raw)
            if cur.get("holder") != me and dt.datetime.fromisoformat(cur["expires"]) > now:
                return False
        except (ValueError, KeyError, TypeError):
            pass
    write_lease(cloud, me, minutes)
    if settle:
        time.sleep(settle)
    try:
        return json.loads(cloud.read(LEASE) or "{}").get("holder") == me
    except ValueError:
        return False


def write_lease(cloud: Store, me: str, minutes: int) -> None:
    now = utcnow()
    cloud.write(LEASE, json.dumps({"holder": me, "expires": (now + dt.timedelta(minutes=minutes)).isoformat(),
                                   "renewed": now.isoformat()}))


def drop_lease(cloud: Store, me: str) -> None:
    try:
        cur = json.loads(cloud.read(LEASE) or "{}")
        if cur.get("holder") == me:
            cur["expires"] = utcnow().isoformat()
            cloud.write(LEASE, json.dumps(cur))
    except (ValueError, StoreError, OSError):
        pass


def walk(store: Store, prefix: str) -> dict[str, str | None]:
    """{relative path: md5} for every file under prefix, skipping _versions/ and hidden names."""
    out: dict[str, str | None] = {}
    entries = store.list(prefix)
    sums = None
    for e in entries:
        if e.name.startswith(".") or e.name == VERSIONS:
            continue
        rel = f"{prefix}/{e.name}"
        if e.is_dir:
            out.update(walk(store, rel))
        else:
            h = getattr(e, "md5", None)
            if h is None:
                sums = sums if sums is not None else store.md5s(prefix)
                h = sums.get(e.name)
            out[rel] = h
    return out


# ----------------------------------------------------------------------- one pass --

class Pass:
    def __init__(self, cfg: dict, dry_run: bool = False):
        b = cfg.get("backend", {})
        self.cfg = cfg
        self.cloud_spec = C.expand(b["cloud"])
        self.cloud = open_store(self.cloud_spec)
        self.work = Path(C.expand(b.get("work", str(C.state_dir().parent / "backend"))))
        self.interval = int(b.get("interval_minutes", 60))
        self.human = b.get("human", "the owner")
        self.account = b.get("account", "")
        self.local_roots = [Path(C.expand(p)) for p in b.get("local_roots", [])]
        self.deny = [re.compile(x, re.I) for x in b.get("deny", [])]
        self.settle = float(b.get("lease_settle_seconds", 20 if self.cloud_spec.startswith("rclone:") else 2))
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

    def renew(self) -> None:
        if not self.dry:
            write_lease(self.cloud, self.me, max(self.interval - 5, 10))

    # ---- inboxes
    def apply_inbox(self, unit: Unit, top: Unit | None) -> list[Outcome]:
        outs = []
        if not self.dry:
            for old, new in heal_duplicates(unit):
                self.note(f"{unit.name}: two items had {old}; the later one is now {new}")
        for e in unit.pending_returns():
            if self.dry:
                self.note(f"would apply {unit.name}/{e.name}")
                continue
            try:
                out = apply_file(unit, e, top=top)
            except Exception as ex:                  # noqa: BLE001 (one bad file never stops the pass)
                self.problem(f"{unit.name}: {e.name}: {type(ex).__name__}: {ex}")
                continue
            outs.append(out)
            self.note(f"{unit.name}: {out.status} {out.rid} {out.message}")
            if out.status in ("failed", "stray"):
                self.problem(f"{unit.name}: a return {('could not be filed' if out.status == 'failed' else 'was set aside')}: "
                             f"{e.name} ({out.message})")
            elif out.status == "waiting" and "End." in out.message:
                self.problem(f"{unit.name}: {e.name} is not finished yet (no End.)")
        return outs

    # ---- repositories
    def sync_clone(self, spec: dict) -> Path:
        """The back end's own clone, at the remote's state. With pushing on, any local commit not on
        the remote is dropped: its returns are still in the cloud inbox and are applied again."""
        d = self.work / spec["name"]
        branch = spec.get("branch", "main")
        if not (d / ".git").is_dir():
            self.work.mkdir(parents=True, exist_ok=True)
            res = subprocess.run(["git", "clone", "-q", "--branch", branch, C.expand(spec["repo"]), str(d)],
                                 capture_output=True, text=True, timeout=600, env={**os.environ, **GIT_ENV})
            if res.returncode != 0:
                raise Problem(f"cannot clone {spec['name']}: {res.stderr.strip()[:200]}")
        git(d, "fetch", "-q", "origin")
        if git(d, "branch", "--show-current").strip() != branch:
            git(d, "checkout", "-q", branch)
        if spec.get("push", False):
            git(d, "reset", "-q", "--hard", f"origin/{branch}")
        else:
            git(d, "reset", "-q", "--hard", "HEAD")
            res = subprocess.run(["git", "-C", str(d), "merge", "-q", "--ff-only", f"origin/{branch}"],
                                 capture_output=True, text=True, env={**os.environ, **GIT_ENV})
            if res.returncode != 0:
                raise Problem(f"{spec['name']}: the back end's clone (not pushed) and the remote have diverged; "
                              f"merge them by hand in {d}")
        git(d, "clean", "-q", "-fd")
        return d

    def is_ancestor(self, d: Path, commit: str) -> bool:
        return subprocess.run(["git", "-C", str(d), "merge-base", "--is-ancestor", commit, "HEAD"],
                              capture_output=True).returncode == 0

    def commit(self, d: Path, message: str) -> str | None:
        git(d, "add", "-A", "--", "collab-kit")
        staged = git(d, "diff", "--cached", "--name-only").split()
        if not staged:
            return None
        outside = [p for p in staged if not p.startswith("collab-kit/")]
        if outside:
            git(d, "reset", "-q")
            raise Problem(f"refusing to commit outside collab-kit/: {outside[:3]}")
        git(d, "-c", "user.name=Collab Kit back end", "-c", "user.email=collab-kit@users.noreply.github.com",
            "commit", "-q", "-m", message)
        return git(d, "rev-parse", "HEAD").strip()

    def repo_project(self, name: str, spec: dict) -> None:
        d = self.sync_clone(spec)
        branch = spec.get("branch", "main")
        repo_unit = Unit(FolderStore(d / "collab-kit"), name, home="repo")
        cloud_unit = Unit(SubStore(self.cloud, f"projects/{name}/collab-kit"), name, home="repo")
        moves: list[tuple[str, str, str | None]] = []       # (cloud file, where it goes, the commit that applied it)
        for e in cloud_unit.pending_returns():
            if e.native or not e.name.lower().endswith((".md", ".txt")):
                out = raise_item(repo_unit, f"A file was set aside: {one_line(e.name, 60)}",
                                 f"`{e.name}` arrived in the inbox but is not a plain .md or .txt return "
                                 f"(a Google Doc, or another kind of file); it is in `_returns/strays/`.", top=self.top)
                moves.append((e.name, STRAYS, self.commit(d, f"collab-kit: set aside {e.name}")))
                self.problem(f"{name}: {e.name} was set aside (not a plain return)")
                continue
            text = cloud_unit.read(f"{RETURNS}/{e.name}")
            if text is None:
                continue
            dest = d / "collab-kit" / RETURNS / e.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            os.utime(dest, (e.mtime or 0, e.mtime or 0))
            out = apply_file(repo_unit, repo_unit.store.entry(f"{RETURNS}/{e.name}"), top=self.top)
            if out.status == "waiting":
                dest.unlink(missing_ok=True)
                if "End." in out.message:
                    self.problem(f"{name}: {e.name} is not finished yet (no End.)")
                continue
            if not spec.get("returns_in_git", False):
                for p in (d / "collab-kit" / RETURNS).rglob(e.name):
                    if p.is_file():
                        p.unlink()                  # its text stays in the cloud; the ledger goes to git
            where = {"failed": FAILED, "stray": STRAYS}.get(out.status, APPLIED)
            moves.append((e.name, where, self.commit(d, f"collab-kit: {out.status} return {out.rid}")))
            self.note(f"{name}: {out.status} {out.rid}")
            if out.status in ("failed", "stray"):
                self.problem(f"{name}: a return could not be filed: {e.name} ({out.message})")
        for out in self.apply_inbox(repo_unit, self.top):   # returns that came in through the repository
            self.commit(d, f"collab-kit: {out.status} return {out.rid}")
        if (d / "tools" / "kb" / "kb.py").is_file():
            res = subprocess.run([sys.executable, "tools/kb/kb.py", "build"], cwd=d, capture_output=True, text=True,
                                 timeout=600)
            if res.returncode != 0:
                self.problem(f"{name}: the knowledge build failed: {res.stderr.strip()[:200]}")
            else:
                self.commit(d, "collab-kit: rebuild the knowledge")
        unpushed = lambda: git(d, "rev-list", "--count", f"origin/{branch}..HEAD").strip() != "0"  # noqa: E731
        if spec.get("push", False) and unpushed():
            bad = self.guard(name, spec, d, branch)
            if bad:
                sha_, why = bad
                culprit = next((m for m in moves if m[2] == sha_), None)
                git(d, "reset", "-q", "--hard", f"{sha_}^")       # the bad commit and everything after it go
                if culprit:
                    self.move_cloud(cloud_unit, culprit[0], FAILED)
                self.problem(f"{name}: not pushed: {why}" + (f"; the return {culprit[0]} was moved to _returns/failed/"
                                                             if culprit else ""))
                # returns applied after the bad commit stay in the inbox and are applied again next pass
                moves = [m for m in moves if m is not culprit and (m[2] is None or self.is_ancestor(d, m[2]))]
                if unpushed() and (self.guard(name, spec, d, branch) or not self.push(name, d, branch)):
                    return
            elif not self.push(name, d, branch):
                return                                # nothing moves; the next pass redoes it all
        for fname, where, _ in moves:
            self.move_cloud(cloud_unit, fname, where)
        self.mirror(name, d / "collab-kit", cloud_unit)

    def push(self, name: str, d: Path, branch: str) -> bool:
        res = subprocess.run(["git", "-C", str(d), "push", "-q", "origin", f"HEAD:{branch}"], capture_output=True,
                             text=True, timeout=300, env={**os.environ, **GIT_ENV})
        if res.returncode != 0:
            self.problem(f"{name}: the push failed; the returns stay in the inbox and are applied again next pass "
                         f"({res.stderr.strip()[:200]})")
            return False
        return True

    def guard(self, name: str, spec: dict, d: Path, branch: str) -> tuple[str, str] | None:
        """(the first unpushed commit that must not be pushed, why), or None. Checks every commit
        between the remote and HEAD: only collab-kit/ changes, nothing on the deny-list; and the
        repository is private unless the project allows public."""
        if not spec.get("allow_public", False) and self.is_public(d):
            first = git(d, "rev-list", "--reverse", f"origin/{branch}..HEAD").split()[0]
            return first, "the repository is public (or its visibility is unknown) and allow_public is not set"
        for c in git(d, "rev-list", "--reverse", f"origin/{branch}..HEAD").split():
            paths = git(d, "show", "--name-only", "--format=", c).split()
            if any(not p.startswith("collab-kit/") for p in paths):
                return c, f"a commit changes files outside collab-kit/ ({paths[:2]})"
            diff = git(d, "show", "--format=", c)
            for rx in self.deny:
                if rx.search(diff):
                    return c, f"the change contains a denied word ({rx.pattern})"
        return None

    def is_public(self, d: Path) -> bool:
        url = git(d, "remote", "get-url", "origin", check=False).strip()
        if url and (Path(url).expanduser().exists() or url.startswith("file://")):
            return False                               # a local repository: nothing is published
        m = re.match(r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+)/(.+?)(?:\.git)?/?$", url)
        if not m:
            return True                                # an unknown host: treat as public
        try:
            res = subprocess.run(["gh", "repo", "view", f"{m.group(1)}/{m.group(2)}", "--json", "visibility",
                                  "-q", ".visibility"], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return True
        return res.returncode != 0 or res.stdout.strip().upper() != "PRIVATE"

    def move_cloud(self, cloud_unit: Unit, fname: str, where: str) -> None:
        src = f"{RETURNS}/{fname}"
        if not cloud_unit.store.exists(src):
            return
        cloud_unit.store.mkdir(where)
        dst = f"{where}/{fname}"
        n = 1
        while cloud_unit.store.exists(dst):
            n += 1
            dst = f"{where}/{stamp()}-{n}-{fname}"
        cloud_unit.store.move(src, dst)

    # ---- the mirror
    def mirror(self, name: str, src: Path, cloud_unit: Unit) -> None:
        """Copy the repository's channels out by hash. Never sync, never delete."""
        state_path = f"{MIRROR_STATE}/{name}.json"
        raw = self.cloud.read(state_path)
        if raw is None:
            first, written = True, {}
        else:
            try:
                written = {k: (v if isinstance(v, str) else v.get("md5")) for k, v in json.loads(raw).items()}
                first = False
            except (ValueError, AttributeError):
                self.problem(f"{name}: the mirror's state file {state_path} is unreadable; not mirroring until it is "
                             f"fixed (delete it to start again: the next mirror keeps whatever it replaces)")
                return
        want: dict[str, bytes] = {}
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src).as_posix()
            if not p.is_file() or not (rel == START or rel.startswith((f"{KNOWLEDGE}/", f"{AGENDA}/"))):
                continue
            if f"/{VERSIONS}/" in f"/{rel}" or any(part.startswith(".") for part in rel.split("/")):
                continue
            want[rel] = p.read_bytes()
        have = {**walk(cloud_unit.store, KNOWLEDGE), **walk(cloud_unit.store, AGENDA)}
        if cloud_unit.store.exists(START):
            have[START] = cloud_unit.store.md5s("").get(START)
        new_state: dict[str, str] = {}
        for rel, data in want.items():
            local = md5(data)
            new_state[rel] = local
            if rel in have:
                cur = have[rel]
                if cur is None:
                    cur_text = cloud_unit.store.read(rel)
                    cur = md5(cur_text.encode("utf-8")) if cur_text is not None else None
                if cur == local:
                    continue
                if first:
                    self.keep_aside(cloud_unit, rel, f"{VERSIONS}/before-first-mirror/{rel}")
                elif cur != written.get(rel):
                    self.save_cloud_edit(name, rel, cloud_unit)
            self.put(cloud_unit, rel, data)
        for rel, cur in have.items():
            if rel in want:
                continue
            if rel in written:                         # the repository no longer has it
                if cur != written[rel]:
                    self.save_cloud_edit(name, rel, cloud_unit)
                self.keep_aside(cloud_unit, rel, version_path(rel), move=True)
            elif first:
                self.keep_aside(cloud_unit, rel, f"{VERSIONS}/before-first-mirror/{rel}", move=True)
            else:                                      # made in a copy: it belongs in a return
                flat = re.sub(r"[^A-Za-z0-9._-]+", "-", rel)
                self.keep_aside(cloud_unit, rel, f"{STRAYS}/{stamp()}-{flat}", move=True)
                self.problem(f"{name}: {rel} was created in the folder, where it is a copy of the repository; "
                             f"moved to _returns/strays/")
        self.cloud.write(state_path, json.dumps(new_state, indent=0, sort_keys=True))

    def put(self, unit: Unit, rel: str, data: bytes) -> None:
        try:
            unit.store.write(rel, data.decode("utf-8"))
            return
        except UnicodeDecodeError:
            pass
        fd, tmp = tempfile.mkstemp(prefix="collab-kit-mirror-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            unit.store.put_file(tmp, rel)
        finally:
            os.unlink(tmp)

    def keep_aside(self, unit: Unit, rel: str, dst: str, move: bool = False) -> None:
        n = 1
        base = dst
        while unit.store.exists(dst):
            n += 1
            dst = f"{base}.{n}"
        (unit.store.move if move else unit.store.copy)(rel, dst)

    def save_cloud_edit(self, name: str, rel: str, cloud_unit: Unit) -> None:
        """An edit made in the cloud copy of a repository-homed unit: kept as a return (text) or in
        _versions/ (anything else), before the repository's version replaces it."""
        tag = hashlib.sha256(rel.encode()).hexdigest()[:8]
        if Path(rel).suffix.lower() not in TEXT_SUFFIXES:
            self.keep_aside(cloud_unit, rel, f"{VERSIONS}/edited-in-the-folder/{stamp()}-{tag}-{Path(rel).name}")
            self.problem(f"{name}: {rel} was edited in the folder (a copy); the edited file is in _versions/")
            return
        text = cloud_unit.store.read(rel) or ""
        rid = f"{stamp()}-edited-in-the-folder-{tag}-{re.sub(r'[^a-z0-9]+', '-', rel.lower())[:32].strip('-')}"
        body = "\n".join("  " + line for line in text.splitlines())
        ret = (f"Project: {name}\nId: {rid}\nFrom: the back end\nType: note\n"
               f"Topic: {rel} was edited in the Collab Kit folder, where it is a copy; this saves that version\n"
               f"What was worked out: the repository's version replaced it. The edited text follows; file what it "
               f"meant as changes if it is still wanted.\nVerbatim:\n{body}\nEnd.\n")
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
            try:
                items = unit.items()
            except Exception as ex:                  # noqa: BLE001
                self.problem(f"{name}: its agenda could not be read: {ex}")
                continue
            for it in items:
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
            return f"- **{one_line(it.title, 100)}** ({where} {it.id}; {d}{one_line(it.kind, 12)}, importance {it.importance})"
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

    def health_text(self, today) -> str:
        when = today.isoformat()
        if self.problems:
            probs = "\n".join(f"  - {p}" for p in self.problems[:8])
            more = f"\n  - ... and {len(self.problems) - 8} more (in `_backend/heartbeat.json`)" if len(self.problems) > 8 else ""
            return (f"**A back end runs for this folder** (every {self.interval} minutes; checked {when}). **File "
                    f"returns; do not edit agendas or knowledge yourself**: it applies them.\n\n**Raise these with "
                    f"{self.human} first (the back end could not handle them):**\n{probs}{more}")
        return (f"**A back end runs for this folder** (every {self.interval} minutes; healthy on {when}). **File "
                f"returns; do not edit agendas or knowledge yourself**: it applies them, usually within the hour, and "
                f"reports anything it could not file on the agenda. If this date is more than a day old, the back end "
                f"has stopped: tell {self.human} (the exact time of the last run is in `_backend/heartbeat.json`).\n\n"
                f"What is pressing across every project: `agenda/00-PRESSING.md`.")

    def start_file_blocks(self, dated, today, due) -> None:
        soon = [r for r in dated if due(r[1]) <= today + dt.timedelta(days=7)]
        due_md = "\n".join(f"- {r[1].due}: {one_line(r[1].title, 100)} ({'top level' if r[0] == 'top' else r[0]} {r[1].id})"
                           for r in soon) or "Nothing due in the next week."
        for _attempt in range(2):                 # compare and swap: a conversation may edit it meanwhile
            text = self.cloud.read(START)
            if not text:
                return
            new = text
            for name, body in (("health", self.health_text(today)), ("due", due_md)):
                out = replace_block(new, name, body)
                if out is not None:
                    new = out
                elif name == "health":
                    self.problem("the top-level start file has no health block; run install.py top on the folder")
            if new == text:
                return
            if self.cloud.read(START) == text:
                write_versioned(self.top, START, new)
                return

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

    def check_account(self) -> str | None:
        """Why this folder may not be the configured account's, or None. A Drive for desktop path
        names its account; an rclone remote is asked."""
        if not self.account:
            return None
        if self.cloud_spec.startswith("rclone:"):
            remote = self.cloud_spec[len("rclone:"):].split(":", 1)[0] + ":"
            try:
                res = subprocess.run(["rclone", "config", "userinfo", remote], capture_output=True, text=True, timeout=60,
                                     env={k: v for k, v in os.environ.items() if not k.startswith("RCLONE_")})
            except (OSError, subprocess.TimeoutExpired) as e:
                return f"cannot ask rclone which account {remote} is: {e}"
            if self.account.lower() not in res.stdout.lower():
                return f"the rclone remote {remote} is not {self.account}"
            return None
        if self.account.lower() not in self.cloud_spec.lower():
            return f"the folder {self.cloud_spec} does not name the account {self.account}"
        return None

    # ---- the pass
    def step(self, label: str, fn, *args) -> None:
        try:
            fn(*args)
        except Exception as ex:                       # noqa: BLE001 (report it; carry on with the rest)
            self.problem(f"{label}: {type(ex).__name__}: {ex}")

    def run(self) -> int:
        wrong = self.check_account()
        if wrong:
            print(f"PROBLEM: refusing to run: {wrong}")
            return 2
        try:
            if not self.dry and not take_lease(self.cloud, self.me, max(self.interval - 5, 10), self.settle):
                print("collab-kit back end: another runner holds the lease; exiting")
                return 0
        except (StoreError, OSError) as ex:
            print(f"PROBLEM: the Collab Kit folder is not reachable: {ex}")
            return 2
        try:
            self.step("the list of taken names", self.repositories)
            self.step("the top-level inbox", self.apply_inbox, self.top, None)
            for name, unit in self.all_units()[1:]:
                self.step("the lease", self.renew)
                if name in self.repos:
                    if not self.dry:
                        self.step(name, self.repo_project, name, self.repos[name])
                else:
                    self.step(name, self.apply_inbox, unit, self.top)
            self.step("the views", self.views)
        finally:
            if not self.dry:
                try:
                    self.cloud.write(HEARTBEAT, json.dumps({
                        "last_run": utcnow().isoformat(), "interval_minutes": self.interval, "host": socket.gethostname(),
                        "problems": self.problems, "applied": len(self.log)}, indent=1))
                except Exception as ex:               # noqa: BLE001
                    print(f"PROBLEM: could not write the heartbeat: {ex}")
                drop_lease(self.cloud, self.me)
        for line in self.log:
            print(line)
        for p in self.problems:
            print(f"PROBLEM: {p}")
        return 1 if self.problems else 0


def version_path(rel: str) -> str:
    folder, _, base = rel.rpartition("/")
    return f"{folder}/{VERSIONS}/{stamp()}-{base}" if folder else f"{VERSIONS}/{stamp()}-{base}"


def load_config(path: str | None) -> dict:
    p = Path(C.expand(path)) if path else C.config_dir() / "backend.toml"
    cfg = C.load_toml(p)
    if not cfg.get("backend", {}).get("cloud"):
        raise SystemExit(f"collab-kit back end: no [backend].cloud in {p}")
    return cfg


def run(path: str | None, once: bool = True, dry_run: bool = False) -> int:
    return Pass(load_config(path), dry_run=dry_run).run()

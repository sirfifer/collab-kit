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
    views        agenda/00-PRESSING.md at the top level, the agenda's front page: the back end's own
                 health first (the time of this pass, and anything it could not handle), then every
                 unit's deadlines, critical items, work in progress, what happened lately (status
                 lines, items settled, returns still waiting), and important items. Start files are
                 never reports: the back end only sets the top-level start file's setup line, once,
                 the first time it runs for the folder.
    heartbeat    _backend/heartbeat.json: when it ran, what failed. Written whatever happened.
                 agenda/00-HEARTBEAT.md: the time of the last check, written by every check the
                 schedule makes (each minute), full pass or not: one small file, never the page.
                 Then the optional [heartbeat] command (a dead-man ping to somewhere outside).

Through rclone a pass reads the folder from one listing taken after the lease (RcloneStore.snapshot):
a file is downloaded only when its md5 is not in the work folder's cache (DESIGN-0.5 section 22).

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

    [notify]                              # optional (docs/notifications.md)
    command = ["sh", "-c", "..."]         # run the first time a critical item appears
    status = false                        # true: also for each new status line (finished work)

    [heartbeat]                           # optional: a dead-man ping, so something outside notices a stop
    command = ["sh", "-c", "..."]         # run after a successful check; nothing from the folder reaches it
    every_minutes = 5                     # at most this often

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
from . import kit_version
from .apply import SETTLE_SECONDS, Outcome, apply_file, changed_since_listed, heal_duplicates, raise_item
from .store import FolderStore, RcloneStore, Store, StoreError, SubStore, open_store, run_quiet
from .templates import SETUP_NONE_MARK, SETUP_TEXT, get_block, replace_block, set_human
from .views import (HEARTBEAT_PAGE, PRESSING, STALE_MINUTES, cloud_units, front_page, heartbeat_text,  # noqa: F401
                    inactive_projects, status_entries, write_front_page)
from .text import one_line, sha, stamp, utcnow
from .unit import AGENDA, APPLIED, FAILED, KNOWLEDGE, RETURNS, START, STRAYS, VERSIONS, Unit, write_versioned

LEASE = "_backend/lease.json"
HEARTBEAT = "_backend/heartbeat.json"
ACCEPTS = ["blocks"]                                  # additions to Changes v1 this back end applies (said in the heartbeat)
MIRROR_STATE = "_backend/mirror"
TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json", ".html", ".toml", ".tsv", ".svg", ".yml", ".yaml"}
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}


class Problem(Exception):
    pass


class LeaseLost(Exception):
    pass


def git_paths(d: Path, *args) -> list[str]:
    """File names from git, exactly (no C-quoting of non-ASCII, NUL-separated, spaces kept)."""
    out = git(d, "-c", "core.quotePath=false", *args, "-z")
    return [p for p in out.split("\0") if p]


def local_name(name: str) -> str:
    """A cloud file name, made safe and unambiguous as a local file name on any platform (the same
    name every pass, so a return keeps its id): Drive's "(1)" suffix and characters Windows or a
    path would misread become hyphens."""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, "md"
    stem = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "-", stem)
    stem = re.sub(r"\s+\((\d{1,3})\)$", r"-\1", stem).strip(" .") or "return"
    return f"{stem}.{ext.lower()}"


def git(cwd: Path, *args, check=True, timeout=300) -> str:
    res = run_quiet(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8",
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
    raw = cloud.read_fresh(LEASE)
    if raw:
        try:
            cur = json.loads(raw)
            stale = (now - dt.datetime.fromisoformat(cur.get("renewed", cur["expires"]))).total_seconds() > 300
            if cur.get("holder") != me and dt.datetime.fromisoformat(cur["expires"]) > now \
                    and not (stale and _dead_here(cur.get("holder", ""))):
                return False
        except (ValueError, KeyError, TypeError):
            pass
    write_lease(cloud, me, minutes)
    if settle:
        time.sleep(settle)
    try:
        return json.loads(cloud.read_fresh(LEASE) or "{}").get("holder") == me
    except ValueError:
        return False


def _dead_here(holder: str) -> bool:
    """A lease left by a process of this machine that no longer exists (a pass stopped by a reinstall):
    free at once rather than at its expiry. POSIX only (Windows has no harmless liveness check)."""
    host, _, pid = holder.rpartition(":")
    if os.name == "nt" or host != socket.gethostname() or not pid.isdigit():
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return False


def write_lease(cloud: Store, me: str, minutes: int) -> None:
    now = utcnow()
    cloud.write(LEASE, json.dumps({"holder": me, "expires": (now + dt.timedelta(minutes=minutes)).isoformat(),
                                   "renewed": now.isoformat()}))


def drop_lease(cloud: Store, me: str) -> None:
    try:
        cur = json.loads(cloud.read_fresh(LEASE) or "{}")
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

def command_of(section) -> list[str] | None:
    """The command of a [notify] or [heartbeat] table: None when there is none, [] when it is not a
    list of strings (reported, never run). Only its first word is expanded (~)."""
    cmd = section.get("command") if isinstance(section, dict) else None
    if cmd is None:
        return None
    if isinstance(cmd, list) and cmd and all(isinstance(a, str) for a in cmd):
        return [C.expand(a) if i == 0 else a for i, a in enumerate(cmd)]
    return []


class Pass:
    def __init__(self, cfg: dict, dry_run: bool = False, minute: bool = False):
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
        notify = cfg.get("notify") if isinstance(cfg.get("notify"), dict) else {}
        self.notify_cmd = command_of(notify)             # None: off; a list: on; []: reported
        self.notify_status = notify.get("status") is True    # also each new status line: only when asked
        self.minute = minute                             # the schedule's minute check keeps agenda/00-HEARTBEAT.md
        self.lost = False
        self.me = f"{socket.gethostname()}:{os.getpid()}"
        self.dry = dry_run
        self.held_lease = False
        self.renewed_at = time.monotonic()
        self.lease_checked = False
        self.problems: list[str] = []
        self.log: list[str] = []
        self.top = Unit(self.cloud, "top", home="cloud", top=True)
        set_human(self.human)

    def note(self, msg: str) -> None:
        self.log.append(msg)

    def problem(self, msg: str) -> None:
        self.problems.append(one_line(msg, 300))

    RENEW_EVERY = 120                 # seconds: well inside the lease (interval - 5 minutes) and its 300-second staleness

    def renew(self) -> None:
        """Stop this pass if another runner holds the lease; extend it when due. Called before every
        project. The first call of a pass always reads the lease (the backstop for two runners that
        both read their own name back); later calls read and write it only once RENEW_EVERY seconds
        have passed, so a fast pass spends one read on it (a live holder's lease cannot be taken
        before it expires)."""
        due = time.monotonic() - self.renewed_at >= self.RENEW_EVERY
        if self.dry or (self.lease_checked and not due):
            return
        try:
            holder = json.loads(self.cloud.read_fresh(LEASE) or "{}").get("holder")
        except ValueError:
            holder = None
        if holder not in (None, self.me):
            raise LeaseLost(f"another runner ({holder}) took the lease; this pass stops here")
        self.lease_checked = True
        if due:
            write_lease(self.cloud, self.me, max(self.interval - 5, 10))
            self.renewed_at = time.monotonic()

    # ---- inboxes
    def apply_inbox(self, unit: Unit, top: Unit | None) -> list[Outcome]:
        outs = []
        if not self.dry:
            for old, new in heal_duplicates(unit):
                self.note(f"{unit.name}: two items had {old}; the later one is now {new}")
        for e in unit.pending_returns():
            if self.dry:
                young = e.mtime and utcnow().timestamp() - e.mtime < SETTLE_SECONDS
                self.note(f"{unit.name}/{e.name}: " + (f"waits (younger than {SETTLE_SECONDS} seconds: it may still "
                          "be syncing or moving)" if young else "would be applied"))
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
            res = run_quiet(["git", "clone", "-q", "-c", "core.symlinks=false", "--branch", branch,
                                  C.expand(spec["repo"]), str(d)],
                                 capture_output=True, text=True, timeout=600, env={**os.environ, **GIT_ENV})
            if res.returncode != 0:
                raise Problem(f"cannot clone {spec['name']}: {res.stderr.strip()[:200]}")
        git(d, "config", "core.symlinks", "false")      # a link in the repository never reaches outside it
        git(d, "fetch", "-q", "origin")
        if git(d, "branch", "--show-current").strip() != branch:
            git(d, "checkout", "-q", branch)
        if spec.get("push", False):
            git(d, "reset", "-q", "--hard", f"origin/{branch}")
        else:
            git(d, "reset", "-q", "--hard", "HEAD")
            res = run_quiet(["git", "-C", str(d), "-c", "user.name=Collab Kit back end",
                                  "-c", "user.email=collab-kit@users.noreply.github.com", "rebase", "-q", f"origin/{branch}"],
                                 capture_output=True, text=True, env={**os.environ, **GIT_ENV})
            if res.returncode != 0:
                git(d, "rebase", "--abort", check=False)
                raise Problem(f"{spec['name']}: the back end's own commits (not pushed) no longer apply on top of the "
                              f"remote; resolve it by hand in {d}")
        git(d, "clean", "-q", "-fd")
        return d

    def is_ancestor(self, d: Path, commit: str) -> bool:
        return run_quiet(["git", "-C", str(d), "merge-base", "--is-ancestor", commit, "HEAD"],
                              capture_output=True).returncode == 0

    def commit(self, d: Path, message: str) -> str | None:
        git(d, "add", "-A", "--", "collab-kit")
        staged = git_paths(d, "diff", "--cached", "--name-only")
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
            if e.mtime and time.time() - e.mtime < SETTLE_SECONDS:
                continue                                   # still settling: a conversation may still move it
            if e.native or not e.name.lower().endswith((".md", ".txt")):
                out = raise_item(repo_unit, "A file in the inbox was set aside",
                                 f"`{one_line(e.name, 120)}` arrived in the inbox but is not a plain .md or .txt return "
                                 f"(a Google Doc, or another kind of file); it is in `_returns/strays/`.", top=self.top)
                moves.append((e.name, STRAYS, self.commit(d, f"collab-kit: set aside {e.name}")))
                self.problem(f"{name}: {e.name} was set aside (not a plain return)")
                continue
            try:
                text = cloud_unit.read(f"{RETURNS}/{e.name}")
            except (StoreError, OSError) as ex:
                self.problem(f"{name}: {e.name} could not be read: {ex}")
                continue
            if text is None or changed_since_listed(cloud_unit, f"{RETURNS}/{e.name}", e):
                continue                                   # gone, or changed since the listing: it settles again
            lname = local_name(e.name)
            dest = d / "collab-kit" / RETURNS / lname
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            os.utime(dest, (e.mtime or 0, e.mtime or 0))
            try:
                out = apply_file(repo_unit, repo_unit.store.entry(f"{RETURNS}/{lname}"), top=self.top)
            except Exception as ex:                  # noqa: BLE001 (one return never stalls the project)
                git(d, "reset", "-q", "--hard", "HEAD")
                git(d, "clean", "-q", "-fd", "--", "collab-kit")
                self.move_cloud(cloud_unit, e.name, FAILED)
                self.problem(f"{name}: {e.name} could not be applied ({type(ex).__name__}: {ex}); moved to _returns/failed/")
                continue
            if out.status == "waiting":
                dest.unlink(missing_ok=True)
                if "End." in out.message:
                    self.problem(f"{name}: {e.name} is not finished yet (no End.)")
                continue
            if not spec.get("returns_in_git", False):
                for p in (d / "collab-kit" / RETURNS).rglob("*"):
                    if p.is_file() and (p.name == lname or p.name.endswith("-" + lname)):
                        p.unlink()                  # its text stays in the cloud; the ledger goes to git
            where = {"failed": FAILED, "stray": STRAYS}.get(out.status, APPLIED)
            moves.append((e.name, where, self.commit(d, f"collab-kit: {out.status} return {out.rid}")))
            self.note(f"{name}: {out.status} {out.rid}")
            if out.status in ("failed", "stray"):
                self.problem(f"{name}: a return could not be filed: {e.name} ({out.message})")
        for out in self.apply_inbox(repo_unit, self.top):   # returns that came in through the repository
            self.commit(d, f"collab-kit: {out.status} return {out.rid}")
        if (d / "tools" / "kb" / "kb.py").is_file():
            res = run_quiet([sys.executable, "tools/kb/kb.py", "build"], cwd=d, capture_output=True, text=True,
                                 timeout=600)
            if res.returncode != 0:
                self.problem(f"{name}: the knowledge build failed: {res.stderr.strip()[:200]}")
            else:
                self.commit(d, "collab-kit: rebuild the knowledge")
        unpushed = lambda: git(d, "rev-list", "--count", f"origin/{branch}..HEAD").strip() != "0"  # noqa: E731
        if spec.get("push", False) and unpushed() and not spec.get("allow_public", False) and self.is_public(d):
            self.problem(f"{name}: not pushed: the repository is public, or its visibility could not be checked "
                         f"(gh), and allow_public is not set; the returns stay in the inbox")
            return                                    # nothing is blamed and nothing moves; retried next pass
        if spec.get("push", False) and unpushed():
            bad = self.guard(name, spec, d, branch)
            if bad:
                sha_, why = bad
                culprit = next((m for m in moves if m[2] == sha_), None)
                git(d, "reset", "-q", "--hard", f"{sha_}^")       # the bad commit and everything after it go
                if culprit:
                    self.move_cloud(cloud_unit, culprit[0], FAILED)
                    self.file_cloud_note(cloud_unit, name, "A return was not filed",
                                         f"`{one_line(culprit[0], 120)}` was moved to `_returns/failed/`: {why}. Change it and file it again, or "
                                         f"drop it.")
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
        res = run_quiet(["git", "-C", str(d), "push", "-q", "origin", f"HEAD:{branch}"], capture_output=True,
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
        for c in git(d, "rev-list", "--reverse", f"origin/{branch}..HEAD").split():
            paths = git_paths(d, "show", "--name-only", "--format=", c)
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
            res = run_quiet(["gh", "repo", "view", f"{m.group(1)}/{m.group(2)}", "--json", "visibility",
                                  "-q", ".visibility"], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return True
        return res.returncode != 0 or res.stdout.strip().upper() != "PRIVATE"

    def file_cloud_note(self, cloud_unit: Unit, name: str, title: str, needed: str) -> None:
        """Put something on a repository-homed unit's agenda from the outside: a return of the back
        end's own into its cloud inbox, applied (and pushed) like any other on the next pass."""
        from .returns import render_change, render_return
        rid = f"{stamp()}-backend-{hashlib.sha256(title.encode()).hexdigest()[:8]}"
        body = f"## What's needed\n{needed}\n\n## Done when\nSomeone has looked at it and settled this item.\n"
        ch = render_change("new-item", None, None, None, body, kind="task", importance="1", title=one_line(title, 120))
        cloud_unit.store.write(f"{RETURNS}/{rid}.md", render_return(name, rid, "the back end", "task", title, [ch]))

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
            if p.is_symlink() or any(q.is_symlink() for q in p.parents if src in q.parents or q == src):
                continue                              # never follow a link out of the repository
            if not p.is_file() or not (rel == START or rel.startswith((f"{KNOWLEDGE}/", f"{AGENDA}/"))):
                continue
            if f"/{VERSIONS}/" in f"/{rel}" or any(part.startswith(".") for part in rel.split("/")):
                continue
            want[rel] = p.read_bytes()
        have = self.cloud_copy(cloud_unit)
        if (any(have.get(rel) != md5(data) for rel, data in want.items()) or set(have) - set(want)) \
                and cloud_unit.store.refresh(""):     # about to write: the copy as it is now, not as listed
            have = self.cloud_copy(cloud_unit)
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
        state = json.dumps(new_state, indent=0, sort_keys=True)
        if state != raw:
            self.cloud.write(state_path, state)

    @staticmethod
    def cloud_copy(cloud_unit: Unit) -> dict[str, str | None]:
        """{path: md5} of the mirrored files in a repository-homed unit's cloud copy."""
        have = {**walk(cloud_unit.store, KNOWLEDGE), **walk(cloud_unit.store, AGENDA)}
        if cloud_unit.store.exists(START):
            have[START] = cloud_unit.store.md5s("").get(START)
        return have

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
        return cloud_units(self.cloud, set(self.repos))

    def views(self) -> None:
        """The optional push first (so a failure reaches the page), then the agenda's front page
        (views.py), the back end's health first."""
        self.step("the top-level start file", self.start_file_setup)
        now = utcnow()
        units = self.all_units()
        if self.notify_cmd is not None and not self.dry:
            self.step("the push notification", self.notify, units)
        text = front_page(units, today=now.date(), human=self.human, inactive=inactive_projects(self.cloud),
                          interval=self.interval, problems=self.problems, unreadable=self.problem,
                          now=now, heartbeat=self.minute)
        if not self.dry and write_front_page(self.cloud, text):
            self.note("the agenda's front page was rebuilt")

    NOTIFY_PER_PASS, NOTIFY_PER_HOUR = 5, 20

    def notify(self, units) -> None:
        """Optional ([notify] command): tell the person the moment a critical item (importance 1) first
        appears, wherever it came from; and, only with `status = true`, each new status line (what work
        outside conversations reports: finished, blocked, started). The command gets the text in
        environment variables (COLLAB_KIT_TITLE, COLLAB_KIT_MESSAGE, COLLAB_KIT_ITEM), never on a
        command line: titles and status lines are outside text. COLLAB_KIT_KIND says which kind of
        push it is, so a phone can tell them apart: `critical`, `blocked` (a critical item that names
        the item it blocks), or `status`. The engine sets it; it is never text from a file. Each is
        sent once; what a pass could not send (a cap, a failure) is sent by a later one; at most five
        a pass and twenty an hour, critical items first. docs/notifications.md has examples."""
        if not self.notify_cmd:
            raise ValueError("[notify] command must be a list of strings, e.g. [\"sh\", \"-c\", \"...\"]")
        state = self.work / "notified.json"
        try:
            st = json.loads(state.read_text(encoding="utf-8"))
            seen = {k: float(v) for k, v in st["seen"].items()} if isinstance(st["seen"], dict) \
                else {k: time.time() for k in st["seen"]}
            times = [float(x) for x in st.get("times", [])]
            had_status = st.get("status") is True
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            seen, times, had_status = None, [], False    # first run: remember what is there, send nothing
        now = {}                                         # key -> (title, message, reference, kind)
        for name, unit in units:
            where = "top level" if name == "top" else name
            for it in unit.items():
                if it.is_open and it.importance <= 1:
                    kind = "blocked" if it.blocks else "critical"
                    now[f"{name}:{it.id}"] = (f"Collab Kit: {kind} in {where}", it.title, f"{where} {it.id}", kind)
            if self.notify_status:                       # a day's worth: older lines are never news
                since = (utcnow() - dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
                try:
                    entries = status_entries(unit)
                except (StoreError, OSError):
                    entries = []
                for at, rest in entries:
                    if rest == self.human or rest.startswith(f"{self.human}:"):
                        continue                         # the person's own line (a conversation's): not news to them
                    if len(at) > 10 and at >= since:
                        now[f"status:{name}:{at}:{sha(rest)[:8]}"] = (f"Collab Kit: status in {where}", rest,
                                                                     f"{where} status {at} UTC", "status")
        clock = time.time()
        if seen is None:
            seen = {k: clock for k in now}
        else:                                            # forgotten a week after it was last seen
            seen = {k: (clock if k in now else v) for k, v in seen.items() if k in now or clock - v < 7 * 86400}
            if self.notify_status and not had_status:    # status lines just turned on: those already there are not news
                seen.update({k: clock for k in now if k.startswith("status:")})
        times = [x for x in times if x > time.time() - 3600]
        try:
            for key in sorted(set(now) - set(seen), key=lambda k: (k.startswith("status:"), k))[: self.NOTIFY_PER_PASS]:
                if len(times) >= self.NOTIFY_PER_HOUR:
                    self.note("push: the hourly limit is reached; the rest wait for a later pass")
                    break
                title, text, ref, kind = now[key]
                message = one_line(text, 200).lstrip("@<")        # never a curl file reference
                env = {**os.environ, "COLLAB_KIT_TITLE": title, "COLLAB_KIT_MESSAGE": message, "COLLAB_KIT_ITEM": ref,
                       "COLLAB_KIT_KIND": kind}
                res = run_quiet(self.notify_cmd, env=env, capture_output=True, timeout=20)
                if res.returncode != 0:
                    raise RuntimeError(f"the notify command failed ({res.returncode}): "
                                       f"{res.stderr.decode('utf-8', 'replace').strip()[:200]}")
                seen[key] = time.time()
                times.append(time.time())
                self.note(f"pushed: {ref}")
        finally:
            self.work.mkdir(parents=True, exist_ok=True)
            state.write_text(json.dumps({"seen": dict(sorted(seen.items())), "times": times,
                                         "status": self.notify_status}), encoding="utf-8")

    def write_if_changed(self, unit: Unit, rel: str, text: str) -> None:
        if unit.store.read(rel) != text:
            write_versioned(unit, rel, text)

    def start_file_setup(self) -> None:
        """The top-level start file's setup line says a back end runs: set once, on the first run,
        and only from the "no back end" wording. A line edited by hand, or already set, is left alone,
        and nothing else in any start file is ever written: start files stay put, and the back end's
        health is on the agenda's front page. (A store has no atomic swap: the file is read again just
        before the write, and left alone if it changed.)"""
        raw = self.cloud.read(START)
        if raw is None:
            self.problem("the top-level start file (00-START-HERE.md) is missing")
            return
        text = raw.replace("\r\n", "\n")
        have = get_block(text, "setup")
        if have is None:
            self.problem("the top-level start file has no setup line (<!-- collab-kit:begin setup -->): it predates "
                         "Collab Kit 0.5.1; replace it with install.py top --replace-start (the old one is kept)")
            return
        if self.dry or not have.strip().startswith(SETUP_NONE_MARK):
            return
        new = replace_block(text, "setup", SETUP_TEXT["backend"])
        if self.cloud.read_fresh(START) == raw:
            write_versioned(self.top, START, new)
            self.note("the top-level start file now says a back end runs for this folder")

    def repositories(self) -> None:
        """knowledge/repositories.md: every name already taken (GitHub, and local project folders)."""
        names: dict[str, str] = {}
        try:
            res = run_quiet(["gh", "repo", "list", "--limit", "500", "--json", "name,visibility"],
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
        names its account; through rclone, the owner of the folder's start file is read."""
        if not self.account:
            return None
        if self.cloud_spec.startswith("rclone:"):
            try:
                who = self.cloud.account()
            except (StoreError, OSError, subprocess.TimeoutExpired) as e:
                return f"cannot ask rclone who owns the folder: {e}"
            if who.lower() != self.account.lower():
                return (f"the folder's start file is owned by {who or 'an account rclone cannot tell'}, "
                        f"not {self.account}")
            return None
        if self.account.lower() not in self.cloud_spec.lower():
            return f"the folder {self.cloud_spec} does not name the account {self.account}"
        return None

    # ---- the pass
    def step(self, label: str, fn, *args) -> None:
        try:
            fn(*args)
        except LeaseLost:
            raise
        except Exception as ex:                       # noqa: BLE001 (report it; carry on with the rest)
            self.problem(f"{label}: {type(ex).__name__}: {ex}")

    def passes(self) -> None:
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

    def check_folder(self) -> str | None:
        """Why the cloud root may not be a Collab Kit folder, or None. Checked before the lease, so a
        remote pointed at the wrong place (a reconnect answered Yes to rclone's Shared Drive question,
        which empties root_folder_id) gets nothing written to it and is never walked."""
        if self.account and self.cloud_spec.startswith("rclone:"):
            return None                               # check_account found the owner of its start file
        try:
            names = {e.name for e in self.cloud.list("")}
        except (StoreError, OSError) as e:
            return f"the Collab Kit folder is not reachable: {e}"
        if START in names or AGENDA in names:
            return None
        return (f"{self.cloud_spec} has no {START} and no {AGENDA}/ at its top, so it is not a Collab Kit folder; "
                f"nothing was written. Check where the remote points (for rclone: `rclone lsf <remote>: --max-depth 1` "
                f"must show {START}; a reconnect that answered Yes to the Shared Drive question empties root_folder_id)")

    def run(self) -> int:
        started = time.monotonic()
        wrong = self.check_account() or self.check_folder()
        if wrong:
            print(f"PROBLEM: refusing to run: {wrong}")
            return 2
        if isinstance(self.cloud, RcloneStore) and self.cloud.uses_shared_google_client():
            self.problem("rclone reaches Drive with rclone's shared Google client, which Google retires during "
                         "2026 (then the back end stops) and which is slow: give the remote its own client "
                         "(docs/rclone-intake.md, 'OAuth')")
        try:
            if not self.dry and not take_lease(self.cloud, self.me, max(self.interval - 5, 10), self.settle):
                print("collab-kit back end: another runner holds the lease; exiting")
                return 0
            self.held_lease = not self.dry
            self.renewed_at = time.monotonic()
        except (StoreError, OSError) as ex:
            print(f"PROBLEM: the Collab Kit folder is not reachable: {ex}")
            return 2
        self.start_snapshot()
        lost = False
        try:
            note = self.work / PING_PROBLEM            # a dead-man ping that failed since the last pass
            if note.is_file():
                self.problem(note.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
        try:
            self.passes()
        except LeaseLost as ex:
            lost = self.lost = True                    # another runner owns the folder now: write nothing more
            print(f"collab-kit back end: {ex}")
        finally:
            if isinstance(self.cloud, RcloneStore):
                self.cloud.end_snapshot()
            if not self.dry and not lost:
                try:
                    self.cloud.write(HEARTBEAT, json.dumps({
                        "last_run": utcnow().isoformat(), "interval_minutes": self.interval, "host": socket.gethostname(),
                        "problems": self.problems, "applied": len(self.log), "kit": kit_version(),
                        "accepts": ACCEPTS, "minute_check": self.minute}, indent=1))
                except Exception as ex:               # noqa: BLE001
                    print(f"PROBLEM: could not write the heartbeat: {ex}")
                drop_lease(self.cloud, self.me)
        for line in self.log:
            print(line)
        for p in self.problems:
            print(f"PROBLEM: {p}")
        print(self.summary(time.monotonic() - started))
        return 1 if self.problems else 0

    CACHE = "rclone-cache"                            # in the work folder: file contents by md5

    def start_snapshot(self) -> None:
        """Through rclone, read the whole folder in one listing; a file is downloaded only when its md5
        is not in the work folder's cache (a dry run keeps the cache in memory). If the listing fails,
        the pass reads file by file and says so."""
        if not isinstance(self.cloud, RcloneStore):
            return
        try:
            self.cloud.snapshot(None if self.dry else self.work / self.CACHE)
        except (StoreError, OSError, ValueError) as ex:
            self.problem(f"the folder could not be read in one listing, so this pass read it file by file: {ex}")

    def summary(self, seconds: float) -> str:
        """The log's line for this pass: when, how long, and (through rclone) what it cost."""
        line = (f"{utcnow():%Y-%m-%d %H:%M:%S} UTC: {'dry run' if self.dry else 'full pass'} took {seconds:.0f} s, "
                f"{len(self.problems)} problem(s)")
        if isinstance(self.cloud, RcloneStore):
            calls = ", ".join(f"{k} {v}" for k, v in sorted(self.cloud.calls.items())) or "none"
            line += f"; rclone calls: {calls}; {self.cloud.cache_hits} read(s) from the cache"
        return line


def version_path(rel: str) -> str:
    folder, _, base = rel.rpartition("/")
    return f"{folder}/{VERSIONS}/{stamp()}-{base}" if folder else f"{VERSIONS}/{stamp()}-{base}"


def load_config(path: str | None) -> dict:
    p = Path(C.expand(path)) if path else C.config_dir() / "backend.toml"
    cfg = C.load_toml(p)
    b = cfg.get("backend", {})
    if not b.get("cloud"):
        raise SystemExit(f"collab-kit back end: no [backend].cloud in {p}")
    for key, env in (("rclone", "COLLAB_KIT_RCLONE"), ("rclone_config", "COLLAB_KIT_RCLONE_CONFIG")):
        if b.get(key):                               # the pinned binary and its own config, where a schedule's PATH
            os.environ[env] = C.expand(b[key])        # would not find them
    return cfg


LAST_PASS = "last-pass"                               # in the work folder: when the last full pass ended
INBOX_PRINT = "inbox-fingerprint.json"                # what the inboxes held, settled, after that pass
LAST_CHECK = "last-check"                             # when the schedule's check last wrote the heartbeat
LAST_PING = "last-ping"                               # when the [heartbeat] command last ran
PING_PROBLEM = "ping-problem.txt"                     # why it failed, for the next full pass to report
PING_EVERY = 5                                        # minutes, unless [heartbeat] every_minutes says


def settled_inbox(store: Store, entries=None) -> list:
    """The inboxes' settled files as [path, mtime, size]: a return still settling is left out until it
    has settled, so it starts exactly one pass; a return a pass leaves in place (a failed push, no End.
    yet) is in it and starts no more."""
    from .apply import SETTLE_SECONDS
    now = time.time()
    entries = store.inbox_entries() if entries is None else entries
    return sorted([p, int(m), s] for p, m, s in entries if not m or now - m >= SETTLE_SECONDS)


def _younger(path: Path, seconds: float) -> bool:
    try:
        return time.time() - path.stat().st_mtime < seconds
    except OSError:
        return False


def beat(cfg: dict, store: Store, work: Path, minute: bool) -> None:
    """A check succeeded (a quiet minute, or a full pass): say so. With `minute` (the schedule's
    check, every minute), write the time to agenda/00-HEARTBEAT.md: one small file, in place, so
    the front page is not rewritten every minute. Then the optional [heartbeat] command. Neither
    failing stops anything: it is printed to the log, and a failed command is reported by the next
    full pass."""
    now = utcnow()
    if minute:
        try:
            store.write(HEARTBEAT_PAGE, heartbeat_text(now, cfg.get("backend", {}).get("human", "the owner")))
            work.mkdir(parents=True, exist_ok=True)
            (work / LAST_CHECK).write_text(now.isoformat() + "\n", encoding="utf-8")
        except (StoreError, OSError) as ex:
            print(f"PROBLEM: could not write {HEARTBEAT_PAGE}: {ex}")
            return                                    # no ping either: the folder could not be written
    ping(cfg, work, now)


def ping(cfg: dict, work: Path, now) -> None:
    """Optional ([heartbeat] command): a dead-man ping. A back end that has stopped cannot say so, so
    something outside has to notice the silence: the command tells a service of the person's choosing
    "still here" after a successful check, at most every `every_minutes` (5), and that service
    raises the alarm when the pings stop. Nothing read from the folder reaches the command: its one
    variable, COLLAB_KIT_CHECKED, is the time of the check."""
    section = cfg.get("heartbeat", {})
    cmd = command_of(section)
    if cmd is None:
        return
    note = work / PING_PROBLEM
    try:
        if not cmd:
            raise ValueError("[heartbeat] command must be a list of strings, e.g. [\"sh\", \"-c\", \"...\"]")
        every = max(int(section.get("every_minutes", PING_EVERY)), 1)
        if _younger(work / LAST_PING, every * 60 - 30):
            return
        res = run_quiet(cmd, env={**os.environ, "COLLAB_KIT_CHECKED": now.isoformat()}, capture_output=True, timeout=20)
        if res.returncode != 0:
            raise RuntimeError(f"the [heartbeat] command failed ({res.returncode}): "
                               f"{res.stderr.decode('utf-8', 'replace').strip()[:200]}")
        work.mkdir(parents=True, exist_ok=True)
        (work / LAST_PING).write_text(now.isoformat() + "\n", encoding="utf-8")
        note.unlink(missing_ok=True)
    except (ValueError, TypeError, RuntimeError, OSError, subprocess.TimeoutExpired) as ex:
        msg = one_line(f"the dead-man ping: {type(ex).__name__}: {ex}", 300)
        print(f"PROBLEM: {msg}")
        try:
            work.mkdir(parents=True, exist_ok=True)
            note.write_text(msg, encoding="utf-8")
        except OSError:
            pass


def run(path: str | None, once: bool = True, dry_run: bool = False, if_waiting: bool = False) -> int:
    """One pass. With if_waiting (what the schedule runs, every minute and on a file event), first ask
    one cheap question, whether the inboxes hold anything new since the last pass (one listing), and do
    the full pass only if they do or the last full pass is older than interval_minutes (the sweep,
    which also pulls and mirrors). Either way a check that succeeded says so (beat): the quiet minute
    only when the same listing showed the folder's start file, so nothing is written to a folder that
    is not a Collab Kit folder."""
    cfg = load_config(path)
    b = cfg["backend"]
    work = Path(C.expand(b.get("work", str(C.state_dir().parent / "backend"))))
    stamp_file, print_file = work / LAST_PASS, work / INBOX_PRINT
    before = None                                    # the inboxes as this pass starts (settled files)
    store, start_there = None, False
    minute = if_waiting or _younger(work / LAST_CHECK, STALE_MINUTES * 60)   # a pass by hand beside the schedule
    if not dry_run:
        try:
            store = open_store(C.expand(b["cloud"]))
            entries, start_there = store.check_entries()
            before = settled_inbox(store, entries)
        except (StoreError, OSError):
            before = None                            # the full pass says what is wrong, on the agenda
    if if_waiting and not dry_run and before is not None:
        interval = int(b.get("interval_minutes", 60))
        try:
            fresh = time.time() - stamp_file.stat().st_mtime < interval * 60 - 30
        except OSError:
            fresh = False
        try:
            last = json.loads(print_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            last = None
        if fresh and before == last:
            if start_there:
                beat(cfg, store, work, minute=True)
            return 0
    p = Pass(cfg, dry_run=dry_run, minute=minute)
    rc = p.run()
    if not dry_run and p.held_lease:
        try:
            work.mkdir(parents=True, exist_ok=True)
            stamp_file.write_text(utcnow().isoformat() + "\n", encoding="utf-8")
            after = settled_inbox(p.cloud)           # what this pass saw settled and left: nothing that
            seen = [e for e in after if before is None or e in before]   # settled or arrived meanwhile
            print_file.write_text(json.dumps(seen), encoding="utf-8")
        except (OSError, StoreError):
            pass
        if not p.lost:
            beat(cfg, p.cloud, work, minute=minute)
    return rc

"""The project side: what an agent working in a repository uses to see and change Collab Kit.

A repository with Collab Kit installed has tools/collab-kit/ (this engine, vendored; the `ck`
launcher; project.toml). From there this module finds the project's unit (its folder in the Collab
Kit folder, or the repository's own collab-kit/), whether a back end is running, and files returns
the way the start files describe: one format, one inbox, one writer per file.

Where a return goes (DESIGN-0.5 sections 5, 7, 16):
  - a back end is running and the folder is reachable:  the unit's cloud inbox; the back end applies it.
  - no back end, home is the cloud folder (level 1):    the cloud inbox, applied there at once; two
                                                        sessions that took the same item number heal
                                                        (the later file renumbers itself).
  - home is the repository, no back end reachable:      the repository's collab-kit/_returns/, never
                                                        applied here (sessions never mint item
                                                        numbers in a repository); the back end
                                                        applies it once it reaches the main branch.
  - home is the cloud folder but it is unreachable:     the repository's collab-kit/_returns/, to be
                                                        committed; the next session that can reach the
                                                        folder delivers it.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import secrets
import subprocess
import tempfile
from pathlib import Path

from . import config as C
from . import kit_version
from . import returns as R
from .apply import Planner, Reject, apply_return, heal_duplicates
from .store import FolderStore, Store, StoreError, SubStore, open_store
from .text import fold, slug, utcnow
from .unit import RETURNS, Unit

REPO_UNIT_DIR = "collab-kit"
HEARTBEAT = "_backend/heartbeat.json"
VENDORED_ROOT = Path(__file__).resolve().parents[3]    # <repo>, when this file is <repo>/tools/collab-kit/collab_kit/


def git(root: Path, *args: str, timeout: float = 8) -> str | None:
    try:
        res = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return res.stdout if res.returncode == 0 else None


def parse_time(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


class Project:
    def __init__(self, root: Path, machine: dict | None = None):
        self.root = root
        self.cfg = C.project(root)
        self.machine = machine if machine is not None else C.machine()
        p = self.cfg["project"]
        self.name: str = p["name"]
        self.home: str = p["home"]
        self.unit_rel: str = p["unit"]
        self._cloud: Store | None | bool = False
        self._backend: dict | None = None

    @classmethod
    def find(cls, start: Path | str | None = None) -> "Project | None":
        """The project at or above `start` (default: the current folder); else the one named by
        $CLAUDE_PROJECT_DIR; else the project this engine is vendored in (so `ck` works from any
        folder, e.g. a session started in ~/dev)."""
        for cand in (start or os.getcwd(), os.environ.get("CLAUDE_PROJECT_DIR")):
            if cand:
                root = C.find_project_root(Path(cand))
                if root:
                    return cls(root)
        if (VENDORED_ROOT / C.PROJECT_FILE).is_file():
            return cls(VENDORED_ROOT)
        return None

    def ck(self, cwd: str | Path | None = None) -> str:
        """How to call ck from `cwd`: short inside the project, absolute anywhere else."""
        try:
            inside = Path(cwd or os.getcwd()).resolve().is_relative_to(self.root.resolve())
        except OSError:
            inside = False
        launcher = self.root / "tools" / "collab-kit" / "ck"
        return "tools/collab-kit/ck" if inside else f'"{launcher.as_posix()}"'

    # ------------------------------------------------------------------------- stores --
    def cloud(self) -> Store | None:
        """The Collab Kit folder, if this machine is set up to reach it and it is there."""
        if self._cloud is False:
            cloud = self.machine.get("cloud", {})
            spec = C.expand(cloud.get("root", ""))
            for key, env in (("rclone", "COLLAB_KIT_RCLONE"), ("rclone_config", "COLLAB_KIT_RCLONE_CONFIG")):
                if cloud.get(key) and not os.environ.get(env):
                    os.environ[env] = C.expand(cloud[key])   # a machine that reaches the folder through rclone
            store = None
            if spec:
                try:
                    store = open_store(spec)
                    if isinstance(store, FolderStore) and not store.root.is_dir():
                        store = None
                    elif store is not None and not store.list(""):
                        store = None
                except (StoreError, OSError):
                    store = None
            self._cloud = store
        return self._cloud or None

    def cloud_unit(self) -> Unit | None:
        c = self.cloud()
        if not c:
            return None
        try:
            sub = SubStore(c, self.unit_rel)
            return Unit(sub, self.name, home=self.home) if sub.list("") else None
        except StoreError:
            return None

    def repo_unit(self) -> Unit:
        return Unit(FolderStore(self.root / REPO_UNIT_DIR), self.name, home="repo")

    def top_unit(self) -> Unit | None:
        c = self.cloud()
        return Unit(c, "top", home="cloud", top=True) if c else None

    def view(self) -> tuple[Unit | None, str]:
        """The copy of the unit to read. Home in the cloud: the cloud folder. Home in the repository:
        the cloud copy only while a back end keeps it current, else this checkout's collab-kit/."""
        repo_dir = self.root / REPO_UNIT_DIR
        if self.home == "repo":
            cu = self.cloud_unit()
            if cu and self.backend()["live"]:
                return cu, "the Collab Kit folder (the back end's copy of this repository's collab-kit/)"
            if repo_dir.is_dir():
                return self.repo_unit(), "this checkout's collab-kit/ (the project's home)"
            return cu, "the Collab Kit folder"
        cu = self.cloud_unit()
        if cu:
            return cu, "the Collab Kit folder (the project's home)"
        return None, "nowhere: the Collab Kit folder is not reachable from this machine"

    # ---------------------------------------------------------------------- back end --
    def backend(self) -> dict:
        if self._backend is not None:
            return self._backend
        c = self.cloud()
        if not c:
            self._backend = {"known": False, "live": False, "say": "unknown (the Collab Kit folder is not reachable from here)"}
            return self._backend
        try:
            raw = c.read(HEARTBEAT)
        except (StoreError, OSError):
            raw = None
        if not raw:
            self._backend = {"known": True, "live": False, "say": "none is running"}
            return self._backend
        try:
            hb = json.loads(raw)
            last = parse_time(hb["last_run"])
            every = int(hb.get("interval_minutes", 60))
            age_min = (utcnow() - last).total_seconds() / 60
        except (ValueError, KeyError, TypeError):
            self._backend = {"known": True, "live": False, "stopped": True, "say": "its heartbeat file is unreadable"}
            return self._backend
        live = age_min <= max(3 * every, 90)            # routing: file only while it is keeping up
        stopped = age_min > max(3 * every, 24 * 60)        # said loudly only after a day, as on the front page
        when = last.strftime("%Y-%m-%d %H:%M UTC")
        problems = hb.get("problems") or []
        say = (f"running (last ran {when}, every {every} minutes)" if live else
               f"stopped: it last ran {when}" if stopped else f"late: it last ran {when}, every {every} minutes")
        if problems and isinstance(problems, list):
            say += f"; {len(problems)} problem(s) listed at the top of agenda/00-PRESSING.md"
        self._backend = {"known": True, "live": live, "stopped": stopped, "say": say, "last": when}
        return self._backend

    # ------------------------------------------------------------------------ kit version --
    def kit_status(self) -> dict:
        here = kit_version()
        src = C.expand(self.machine.get("kit", {}).get("source", ""))
        newest = None
        if src:
            v = Path(src) / "VERSION"
            if v.is_file():
                newest = v.read_text(encoding="utf-8").strip()
        behind = bool(newest) and vkey(newest) > vkey(here)
        return {"here": here, "newest": newest, "behind": behind, "source": src}

    # ------------------------------------------------------------------------- filing --
    def sender(self) -> str:
        branch = (git(self.root, "branch", "--show-current") or "").strip()
        return f"Claude Code in {self.name}" + (f" ({branch})" if branch else "")

    def route(self) -> tuple[str, Unit, bool, str]:
        """(where, unit to file into, apply now?, how it is checked: 'full' or 'grammar')."""
        be = self.backend()
        cu = self.cloud_unit()
        if cu and be["live"]:
            return "cloud", cu, False, "full"
        if self.home == "cloud" and cu:
            return "cloud", cu, True, "full"
        if self.home == "repo":
            return "repo", self.repo_unit(), False, "full" if (self.root / REPO_UNIT_DIR / "agenda").is_dir() else "grammar"
        return "offline", self.repo_unit(), False, "grammar"

    def file(self, text: str, *, dry_run: bool = False) -> dict:
        """Validate a return, put it where it belongs, and apply it when nobody else will."""
        rid = f"{utcnow().strftime('%Y-%m-%d-%H%M')}-{secrets.token_hex(2)}"
        ret = R.parse(text, rid + ".md")
        if fold(ret.project) != fold(self.name):
            raise Reject(f"this return says Project: {ret.project[:60]}, but this repository is '{self.name}'")
        if not ret.complete:
            raise Reject("the return does not end with 'End.'")
        where, target, now, check = self.route()
        if check == "full":
            try:
                Planner(self.view()[0] or target, ret, self.top_unit()).plan()
            except Reject as e:
                raise Reject(f"not filed: {e}") from None
        name = f"{ret.id}.md"
        result = {"id": ret.id, "route": where, "applied": False, "minted": [], "file": None, "renumbered": []}
        if dry_run:
            result["dry_run"] = True
            return result
        target.store.mkdir(RETURNS)
        target.store.write(f"{RETURNS}/{name}", text)
        result["file"] = f"{RETURNS}/{name}"
        if now:
            out = apply_return(target, ret, name, top=self.top_unit())
            result.update(applied=out.status in ("applied", "recorded", "undone"), minted=out.minted,
                          status=out.status, message=out.message)
            if out.minted:
                result["renumbered"] = heal_duplicates(target)
            if result["applied"]:
                try:                                    # level 1: nobody else keeps the agenda's front page
                    from .views import rebuild_without_backend
                    rebuild_without_backend(self.cloud(), self.machine.get("human") or "the owner", utcnow().date())
                except Exception:                       # noqa: BLE001 (the change itself is filed and applied)
                    pass
        log_filed(self.root, self.name, ret.id, where)
        return result

    def compose(self, rtype: str, topic: str, changes: list[str], **fields) -> str:
        rid = f"{utcnow().strftime('%Y-%m-%d-%H%M')}-{slug(topic, 32)}-{secrets.token_hex(2)}"
        return R.render_return(self.name, rid, fields.pop("sender", None) or self.sender(), rtype, topic,
                               changes, **fields)

    def deliver_offline(self) -> list[str]:
        """Returns filed while the Collab Kit folder was unreachable (cloud-homed projects) are moved
        into the cloud inbox as soon as it is reachable. The removal from collab-kit/_returns/ is a
        change to commit."""
        if self.home != "cloud":
            return []
        inbox = self.root / REPO_UNIT_DIR / RETURNS
        cu = self.cloud_unit()
        if not inbox.is_dir() or not cu:
            return []
        moved = []
        for p in sorted(inbox.glob("*.md")):
            if p.name.lower() == "readme.md":
                continue
            dest = f"{RETURNS}/{p.name}"
            if not cu.store.exists(dest):
                cu.store.write(dest, p.read_text(encoding="utf-8"))
            p.unlink()
            moved.append(p.name)
        return moved


def vkey(v: str) -> tuple:
    """Version order: 0.5.0-rc1 < 0.5.0 < 0.5.1."""
    core, _, pre = v.strip().partition("-")
    nums = []
    for part in core.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        nums.append(int(digits) if digits else 0)
    while len(nums) < 3:
        nums.append(0)
    return (*nums, 0 if pre else 1, pre)


# -------------------------------------------------------------- per-session markers --

def _session_dir() -> Path:
    d = C.state_dir() / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_filed(root: Path, project: str, rid: str, route: str) -> None:
    d = C.state_dir()
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "filed.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"root": str(root.resolve()), "project": project, "id": rid, "route": route,
                            "at": utcnow().isoformat()}) + "\n")


def filed_since(root: Path, since: str) -> list[dict]:
    """Returns filed from this checkout (this worktree, not just this project) since `since`."""
    p = C.state_dir() / "filed.jsonl"
    if not p.is_file():
        return []
    want = str(root.resolve())
    out = []
    for line in p.read_text(encoding="utf-8").splitlines()[-1000:]:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("root") == want and e.get("at", "") >= since:
            out.append(e)
    return out


def safe_session_id(sid: str) -> str:
    return "".join(ch for ch in str(sid) if ch.isalnum() or ch in "-_")[:80] or "unknown"


def load_session(sid: str) -> dict:
    p = _session_dir() / f"{safe_session_id(sid)}.json"
    try:
        st = json.loads(p.read_text(encoding="utf-8"))
        return st if isinstance(st, dict) else {"repos": {}}
    except (OSError, ValueError):
        return {"repos": {}}


def save_session(sid: str, state: dict) -> None:
    d = _session_dir()
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, d / f"{safe_session_id(sid)}.json")


def claim_once(sid: str, what: str) -> bool:
    """True the first time this session claims `what` (atomic across parallel hooks)."""
    p = _session_dir() / f"{safe_session_id(sid)}.{safe_session_id(what)}"
    try:
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _fingerprint(root: Path, rel: str) -> str:
    try:
        st = (root / rel).stat()
        return f"{st.st_mtime_ns}:{st.st_size}"
    except OSError:
        return "gone"


def snapshot(root: Path, exclude: set[str] | None = None) -> dict:
    """Where the checkout stands: HEAD, and each uncommitted file with a fingerprint (so a further
    change to a file that was already modified still counts)."""
    head = (git(root, "rev-parse", "HEAD") or "").strip()
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all") or ""
    dirty = {p: _fingerprint(root, p) for p in sorted(_paths(status) - (exclude or set()))}
    return {"head": head, "dirty": dirty, "at": utcnow().isoformat()}


def _paths(porcelain: str) -> set[str]:
    out = set()
    for line in porcelain.splitlines():
        if len(line) > 3:
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            out.add(path.strip('"'))
    return out


IGNORED_FOR_RECORD = ("collab-kit/", "tools/collab-kit/", ".claude/")


def changed_since(root: Path, snap: dict) -> tuple[list[str], list[str]]:
    """(project files changed since the snapshot, collab-kit files changed since it). Commits count
    only along the first parent and without merges, so a pull or a merge of someone else's work is
    not counted as this session's."""
    before = snap.get("dirty", {})
    if isinstance(before, list):                    # an older state file
        before = {p: "" for p in before}
    now = _paths(git(root, "status", "--porcelain=v1", "--untracked-files=all") or "")
    files = {p for p in now if p not in before or (before[p] and before[p] != _fingerprint(root, p))}
    head = (git(root, "rev-parse", "HEAD") or "").strip()
    if snap.get("head") and head and head != snap["head"]:
        # commits made since the snapshot (a pull of older work from elsewhere is not this session's)
        log = git(root, "log", "--first-parent", "--no-merges", f"--since={snap.get('at', '')}", "--format=",
                  "--name-only", f"{snap['head']}..{head}") or ""
        files |= {x for x in log.splitlines() if x}
    project = sorted(f for f in files if not f.startswith(IGNORED_FOR_RECORD))
    kit = sorted(f for f in files if f.startswith("collab-kit/"))
    return project, kit

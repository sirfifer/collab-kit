"""The project side: what an agent working in a repository uses to see and change Collab Kit.

A repository with Collab Kit installed has tools/collab-kit/ (this engine, vendored, and
project.toml). From there this module finds the project's unit (its folder in the Collab Kit
folder, or the repository's own collab-kit/), whether a back end is running, and files returns the
way the start files describe: one format, one inbox, one writer per file.

Where a return goes (DESIGN-0.5 sections 5, 7, 16):
  - a back end is running:            the unit's cloud inbox; the back end applies it.
  - no back end, home is the cloud:   the cloud inbox, and applied there at once (level 1).
  - no back end, home is the repo:    the repository's collab-kit/_returns/, applied in this
                                      checkout at once; it travels with the work when merged.
  - the cloud folder is unreachable:  the repository's collab-kit/_returns/, for the back end.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import secrets
import subprocess
from pathlib import Path

from . import config as C
from . import kit_version
from . import returns as R
from .apply import Planner, Reject, apply_return
from .store import FolderStore, Store, StoreError, SubStore, open_store
from .text import fold, slug, utcnow
from .unit import RETURNS, Unit

REPO_UNIT_DIR = "collab-kit"
HEARTBEAT = "_backend/heartbeat.json"


def git(root: Path, *args: str, timeout: float = 8) -> str | None:
    try:
        res = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return res.stdout if res.returncode == 0 else None


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

    @classmethod
    def find(cls, start: Path | str | None = None) -> "Project | None":
        root = C.find_project_root(Path(start or os.getcwd()))
        return cls(root) if root else None

    # ------------------------------------------------------------------------- stores --
    def cloud(self) -> Store | None:
        """The Collab Kit folder, if this machine is set up to reach it and it is there."""
        if self._cloud is False:
            spec = C.expand(self.machine.get("cloud", {}).get("root", ""))
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
        sub = SubStore(c, self.unit_rel)
        return Unit(sub, self.name, home=self.home) if sub.list("") else None

    def repo_unit(self) -> Unit | None:
        d = self.root / REPO_UNIT_DIR
        if self.home == "repo" or d.is_dir():
            return Unit(FolderStore(d), self.name, home="repo")
        return None

    def top_unit(self) -> Unit | None:
        c = self.cloud()
        return Unit(c, "top", home="cloud", top=True) if c else None

    def view(self) -> tuple[Unit | None, str]:
        """The freshest copy of the unit to read: the cloud folder (the back end's mirror, or the
        home itself), else the repository's collab-kit/."""
        cu = self.cloud_unit()
        if cu:
            return cu, "the Collab Kit folder"
        ru = self.repo_unit()
        if ru and (self.root / REPO_UNIT_DIR).is_dir():
            return ru, "this repository's collab-kit/ (the Collab Kit folder is not reachable from here)"
        return None, "nowhere (the Collab Kit folder is not reachable from this machine)"

    # ---------------------------------------------------------------------- back end --
    def backend(self) -> dict:
        c = self.cloud()
        if not c:
            return {"known": False, "live": False, "say": "unknown (the Collab Kit folder is not reachable from here)"}
        raw = c.read(HEARTBEAT)
        if not raw:
            return {"known": True, "live": False, "say": "none is running"}
        try:
            hb = json.loads(raw)
            last = dt.datetime.fromisoformat(hb["last_run"])
            every = int(hb.get("interval_minutes", 60))
        except (ValueError, KeyError, TypeError):
            return {"known": True, "live": False, "say": "its heartbeat file is unreadable"}
        age_min = (utcnow() - last).total_seconds() / 60
        live = age_min <= max(3 * every, 90)
        when = last.strftime("%Y-%m-%d %H:%M UTC")
        problems = hb.get("problems") or []
        say = (f"running (last ran {when}, every {every} minutes)" if live else
               f"stopped: it last ran {when}")
        if problems:
            say += f"; {len(problems)} problem(s) reported in the top-level start file"
        return {"known": True, "live": live, "say": say, "last": when}

    # ------------------------------------------------------------------------ kit version --
    def kit_status(self) -> dict:
        here = kit_version()
        src = C.expand(self.machine.get("kit", {}).get("source", ""))
        newest = None
        if src:
            v = Path(src) / "VERSION"
            if v.is_file():
                newest = v.read_text(encoding="utf-8").strip()
        behind = bool(newest) and _vtuple(newest) > _vtuple(here)
        return {"here": here, "newest": newest, "behind": behind, "source": src}

    # ------------------------------------------------------------------------- filing --
    def sender(self) -> str:
        branch = (git(self.root, "branch", "--show-current") or "").strip()
        return f"Claude Code in {self.name}" + (f" ({branch})" if branch else "")

    def file(self, text: str, *, apply_now: bool | None = None, dry_run: bool = False) -> dict:
        """Validate a return, put it where it belongs, and apply it when nobody else will."""
        rid = f"{utcnow().strftime('%Y-%m-%d-%H%M')}-{secrets.token_hex(2)}"
        ret = R.parse(text, rid + ".md")
        if fold(ret.project) != fold(self.name):
            raise Reject(f"this return says Project: {ret.project}, but this repository is '{self.name}'")
        if not ret.complete:
            raise Reject("the return does not end with 'End.'")
        backend = self.backend()
        cloud_unit = self.cloud_unit()
        top = self.top_unit()
        if backend["live"] and cloud_unit:
            route, target, now = "cloud", cloud_unit, False
        elif self.home == "cloud" and cloud_unit:
            route, target, now = "cloud", cloud_unit, True
        else:
            route, target, now = "repo", self.repo_unit() or Unit(FolderStore(self.root / REPO_UNIT_DIR), self.name, home="repo"), self.home == "repo"
        if apply_now is not None:
            now = apply_now
        # Check it against the unit as it is now, so a mistake is caught here, not by the back end.
        check_unit = cloud_unit or target
        try:
            Planner(check_unit, ret, top).plan()
        except Reject as e:
            raise Reject(f"not filed: {e}") from None
        name = f"{ret.id}.md"
        result = {"id": ret.id, "route": route, "applied": False, "minted": [], "file": None}
        if dry_run:
            result["dry_run"] = True
            return result
        target.store.mkdir(RETURNS)
        target.store.write(f"{RETURNS}/{name}", text)
        result["file"] = f"{RETURNS}/{name}"
        if now:
            out = apply_return(target, ret, name, top=top)
            result.update(applied=out.status in ("applied", "recorded", "undone"), minted=out.minted,
                          status=out.status, message=out.message)
        _log_filed(self.name, ret.id, route)
        return result

    def compose(self, rtype: str, topic: str, changes: list[str], **fields) -> str:
        rid = f"{utcnow().strftime('%Y-%m-%d-%H%M')}-{slug(topic, 32)}-{secrets.token_hex(2)}"
        return R.render_return(self.name, rid, fields.pop("sender", None) or self.sender(), rtype, topic,
                               changes, **fields)


def _vtuple(v: str) -> tuple:
    out = []
    for part in v.split("."):
        num = "".join(ch for ch in part if ch.isdigit())
        out.append(int(num) if num else 0)
    return tuple(out)


# -------------------------------------------------------------- per-session markers --

def _session_dir() -> Path:
    d = C.state_dir() / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _log_filed(project: str, rid: str, route: str) -> None:
    d = C.state_dir()
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "filed.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"project": project, "id": rid, "route": route, "at": utcnow().isoformat()}) + "\n")


def filed_since(project: str, since: str) -> list[dict]:
    p = C.state_dir() / "filed.jsonl"
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines()[-500:]:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("project") == project and e.get("at", "") >= since:
            out.append(e)
    return out


def safe_session_id(sid: str) -> str:
    return "".join(ch for ch in str(sid) if ch.isalnum() or ch in "-_")[:80] or "unknown"


def load_session(sid: str) -> dict:
    p = _session_dir() / f"{safe_session_id(sid)}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"repos": {}}


def save_session(sid: str, state: dict) -> None:
    p = _session_dir() / f"{safe_session_id(sid)}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    os.replace(tmp, p)


def claim_once(sid: str, what: str) -> bool:
    """True the first time this session claims `what` (atomic across parallel hooks)."""
    p = _session_dir() / f"{safe_session_id(sid)}.{what}"
    try:
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        return False


def snapshot(root: Path) -> dict:
    head = (git(root, "rev-parse", "HEAD") or "").strip()
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all") or ""
    return {"head": head, "dirty": sorted(_paths(status)), "at": utcnow().isoformat()}


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
    """(project files changed since the snapshot, collab-kit files changed since it)."""
    now = snapshot(root)
    files = set(_paths(git(root, "status", "--porcelain=v1", "--untracked-files=all") or "")) - set(snap.get("dirty", []))
    if snap.get("head") and now["head"] and now["head"] != snap["head"]:
        diff = git(root, "diff", "--name-only", f"{snap['head']}..{now['head']}") or ""
        files |= {x for x in diff.splitlines() if x}
    project = sorted(f for f in files if not f.startswith(IGNORED_FOR_RECORD))
    kit = sorted(f for f in files if f.startswith("collab-kit/"))
    return project, kit

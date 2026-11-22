"""Settings: one file per machine (where the Collab Kit folder is reachable from here, whose it is),
one file per project (committed: its name, its unit, its home), and one for a back end.

Machine:  $COLLAB_KIT_CONFIG, else  ~/.config/collab-kit/config.toml  ($XDG_CONFIG_HOME honoured;
          %APPDATA%\\collab-kit\\config.toml on Windows)

    human = "Sam"                                   # who the conversations work with
    [cloud]
    root = "~/Library/CloudStorage/GoogleDrive-sam@example.com/My Drive/Collab Kit"
                                                    # a folder, or "rclone:gdrive:Collab Kit"
    [kit]
    source = "~/src/collab-kit"                     # the newest kit, for "is this project behind?"

Project:  <repo>/tools/collab-kit/project.toml  (committed; written by install.py)

    [project]
    name = "garden-planner"                         # the repository's name, and the project's folder
    unit = "projects/garden-planner/collab-kit"     # inside the Collab Kit folder
    home = "cloud"                                  # "cloud" (the folder is the truth) or "repo"
    [session]
    stop_check = true                               # ask (at most every 15 minutes, 3 times) before a session ends without a record

Back end: <config dir>/backend.toml  (machine-local; every setting is in backend.py). One table of
          it is read here too, so `ck doctor` can check it: `[new_projects]`, off unless set.

    [new_projects]
    repositories = "~/dev"                          # a new project also gets a git repository here
    github_owner = "sam"                            # and a private GitHub repository under this account
    per_day = 3                                     # at most this many repositories a day
"""
from __future__ import annotations

import os
import re
import sys
import tomllib
from pathlib import Path

PROJECT_FILE = Path("tools") / "collab-kit" / "project.toml"


def _home() -> Path:
    return Path.home()


def config_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", _home() / "AppData" / "Roaming")) / "collab-kit"
    return Path(os.environ.get("XDG_CONFIG_HOME", _home() / ".config")) / "collab-kit"


def state_dir() -> Path:
    """Machine-local scratch: session markers for the hooks. Never synced, never committed."""
    if os.environ.get("COLLAB_KIT_STATE"):
        return Path(os.environ["COLLAB_KIT_STATE"])
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", _home() / "AppData" / "Local")) / "collab-kit" / "state"
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / "collab-kit" / "state"
    return Path(os.environ.get("XDG_STATE_HOME", _home() / ".local" / "state")) / "collab-kit"


def machine_file() -> Path:
    return Path(os.environ["COLLAB_KIT_CONFIG"]) if os.environ.get("COLLAB_KIT_CONFIG") else config_dir() / "config.toml"


def load_toml(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"collab-kit: {path} is not valid TOML: {e}") from None


def machine() -> dict:
    cfg = load_toml(machine_file())
    cfg.setdefault("human", "the owner")
    cfg.setdefault("cloud", {})
    cfg.setdefault("kit", {})
    return cfg


def expand(p: str) -> str:
    return os.path.expandvars(os.path.expanduser(p)) if p and not p.startswith("rclone:") else p


def find_project_root(start: Path) -> Path | None:
    """The nearest folder at or above `start` that has tools/collab-kit/project.toml."""
    try:
        start = start.resolve()
    except OSError:
        return None
    for d in [start, *start.parents]:
        if (d / PROJECT_FILE).is_file():
            return d
    return None


def project(root: Path) -> dict:
    cfg = load_toml(root / PROJECT_FILE)
    p = cfg.setdefault("project", {})
    p.setdefault("name", root.name)
    p.setdefault("unit", f"projects/{p['name']}/collab-kit")
    p.setdefault("home", "cloud")
    cfg.setdefault("session", {}).setdefault("stop_check", True)
    return cfg


# ------------------------------------------------- a new project's repository (off unless set) --

NEW_PROJECT_KEYS = ("repositories", "github_owner", "per_day")
REPOSITORIES_PER_DAY = 3
GITHUB_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


def backend_file() -> Path:
    return config_dir() / "backend.toml"


def new_projects(cfg: dict) -> tuple[dict | None, str | None]:
    """The `[new_projects]` table of a back end's config (DESIGN-0.5 section 25), checked.

    (None, None): not set, so a new project is a folder and nothing else, as before.
    (None, why):  set, but not usable; nothing is made until it is corrected (never a guess).
    (settings, None): {"repositories": Path, "github_owner": str or "", "per_day": int}.

    There is no key for visibility: a repository the kit creates is private, always."""
    t = cfg.get("new_projects")
    if t is None:
        return None, None
    if not isinstance(t, dict):
        return None, "[new_projects] must be a table"
    extra = sorted(set(t) - set(NEW_PROJECT_KEYS))
    if extra:
        return None, (f"[new_projects] has no setting {', '.join(repr(k) for k in extra)} (it has: "
                      f"{', '.join(NEW_PROJECT_KEYS)}; a repository it creates is always private)")
    root, owner, per_day = t.get("repositories", ""), t.get("github_owner", ""), t.get("per_day", REPOSITORIES_PER_DAY)
    if not isinstance(root, str) or not isinstance(owner, str):
        return None, "[new_projects] repositories and github_owner are text"
    if not root.strip():
        if owner.strip():
            return None, ("[new_projects] github_owner needs repositories (the folder where the local "
                          "repository is made)")
        return None, None
    if owner.strip() and not GITHUB_OWNER_RE.fullmatch(owner.strip()):
        return None, "[new_projects] github_owner is a GitHub account's name (letters, digits, single hyphens)"
    if isinstance(per_day, bool) or not isinstance(per_day, int) or not 0 <= per_day <= 20:
        return None, "[new_projects] per_day is a whole number from 0 to 20"
    path = Path(expand(root.strip()))
    if not path.is_absolute():
        return None, "[new_projects] repositories is a full path (or starts with ~)"
    return {"repositories": path, "github_owner": owner.strip(), "per_day": per_day}, None


def new_projects_ready(settings: dict) -> list[str]:
    """What stops this machine from making a new project's repository, each with its fix. Empty when
    it is ready. With github_owner set it asks `gh` whether it is signed in (one call to GitHub)."""
    import shutil
    import subprocess
    out = []
    root = settings["repositories"]
    if not root.is_dir():
        out.append(f"{root} is not a folder on this machine: create it, or correct [new_projects] repositories")
    elif not os.access(root, os.W_OK):
        out.append(f"{root} cannot be written by the user the back end runs as")
    if not shutil.which("git"):
        out.append("git is not installed (or not on the back end's PATH)")
    if settings["github_owner"]:
        gh = shutil.which("gh")
        if not gh:
            out.append("the GitHub CLI, gh, is not installed (or not on the back end's PATH): install it "
                       "(https://cli.github.com), then sign in with `gh auth login`")
        else:
            try:
                res = subprocess.run([gh, "auth", "status", "--hostname", "github.com"], capture_output=True,
                                     text=True, timeout=30)
                ok = res.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                ok = False
            if not ok:
                out.append("gh is not signed in to github.com (or GitHub cannot be reached): run `gh auth login` "
                           "on this machine, as the user the back end runs as, and check with `gh auth status`")
    return out

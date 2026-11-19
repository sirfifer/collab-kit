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
"""
from __future__ import annotations

import os
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

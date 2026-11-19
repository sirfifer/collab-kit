"""Imported first by every test module: the tests never read or write this machine's real Collab Kit.

Without it, code under test that reads the machine config (install_project, ck) would find the real
~/.config/collab-kit/config.toml and reach the person's live Collab Kit folder (found 2026-11-19 by a
review: the public example's generator did). A test that needs a config sets its own and, when done,
calls restore() rather than removing the variables.
"""
import atexit
import os
import shutil
import tempfile
from pathlib import Path

_BASE = Path(tempfile.mkdtemp(prefix="ck-tests-"))
atexit.register(shutil.rmtree, _BASE, True)
SAFE = {
    "COLLAB_KIT_CONFIG": str(_BASE / "no-machine-config.toml"),   # never created: no machine config
    "COLLAB_KIT_STATE": str(_BASE / "state"),
    "COLLAB_KIT_DATA": str(_BASE / "data"),
    "XDG_CONFIG_HOME": str(_BASE / "xdg-config"),
}


def restore() -> None:
    os.environ.update(SAFE)


restore()

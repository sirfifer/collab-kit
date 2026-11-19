#!/usr/bin/env python3
"""ck: the Collab Kit command (see collab_kit/cli.py). Standard library only, Python 3.11+."""
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    sys.exit("Collab Kit needs Python 3.11 or later")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True       # never leave __pycache__ in a project's tools/collab-kit/


def _damaged(err: BaseException) -> int:
    """The engine beside this file is incomplete or broken: say how to repair it, never a traceback."""
    kit = "<the kit's checkout>"
    try:
        import os
        import tomllib
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        cfg = os.environ.get("COLLAB_KIT_CONFIG") or (
            str(Path(os.environ.get("APPDATA", "")) / "collab-kit" / "config.toml") if os.name == "nt"
            else str(Path(base) / "collab-kit" / "config.toml"))
        with open(cfg, "rb") as f:
            kit = os.path.expanduser(os.path.expandvars(tomllib.load(f).get("kit", {}).get("source") or kit))
    except Exception:                                    # noqa: BLE001 (best effort: the message matters)
        pass
    if HERE.name == "collab-kit":                       # a project's copy: tools/collab-kit/
        fix = f"python3 \"{kit}/install.py\" project \"{HERE.parent.parent}\", then tools/collab-kit/ck doctor"
    elif (HERE.parent / "install.py").is_file():         # the kit's own checkout
        fix = f"restore the checkout: git -C \"{HERE.parent}\" status, then git -C \"{HERE.parent}\" checkout -- engine"
    else:                                                # this machine's copy for the user-level hooks
        fix = f"python3 \"{kit}/install.py\" machine --user-hooks"
    msg = (f"Collab Kit: the engine in {HERE} is damaged or incomplete ({type(err).__name__}: {err}). "
           f"Repair it (the installer manages it; never edit it by hand): {fix}")
    if len(sys.argv) > 1 and sys.argv[1] == "hook":
        print(msg)                                       # a hook's output reaches the agent; never block it
        return 0
    print(msg, file=sys.stderr)
    return 3


try:
    from collab_kit.cli import main  # noqa: E402
except Exception as e:                                   # noqa: BLE001
    sys.exit(_damaged(e))

if __name__ == "__main__":
    sys.exit(main())

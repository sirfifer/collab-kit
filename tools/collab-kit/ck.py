#!/usr/bin/env python3
"""ck: the Collab Kit command (see collab_kit/cli.py). Standard library only, Python 3.11+."""
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    sys.exit("Collab Kit needs Python 3.11 or later")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True       # never leave __pycache__ in a project's tools/collab-kit/

from collab_kit.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

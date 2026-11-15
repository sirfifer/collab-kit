"""Collab Kit 0.5 engine: plain-file channels (inbox, agenda, knowledge, WIP) applied by scripts.

Standard library only (Python 3.11+), on macOS, Linux, and Windows. No module here calls an AI:
the back end files, indexes, and sorts; every judgment belongs to a conversation (VISION.md).
"""
from __future__ import annotations

from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent.parent   # the kit checkout (or tools/collab-kit/ in a project)


def kit_version() -> str:
    """The version of the engine that is running: VERSION beside the package (vendored copies carry it)."""
    for p in (Path(__file__).resolve().parent / "VERSION", KIT_ROOT / "VERSION"):
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()
    return "0.0.0"


__all__ = ["kit_version", "KIT_ROOT"]

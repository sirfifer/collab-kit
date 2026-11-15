"""The files a unit starts with, rendered from templates/ beside this module."""
from __future__ import annotations

import re
from pathlib import Path

from . import kit_version

TEMPLATES = Path(__file__).resolve().parent / "templates"
_PH = re.compile(r"\{\{(\w+)\}\}")
_HUMAN = {"name": "the owner"}


def set_human(name: str) -> None:
    _HUMAN["name"] = name or "the owner"


def render(template: str, **ctx) -> str:
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    ctx = {"kit_version": kit_version(), "human": _HUMAN["name"], **ctx}

    def sub(m):
        if m.group(1) not in ctx:
            raise KeyError(f"template {template} needs {{{{{m.group(1)}}}}}")
        return str(ctx[m.group(1)])
    return _PH.sub(sub, text)


HOME_NOTES = {
    "cloud": ("**Home: this folder.** It is the truth for this project: there is no repository copy to "
              "keep in step. Change it the way the top-level start file says (write a return; apply it "
              "yourself when no back end runs)."),
    "repo": ("**Home: the project's repository.** `knowledge/` and `agenda/` here are copies the back end "
             "keeps in step with the repository. **Do not edit them here**: file a return in `_returns/`; "
             "the back end applies it in the repository and copies the result back."),
}


def project_start_file(name: str, about: str, spoken: str, *, home: str = "cloud") -> str:
    said = ", ".join(f"\"{s.strip()}\"" for s in spoken.split(",") if s.strip()) or f"\"{name}\""
    return render("project-start.md", name=name, about=about.rstrip(".") + ".", spoken=said,
                  home_note=HOME_NOTES[home])


def returns_readme(name: str) -> str:
    return render("returns-readme.md", name=name)


def top_start_file() -> str:
    return render("top-start.md")


BLOCK_RE = re.compile(r"(<!-- collab-kit:begin (?P<name>[\w-]+) -->\n)(?P<body>.*?)(\n?<!-- collab-kit:end (?P=name) -->)", re.S)


def replace_block(text: str, name: str, body: str) -> str | None:
    """Replace the text between <!-- collab-kit:begin NAME --> and its end marker; None if absent."""
    found = False

    def sub(m):
        nonlocal found
        if m.group("name") != name:
            return m.group(0)
        found = True
        return m.group(1) + body.strip("\n") + "\n" + m.group(4).lstrip("\n")
    out = BLOCK_RE.sub(sub, text)
    return out if found else None


def get_block(text: str, name: str) -> str | None:
    for m in BLOCK_RE.finditer(text):
        if m.group("name") == name:
            return m.group("body")
    return None

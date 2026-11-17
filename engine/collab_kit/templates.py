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
    ctx = {"kit_version": kit_version(), "kit_series": kit_series(), "human": _HUMAN["name"], **ctx}

    def sub(m):
        if m.group(1) not in ctx:
            raise KeyError(f"template {template} needs {{{{{m.group(1)}}}}}")
        return str(ctx[m.group(1)])
    return _PH.sub(sub, text)


def kit_series() -> str:
    """The version a start file names: major and minor only ("0.5"), so a patch release never changes
    a start file (they are meant to stay put; what is going on lives on the agenda)."""
    return ".".join(kit_version().split(".")[:2])


# The one line of the top-level start file that depends on how the folder is set up. It changes when
# the folder is set up and when a back end first runs for it (the back end sets it, once), never as
# a report: the back end's health is at the top of agenda/00-PRESSING.md.
SETUP_TEXT = {
    "none": ("**No back end runs for this folder.** You apply changes yourself, as described below (\"Changing "
             "anything\"): what you write is what exists."),
    "backend": ("**A back end runs for this folder.** File returns and stop: it applies them within a few minutes of "
                "arriving, and reports on the agenda anything it could not file. Never edit an agenda or knowledge "
                "yourself. Its health is at the top of `agenda/00-PRESSING.md`."),
}


SETUP_BACKEND_MARK = "**A back end runs for this folder.**"
SETUP_NONE_MARK = "**No back end runs for this folder.**"


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
    about = about.strip().rstrip(".")
    return render("project-start.md", name=name, about=(about + ".") if about else "", spoken=said,
                  home_note=HOME_NOTES[home])


def returns_readme(name: str) -> str:
    return render("returns-readme.md", name=name)


def top_start_file(setup: str = "none") -> str:
    return render("top-start.md", setup=SETUP_TEXT[setup])


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

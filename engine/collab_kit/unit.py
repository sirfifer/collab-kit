"""A unit: the top level, or one project's collab-kit/ folder. Same shape at every level:

    00-START-HERE.md   _returns/   agenda/   knowledge/   WIP/

A unit lives in a Store. Its home is either the cloud folder (versioning by name: every edit
keeps the older file in that folder's _versions/) or a repository (git is the history).
"""
from __future__ import annotations

import dataclasses
import re

from .store import Entry, Store
from .text import join_front_matter, set_front_matter, sha, split_front_matter, stamp, today

START = "00-START-HERE.md"
RETURNS = "_returns"
AGENDA = "agenda"
KNOWLEDGE = "knowledge"
WIP = "WIP"
VERSIONS = "_versions"
APPLIED = f"{RETURNS}/applied"
FAILED = f"{RETURNS}/failed"
STRAYS = f"{RETURNS}/strays"
CHANNELS = (RETURNS, AGENDA, KNOWLEDGE, WIP)
ITEM_FILE_RE = re.compile(r"^W-(\d{3,5})(?:-[^/]*)?\.md$")
VERSION_RE = re.compile(r"^(?P<stem>.+)\.(?P<ts>\d{8}T\d{6}Z)(?P<ext>\.[^.]+)$")
GENERATED_MARK = re.compile(r"\n<!-- (?:kb|collab-kit):generated:start")
RETURN_SUFFIXES = (".md", ".txt")
# Knowledge files produced by tools/kb/kb.py build in a repository-homed unit; never written by a return.
GENERATED_KNOWLEDGE = {"01-INDEX.md", "02-RECENT.md", "graph.json"}
GENERATED_KNOWLEDGE_DIRS = {"documents", "full"}


@dataclasses.dataclass
class Item:
    id: str
    num: int
    path: str            # relative to the unit
    fields: dict
    raw_fm: str
    body: str
    text: str

    @property
    def title(self) -> str:
        return str(self.fields.get("title", ""))

    @property
    def status(self) -> str:
        s = str(self.fields.get("status", "open")).lower()
        return {"done": "settled", "closed": "settled", "wontfix": "dropped"}.get(s, s)

    @property
    def is_open(self) -> bool:
        return self.status in ("open", "in-progress")

    @property
    def importance(self) -> int:
        try:
            return int(self.fields.get("importance", 3))
        except (TypeError, ValueError):
            return 3

    @property
    def due(self) -> str:
        return str(self.fields.get("due", "") or "")

    @property
    def kind(self) -> str:
        return str(self.fields.get("kind", "task"))

    @property
    def blocks(self) -> str:
        """The item whose work waits for this one (a question an agent is blocked on), or ""."""
        m = re.fullmatch(r"W-?(\d{1,5})", str(self.fields.get("blocks", "") or "").strip(), re.I)
        return f"W-{int(m.group(1)):03d}" if m else ""


class Unit:
    def __init__(self, store: Store, name: str, *, home: str = "cloud", top: bool = False):
        self.store = store
        self.name = name                      # "top" for the top level, else the project's folder name
        self.home = home                      # "cloud" or "repo"
        self.top = top

    def __repr__(self):
        return f"Unit({self.name}, home={self.home}, {self.store!r})"

    @property
    def versioned(self) -> bool:
        return self.home == "cloud"

    # ---------------------------------------------------------------------------- reading --
    def read(self, rel: str) -> str | None:
        return self.store.read(rel)

    def items(self) -> list[Item]:
        out = []
        for e in self.store.files(AGENDA):
            m = ITEM_FILE_RE.match(e.name)
            if not m:
                continue
            text = self.store.read(f"{AGENDA}/{e.name}") or ""
            try:
                fields, raw, body = split_front_matter(text)
            except ValueError:
                fields, raw, body = {}, "", text
            num = int(m.group(1))
            out.append(Item(f"W-{num:03d}", num, f"{AGENDA}/{e.name}", fields, raw, body, text))
        out.sort(key=lambda i: i.num)
        return out

    def item(self, wid: str) -> Item | None:
        found = [i for i in self.items() if i.id == wid]
        return found[0] if found else None

    def used_numbers(self) -> set[int]:
        nums = set()
        for e in self.store.files(AGENDA):
            m = ITEM_FILE_RE.match(e.name)
            if m:
                nums.add(int(m.group(1)))
        for e in self.store.files(f"{AGENDA}/{VERSIONS}"):
            m = re.match(r"^W-(\d{3,5})", e.name)
            if m:
                nums.add(int(m.group(1)))
        return nums

    def pending_returns(self) -> list[Entry]:
        out = []
        for e in self.store.list(RETURNS):
            if e.is_dir or e.name.startswith(("_", ".")) or e.name.lower() == "readme.md":
                continue
            if e.native or e.name.lower().endswith(RETURN_SUFFIXES):
                out.append(e)
            else:
                out.append(e)   # an unexpected file: the back end moves it to strays
        return out

    def wip_notes(self) -> list[Entry]:
        return [e for e in self.store.files(WIP) if not e.name.startswith((".", "_"))]

    def ledger_names(self) -> set[str]:
        return {e.name[: -len(".ledger.json")] for e in self.store.files(APPLIED) if e.name.endswith(".ledger.json")}


# ------------------------------------------------------------------- editing item files --

def render_item(wid: str, title: str, *, kind="task", importance=3, status="open", due="", project="",
                body: str | None = None, log: list[str] | None = None, blocks: str = "") -> str:
    fields = {"id": wid, "title": title, "kind": kind, "importance": int(importance),
              "status": status, "due": due or "", "project": project or ""}
    if blocks:                                    # only a question that blocks an item carries the field
        fields["blocks"] = blocks
    fm = set_front_matter("", fields)
    if body and re.search(r"^## ", body, re.M):
        text = body.strip() + "\n"
    else:
        text = f"## What's needed\n{(body or title).strip()}\n\n## What we know so far\n\n## Done when\n"
    if not re.search(r"^## Log\s*$", text, re.M):
        text += "\n## Log\n"
    for line in log or []:
        text = append_log_text(text, line)
    return join_front_matter(fm, "\n" + text)


def append_log_text(body: str, entry: str, date: str | None = None) -> str:
    """Add '- DATE: entry' at the end of the ## Log section (before any generated block)."""
    first, *rest = entry.strip().split("\n")
    line = f"- {date or today()}: {first.strip()}"
    if rest:
        line += "\n" + "\n".join("  " + r.rstrip() for r in rest)
    gen = GENERATED_MARK.search(body)
    head, tail = (body[: gen.start()], body[gen.start():]) if gen else (body, "")
    m = re.search(r"^## Log\s*$", head, re.M)
    if not m:
        head = head.rstrip("\n") + "\n\n## Log\n" + line + "\n"
    else:
        nxt = re.search(r"^## ", head[m.end():], re.M)
        end = m.end() + nxt.start() if nxt else len(head)
        section = head[:end].rstrip("\n")
        head = section + "\n" + line + "\n" + ("\n" + head[end:] if nxt else "")
    return head + tail


def edit_item_text(item: Item, changes: dict, log: str | None) -> str:
    raw = set_front_matter(item.raw_fm, changes) if changes else item.raw_fm
    body = item.body
    if log:
        body = append_log_text(body, log)
    return join_front_matter(raw, body) if raw else body


# --------------------------------------------------------------------------- versioning --

def version_name(rel: str, when: str | None = None) -> str:
    folder, _, base = rel.rpartition("/")
    stem, dot, ext = base.rpartition(".")
    if not dot:
        stem, ext = base, "md"
    vname = f"{stem}.{when or stamp()}.{ext}"
    return f"{folder}/{VERSIONS}/{vname}" if folder else f"{VERSIONS}/{vname}"


def write_versioned(unit: Unit, rel: str, text: str) -> str | None:
    """Write a file; in a cloud-homed unit keep the older content in _versions/ first.
    Returns the version's path (or None). Copy-then-replace: a crash leaves an extra version,
    never a missing file."""
    store = unit.store
    current = store.read(rel)
    if current == text:
        return None
    vpath = None
    if current is not None and unit.versioned:
        vpath = version_name(rel)
        n = 1
        while store.exists(vpath):
            n += 1
            vpath = version_name(rel, stamp() + f"-{n}")
        store.copy(rel, vpath)
    store.write(rel, text)
    return vpath


def retire(unit: Unit, rel: str) -> str:
    """Move a file into its folder's _versions/ (the back end never deletes)."""
    vpath = version_name(rel)
    n = 1
    while unit.store.exists(vpath):
        n += 1
        vpath = version_name(rel, stamp() + f"-{n}")
    unit.store.move(rel, vpath)
    return vpath


def content_hash(text: str | None) -> str | None:
    return None if text is None else sha(text)

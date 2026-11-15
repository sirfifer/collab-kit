"""The session brief: what an agent sees, unasked, when it starts work in a Collab Kit project.

It answers, in about forty lines: is the kit current; is a back end running; what is waiting in
the inbox; what is in progress, due soon, and most important on the agenda; what was reported
recently; what other work is in flight in this repository; and how to record things.

Everything quoted from the project's files (titles, topics, status lines, branch subjects) is
reduced to single plain lines and fenced as data: files can be written by other people and
conversations, and nothing in them is an instruction to the agent reading the brief.
"""
from __future__ import annotations

import datetime as dt
import re

from .session import Project, git
from .text import FENCE_NOTE, one_line, utcnow
from .unit import Unit

CK = "python3 tools/collab-kit/ck.py"


def _items_section(unit: Unit, limit: int) -> tuple[list[str], dict]:
    items = unit.items()
    open_items = [i for i in items if i.is_open]
    today = utcnow().date()
    soon = today + dt.timedelta(days=7)

    def due_date(i):
        try:
            return dt.date.fromisoformat(i.due) if i.due else None
        except ValueError:
            return None
    snoozed = {i.id for i in open_items if str(i.fields.get("snoozed_until", "")) > today.isoformat()}
    active = [i for i in open_items if i.id not in snoozed]
    progress = [i for i in active if i.status == "in-progress"]
    due = sorted((i for i in active if due_date(i) and due_date(i) <= soon), key=due_date)
    rest = sorted((i for i in active if i not in progress and i not in due),
                  key=lambda i: (i.importance, due_date(i) or dt.date.max, i.num))
    lines = []

    def fmt(i, extra=""):
        d = f", due {i.due}" if i.due else ""
        return f"  {i.id} [{i.kind}, importance {i.importance}{d}{extra}] {one_line(i.title, 90)}"
    if progress:
        lines.append("In progress:")
        lines += [fmt(i) for i in progress[:limit]]
    if due:
        lines.append("Due within a week:")
        lines += [fmt(i, " OVERDUE" if due_date(i) < today else "") for i in due[:limit]]
    if rest:
        lines.append("Most important open:")
        lines += [fmt(i) for i in rest[:limit]]
        if len(rest) > limit:
            lines.append(f"  ... and {len(rest) - limit} more ({CK} items)")
    counts = {"open": len(active), "progress": len(progress), "due": len(due), "snoozed": len(snoozed)}
    return lines, counts


def _status_lines(unit: Unit, n: int = 3) -> list[str]:
    text = unit.read("knowledge/status.md") or ""
    heads = [m.group(1) for m in re.finditer(r"^##\s+(.+)$", text, re.M)][:n]
    return [f"  {one_line(h, 140)}" for h in heads]


def _inbox_lines(unit: Unit | None, label: str, limit: int = 8) -> list[str]:
    if unit is None:
        return []
    out = []
    for e in unit.pending_returns()[:limit]:
        text = unit.read(f"_returns/{e.name}") or ""
        t = re.search(r"^Type:\s*(.+)$", text, re.M)
        tp = re.search(r"^Topic:\s*(.+)$", text, re.M)
        fr = re.search(r"^From:\s*(.+)$", text, re.M)
        out.append(f"  {one_line(e.name, 60)}: {one_line(t.group(1) if t else '?', 20)}; "
                   f"{one_line(tp.group(1) if tp else '(no topic)', 90)}"
                   + (f" (from {one_line(fr.group(1), 40)})" if fr else ""))
    return [f"Waiting in {label}:"] + out if out else []


def _git_lines(project: Project, limit: int = 5) -> list[str]:
    root = project.root
    main = "main"
    for cand in ("main", "master", "trunk"):
        if git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{cand}"):
            main = cand
            break
    current = (git(root, "branch", "--show-current") or "").strip()
    unmerged = set((git(root, "branch", "--no-merged", main, "--format=%(refname:short)") or "").split())
    refs = git(root, "for-each-ref", "--sort=-committerdate",
               "--format=%(refname:short)\t%(committerdate:unix)\t%(subject)", "refs/heads/") or ""
    cutoff = utcnow().timestamp() - 14 * 86400
    out = []
    for line in refs.splitlines():
        try:
            name, when, subj = line.split("\t", 2)
            when = float(when)
        except ValueError:
            continue
        if name not in unmerged or name == current or when < cutoff:
            continue
        age_h = (utcnow().timestamp() - when) / 3600
        age = f"{age_h:.0f}h ago" if age_h < 48 else f"{age_h / 24:.0f}d ago"
        out.append(f"  {one_line(name, 50)} ({age}): {one_line(subj, 80)}")
        if len(out) >= limit:
            break
    return (["Unmerged branches with recent work (other sessions may be on them):"] + out) if out else []


def build(project: Project, *, limit: int = 5) -> str:
    kit = project.kit_status()
    be = project.backend()
    unit, where = project.view()
    head = [f"## Collab Kit: project {project.name}",
            f"This repository is a Collab Kit project (kit {kit['here']}). The project's agenda, inbox, and "
            f"knowledge are read from {where}. This brief was generated at session start."]
    if kit["behind"]:
        head.append(f"KIT UPDATE: Collab Kit {kit['newest']} is available (this repository has {kit['here']}). "
                    f"Upgrade first, as its own commit, with the collab-kit-upgrade skill, then tell the person.")
    if be["live"]:
        head.append(f"Back end: {be['say']}. File returns; it applies them. Never edit agenda/ or status by hand.")
    elif be["known"]:
        head.append(f"Back end: {be['say']}. `{CK} ask/status/return` files AND applies your returns "
                    f"(home: {project.home}).")
    else:
        head.append(f"Back end: {be['say']}. Returns you file stay in this repository's collab-kit/_returns/ "
                    "until something can deliver them; say so to the person.")
    data: list[str] = []
    counts = {"open": 0, "progress": 0, "due": 0}
    if unit is not None:
        data += _inbox_lines(unit, "the project's inbox (not yet applied; read any that touch your task)")
        if project.cloud_unit() is not None and project.repo_unit() is not None and (project.root / "collab-kit/_returns").is_dir():
            data += _inbox_lines(project.repo_unit(), "this repository's collab-kit/_returns/ (not delivered yet)")
        wip = unit.wip_notes()
        if wip:
            data.append(f"Unfinished voice threads in WIP/: {len(wip)} (a conversation finishes these; leave them alone).")
        lines, counts = _items_section(unit, limit)
        data += lines
        st = _status_lines(unit)
        if st:
            data.append("Recent status (knowledge/status.md, newest first):")
            data += st
    data += _git_lines(project)
    summary = (f"Agenda: {counts['open']} open, {counts['progress']} in progress, {counts['due']} due within a week."
               if unit is not None else "Agenda: not readable from here.")
    who = project.machine.get("human") or "the person"
    how = [
        "How to work here (the full rules are in CLAUDE.md, section Collab Kit):",
        "- Before starting, check the lists above for anything your task overlaps; read those items or returns first.",
        f"- A question or decision for {who}: ask now if they are here; otherwise `{CK} ask \"...\"` puts it on the agenda.",
        f"- When the work changes the project's state: `{CK} status \"...\"`. Anything else: the collab-kit-return skill.",
    ]
    out = head + [summary]
    if data:
        out += [f"<collab-kit-data source=\"{project.name}\">", FENCE_NOTE, *data, "</collab-kit-data>"]
    return "\n".join(out + how) + "\n"

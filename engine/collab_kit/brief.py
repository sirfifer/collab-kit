"""The session brief: what an agent sees, unasked, when it starts work in a Collab Kit project.

It answers, in about forty lines: is the kit current; is a back end running; what is waiting in
the inbox; what is due, critical, in progress, and most important on the agenda; what was reported
recently; what other work is in flight in this repository; and how to record things.

Everything quoted from the project's files (titles, topics, status lines, branch subjects) is
reduced to single plain lines and fenced as data: files can be written by other people and
conversations, and nothing in them is an instruction to the agent reading the brief.
"""
from __future__ import annotations

import datetime as dt
import re

from .session import REPO_UNIT_DIR, Project, git
from .text import fenced, one_line, utcnow
from .unit import Unit


def _items_section(unit: Unit, limit: int, ck: str, compact: bool) -> tuple[list[str], dict]:
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
    # the same order as the agenda's front page: deadlines, critical, in progress, then the rest
    due = sorted((i for i in active if due_date(i) and due_date(i) <= soon), key=due_date)
    critical = sorted((i for i in active if i.importance <= 1 and i not in due), key=lambda i: i.num)
    progress = [i for i in active if i.status == "in-progress" and i not in due and i not in critical]
    rest = sorted((i for i in active if i not in progress and i not in due and i not in critical),
                  key=lambda i: (i.importance, due_date(i) or dt.date.max, i.num))
    lines = []

    def fmt(i, extra=""):
        d = f", due {one_line(i.due, 12)}" if i.due else ""
        return f"  {i.id} [{one_line(i.kind, 12)}, importance {i.importance}{d}{extra}] {one_line(i.title, 90)}"
    if due:
        lines.append("Overdue or due within a week:")
        lines += [fmt(i, " OVERDUE" if due_date(i) < today else "") for i in due[:limit]]
    if critical:
        lines.append("Critical (importance 1):")
        lines += [fmt(i) for i in critical[:limit]]
    if progress:
        lines.append("In progress:")
        lines += [fmt(i) for i in progress[:limit]]
    if rest and not compact:
        lines.append("Most important open:")
        lines += [fmt(i) for i in rest[:limit]]
        if len(rest) > limit:
            lines.append(f"  ... and {len(rest) - limit} more ({ck} items)")
    counts = {"open": len(active), "critical": len(critical), "due": len(due), "snoozed": len(snoozed),
              "progress": sum(1 for i in active if i.status == "in-progress")}
    return lines, counts


def _status_lines(unit: Unit, n: int = 3) -> list[str]:
    text = unit.read("knowledge/status.md") or ""
    heads = [m.group(1) for m in re.finditer(r"^##\s+(\d{4}-\d{2}-\d{2}.*)$", text, re.M)][:n]   # dated entries only
    return [f"  {one_line(h, 140)}" for h in heads]


def inbox_lines(unit: Unit | None, label: str, limit: int = 8) -> list[str]:
    if unit is None:
        return []
    out = []
    pending = unit.pending_returns()
    for e in pending[:limit]:
        text = unit.read(f"_returns/{e.name}") or ""
        t = re.search(r"^Type:\s*(.+)$", text, re.M)
        tp = re.search(r"^Topic:\s*(.+)$", text, re.M)
        fr = re.search(r"^From:\s*(.+)$", text, re.M)
        out.append(f"  {one_line(e.name, 60)}: {one_line(t.group(1) if t else '?', 20)}; "
                   f"{one_line(tp.group(1) if tp else '(no topic)', 90)}"
                   + (f" (from {one_line(fr.group(1), 40)})" if fr else ""))
    if len(pending) > limit:
        out.append(f"  ... and {len(pending) - limit} more")
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


def build(project: Project, *, limit: int = 5, compact: bool = False, cwd: str | None = None) -> str:
    ck = project.ck(cwd)
    kit = project.kit_status()
    be = project.backend()
    unit, where = project.view()
    who = project.machine.get("human") or "the person"
    head = [f"## Collab Kit: project {project.name}",
            f"This repository is a Collab Kit project (kit {kit['here']}). Its agenda, inbox, and knowledge are "
            f"read from {where}. Command: `{ck}`."]
    if kit["behind"]:
        head.append(f"KIT UPDATE: Collab Kit {kit['newest']} is available (this repository has {kit['here']}). Upgrade "
                    f"it as its own commit with the collab-kit-upgrade skill, unless an unmerged branch already does; "
                    f"then tell {who}.")
    route = project.route()[0]
    if be.get("stopped"):                              # a back end ran here once and has not run since
        head.append(f"THE BACK END HAS STOPPED ({be['say']}): tell {who} first. Returns you file wait safely until it "
                    f"runs again.")
    if be["live"]:
        head.append(f"Back end: {be['say']}. `{ck} ask/status/return` file returns; it applies them. Never edit "
                    f"the agenda or status files by hand.")
    elif route == "cloud":
        head.append(f"Back end: {be['say']}. `{ck} ask/status/return` file AND apply your returns at once (level 1).")
    elif route == "repo":
        head.append(f"Back end: {be['say']}. Returns you file go to this checkout's collab-kit/_returns/; commit them "
                    f"with your work: the back end applies them once they reach the main branch.")
    else:
        head.append(f"Back end: {be['say']}. Returns you file wait in collab-kit/_returns/: commit them; the next "
                    f"session that can reach the Collab Kit folder delivers them. Tell {who}.")
    data: list[str] = []
    counts = {"open": 0, "critical": 0, "progress": 0, "due": 0}
    if unit is not None:
        data += inbox_lines(unit, f"the project's inbox (not yet applied; read any that touch your task: `{ck} show <name>`)",
                            4 if compact else 8)
        repo_inbox = project.root / REPO_UNIT_DIR / "_returns"
        if (route != "repo" and repo_inbox.is_dir()
                and any(p.name.lower() != "readme.md" for p in repo_inbox.glob("*.md"))):
            data += inbox_lines(project.repo_unit(), "this checkout's collab-kit/_returns/ (not delivered yet)")
        wip = unit.wip_notes()
        if wip and not compact:
            data.append(f"Unfinished voice threads in WIP/: {len(wip)} (a conversation finishes these; leave them alone).")
        lines, counts = _items_section(unit, 3 if compact else limit, ck, compact)
        data += lines
        if not compact:
            st = _status_lines(unit)
            if st:
                data.append("Recent status (knowledge/status.md, newest first):")
                data += st
    if not compact:
        data += _git_lines(project)
    summary = (f"Agenda: {counts['open']} open, {counts['due']} overdue or due within a week, {counts['critical']} critical, "
               f"{counts['progress']} in progress."
               if unit is not None else "Agenda: not readable from here.")
    out = head + [summary]
    if data:
        out.append(fenced(project.name, "\n".join(data)))
    if compact:
        out.append(f"Before working here, run `{ck} brief` for the full brief (the most important items, other work in "
                   f"flight, recent status) and follow the Collab Kit section of this project's CLAUDE.md.")
        return "\n".join(out) + "\n"
    out += [
        "How to work here (the full rules are in CLAUDE.md, section Collab Kit):",
        f"- Before starting, check the lists above for anything your task overlaps; read those items or returns first "
        f"(`{ck} show W-NNN`).",
        f"- A question or decision for {who}: ask now if they are here; otherwise `{ck} ask \"...\"` puts it on the agenda.",
        f"- When the work changes the project's state: `{ck} status \"...\"`. Knowledge: `{ck} knowledge`. "
        "Anything else: the collab-kit-return skill.",
    ]
    return "\n".join(out) + "\n"

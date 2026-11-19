"""ck: the Collab Kit command. In a project, call it as tools/collab-kit/ck (it finds a Python 3.11+).

In a project (from anywhere inside the repository, or by its full path from any folder):
    ck brief                           what the session-start hook shows
    ck ask "Which venue?" [--kind decision] [--importance 2] [--due 2026-12-01] [--why "..."]
                                       put a question or decision on the project's agenda
    ck status "Draft two is written."  add an entry to the project's knowledge/status.md
    ck return --type note --topic "..." --change 'log W-004 "venue" "..."' [--change ...]
                                       file any return (changes as in the collab-kit-return skill)
    ck file <path>                     file a return written to a file (checked first)
    ck items [--all]                   the agenda, most pressing first
    ck show W-004 | ck show <return>   one agenda item, or one return in the inbox
    ck inbox                           returns waiting to be applied
    ck knowledge [path] [--from-file F]
                                       list the knowledge folder, read one file, or replace it
    ck version | ck doctor
    ck hook session-start|stop|touch   (called by Claude Code; reads the hook's JSON on stdin)

For a back end:
    ck backend run [--config FILE]     one pass: apply returns, mirror, health, the generated views
                   [--if-waiting]      only if a return waits or the last pass is older than the interval
    ck apply <folder-or-rclone:remote> --unit NAME [--top]   apply one unit's inbox (testing, level 1)

Everything printed from the project's files is fenced as data (see text.FENCE_NOTE).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import kit_version
from . import returns as R
from .apply import Reject


def _project():
    from .session import Project
    p = Project.find()
    if not p:
        sys.exit("ck: not inside a Collab Kit project (no tools/collab-kit/project.toml above here)")
    return p


def _report(p, res: dict) -> None:
    where = {"cloud": "the project's inbox in the Collab Kit folder",
             "repo": "this checkout's collab-kit/_returns/",
             "offline": "this checkout's collab-kit/_returns/ (the Collab Kit folder is not reachable)"}[res["route"]]
    if res.get("dry_run"):
        print(f"OK (dry run): would file {res['id']} to {where}.")
        return
    if res.get("applied"):
        made = f" New: {', '.join(res['minted'])}." if res.get("minted") else ""
        if res.get("renumbered"):
            made += " Renumbered (another session took the same number): " + \
                    ", ".join(f"{a} -> {b}" for a, b in res["renumbered"]) + "."
        print(f"Filed and applied {res['id']} ({where}).{made}")
    elif res["route"] == "cloud":
        print(f"Filed {res['id']} to {where}; the back end applies it.")
    elif res["route"] == "repo":
        print(f"Filed {res['id']} to {where}. Commit it with your work; the back end applies it once it reaches "
              f"the main branch.")
    else:
        print(f"Filed {res['id']} to {where}. Commit it with your work; the next session that can reach the "
              f"folder delivers it. Tell {p.machine.get('human') or 'the person'} it is waiting.")


def _file(p, text: str, dry: bool) -> int:
    try:
        res = p.file(text, dry_run=dry)
    except (Reject, R.ReturnError) as e:
        print(f"ck: {e}", file=sys.stderr)
        return 2
    _report(p, res)
    return 0


def cmd_brief(a):
    from .brief import build
    sys.stdout.write(build(_project()))


def cmd_ask(a):
    p = _project()
    body = None
    if a.why:
        body = f"## What's needed\n{a.question}\n\n## What we know so far\n{a.why}\n\n## Done when\nIt is answered."
    ch = R.render_change("new-item", None, None, None, body, kind=a.kind, importance=str(a.importance),
                         due=a.due or "", title=a.question)
    return _file(p, p.compose(a.kind, a.question, [ch], sender=a.sender), a.dry_run)


def cmd_status(a):
    p = _project()
    multi = "\n" in a.text
    ch = R.render_change("status", text=None if multi else a.text, body=a.text if multi else None)
    return _file(p, p.compose("status", a.topic or a.text.split("\n")[0][:80], [ch], sender=a.sender), a.dry_run)


def cmd_return(a):
    p = _project()
    changes = list(a.change or [])
    if a.changes_file:
        changes.append(Path(a.changes_file).read_text(encoding="utf-8").strip())
    fields = {}
    for kv in a.field or []:
        k, _, v = kv.partition("=")
        fields[k.strip().lower().replace(" ", "_")] = v
    return _file(p, p.compose(a.type, a.topic, changes, sender=a.sender, **fields), a.dry_run)


def cmd_file(a):
    p = _project()
    return _file(p, Path(a.path).read_text(encoding="utf-8"), a.dry_run)


def _view(p):
    unit, where = p.view()
    if not unit:
        sys.exit(f"ck: the project's Collab Kit folder is not readable from here ({where})")
    return unit, where


def cmd_items(a):
    from .text import fenced, one_line
    p = _project()
    unit, _ = _view(p)
    items = unit.items()
    if not a.all:
        items = [i for i in items if i.is_open]
    import datetime as _dt
    from .text import check_date, utcnow
    soon = (utcnow().date() + _dt.timedelta(days=7)).isoformat()

    def order(i):                      # the agenda's own order: due within a week, critical, in progress, the rest
        d = check_date(i.due or "") or ""
        urgent = bool(d) and d <= soon
        return (not urgent, d if urgent else "", i.importance > 1, i.status != "in-progress", i.importance,
                d or "9999", i.num)
    items.sort(key=order)
    lines = [f"{i.id} [{one_line(i.status, 12)}, {one_line(i.kind, 12)}, importance {i.importance}"
             f"{', due ' + one_line(i.due, 12) if i.due else ''}] {one_line(i.title, 100)}" for i in items]
    print(fenced(f"{p.name} agenda", "\n".join(lines) or "(no open items)"))


def cmd_show(a):
    from .returns import item_id
    from .text import fenced
    from .unit import RETURNS
    p = _project()
    unit, where = _view(p)
    wid = item_id(a.what)
    if wid:
        it = unit.item(wid)
        if not it:
            sys.exit(f"ck: no item {wid} in {where}")
        print(fenced(f"{p.name} {wid}", it.text))
        return
    name = a.what if a.what.endswith((".md", ".txt")) else a.what + ".md"
    for u in (unit, p.repo_unit()):
        for folder in (RETURNS, f"{RETURNS}/applied", f"{RETURNS}/failed", f"{RETURNS}/strays"):
            try:
                text = u.read(f"{folder}/{name}")
            except Exception:                    # noqa: BLE001 (an unsafe name finds nothing)
                text = None
            if text is not None:
                print(fenced(f"{p.name} return {name}", text))
                return
    sys.exit(f"ck: no item or return named {a.what!r}")


def cmd_inbox(a):
    from .brief import inbox_lines
    from .text import fenced
    p = _project()
    unit, _ = _view(p)
    lines = inbox_lines(unit, "the inbox", limit=100)
    print(fenced(f"{p.name} inbox", "\n".join(lines)) if lines else "The inbox is empty.")


def cmd_knowledge(a):
    from .text import fenced, safe_relpath
    from .unit import KNOWLEDGE
    p = _project()
    unit, where = _view(p)
    if a.from_file:
        if not a.path:
            sys.exit("ck: knowledge --from-file needs the path inside knowledge/ to replace")
        body = Path(a.from_file).read_text(encoding="utf-8")
        ch = R.render_change("knowledge", a.path, body=body)
        return _file(p, p.compose("note", f"knowledge: {a.path}", [ch], sender=a.sender), a.dry_run)
    if a.path:
        rel = safe_relpath(a.path)
        text = unit.read(f"{KNOWLEDGE}/{rel}") if rel else None
        if text is None:
            sys.exit(f"ck: no knowledge/{a.path} in {where}")
        print(fenced(f"{p.name} knowledge/{rel}", text))
        return

    def walk(prefix, depth=0):
        out = []
        for e in unit.store.list(f"{KNOWLEDGE}/{prefix}".rstrip("/")):
            if e.name.startswith(("_", ".")):
                continue
            rel = f"{prefix}{e.name}"
            if e.is_dir:
                if depth < 2 and e.name not in ("documents", "full"):
                    out += walk(rel + "/", depth + 1)
                else:
                    out.append(rel + "/ (folder)")
            else:
                out.append(rel)
        return out
    print(f"The project's knowledge ({where}); read one with `ck knowledge <path>`; replace one with "
          f"`ck knowledge <path> --from-file <file>` (a return):")
    print(fenced(f"{p.name} knowledge", "\n".join(walk("")) or "(empty)"))


def cmd_version(a):
    print(f"Collab Kit {kit_version()}")


def cmd_doctor(a):
    from . import config as C
    from .session import Project, git
    print(f"Collab Kit {kit_version()}; Python {sys.version.split()[0]}; machine config {C.machine_file()}"
          f" ({'present' if C.machine_file().is_file() else 'MISSING'})")
    p = Project.find()
    if not p:
        print("Not inside a Collab Kit project.")
        return 0
    print(f"Project {p.name}: home {p.home}, unit {p.unit_rel}, checkout {p.root}")
    print(f"Collab Kit folder: {'reachable' if p.cloud() else 'NOT reachable'} ({p.machine.get('cloud', {}).get('root', 'not configured')})")
    print(f"This project's folder there: {'present' if p.cloud_unit() else 'missing'}")
    print(f"Back end: {p.backend()['say']}; returns from here go to: {p.route()[0]}")
    k = p.kit_status()
    print(f"Kit: {k['here']} here; newest known {k['newest'] or 'unknown'}"
          f"{' (UPGRADE AVAILABLE: ' + k['source'] + ')' if k['behind'] else ''}")
    common = (git(p.root, "rev-parse", "--path-format=absolute", "--git-common-dir") or "").strip()
    main = Path(common).parent if common else p.root
    for label, root in (("this checkout", p.root), ("the main checkout (whose hooks a worktree session uses)", main)):
        if label != "this checkout" and root == p.root:
            continue
        s = root / ".claude" / "settings.json"
        try:
            hooks = json.loads(s.read_text(encoding="utf-8")).get("hooks", {}) if s.is_file() else {}
        except ValueError:
            hooks = {}
        for ev in ("SessionStart", "Stop"):
            ok = any("tools/collab-kit/ck" in h.get("command", "") for m in hooks.get(ev, []) for h in m.get("hooks", []))
            print(f"Hook {ev} in {label}: {'installed' if ok else 'MISSING'}")
    return 0


def cmd_hook(a):
    from .hooks import main
    return main(a.event)


def cmd_apply(a):
    from .apply import apply_file, heal_duplicates
    from .store import open_store
    from .unit import Unit
    store = open_store(a.store)
    unit = Unit(store, "top" if a.top else a.unit, home=a.home, top=a.top)
    for old, new in heal_duplicates(unit):
        print(f"renumbered {old} -> {new}")
    rc = 0
    for e in unit.pending_returns():
        out = apply_file(unit, e, force_settled=a.now)
        print(f"{out.status:8} {out.rid}: {out.message}")
        rc = rc or (1 if out.status in ("failed", "stray") else 0)
    return rc


def cmd_backend(a):
    from .backend import run
    return run(a.config, once=True, dry_run=a.dry_run, if_waiting=a.if_waiting)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="ck", description="Collab Kit: plain-file collaboration channels.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("brief").set_defaults(fn=cmd_brief)
    s = sub.add_parser("ask")
    s.add_argument("question")
    s.add_argument("--kind", default="question", choices=R.KINDS)
    s.add_argument("--importance", type=int, default=3, choices=range(1, 6),
                   help="1 critical (raised first, everywhere, until settled), 2 important, 3 normal (default), 4 and 5 later")
    s.add_argument("--due")
    s.add_argument("--why")
    s.set_defaults(fn=cmd_ask)
    s = sub.add_parser("status")
    s.add_argument("text")
    s.add_argument("--topic")
    s.set_defaults(fn=cmd_status)
    s = sub.add_parser("return")
    s.add_argument("--type", required=True)
    s.add_argument("--topic", required=True)
    s.add_argument("--change", action="append", help="one change line (repeatable)")
    s.add_argument("--changes-file", help="a file holding change lines (fenced bodies allowed)")
    s.add_argument("--field", action="append", help="an extra header field, e.g. 'What was worked out=...'")
    s.set_defaults(fn=cmd_return)
    s = sub.add_parser("file")
    s.add_argument("path")
    s.set_defaults(fn=cmd_file)
    s = sub.add_parser("knowledge")
    s.add_argument("path", nargs="?")
    s.add_argument("--from-file", help="replace knowledge/<path> with this file's content (files a return)")
    s.set_defaults(fn=cmd_knowledge)
    for name in ("ask", "status", "return", "file", "knowledge"):
        sp = sub.choices[name]
        sp.add_argument("--dry-run", action="store_true", help="check it, file nothing")
        if name != "file":
            sp.add_argument("--from", dest="sender", help="who it is from (default: this session)")
    s = sub.add_parser("items")
    s.add_argument("--all", action="store_true")
    s.set_defaults(fn=cmd_items)
    s = sub.add_parser("show")
    s.add_argument("what", help="an item (W-004) or a return's file name")
    s.set_defaults(fn=cmd_show)
    sub.add_parser("inbox").set_defaults(fn=cmd_inbox)
    sub.add_parser("version").set_defaults(fn=cmd_version)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    s = sub.add_parser("hook")
    s.add_argument("event", choices=["session-start", "stop", "touch"])
    s.set_defaults(fn=cmd_hook)
    s = sub.add_parser("apply")
    s.add_argument("store")
    s.add_argument("--unit", default="top")
    s.add_argument("--top", action="store_true")
    s.add_argument("--home", default="cloud", choices=["cloud", "repo"])
    s.add_argument("--now", action="store_true", help="do not wait for recent files to settle")
    s.set_defaults(fn=cmd_apply)
    s = sub.add_parser("backend")
    s.add_argument("action", choices=["run"])
    s.add_argument("--config")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--if-waiting", action="store_true",
                   help="a full pass only if a return is waiting or the last pass is older than interval_minutes")
    s.set_defaults(fn=cmd_backend)
    a = ap.parse_args(argv)
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())

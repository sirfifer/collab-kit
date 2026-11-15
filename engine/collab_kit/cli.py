"""ck: the Collab Kit command.

In a project (run from anywhere inside the repository):
    ck brief                           what the session-start hook shows
    ck ask "Which venue?" [--kind decision] [--importance 2] [--due 2026-12-01] [--why "..."]
                                       put a question or decision on the project's agenda
    ck status "Draft two is written."  add a line to the project's knowledge/status.md
    ck return --type note --topic "..." --change 'log W-004 "venue" "..."' [--change ...]
                                       file any return (changes as in the start file)
    ck file <path>                     file a return written to a file (validated first)
    ck items [--all]                   the agenda, most pressing first
    ck show W-004                      one agenda item
    ck inbox                           returns waiting to be applied
    ck version | ck doctor
    ck hook session-start|stop|touch   (called by Claude Code; reads the hook's JSON on stdin)

For a back end:
    ck backend run [--config FILE]     one pass: apply returns, mirror, health, the generated views
    ck apply <folder-or-rclone:remote> --unit NAME [--top]   apply one unit's inbox (testing, level 1)
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


def _report(res: dict) -> None:
    where = {"cloud": "the project's inbox in the Collab Kit folder",
             "repo": "this repository's collab-kit/_returns/"}[res["route"]]
    if res.get("dry_run"):
        print(f"OK (dry run): would file {res['id']} to {where}.")
        return
    if res.get("applied"):
        made = f" New: {', '.join(res['minted'])}." if res.get("minted") else ""
        tail = " Commit collab-kit/ with your work." if res["route"] == "repo" else ""
        print(f"Filed and applied {res['id']} ({where}).{made}{tail}")
    else:
        print(f"Filed {res['id']} to {where}; the back end applies it.")


def _file(p, text: str, dry: bool) -> int:
    try:
        res = p.file(text, dry_run=dry)
    except (Reject, R.ReturnError) as e:
        print(f"ck: {e}", file=sys.stderr)
        return 2
    _report(res)
    return 0


def cmd_brief(a):
    from .brief import build
    sys.stdout.write(build(_project()))


def cmd_ask(a):
    p = _project()
    body = None
    if a.why:
        body = f"## What's needed\n{a.question}\n\n## What we know so far\n{a.why}\n\n## Done when\nThe person has answered."
    ch = R.render_change("new-item", None, None, None, body, kind=a.kind, importance=str(a.importance),
                         due=a.due or "", title=a.question)
    text = p.compose(a.kind, a.question, [ch], sender=a.sender)
    return _file(p, text, a.dry_run)


def cmd_status(a):
    p = _project()
    ch = R.render_change("status", text=a.text if "\n" not in a.text else None,
                         body=a.text if "\n" in a.text else None)
    text = p.compose("status", a.topic or a.text.split("\n")[0][:80], [ch], sender=a.sender)
    return _file(p, text, a.dry_run)


def cmd_return(a):
    p = _project()
    changes = list(a.change or [])
    if a.changes_file:
        changes.append(Path(a.changes_file).read_text(encoding="utf-8").strip())
    fields = {}
    for kv in a.field or []:
        k, _, v = kv.partition("=")
        fields[k.strip().lower().replace(" ", "_")] = v
    text = p.compose(a.type, a.topic, changes, sender=a.sender, **fields)
    return _file(p, text, a.dry_run)


def cmd_file(a):
    p = _project()
    return _file(p, Path(a.path).read_text(encoding="utf-8"), a.dry_run)


def cmd_items(a):
    from .text import FENCE_NOTE, one_line
    p = _project()
    unit, where = p.view()
    if not unit:
        sys.exit(f"ck: the agenda is not readable from here ({where})")
    items = unit.items()
    if not a.all:
        items = [i for i in items if i.is_open]
    items.sort(key=lambda i: (i.status != "in-progress", i.due or "9999", i.importance, i.num))
    print(f"<collab-kit-data source=\"{p.name} agenda\">\n{FENCE_NOTE}")
    for i in items:
        print(f"{i.id} [{i.status}, {i.kind}, importance {i.importance}{', due ' + i.due if i.due else ''}] "
              f"{one_line(i.title, 100)}")
    print("</collab-kit-data>")


def cmd_show(a):
    from .returns import item_id
    from .text import FENCE_NOTE
    p = _project()
    unit, where = p.view()
    wid = item_id(a.item)
    it = unit.item(wid) if unit and wid else None
    if not it:
        sys.exit(f"ck: no item {a.item} in {where}")
    print(f"<collab-kit-data source=\"{p.name} {wid}\">\n{FENCE_NOTE}\n{it.text.rstrip()}\n</collab-kit-data>")


def cmd_inbox(a):
    from .brief import _inbox_lines
    from .text import FENCE_NOTE
    p = _project()
    unit, where = p.view()
    lines = _inbox_lines(unit, "the inbox", limit=50) if unit else []
    if not lines:
        print("The inbox is empty.")
        return
    print(f"<collab-kit-data source=\"{p.name} inbox\">\n{FENCE_NOTE}\n" + "\n".join(lines) + "\n</collab-kit-data>")


def cmd_version(a):
    print(f"Collab Kit {kit_version()}")


def cmd_doctor(a):
    from . import config as C
    from .session import Project
    print(f"Collab Kit {kit_version()}; Python {sys.version.split()[0]}; machine config {C.machine_file()}"
          f" ({'present' if C.machine_file().is_file() else 'missing'})")
    p = Project.find()
    if not p:
        print("Not inside a Collab Kit project.")
        return 0
    print(f"Project {p.name}: home {p.home}, unit {p.unit_rel}")
    print(f"Collab Kit folder: {'reachable' if p.cloud() else 'NOT reachable'} ({p.machine.get('cloud', {}).get('root', 'not configured')})")
    print(f"This unit there: {'present' if p.cloud_unit() else 'missing'}")
    print(f"Back end: {p.backend()['say']}")
    k = p.kit_status()
    print(f"Kit: {k['here']} here; newest known {k['newest'] or 'unknown'}{' (UPGRADE AVAILABLE)' if k['behind'] else ''}")
    s = p.root / ".claude" / "settings.json"
    hooks = json.loads(s.read_text(encoding="utf-8")).get("hooks", {}) if s.is_file() else {}
    for ev in ("SessionStart", "Stop"):
        ok = any("tools/collab-kit/ck.py" in h.get("command", "") for m in hooks.get(ev, []) for h in m.get("hooks", []))
        print(f"Hook {ev}: {'installed' if ok else 'MISSING'}")
    return 0


def cmd_hook(a):
    from .hooks import main
    return main(a.event)


def cmd_apply(a):
    from .apply import apply_file
    from .store import open_store
    from .unit import Unit
    store = open_store(a.store)
    unit = Unit(store, "top" if a.top else a.unit, home=a.home, top=a.top)
    rc = 0
    for e in unit.pending_returns():
        out = apply_file(unit, e, force_settled=a.now)
        print(f"{out.status:8} {out.rid}: {out.message}")
        rc = rc or (1 if out.status in ("failed", "stray") else 0)
    return rc


def cmd_backend(a):
    from .backend import run
    return run(a.config, once=True, dry_run=a.dry_run)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ck", description="Collab Kit: plain-file collaboration channels.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("brief").set_defaults(fn=cmd_brief)
    s = sub.add_parser("ask")
    s.add_argument("question")
    s.add_argument("--kind", default="question", choices=R.KINDS)
    s.add_argument("--importance", type=int, default=3, choices=range(1, 6))
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
    for name in ("ask", "status", "return", "file"):
        sp = sub.choices[name]
        sp.add_argument("--dry-run", action="store_true", help="check it, file nothing")
        if name != "file":
            sp.add_argument("--from", dest="sender", help="who it is from (default: this session)")
    s = sub.add_parser("items")
    s.add_argument("--all", action="store_true")
    s.set_defaults(fn=cmd_items)
    s = sub.add_parser("show")
    s.add_argument("item")
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
    s.set_defaults(fn=cmd_backend)
    a = ap.parse_args(argv)
    rc = a.fn(a)
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())

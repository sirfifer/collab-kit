"""Work sent out, and what comes back (DESIGN-0.5 section 27): a dispatched return becomes one item
that carries all of it and says truthfully where the work stands; a return that asks for nothing is
said, never silent; work nobody started is raised and pushed.
Standard library and git only:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import isolation  # noqa: E402,F401  (first: never the machine's real Collab Kit)

import datetime as dt
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "engine"))

from collab_kit import backend as BE                    # noqa: E402
from collab_kit import returns as R                     # noqa: E402
from collab_kit.apply import apply_return               # noqa: E402
from collab_kit.store import FolderStore, SubStore      # noqa: E402
from collab_kit.templates import set_human, top_start_file  # noqa: E402
from collab_kit.text import utcnow                      # noqa: E402
from collab_kit.unit import Unit                        # noqa: E402

SENT = """Project: garden
From: Sam
Type: task
Topic: Work out the drip line for the north beds
State: dispatched
What was worked out:
The north beds dry out by noon. Sam wants a drip line, fed from the rain barrel.
## Not a heading of the item
Decided:
- Two lines, one per bed.
Verbatim: "Just make it work without me carrying cans."
End.
"""


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.cloud = self.t / "Collab Kit"
        set_human("Sam")
        self.s = FolderStore(self.cloud)
        self.s.write("00-START-HERE.md", top_start_file())
        self.s.write("knowledge/projects.md", "| Folder | Say | What it is | Home |\n|---|---|---|---|\n"
                                              "| `garden` | \"g\" | g | cloud |\n")
        for d in ("_returns", "agenda", "WIP", "projects/garden/collab-kit/_returns",
                  "projects/garden/collab-kit/agenda", "projects/garden/collab-kit/knowledge"):
            self.s.mkdir(d)
        self.garden = Unit(SubStore(self.s, "projects/garden/collab-kit"), "garden")
        self.top = Unit(self.s, "top", top=True)
        self.work = self.t / "work"
        self.cfg = {"backend": {"cloud": str(self.cloud), "work": str(self.work), "human": "Sam",
                                "local_roots": [], "lease_settle_seconds": 0, "interval_minutes": 60}}

    def tearDown(self):
        isolation.restore()
        self.tmp.cleanup()

    def cfgfile(self) -> str:
        out = ""
        for name, d in self.cfg.items():
            out += f"[{name}]\n" + "".join(f"{k} = {json.dumps(v)}\n" for k, v in d.items())
        f = self.t / "backend.toml"
        f.write_text(out, encoding="utf-8")
        return str(f)

    def drop(self, rel: str, text: str):
        self.s.write(rel, text)
        t = time.time() - 3600
        os.utime(self.cloud / rel, (t, t))

    def run_pass(self, **kw):
        p = BE.Pass(self.cfg, **kw)
        return p, p.run()

    def page(self) -> str:
        return self.s.read("agenda/00-PRESSING.md")

    def send(self, text=SENT, name="2026-11-22-2031-drip"):
        self.drop(f"projects/garden/collab-kit/_returns/{name}.md", text)

    def change(self, line: str, name="c"):
        out = apply_return(self.garden, R.parse(f"Project: garden\nFrom: the dispatcher\nChanges v1:\n{line}\nEnd.\n",
                                                f"{name}.md"), None, top=self.top)
        self.assertIn(out.status, ("applied", "undone"), out.message)

    def age(self, wid: str, minutes: int):
        it = self.garden.item(wid)
        at = (utcnow() - dt.timedelta(minutes=minutes)).isoformat(timespec="seconds")
        self.garden.store.write(it.path, it.text.replace(str(it.fields["work_at"]), at))


class Receipt(Folder):
    def test_a_dispatched_return_becomes_one_item_that_carries_all_of_it(self):
        self.send()
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue(any("work received as W-001, waiting for an agent" in ln for ln in p.log), p.log)
        it = self.garden.item("W-001")
        self.assertEqual((it.title, it.work, it.status), ("Work out the drip line for the north beds", "received", "open"))
        self.assertEqual(it.fields["work_return"], "2026-11-22-2031-drip")
        for said in ("> The north beds dry out by noon.", "> - Two lines, one per bed.",
                     '> Verbatim: "Just make it work without me carrying cans."', "> From: Sam"):
            self.assertIn(said, it.body)
        self.assertNotIn("\n## Not a heading", it.body, "the copied text is quoted, so it cannot pass for the item's own parts")
        self.assertNotIn("State:", it.body)
        self.assertIn("received as work; no agent has started it yet", it.body)
        self.assertTrue(self.s.exists("projects/garden/collab-kit/_returns/applied/2026-11-22-2031-drip.md"))

    def test_the_front_page_says_where_it_stands_and_never_that_it_is_done(self):
        self.send()
        self.run_pass()
        page = self.page()
        self.assertIn("## Work sent to agents", page)
        self.assertRegex(page, r"\*\*Work out the drip line for the north beds\*\* \(garden W-001\): sent .* UTC; "
                               r"no agent has started it")
        self.assertNotIn("In progress", page)

    def test_change_lines_in_a_dispatched_return_are_still_applied(self):
        self.send(SENT.replace("End.\n", 'Changes v1:\nnew-item kind=question title="Which barrel?"\nEnd.\n'))
        self.run_pass()
        self.assertEqual([(i.title, i.work) for i in self.garden.items()],
                         [("Which barrel?", ""), ("Work out the drip line for the north beds", "received")])

    def test_importance_comes_from_the_header_and_only_as_a_number(self):
        self.send(SENT.replace("State: dispatched", "State: dispatched\nImportance: 2"))
        self.send(SENT.replace("State: dispatched", "State: Dispatched.\nImportance: very"), "2026-11-22-2040-b")
        self.run_pass()
        self.assertEqual([i.importance for i in self.garden.items()], [2, 3])

    def test_a_return_that_asks_for_nothing_is_said_never_silent(self):
        self.send(SENT.replace("State: dispatched\n", ""), "2026-11-22-2050-note")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(self.garden.items(), [])
        status = self.garden.read("knowledge/status.md")
        self.assertIn("the back end: Work out the drip line for the north beds", status)
        self.assertIn("It asks for no change and no work", status)
        self.assertIn("garden: the back end: Work out the drip line", self.page())
        self.assertTrue(any("recorded" in ln and "asked for nothing" in ln for ln in p.log), p.log)

    def test_a_staged_return_waits_in_the_inbox_until_it_is_dispatched(self):
        self.send(SENT.replace("State: dispatched", "State: staged"))
        p, rc = self.run_pass()
        self.assertEqual((rc, self.garden.items()), (0, []))
        self.assertTrue(self.s.exists("projects/garden/collab-kit/_returns/2026-11-22-2031-drip.md"))
        self.send()
        self.run_pass()
        self.assertEqual(self.garden.item("W-001").work, "received")

    def test_undo_takes_the_item_away_again(self):
        self.send()
        self.run_pass()
        self.change("undo 2026-11-22-2031-drip", "u")
        self.assertEqual(self.garden.items(), [])


class States(Folder):
    def setUp(self):
        super().setUp()
        self.send()
        self.run_pass()

    def test_each_state_is_written_with_who_and_what_was_checked(self):
        self.change('work W-001 "drip line" state=started by="studio" branch="ck/W-001-drip"', "a")
        it = self.garden.item("W-001")
        self.assertEqual((it.work, it.status, it.fields["work_by"], it.fields["work_branch"]),
                         ("started", "in-progress", "studio", "ck/W-001-drip"))
        self.change('work W-001 "drip line" state=finished note="exit 0 after 12 min; 3 commits; the check passed"', "b")
        it = self.garden.item("W-001")
        self.assertEqual((it.work, it.status), ("finished", "open"), "finished is not settled: the person judges it")
        self.assertIn("work finished: exit 0 after 12 min; 3 commits; the check passed", it.body)
        self.run_pass()
        self.assertRegex(self.page(), r"\(garden W-001\): ended .* and what it left was checked .* waits for Sam's judgment")

    def test_a_state_the_kit_does_not_know_is_refused(self):
        with self.assertRaises(R.ReturnError):
            R.parse('Project: garden\nChanges v1:\nwork W-001 "drip" state=done\nEnd.\n', "x.md")
        with self.assertRaises(R.ReturnError):
            R.parse('Project: garden\nChanges v1:\nwork W-001 state=started\nEnd.\n', "x.md")

    def test_settling_it_is_the_persons_and_takes_it_off_the_list(self):
        self.change('work W-001 "drip line" state=finished note="2 commits"', "a")
        self.change('settle W-001 "drip line" outcome="Good. Merge it."', "b")
        self.run_pass()
        self.assertNotIn("## Work sent to agents", self.page())


class Unstarted(Folder):
    def setUp(self):
        super().setUp()
        self.out = self.t / "pushes.txt"
        self.cfg["notify"] = {"command": [
            sys.executable, "-c", "import os,sys; open(sys.argv[1],'a').write(os.environ['COLLAB_KIT_KIND']+' '+"
                                  "os.environ['COLLAB_KIT_ITEM']+'\\n')", str(self.out)]}
        self.run_pass()                                   # the first run remembers what is there, sends nothing
        self.send()

    def pushes(self):
        return self.out.read_text().splitlines() if self.out.exists() else []

    def test_fresh_work_is_not_an_alarm_and_its_due_time_is_left_for_the_minute_check(self):
        p, rc = self.run_pass()
        self.assertEqual((rc, p.problems, self.pushes()), (0, [], []))
        due = float((self.work / BE.WORK_DUE).read_text())
        self.assertAlmostEqual(due - time.time(), 600, delta=30)

    def test_work_nobody_started_is_raised_first_and_pushed_once(self):
        self.run_pass()
        self.age("W-001", 11)
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertRegex(p.problems[0], r'garden W-001 \("Work out the drip line for the north beds"\) was sent as work '
                                        r'11 minutes ago and no agent has started it')
        page = self.page()
        self.assertLess(page.index("no agent has started it: no dispatcher"), page.index("## Work sent to agents"))
        self.assertEqual(self.pushes(), ["unstarted garden W-001"])
        self.assertFalse((self.work / BE.WORK_DUE).exists())
        self.run_pass()
        self.assertEqual(self.pushes(), ["unstarted garden W-001"], "once")
        self.assertIn("no agent has started it: no dispatcher", self.page(), "said until it changes")

    def test_how_long_is_a_setting_of_the_machine(self):
        self.cfg["backend"]["unstarted_minutes"] = 30
        self.run_pass()
        self.age("W-001", 11)
        p, rc = self.run_pass()
        self.assertEqual((rc, self.pushes()), (0, []))

    def test_the_minute_check_makes_a_full_pass_when_the_time_is_up(self):
        cfg = self.cfgfile()
        self.assertEqual(BE.run(cfg, if_waiting=True), 0)             # the return arrives: a full pass
        before = self.page()
        self.assertEqual(BE.run(cfg, if_waiting=True), 0)             # a quiet minute
        self.assertEqual(self.page(), before)
        self.age("W-001", 11)
        (self.work / BE.WORK_DUE).write_text(f"{time.time() - 1}\n")
        self.assertEqual(BE.run(cfg, if_waiting=True), 1)
        self.assertIn("no agent has started it: no dispatcher", self.page())

    def test_started_finished_and_failed_are_each_pushed_once_and_failed_is_raised(self):
        self.run_pass()
        self.change('work W-001 "drip line" state=started by="studio"', "a")
        self.run_pass()
        self.change('work W-001 "drip line" state=failed note="exit 0 after 2 min; it left no commit and no account"', "b")
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertIn("was sent to an agent and failed", p.problems[0])
        self.run_pass()
        self.assertEqual(self.pushes(), ["started garden W-001", "failed garden W-001"])


if __name__ == "__main__":
    unittest.main()

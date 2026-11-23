"""The dispatcher (DESIGN-0.5 section 27): work a person sent is started in a worktree of its own,
and what the session left is checked by a program before anything is called finished. The agent is
tests/fake_agent.py: no test starts a real one.
Standard library and git only:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import isolation  # noqa: E402,F401  (first: never the machine's real Collab Kit)

import json
import os
import subprocess
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "engine"))

from collab_kit import dispatch as D                    # noqa: E402
from test_work import SENT, Folder                      # noqa: E402

AGENT = str(KIT / "tests" / "fake_agent.py")
ID = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]


class Dispatch(Folder):
    def setUp(self):
        super().setUp()
        self.repo = self.t / "dev" / "garden"
        self.repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("garden\n")
        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True)
        subprocess.run(["git", *ID, "commit", "-q", "-m", "first"], cwd=self.repo, check=True)
        self.dwork = self.t / "dispatch"
        self.dcfg = {"dispatch": {"cloud": str(self.cloud), "work": str(self.dwork), "machine": "studio",
                                  "home": str(self.t / "My Collab Kit"),
                                  "command": [sys.executable, AGENT, "commit"], "max_minutes": 1},
                     "project": [{"name": "garden", "dir": str(self.repo)}]}
        self.send()
        self.run_pass()

    def agent(self, mode: str):
        self.dcfg["dispatch"]["command"] = [sys.executable, AGENT, mode]

    def dispatch(self, **kw) -> D.Dispatcher:
        d = D.Dispatcher(self.dcfg, **kw)
        d.run()
        return d

    def settle(self):
        """Let the back end apply what the dispatcher filed (its returns are a minute old to it)."""
        inbox = self.cloud / "projects/garden/collab-kit/_returns"
        for f in inbox.glob("*.md"):
            t = time.time() - 3600
            os.utime(f, (t, t))
        return self.run_pass()

    def wait_for_session(self, seconds=20):
        end = time.time() + seconds
        while time.time() < end:
            if list((self.dwork / "sessions").glob("*.result")):
                return
            time.sleep(0.1)
        self.fail("the session did not end")

    def item(self):
        return self.garden.item("W-001")

    def round(self, mode: str):
        self.agent(mode)
        self.dispatch()
        self.settle()
        self.wait_for_session()
        d = self.dispatch()
        self.settle()
        return d

    # --------------------------------------------------------------------------------------
    def test_sent_work_is_started_in_a_worktree_of_its_own_and_says_so(self):
        d = self.dispatch()
        self.assertEqual(d.log, ["garden W-001: started on branch ck/W-001-work-out-the-drip-line-for-the"])
        self.settle()
        it = self.item()
        self.assertEqual((it.work, it.status, it.fields["work_by"], it.fields["work_branch"]),
                         ("started", "in-progress", "studio", "ck/W-001-work-out-the-drip-line-for-the"))
        self.assertRegex(self.page(), r"\(garden W-001\): an agent on studio has been working on it since")
        self.wait_for_session()
        wt = self.dwork / "worktrees" / "garden--W-001"
        seen = (wt / "task-seen.txt").read_text()
        self.assertIn("Never push, never merge", seen)
        self.assertIn('<collab-kit-data source="garden W-001">', seen)
        self.assertIn("> The north beds dry out by noon.", seen)
        self.assertFalse((self.repo / "drip.md").exists(), "the main checkout is never touched")
        self.assertEqual(subprocess.run(["git", "branch", "--show-current"], cwd=self.repo, capture_output=True,
                                        text=True).stdout.strip(), "main")

    def test_it_is_not_started_twice_while_the_first_return_is_on_its_way(self):
        self.dispatch()
        self.assertEqual(self.dispatch().log, [])
        self.assertEqual(len(list((self.dwork / "sessions").glob("*.json"))), 1)

    def test_finished_means_it_was_checked_and_says_what_was_found(self):
        self.dcfg["project"][0]["check"] = [sys.executable, "-c", "import os,sys; sys.exit(os.path.exists('broken.flag'))"]
        self.round("commit")
        it = self.item()
        self.assertEqual((it.work, it.status), ("finished", "open"))
        for fact in ("the command ended normally", "1 commit(s) touching 2 file(s) on branch ck/W-001-",
                     "the project's check passed", "the agent left no account on the item"):
            self.assertIn(fact, it.body)
        self.assertRegex(self.page(), r"\(garden W-001\): ended .* waits for Sam's judgment")
        self.assertEqual(list((self.dwork / "sessions").glob("*")), [self.dwork / "sessions" / "garden--W-001.task"])
        self.assertEqual(self.dispatch().log, [], "finished work is never started again")

    def test_a_session_that_leaves_nothing_is_failed_never_finished(self):
        self.round("nothing")
        it = self.item()
        self.assertEqual(it.work, "failed")
        self.assertIn("it left no commit and no account: there is nothing to check", it.body)
        p, rc = self.run_pass()
        self.assertIn("was sent to an agent and failed", p.problems[0])

    def test_a_failing_command_and_a_failing_check_are_both_failed(self):
        self.round("fail")
        self.assertIn("the command ended with exit 3", self.item().body)
        self.assertEqual(self.item().work, "failed")

    def test_the_projects_own_check_decides(self):
        self.dcfg["project"][0]["check"] = [sys.executable, "-c", "import os,sys; sys.exit(os.path.exists('broken.flag'))"]
        self.round("break")
        it = self.item()
        self.assertEqual(it.work, "failed")
        self.assertIn("the project's check failed (exit 1)", it.body)

    def test_a_question_that_blocks_it_makes_it_blocked_and_the_answer_starts_it_again(self):
        self.agent("nothing")
        self.dispatch()
        self.settle()
        self.wait_for_session()
        self.change('new-item kind=question importance=1 blocks=W-001 title="Which barrel?"', "q")
        self.dispatch()
        self.settle()
        self.assertEqual(self.item().work, "blocked")
        self.assertIn("it waits for W-002", self.item().body)
        self.assertEqual(self.dispatch().log, [], "it waits while the question is open")
        self.change('settle W-002 "barrel" outcome="the green one"', "a")
        self.assertEqual(len(self.dispatch().log), 1)
        self.settle()
        self.assertEqual(self.item().work, "started")
        self.wait_for_session()

    def test_the_time_limit_stops_a_session(self):
        f = self.dwork / "sessions"
        self.agent("sleep")
        self.dispatch()
        s = json.loads((f / "garden--W-001.json").read_text())
        s["max_minutes"] = 0
        # the runner already read its limit: stop it by hand and run one with no time at all
        os.kill(s["runner"], 9)
        (f / "garden--W-001.json").write_text(json.dumps(s))
        self.assertEqual(D.session(str(f / "garden--W-001.json")), 0)
        self.settle()
        self.dispatch()
        self.settle()
        self.assertEqual(self.item().work, "failed")
        self.assertIn("it was stopped at the 1 minute limit", self.item().body)

    def test_only_listed_projects_are_served_and_the_limits_hold(self):
        self.dcfg["project"] = []
        self.assertEqual(self.dispatch().log, [])
        self.dcfg["project"] = [{"name": "garden", "dir": str(self.repo)}]
        self.dcfg["dispatch"]["max_starts_per_day"] = 1
        self.send(SENT.replace("drip line", "second drip line"), "2026-11-22-2040-second")
        self.run_pass()
        self.round("commit")
        d = self.dispatch()
        self.assertEqual(d.log, ["garden W-002: waits: 1 sessions were already started today"])

    def test_one_at_a_time_unless_the_machine_says_more(self):
        self.send(SENT.replace("drip line", "second drip line"), "2026-11-22-2040-second")
        self.run_pass()
        self.agent("sleep")
        d = self.dispatch()
        self.assertEqual(len(d.log), 1)
        self.assertEqual(self.dispatch().log, [])
        for f in (self.dwork / "sessions").glob("*.json"):
            os.kill(json.loads(f.read_text())["runner"], 9)

    def test_top_level_work_runs_in_the_home_folder_which_gets_a_history(self):
        self.dcfg["project"] = [{"name": "top"}]
        self.drop("_returns/2026-11-22-2100-cards.md", SENT.replace("Project: garden", "Project: top"))
        self.run_pass()
        d = self.dispatch()
        self.assertEqual(len(d.log), 1, d.log)
        home = self.t / "My Collab Kit"
        self.assertTrue((home / ".git").exists())
        self.wait_for_session()
        for f in (self.cloud / "_returns").glob("*.md"):
            t = time.time() - 3600
            os.utime(f, (t, t))
        self.run_pass()
        self.dispatch()
        for f in (self.cloud / "_returns").glob("*.md"):
            t = time.time() - 3600
            os.utime(f, (t, t))
        self.run_pass()
        self.assertEqual(self.top.items()[-1].work, "finished")

    def test_a_folder_that_is_not_a_repository_is_said_not_guessed(self):
        self.dcfg["project"][0]["dir"] = str(self.t / "nowhere")
        d = self.dispatch()
        self.assertIn("could not be started on studio", d.log[0])
        self.settle()
        self.assertEqual(self.item().work, "failed")

    def test_nothing_from_the_folder_reaches_a_command_line(self):
        self.send(SENT.replace("Work out the drip line for the north beds", 'A "title"; rm -rf $(HOME) `x`'), "2026-11-22-2040-odd")
        self.run_pass()
        self.dcfg["dispatch"]["max_running"] = 2
        self.dispatch()
        s = json.loads((self.dwork / "sessions" / "garden--W-002.json").read_text())
        self.assertEqual(s["command"], [sys.executable, AGENT, "commit"])
        self.assertRegex(s["branch"], r"^ck/W-002-[a-z0-9-]+$")
        self.settle()
        self.assertEqual(self.garden.item("W-002").work, "started")
        self.wait_for_session()

    def test_a_dry_run_starts_nothing(self):
        d = self.dispatch(dry_run=True)
        self.assertIn("would be started", d.log[0])
        self.assertFalse((self.dwork / "sessions").exists())

    def test_a_config_without_a_command_is_refused(self):
        del self.dcfg["dispatch"]["command"]
        with self.assertRaises(D.Stop):
            D.Dispatcher(self.dcfg)


if __name__ == "__main__":
    import unittest
    unittest.main()

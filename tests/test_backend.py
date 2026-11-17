"""The back end, end to end, against a throwaway Collab Kit folder and a throwaway repository
(with a bare "origin"). Standard library and git only:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "engine"))

from collab_kit import backend as BE                    # noqa: E402
from collab_kit.store import FolderStore                # noqa: E402
from collab_kit.templates import set_human, top_start_file  # noqa: E402


def sh(*args, cwd=None):
    res = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise AssertionError(f"{args}: {res.stderr}")
    return res.stdout


def old(path: Path):
    t = time.time() - 3600
    os.utime(path, (t, t))


class BackEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.t = t
        self.cloud = t / "Collab Kit"
        set_human("Sam")
        s = FolderStore(self.cloud)
        self.s = s
        s.write("00-START-HERE.md", top_start_file())
        s.write("knowledge/projects.md", "| Folder | Say | What it is | Home |\n|---|---|---|---|\n"
                "| `garden` | \"g\" | g | cloud |\n| `site` | \"s\" | the site | repo |\n| `old` | \"o\" | old one (inactive) | cloud |\n")
        for d in ("_returns", "agenda", "WIP", "projects/garden/collab-kit/_returns", "projects/garden/collab-kit/agenda",
                  "projects/old/collab-kit/agenda", "projects/site/collab-kit/_returns"):
            s.mkdir(d)
        # a repository-homed project with a bare origin
        self.origin = t / "site.git"
        sh("git", "init", "-q", "--bare", "-b", "main", str(self.origin))
        seed = t / "seed"
        sh("git", "clone", "-q", str(self.origin), str(seed))
        for k, v in (("user.email", "t@example.com"), ("user.name", "T")):
            sh("git", "config", k, v, cwd=seed)
        (seed / "collab-kit/agenda").mkdir(parents=True)
        (seed / "collab-kit/knowledge").mkdir(parents=True)
        (seed / "collab-kit/00-START-HERE.md").write_text("# site\n")
        (seed / "collab-kit/knowledge/README.md").write_text("# site knowledge\n")
        (seed / "collab-kit/agenda/README.md").write_text("# agenda\n")
        (seed / "index.html").write_text("<p>hi</p>\n")
        sh("git", "add", "-A", cwd=seed)
        sh("git", "commit", "-qm", "seed", cwd=seed)
        sh("git", "push", "-q", "origin", "HEAD:main", cwd=seed)
        self.cfg = {"backend": {"cloud": str(self.cloud), "work": str(t / "work"), "human": "Sam",
                                "local_roots": [], "deny": ["codename-x"],
                                "lease_settle_seconds": 0},
                    "project": [{"name": "site", "repo": str(self.origin), "branch": "main", "push": True,
                                 "allow_public": True}]}

    def tearDown(self):
        self.tmp.cleanup()

    def drop(self, rel: str, text: str):
        self.s.write(rel, text)
        old(self.cloud / rel)

    def run_pass(self):
        p = BE.Pass(self.cfg)
        rc = p.run()
        return p, rc

    def test_cloud_project_and_views(self):
        self.drop("projects/garden/collab-kit/_returns/r1.md",
                  "Project: garden\nChanges v1:\nnew-item title=\"Order seeds\" importance=1 due=2026-11-16\n"
                  "new-item title=\"Someday\" importance=4\nEnd.\n")
        self.drop("_returns/t1.md", "Project: top\nChanges v1:\nnew-item title=\"Top thing\" importance=2\n"
                                    "new-item title=\"Fix the gate\" importance=1\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        pressing = self.s.read("agenda/00-PRESSING.md")
        self.assertIn("Order seeds", pressing)
        self.assertIn("Top thing", pressing)
        self.assertNotIn("Someday", pressing)
        # the front page: the back end's health first, then deadlines, critical, important
        from collab_kit.text import utcnow
        self.assertIn(f"**Up to date as of {utcnow().date().isoformat()} (UTC)**", pressing)
        sections = [line for line in pressing.splitlines() if line.startswith("## ")]
        self.assertEqual(sections, ["## Overdue and due in the next two weeks", "## Critical (importance 1)",
                                    "## Important (importance 2)", "## Inactive projects"], pressing)
        self.assertIn("Fix the gate", pressing.split("## Critical")[1].split("## Important")[0])
        # the start file changed in one place only: its setup line now says a back end runs
        from collab_kit.templates import SETUP_TEXT, replace_block
        start = self.s.read("00-START-HERE.md")
        self.assertEqual(start, replace_block(top_start_file(), "setup", SETUP_TEXT["backend"]))
        hb = json.loads(self.s.read("_backend/heartbeat.json"))
        self.assertEqual(hb["problems"], [])
        # a second pass with nothing new changes nothing (no new versions)
        versions = len(self.s.files("_versions"))
        self.run_pass()
        self.assertEqual(len(self.s.files("_versions")), versions)

    def test_wrong_account_refuses(self):
        self.cfg["backend"]["account"] = "someone@example.com"
        self.drop("_returns/t1.md", "Project: top\nChanges v1:\nnew-item title=\"x\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 2)
        self.assertTrue(self.s.exists("_returns/t1.md"), "nothing applied under the wrong account")

    def test_lease(self):
        from collab_kit.text import utcnow
        import datetime as dt
        self.s.write("_backend/lease.json", json.dumps({"holder": "other:1", "expires": (utcnow() + dt.timedelta(minutes=30)).isoformat()}))
        self.drop("_returns/t1.md", "Project: top\nChanges v1:\nnew-item title=\"Top thing\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertTrue(self.s.exists("_returns/t1.md"), "another runner holds the lease: nothing applied")

    def test_repo_project(self):
        self.drop("projects/site/collab-kit/_returns/r1.md",
                  "Project: site\nChanges v1:\nnew-item title=\"Fix the footer\"\nstatus \"Footer reported broken.\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        check = self.t / "check"
        sh("git", "clone", "-q", str(self.origin), str(check))
        self.assertTrue(list((check / "collab-kit/agenda").glob("W-001-*.md")))
        self.assertTrue((check / "collab-kit/_returns/applied/r1.ledger.json").is_file())
        self.assertFalse((check / "collab-kit/_returns/applied/r1.md").exists(), "return text stays out of git")
        self.assertTrue(self.s.exists("projects/site/collab-kit/_returns/applied/r1.md"))
        self.assertTrue(self.s.files("projects/site/collab-kit/agenda"))      # mirrored out
        self.assertIn("Footer reported broken", self.s.read("projects/site/collab-kit/knowledge/status.md"))
        log = sh("git", "log", "--format=%s", "-1", cwd=check)
        self.assertIn("collab-kit: applied return r1", log)

    def test_cloud_edit_of_a_mirror_is_saved(self):
        self.drop("projects/site/collab-kit/_returns/r1.md", "Project: site\nChanges v1:\nstatus \"one\"\nEnd.\n")
        self.run_pass()
        self.s.write("projects/site/collab-kit/knowledge/README.md", "# edited in the cloud by mistake\n")
        self.drop("projects/site/collab-kit/_returns/r2.md", "Project: site\nChanges v1:\nstatus \"two\"\nEnd.\n")
        p, _ = self.run_pass()
        self.assertEqual(self.s.read("projects/site/collab-kit/knowledge/README.md"), "# site knowledge\n")
        saved = [e.name for e in self.s.files("projects/site/collab-kit/_returns") if "edited-in-the-folder" in e.name]
        self.assertTrue(saved, "the cloud edit is kept as a return")
        self.assertTrue(any("edited in the folder" in x for x in p.problems))

    def test_first_mirror_sets_old_layout_aside(self):
        self.s.write("projects/site/collab-kit/knowledge/agenda/W-001-old.md", "old 0.4 copy\n")
        self.s.write("projects/site/collab-kit/knowledge/README.md", "an older copy\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertFalse(self.s.exists("projects/site/collab-kit/knowledge/agenda/W-001-old.md"))
        self.assertTrue(self.s.exists("projects/site/collab-kit/_versions/before-first-mirror/knowledge/agenda/W-001-old.md"))
        self.assertEqual(self.s.read("projects/site/collab-kit/knowledge/README.md"), "# site knowledge\n")
        self.assertFalse([e for e in self.s.files("projects/site/collab-kit/_returns") if "edited" in e.name])

    def test_deny_list_blocks_push(self):
        self.drop("projects/site/collab-kit/_returns/r1.md",
                  "Project: site\nChanges v1:\nstatus \"about codename-x\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("denied word" in x for x in p.problems))
        check = self.t / "check2"
        sh("git", "clone", "-q", str(self.origin), str(check))
        self.assertFalse((check / "collab-kit/knowledge/status.md").exists())

    def test_failed_return_reaches_health(self):
        self.drop("projects/garden/collab-kit/_returns/bad.md", "Project: garden\nChanges v1:\nfrobnicate\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        pressing = self.s.read("agenda/00-PRESSING.md")
        first = pressing.split("## ")[1]
        self.assertTrue(first.startswith("Raise with Sam first"), pressing)
        self.assertIn("could not be filed", first)
        self.assertIn("A return could not be filed", pressing.split("## Critical (importance 1)")[1])
        self.assertNotIn("could not be filed", self.s.read("00-START-HERE.md"))
        self.assertTrue(self.s.exists("projects/garden/collab-kit/_returns/failed/bad.md"))

    def test_start_file_without_setup_line_is_left_alone(self):
        hand = "# Start here\n\nWritten by hand.\n\n## Due soon\n\n- 2026-12-01: something\n"
        self.s.write("00-START-HERE.md", hand)
        p, rc = self.run_pass()
        self.assertEqual(self.s.read("00-START-HERE.md"), hand)
        self.assertTrue(any("no setup line" in x for x in p.problems), p.problems)
        self.assertIn("no setup line", self.s.read("agenda/00-PRESSING.md"))

    def test_hand_edited_setup_line_is_left_alone(self):
        from collab_kit.templates import replace_block
        hand = replace_block(top_start_file(), "setup", "**A back end runs here, on the Studio.** File returns.")
        self.s.write("00-START-HERE.md", hand)
        self.run_pass()
        self.run_pass()
        self.assertEqual(self.s.read("00-START-HERE.md"), hand)

    def test_windows_line_endings_in_the_start_file(self):
        self.s.write("00-START-HERE.md", top_start_file().replace("\n", "\r\n"))
        p, rc = self.run_pass()
        self.assertFalse(any("setup line" in x for x in p.problems), p.problems)
        self.assertIn("A back end runs for this folder", self.s.read("00-START-HERE.md"))

    def test_dry_run_writes_nothing(self):
        start = self.s.read("00-START-HERE.md")
        BE.Pass(self.cfg, dry_run=True).run()
        self.assertEqual(self.s.read("00-START-HERE.md"), start)
        self.assertFalse(self.s.exists("agenda/00-PRESSING.md"))

    def test_start_file_setup_line_set_once(self):
        self.run_pass()
        start = self.s.read("00-START-HERE.md")
        versions = [f.name for f in self.s.files("_versions") if f.name.startswith("00-START-HERE")]
        self.drop("_returns/t2.md", "Project: top\nChanges v1:\nnew-item title=\"Later\" due=2026-11-20\nEnd.\n")
        self.run_pass()
        self.assertEqual(self.s.read("00-START-HERE.md"), start)
        self.assertEqual([f.name for f in self.s.files("_versions") if f.name.startswith("00-START-HERE")], versions)

    # ------------------------------------------------------------- from the back-end review
    def reject_pushes(self, on: bool):
        hook = self.origin / "hooks" / "pre-receive"
        if on:
            hook.write_text("#!/bin/sh\necho rejected >&2\nexit 1\n")
            hook.chmod(0o755)
        elif hook.exists():
            hook.unlink()

    def origin_text(self):
        check = self.t / f"check-{time.time_ns()}"
        sh("git", "clone", "-q", str(self.origin), str(check))
        return "\n".join(p.read_text(errors="replace") for p in (check / "collab-kit").rglob("*") if p.is_file())

    def test_failed_push_loses_nothing(self):
        self.drop("projects/site/collab-kit/_returns/r1.md", "Project: site\nChanges v1:\nnew-item title=\"Survives\"\nEnd.\n")
        self.reject_pushes(True)
        p, rc = self.run_pass()
        self.assertTrue(any("push failed" in x for x in p.problems))
        self.assertTrue(self.s.exists("projects/site/collab-kit/_returns/r1.md"), "the return stays in the inbox")
        p2, _ = self.run_pass()                                    # still failing: still reported
        self.assertTrue(any("push failed" in x for x in p2.problems))
        self.reject_pushes(False)
        p3, rc3 = self.run_pass()
        self.assertEqual(rc3, 0, p3.problems)
        self.assertIn("Survives", self.origin_text())
        self.assertTrue(self.s.exists("projects/site/collab-kit/_returns/applied/r1.md"))

    def test_deny_list_cannot_be_bypassed_by_a_later_pass(self):
        self.drop("projects/site/collab-kit/_returns/r1.md", "Project: site\nChanges v1:\nstatus \"about codename-x\"\nEnd.\n")
        self.run_pass()
        self.assertTrue(self.s.exists("projects/site/collab-kit/_returns/failed/r1.md"))
        self.drop("projects/site/collab-kit/_returns/r2.md", "Project: site\nChanges v1:\nnew-item title=\"Unrelated\"\nEnd.\n")
        p, rc = self.run_pass()
        text = self.origin_text()
        self.assertIn("Unrelated", text)
        self.assertNotIn("codename-x", text)

    def test_unreadable_mirror_state_stops_that_mirror(self):
        self.drop("projects/site/collab-kit/_returns/r1.md", "Project: site\nChanges v1:\nstatus \"one\"\nEnd.\n")
        self.run_pass()
        self.s.write("_backend/mirror/site.json", "{not json")
        self.s.write("projects/site/collab-kit/knowledge/README.md", "an edit that must survive\n")
        p, _ = self.run_pass()
        self.assertTrue(any("unreadable" in x for x in p.problems))
        self.assertEqual(self.s.read("projects/site/collab-kit/knowledge/README.md"), "an edit that must survive\n")

    def test_first_mirror_keeps_differing_files(self):
        self.s.write("projects/site/collab-kit/knowledge/README.md", "a hand copy with notes\n")
        self.run_pass()
        self.assertEqual(self.s.read("projects/site/collab-kit/_versions/before-first-mirror/knowledge/README.md"),
                         "a hand copy with notes\n")

    def test_binary_files_mirror_exactly(self):
        seed = self.t / "seed"
        png = bytes(range(256)) * 2
        (seed / "collab-kit/knowledge/diagram.png").write_bytes(png)
        sh("git", "add", "-A", cwd=seed)
        sh("git", "commit", "-qm", "a picture", cwd=seed)
        sh("git", "push", "-q", "origin", "HEAD:main", cwd=seed)
        self.run_pass()
        self.assertEqual((self.cloud / "projects/site/collab-kit/knowledge/diagram.png").read_bytes(), png)

    def test_two_cloud_edits_are_two_returns(self):
        seed = self.t / "seed"
        for n in ("a", "b"):
            (seed / f"collab-kit/knowledge/a-very-long-shared-folder-name-for-notes/{n}.md").parent.mkdir(parents=True, exist_ok=True)
            (seed / f"collab-kit/knowledge/a-very-long-shared-folder-name-for-notes/{n}.md").write_text(f"{n}\n")
        sh("git", "add", "-A", cwd=seed)
        sh("git", "commit", "-qm", "notes", cwd=seed)
        sh("git", "push", "-q", "origin", "HEAD:main", cwd=seed)
        self.run_pass()
        for n in ("a", "b"):
            self.s.write(f"projects/site/collab-kit/knowledge/a-very-long-shared-folder-name-for-notes/{n}.md", f"edited {n}\n")
        self.run_pass()
        saved = [e.name for e in self.s.files("projects/site/collab-kit/_returns") if "edited" in e.name]
        self.assertEqual(len(saved), 2, saved)

    def test_cloud_only_file_in_a_copy_goes_to_strays(self):
        self.run_pass()
        self.s.write("projects/site/collab-kit/agenda/W-050-made-in-the-folder.md", "+++\nid = \"W-050\"\n+++\n")
        p, _ = self.run_pass()
        self.assertFalse(self.s.exists("projects/site/collab-kit/agenda/W-050-made-in-the-folder.md"))
        self.assertTrue(any("created in the folder" in x for x in p.problems))

    def test_bad_encoding_does_not_stop_the_pass(self):
        (self.cloud / "projects/garden/collab-kit/_returns/cp.txt").write_bytes(b"Project: garden\nTopic: caf\xe9\nEnd.\n")
        old(self.cloud / "projects/garden/collab-kit/_returns/cp.txt")
        p, _ = self.run_pass()
        self.assertTrue(self.s.exists("_backend/heartbeat.json"))
        self.assertIn("A back end runs", self.s.read("00-START-HERE.md"))

    def test_drive_alias_copy_is_not_a_second_item(self):
        a = self.cloud / "projects/garden/collab-kit/agenda"
        item = '+++\nid = "W-005"\ntitle = "Water"\nkind = "task"\nimportance = 3\nstatus = "open"\n+++\n'
        (a / "W-005-water.md").write_text(item)
        old(a / "W-005-water.md")
        (a / "W-005-water (1).md").write_text(item.replace("Water", "Water the beds"))
        self.run_pass()
        names = sorted(p.name for p in a.glob("W-*.md"))
        self.assertEqual(len(names), 1, names)
        self.assertTrue(names[0].startswith("W-005"))

    def test_public_check(self):
        p = BE.Pass(self.cfg)
        d = self.t / "pub"
        sh("git", "init", "-q", str(d))
        for url, public in (("git@github-personal:sam/site.git", True), ("https://gitlab.example.com/a/b.git", True),
                            (str(self.origin), False)):
            sh("git", "-C", str(d), "remote", "remove", "origin") if "origin" in sh("git", "-C", str(d), "remote") else None
            sh("git", "-C", str(d), "remote", "add", "origin", url)
            self.assertEqual(p.is_public(d), public, url)

    # ------------------------------------------------------------- from the verification review
    def push_seed(self, files: dict, symlinks: dict | None = None):
        seed = self.t / "seed"
        for rel, text in files.items():
            (seed / rel).parent.mkdir(parents=True, exist_ok=True)
            (seed / rel).write_text(text)
        for rel, target in (symlinks or {}).items():
            (seed / rel).parent.mkdir(parents=True, exist_ok=True)
            os.symlink(target, seed / rel)
        sh("git", "add", "-A", cwd=seed)
        sh("git", "commit", "-qm", "seed more", cwd=seed)
        sh("git", "push", "-q", "origin", "HEAD:main", cwd=seed)

    def test_symlinks_never_leave_the_repository(self):
        secret = self.t / "secret.txt"
        secret.write_text("private\n")
        self.push_seed({}, {"collab-kit/knowledge/leak.md": str(secret)})
        self.run_pass()
        leaked = self.cloud / "projects/site/collab-kit/knowledge/leak.md"
        self.assertFalse(leaked.exists() and "private" in leaked.read_text())

    def test_non_ascii_names_commit_and_push(self):
        self.drop("projects/site/collab-kit/_returns/r1.md",
                  "Project: site\nChanges v1:\nknowledge \"notes/caf\u00e9 menu.md\"\n```\nbeans\n```\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertIn("beans", self.origin_text())

    def test_drive_numbered_return_names(self):
        for n in ("x.md", "x (1).md"):
            self.drop(f"projects/site/collab-kit/_returns/{n}", f"Project: site\nChanges v1:\nstatus \"from {n}\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        text = self.origin_text()
        self.assertIn("from x.md", text)
        self.assertIn("from x (1).md", text)

    def test_unknown_visibility_blames_no_return(self):
        self.cfg["project"][0]["allow_public"] = False
        orig = BE.Pass.is_public
        BE.Pass.is_public = lambda self, d: True
        try:
            self.drop("projects/site/collab-kit/_returns/good.md", "Project: site\nChanges v1:\nstatus \"fine\"\nEnd.\n")
            p, rc = self.run_pass()
        finally:
            BE.Pass.is_public = orig
        self.assertTrue(self.s.exists("projects/site/collab-kit/_returns/good.md"), "nothing blamed, nothing moved")
        self.assertTrue(any("not pushed" in x for x in p.problems))

    def test_project_row_change_survives_a_failed_push(self):
        self.drop("projects/site/collab-kit/_returns/r1.md", "Project: site\nChanges v1:\nproject about=\"The new site\"\nEnd.\n")
        self.reject_pushes(True)
        self.run_pass()
        self.reject_pushes(False)
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue(self.s.exists("projects/site/collab-kit/_returns/applied/r1.md"))

    def test_push_false_follows_the_remote(self):
        self.cfg["project"][0]["push"] = False
        self.drop("projects/site/collab-kit/_returns/r1.md", "Project: site\nChanges v1:\nstatus \"local\"\nEnd.\n")
        self.run_pass()
        self.push_seed({"README.md": "someone else's work\n"})
        self.drop("projects/site/collab-kit/_returns/r2.md", "Project: site\nChanges v1:\nstatus \"later\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue(self.s.exists("projects/site/collab-kit/_returns/applied/r2.md"))

    def test_glob_characters_in_names_stay_out_of_git(self):
        self.drop("projects/site/collab-kit/_returns/Notes[draft].md", "Project: site\nChanges v1:\nstatus \"draft\"\nEnd.\n")
        self.run_pass()
        check = self.t / "check-glob"
        sh("git", "clone", "-q", str(self.origin), str(check))
        self.assertFalse([p for p in (check / "collab-kit/_returns").rglob("*") if p.suffix == ".md" and "draft" in p.name.lower()])

    def test_inactive_projects_collapse(self):
        self.s.write("projects/old/collab-kit/agenda/W-001-x.md",
                     '+++\nid = "W-001"\ntitle = "Old thing"\nkind = "task"\nimportance = 2\nstatus = "open"\n+++\n')
        self.s.write("projects/old/collab-kit/agenda/W-002-y.md",
                     '+++\nid = "W-002"\ntitle = "Still critical"\nkind = "task"\nimportance = 1\nstatus = "open"\n+++\n')
        self.run_pass()
        pressing = self.s.read("agenda/00-PRESSING.md")
        self.assertNotIn("Old thing", pressing)
        self.assertIn("Still critical", pressing.split("## Critical (importance 1)")[1])   # critical never hides
        self.assertIn("old: 2 open item(s)", pressing)

    # ------------------------------------------------ 0.5.2: event-driven, push, the catalog --

    def test_inbox_files_lists_every_inbox_once(self):
        self.s.write("_returns/a.md", "x")
        self.s.write("_returns/README.md", "x")
        self.s.write("projects/garden/collab-kit/_returns/b.md", "x")
        self.s.write("projects/garden/collab-kit/_returns/_set-aside/c.md", "x")
        self.assertEqual(sorted(self.s.inbox_files()),
                         ["_returns/a.md", "projects/garden/collab-kit/_returns/b.md"])

    def test_if_waiting_skips_a_quiet_minute_and_runs_when_a_return_waits(self):
        cfgfile = self.t / "backend.toml"
        b = self.cfg["backend"]
        cfgfile.write_text(
            "[backend]\n" + "".join(f"{k} = {json.dumps(v)}\n" for k, v in b.items()) + "interval_minutes = 60\n",
            encoding="utf-8")
        self.assertEqual(BE.run(str(cfgfile), if_waiting=True), 0)          # no stamp yet: a full pass
        hb1 = self.s.read("_backend/heartbeat.json")
        self.assertTrue((self.t / "work" / BE.LAST_PASS).is_file())
        time.sleep(1.1)
        self.assertEqual(BE.run(str(cfgfile), if_waiting=True), 0)          # nothing waits, fresh: no pass
        self.assertEqual(self.s.read("_backend/heartbeat.json"), hb1)
        self.drop("_returns/t9.md", "Project: top\nChanges v1:\nnew-item title=\"Rang the bell\"\nEnd.\n")
        BE.run(str(cfgfile), if_waiting=True)                               # a return waits: a full pass
        self.assertNotEqual(self.s.read("_backend/heartbeat.json"), hb1)
        self.assertTrue(any("Rang the bell" in (self.s.read(f"agenda/{e.name}") or "")
                            for e in self.s.files("agenda")))

    def test_schedule_ticks_every_minute_and_watches_inboxes(self):
        from collab_kit import schedule
        watch = schedule.watch_paths(self.cloud)
        self.assertEqual(watch, [str(self.cloud / "_returns"), str(self.cloud / "projects/garden/collab-kit/_returns"),
                                 str(self.cloud / "projects/site/collab-kit/_returns")])
        plist = schedule.launchd_plist(KIT, self.t / "b.toml", self.t / "logs", 60, None, watch=watch)
        self.assertIn("<string>--if-waiting</string>", plist)
        self.assertIn("<key>StartInterval</key><integer>60</integer>", plist)
        self.assertIn("<key>WatchPaths</key>", plist)
        self.assertNotIn("WatchPaths", schedule.launchd_plist(KIT, self.t / "b.toml", self.t / "logs", 60, None))
        self.assertIn("--if-waiting", (KIT / "engine" / "backend.sh").read_text())

    def test_push_once_per_new_critical_item_text_in_the_environment(self):
        out = self.t / "pushed.txt"
        self.cfg["notify"] = {"command": [sys.executable, "-c",
                                          "import os,sys; open(sys.argv[1],'a').write(os.environ['COLLAB_KIT_MESSAGE']"
                                          "+'|'+os.environ['COLLAB_KIT_ITEM']+'\\n')", str(out)]}
        self.s.write("agenda/W-001-x.md", '+++\nid = "W-001"\ntitle = "Already critical"\nkind = "task"\n'
                                          'importance = 1\nstatus = "open"\n+++\n')
        self.run_pass()
        self.assertFalse(out.exists())                     # the first run remembers, sends nothing
        self.drop("projects/garden/collab-kit/_returns/r5.md", "Project: garden\nChanges v1:\n"
                  "new-item title=\"$(touch /tmp/nope) Water main burst\" importance=1\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(out.read_text().splitlines(), ["$(touch /tmp/nope) Water main burst|garden W-001"])
        self.run_pass()
        self.assertEqual(len(out.read_text().splitlines()), 1)   # never twice
        self.cfg["notify"] = {"command": [sys.executable, "-c", "import sys; sys.exit(3)"]}
        self.drop("_returns/t7.md", "Project: top\nChanges v1:\nnew-item title=\"Another\" importance=1\nEnd.\n")
        p, rc = self.run_pass()
        self.assertTrue(any("notify command failed" in x for x in p.problems), p.problems)

    def test_catalog_collab_kit_status(self):
        self.s.write("knowledge/projects.md", "| Folder | Say | What it is | Where | Status | Collab Kit |\n"
                     "|---|---|---|---|---|---|\n| `garden` | \"g\" | g | cloud | active | live |\n"
                     "| `shed` | \"the shed\" | a shed app | GitHub (private) | active | not set up |\n")
        self.drop("_returns/t2.md", "Project: top\nChanges v1:\nproject shed collab-kit=requested\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertIn("| `shed` | \"the shed\" | a shed app | GitHub (private) | active | requested |",
                      self.s.read("knowledge/projects.md"))
        self.drop("_returns/t3.md", "Project: top\nChanges v1:\nproject shed collab-kit=maybe\nEnd.\n")
        self.run_pass()
        from collab_kit.unit import FAILED
        self.assertTrue(self.s.files(FAILED))                    # refused: not one of the three states


if __name__ == "__main__":
    unittest.main()

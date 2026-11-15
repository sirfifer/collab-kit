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
        s.write("00-START-HERE.md", top_start_file() + "| \"the garden\" | `garden` | g | edit |\n")
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
                                "local_roots": [], "deny": ["codename-x"]},
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
        self.drop("_returns/t1.md", "Project: top\nChanges v1:\nnew-item title=\"Top thing\" importance=2\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        pressing = self.s.read("agenda/00-PRESSING.md")
        self.assertIn("Order seeds", pressing)
        self.assertIn("Top thing", pressing)
        self.assertNotIn("Someday", pressing)
        start = self.s.read("00-START-HERE.md")
        self.assertIn("A back end runs for this folder", start)
        hb = json.loads(self.s.read("_backend/heartbeat.json"))
        self.assertEqual(hb["problems"], [])
        # a second pass with nothing new changes nothing (no new versions)
        versions = len(self.s.files("_versions"))
        self.run_pass()
        self.assertEqual(len(self.s.files("_versions")), versions)

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
        self.assertIn("collab-kit: apply returns", log)

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
        self.assertIn("could not be filed", self.s.read("00-START-HERE.md"))
        self.assertTrue(self.s.exists("projects/garden/collab-kit/_returns/failed/bad.md"))

    def test_inactive_projects_collapse(self):
        self.s.write("projects/old/collab-kit/agenda/W-001-x.md",
                     '+++\nid = "W-001"\ntitle = "Old thing"\nkind = "task"\nimportance = 1\nstatus = "open"\n+++\n')
        self.run_pass()
        pressing = self.s.read("agenda/00-PRESSING.md")
        self.assertNotIn("Old thing", pressing)
        self.assertIn("old: 1 open item(s)", pressing)


if __name__ == "__main__":
    unittest.main()

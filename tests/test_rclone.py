"""RcloneStore against a fake rclone (tests/fake_rclone.py): the intake conditions, and the engine's
apply path running over it unchanged."""
from __future__ import annotations

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import isolation  # noqa: E402,F401  (first: never the machine's real Collab Kit)

import os
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "engine"))

from collab_kit import apply as A                       # noqa: E402
from collab_kit.store import RcloneStore, StoreError    # noqa: E402
from collab_kit.unit import Unit                        # noqa: E402


class Rclone(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        (self.t / "drive" / "Collab Kit" / "_returns").mkdir(parents=True)
        launcher = self.t / ("rclone.cmd" if os.name == "nt" else "rclone")
        if os.name == "nt":
            launcher.write_text(f'@"{sys.executable}" "{HERE / "fake_rclone.py"}" %*\n')
        else:
            launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{HERE / "fake_rclone.py"}" "$@"\n')
            launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
        self.rclone = str(launcher)
        os.environ["FAKE_RCLONE_ROOT"] = str(self.t)
        self.store = RcloneStore("drive:Collab Kit", rclone=self.rclone)

    def tearDown(self):
        for k in ("FAKE_RCLONE_ROOT", "FAKE_RCLONE_VERSION", "FAKE_RCLONE_DUP", "FAKE_RCLONE_OWNER",
                  "FAKE_RCLONE_CALLS", "COLLAB_KIT_RCLONE", "RCLONE_CONFIG_PASS"):
            os.environ.pop(k, None)
        self.tmp.cleanup()

    def test_round_trip_and_large_writes(self):
        self.store.write("knowledge/a.md", "hello\n")
        self.assertEqual(self.store.read("knowledge/a.md"), "hello\n")
        big = "x" * (200 * 1024)
        self.store.write("knowledge/big.md", big)
        self.assertEqual(self.store.read("knowledge/big.md"), big)
        self.store.copy("knowledge/a.md", "knowledge/_versions/a.1.md")
        self.store.move("knowledge/a.md", "knowledge/b.md")
        self.assertEqual(sorted(e.name for e in self.store.files("knowledge")), ["b.md", "big.md"])
        self.assertIsNone(self.store.read("knowledge/missing.md"))
        self.assertEqual(self.store.list("nope"), [])

    def test_account_is_the_owner_of_the_start_file(self):
        # found on the first real run (2026-11-18): rclone has no `config userinfo` for Google Drive
        self.assertEqual(self.store.account(), "", "no start file: cannot be told")
        self.store.write("00-START-HERE.md", "start\n")
        self.assertEqual(self.store.account(), "", "no owner in the listing: cannot be told")
        os.environ["FAKE_RCLONE_OWNER"] = "sam@example.com"
        self.assertEqual(self.store.account(), "sam@example.com")

    def test_shared_google_client_is_noticed(self):
        # found 2026-11-19: the first real back end ran on rclone's shared client, which Google retires in 2026
        conf = self.t / "rclone.conf"
        store = RcloneStore("collabkit:", rclone=self.rclone, config=str(conf))
        self.assertFalse(store.uses_shared_google_client(), "no config file: cannot tell")
        conf.write_text("[collabkit]\ntype = drive\nscope = drive\nclient_id = \ntoken = {}\n")
        self.assertTrue(store.uses_shared_google_client())
        conf.write_text("[collabkit]\ntype = drive\nclient_id = 123-abc.apps.googleusercontent.com\n")
        self.assertFalse(store.uses_shared_google_client())
        conf.write_text("[collabkit]\ntype = onedrive\n")
        self.assertFalse(store.uses_shared_google_client(), "not Google Drive")
        conf.write_text("RCLONE_ENCRYPT_V0:\nabcdef\n")
        self.assertFalse(store.uses_shared_google_client(), "an encrypted config: cannot tell")
        xdg = self.t / "xdg"                                    # no config given: rclone's own default places
        (xdg / "rclone").mkdir(parents=True)
        (xdg / "rclone" / "rclone.conf").write_text("[collabkit]\ntype = drive\n")
        os.environ["XDG_CONFIG_HOME"] = str(xdg)
        try:
            self.assertTrue(RcloneStore("collabkit:", rclone=self.rclone).uses_shared_google_client())
        finally:
            import isolation
            isolation.restore()

    def test_an_error_shows_its_cause_not_rclones_notices(self):
        # found 2026-11-19: every error on the Studio was cut off after the shared-client notice
        import subprocess
        from unittest import mock
        from collab_kit import store as S
        stderr = (b"2026/11/19 13:47:55 NOTICE: collabkit: This remote uses rclone's shared Google Drive client_id, "
                  + b"x" * 400 + b"\n2026/11/19 13:47:56 ERROR : agenda/00-PRESSING.md: Failed to copy: "
                  b"googleapi: Error 403: Rate Limit Exceeded\n")
        done = subprocess.CompletedProcess([], 1, b"", stderr)
        self.store._checked = True
        with mock.patch.object(S, "run_quiet", return_value=done):
            with self.assertRaises(S.StoreError) as cm:
                self.store.write("agenda/00-PRESSING.md", "x")
        self.assertIn("Error 403: Rate Limit Exceeded", str(cm.exception))
        self.assertNotIn("NOTICE", str(cm.exception))

    def test_back_end_checks_the_account_over_rclone(self):
        from collab_kit.backend import Pass
        self.store.write("00-START-HERE.md", "start\n")
        os.environ["FAKE_RCLONE_OWNER"] = "sam@example.com"
        cfg = {"backend": {"cloud": "rclone:drive:Collab Kit", "work": str(self.t / "work"),
                           "account": "sam@example.com"}}
        os.environ["COLLAB_KIT_RCLONE"] = self.rclone
        self.assertIsNone(Pass(cfg).check_account())
        cfg["backend"]["account"] = "someone@example.com"
        self.assertIn("owned by sam@example.com", Pass(cfg).check_account())
        os.environ.pop("FAKE_RCLONE_OWNER")
        self.assertIn("cannot tell", Pass(cfg).check_account())

    def test_inbox_entries_in_one_call(self):
        import time
        for rel in ("_returns/a.md", "_returns/README.md", "_returns/applied/old.md",
                    "projects/garden/collab-kit/_returns/b.md", "projects/garden/collab-kit/agenda/W-001-x.md",
                    "projects/garden/notes/_returns/c.md"):
            self.store.write(rel, "x\n")
        got = self.store.inbox_entries()
        self.assertEqual(sorted(p for p, _, _ in got), ["_returns/a.md", "projects/garden/collab-kit/_returns/b.md"])
        self.assertTrue(all(abs(m - time.time()) < 120 and s == 2 for _, m, s in got), got)

    def test_pinned_version_only(self):
        os.environ["FAKE_RCLONE_VERSION"] = "v1.70.0"
        with self.assertRaises(StoreError):
            RcloneStore("drive:Collab Kit", rclone=self.rclone).list("")

    def test_inherited_rclone_settings_are_stripped(self):
        os.environ["RCLONE_CONFIG_PASS"] = "secret"
        self.store.list("")                                        # the fake exits 9 if it sees it

    def test_duplicates_fail_closed_per_name(self):
        self.store.write("_returns/r.md", "x")
        self.store.write("_returns/s.md", "y")
        os.environ["FAKE_RCLONE_DUP"] = "r.md"
        names = [e.name for e in self.store.list("_returns")]
        self.assertEqual(names, ["r.md", "s.md"])                 # listing still works
        with self.assertRaises(StoreError):
            self.store.read("_returns/r.md")                       # the duplicated name does not
        self.assertEqual(self.store.read("_returns/s.md"), "y")

    def test_non_utf8_and_hashes(self):
        (self.t / "drive" / "Collab Kit" / "_returns" / "cp1252.txt").write_bytes(b"caf\xe9 \x93quoted\x94\n")
        self.assertIn("caf", self.store.read("_returns/cp1252.txt"))
        self.store.write("knowledge/a.md", "hello\n")
        import hashlib
        self.assertEqual(self.store.md5s("knowledge")["a.md"], hashlib.md5(b"hello\n").hexdigest())

    def test_native_files_are_never_read_and_are_set_aside(self):
        f = self.t / "drive" / "Collab Kit" / "_returns" / "notes.gdoc-native"
        f.write_text("binary")
        unit = Unit(self.store, "top", home="cloud", top=True)
        e = [e for e in unit.pending_returns() if e.name.endswith("native")][0]
        self.assertTrue(e.native)
        self.assertEqual(A.apply_file(unit, e).status, "waiting")      # a conversation may still be moving it
        os.utime(f, (time.time() - 3600, time.time() - 3600))
        e = [e for e in unit.pending_returns() if e.name.endswith("native")][0]
        self.assertEqual(A.apply_file(unit, e).status, "stray")

    def test_engine_applies_over_rclone(self):
        unit = Unit(self.store, "top", home="cloud", top=True)
        self.store.write("_returns/r1.md", "Project: top\nChanges v1:\nnew-item title=\"Over rclone\"\nEnd.\n")
        p = self.t / "drive" / "Collab Kit" / "_returns" / "r1.md"
        os.utime(p, (time.time() - 3600, time.time() - 3600))
        out = A.apply_file(unit, unit.store.entry("_returns/r1.md"))
        self.assertEqual(out.status, "applied", out.message)
        self.assertEqual([i.title for i in unit.items()], ["Over rclone"])
        self.store.write("_returns/r2.md", "Project: top\nChanges v1:\nset W-001 \"rclone\" importance=1\nEnd.\n")
        os.utime(self.t / "drive" / "Collab Kit" / "_returns" / "r2.md", (time.time() - 3600, time.time() - 3600))
        A.apply_file(unit, unit.store.entry("_returns/r2.md"))
        self.assertEqual(unit.item("W-001").importance, 1)
        self.assertEqual(len(self.store.files("agenda/_versions")), 1)

    # ---- a pass's snapshot (W-020: one listing per pass, a download only for a changed file)
    def calls(self):
        f = self.t / "calls.log"
        lines = f.read_text().splitlines() if f.exists() else []
        f.write_text("")
        return lines

    def test_a_snapshot_lists_once_and_reads_from_the_cache(self):
        os.environ["FAKE_RCLONE_CALLS"] = str(self.t / "calls.log")
        for rel, text in (("agenda/W-001-a.md", "a\n"), ("agenda/W-002-b.md", "b\n"), ("knowledge/k.md", "k\n")):
            self.store.write(rel, text)
        self.calls()
        cache = self.t / "work" / "rclone-cache"
        self.store.snapshot(cache)
        self.assertEqual([e.name for e in self.store.files("agenda")], ["W-001-a.md", "W-002-b.md"])
        self.assertEqual(self.store.read("agenda/W-001-a.md"), "a\n")
        self.assertEqual(self.store.read("agenda/W-001-a.md"), "a\n")           # the second read: the cache
        self.assertIsNone(self.store.read("agenda/missing.md"))
        self.assertEqual(self.store.list("nope"), [])
        self.assertEqual(self.calls(), ["lsjson -R drive:Collab Kit", "cat drive:Collab Kit/agenda/W-001-a.md"])
        self.store.end_snapshot()
        # the next pass (a new store, as every run is): the cache answers, one changed file is downloaded
        (self.t / "drive" / "Collab Kit" / "agenda" / "W-001-a.md").write_text("a, changed elsewhere\n")
        store = RcloneStore("drive:Collab Kit", rclone=self.rclone)
        store.snapshot(cache)
        self.assertEqual(store.read("agenda/W-001-a.md"), "a, changed elsewhere\n")
        self.assertEqual(store.read("agenda/W-001-a.md"), "a, changed elsewhere\n")
        self.assertEqual(store.read("agenda/W-002-b.md"), "b\n")
        self.assertEqual(self.calls(), ["lsjson -R drive:Collab Kit", "cat drive:Collab Kit/agenda/W-001-a.md",
                                        "cat drive:Collab Kit/agenda/W-002-b.md"])
        store.end_snapshot()
        self.assertEqual(len(list(cache.iterdir())), 2, "the old copy of W-001 is dropped")
        store = RcloneStore("drive:Collab Kit", rclone=self.rclone)
        store.snapshot(cache)
        self.assertEqual([store.read(f"agenda/{n}") for n in ("W-001-a.md", "W-002-b.md")], ["a, changed elsewhere\n", "b\n"])
        self.assertEqual(self.calls(), ["lsjson -R drive:Collab Kit"], "steady state: the listing only")
        self.assertEqual(store.cache_hits, 2)

    def test_a_snapshot_follows_its_own_writes(self):
        os.environ["FAKE_RCLONE_CALLS"] = str(self.t / "calls.log")
        self.store.write("agenda/W-001-a.md", "a\n")
        self.store.snapshot(None)                                   # memory only, as in a dry run
        self.calls()
        self.store.write("agenda/W-001-a.md", "a2\n")
        self.store.copy("agenda/W-001-a.md", "agenda/_versions/W-001-a.1.md")
        self.store.mkdir("agenda")                                  # listed: no call
        self.store.mkdir("_returns/applied")
        self.store.write("_returns/r.md", "r\n")
        self.store.move("_returns/r.md", "_returns/applied/r.md")
        self.store.write("knowledge/new/deep.md", "deep\n")
        self.assertEqual(self.store.read("agenda/W-001-a.md"), "a2\n")
        self.assertEqual(self.store.read("agenda/_versions/W-001-a.1.md"), "a2\n")
        self.assertEqual(self.store.read("_returns/applied/r.md"), "r\n")
        self.assertIsNone(self.store.read("_returns/r.md"))
        self.assertTrue(self.store.exists("knowledge/new"))
        self.assertEqual([e.name for e in self.store.dirs("knowledge")], ["new"])
        with self.assertRaises(StoreError):
            self.store.copy("agenda/W-001-a.md", "agenda/_versions/W-001-a.1.md")
        self.assertEqual([c.split()[0] for c in self.calls()], ["rcat", "copyto", "mkdir", "rcat", "moveto", "rcat"])
        self.store.end_snapshot()
        self.assertEqual(self.store.read("_returns/applied/r.md"), "r\n")    # the folder agrees
        self.assertEqual(self.store.read("agenda/_versions/W-001-a.1.md"), "a2\n")

    def test_a_snapshot_keeps_the_rules(self):
        self.store.write("_returns/r.md", "x")
        self.store.write("_returns/s.md", "y")
        (self.t / "drive" / "Collab Kit" / "_returns" / "notes.gdoc-native").write_text("binary")
        self.store.write("_backend/lease.json", "{}")
        os.environ["FAKE_RCLONE_DUP"] = "r.md"
        self.store.snapshot(self.t / "cache")
        with self.assertRaises(StoreError):
            self.store.read("_returns/r.md")                         # a duplicated name still fails closed
        with self.assertRaises(StoreError):
            self.store.write("_returns/r.md", "z")
        self.assertEqual(self.store.read("_returns/s.md"), "y")
        native = [e for e in self.store.list("_returns") if e.name.endswith("native")][0]
        self.assertTrue(native.native)
        self.assertGreater(native.mtime, 0)
        self.assertEqual(self.store.read("_backend/lease.json"), "{}")       # downloaded once: now in the cache
        os.environ["FAKE_RCLONE_CALLS"] = str(self.t / "calls.log")
        (self.t / "drive" / "Collab Kit" / "_backend" / "lease.json").write_text('{"holder": "other"}')
        self.assertEqual(self.store.read("_backend/lease.json"), "{}", "a read is the folder as the pass listed it")
        self.assertEqual(self.store.read_fresh("_backend/lease.json"), '{"holder": "other"}', "the lease: as it is now")
        self.assertEqual(self.calls(), ["cat drive:Collab Kit/_backend/lease.json"])
        from collab_kit.store import ContentCache
        cc = ContentCache(self.t / "cache")
        self.assertIsNone(cc.get("../../etc/passwd"), "a listed hash is never a path")
        h = cc.put(b"hello")
        (self.t / "cache" / h).write_bytes(b"tampered")
        self.assertIsNone(cc.get(h), "a copy that no longer matches its md5 is dropped")
        self.assertFalse((self.t / "cache" / h).exists())



class PassOverRclone(unittest.TestCase):
    """A whole back end pass through rclone (the fake), counted call by call: one listing of the
    folder, and a download only for a file whose md5 the cache does not hold (W-020)."""

    def setUp(self):
        import subprocess
        from collab_kit.store import FolderStore
        from collab_kit.templates import set_human, top_start_file
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        launcher = t / ("rclone.cmd" if os.name == "nt" else "rclone")
        if os.name == "nt":
            launcher.write_text(f'@"{sys.executable}" "{HERE / "fake_rclone.py"}" %*\n')
        else:
            launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{HERE / "fake_rclone.py"}" "$@"\n')
            launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
        os.environ.update(FAKE_RCLONE_ROOT=str(t), COLLAB_KIT_RCLONE=str(launcher), FAKE_RCLONE_CALLS=str(t / "calls.log"))
        self.root = t / "drive" / "Collab Kit"
        set_human("Sam")
        s = self.s = FolderStore(self.root)                         # the folder itself, written behind rclone's back
        s.write("00-START-HERE.md", top_start_file())
        s.write("knowledge/projects.md", "| Folder | Say | What it is | Home |\n|---|---|---|---|\n"
                "| `garden` | \"g\" | g | cloud |\n| `site` | \"s\" | the site | repo |\n")
        for d in ("_returns", "agenda", "projects/garden/collab-kit/_returns", "projects/garden/collab-kit/agenda",
                  "projects/site/collab-kit/_returns"):
            s.mkdir(d)
        origin, seed = t / "site.git", t / "seed"

        def sh(*a, cwd=None):
            subprocess.run(list(a), cwd=cwd, check=True, capture_output=True)
        sh("git", "init", "-q", "--bare", "-b", "main", str(origin))
        sh("git", "clone", "-q", str(origin), str(seed))
        sh("git", "-c", "user.email=t@example.com", "-c", "user.name=T", "commit", "-q", "--allow-empty", "-m", "x", cwd=seed)
        (seed / "collab-kit/knowledge").mkdir(parents=True)
        (seed / "collab-kit/00-START-HERE.md").write_text("# site\n")
        (seed / "collab-kit/knowledge/README.md").write_text("# site knowledge\n")
        sh("git", "add", "-A", cwd=seed)
        sh("git", "-c", "user.email=t@example.com", "-c", "user.name=T", "commit", "-qm", "seed", cwd=seed)
        sh("git", "push", "-q", "origin", "HEAD:main", cwd=seed)
        self.cfg = {"backend": {"cloud": "rclone:drive:Collab Kit", "work": str(t / "work"), "human": "Sam",
                                "local_roots": [], "lease_settle_seconds": 0},
                    "project": [{"name": "site", "repo": str(origin), "branch": "main", "push": True,
                                 "allow_public": True}]}

    def tearDown(self):
        for k in ("FAKE_RCLONE_ROOT", "FAKE_RCLONE_CALLS", "COLLAB_KIT_RCLONE"):
            os.environ.pop(k, None)
        self.tmp.cleanup()

    def drop(self, rel, text):
        self.s.write(rel, text)
        t = time.time() - 3600
        os.utime(self.root / rel, (t, t))

    def run_pass(self):
        from collab_kit.backend import Pass
        log = self.t / "calls.log"
        log.write_text("")
        p = Pass(self.cfg)
        rc = p.run()
        return p, rc, log.read_text().splitlines()

    def test_a_steady_pass_is_one_listing(self):
        self.drop("projects/garden/collab-kit/_returns/r1.md",
                  "Project: garden\nChanges v1:\nnew-item title=\"Order seeds\" importance=1\n"
                  "new-item title=\"Plan beds\" importance=2\nEnd.\n")
        self.drop("_returns/t1.md", "Project: top\nChanges v1:\nnew-item title=\"Top thing\" importance=2\nEnd.\n")
        lease = "cat drive:Collab Kit/_backend/lease.json"
        p, rc, calls = self.run_pass()                               # the first pass: the cache is empty
        self.assertEqual(rc, 0, p.problems)
        pressing = self.s.read("agenda/00-PRESSING.md")
        for title in ("Order seeds", "Plan beds", "Top thing"):
            self.assertIn(title, pressing)
        self.assertEqual(self.s.read("projects/site/collab-kit/knowledge/README.md"), "# site knowledge\n", "mirrored")
        self.assertEqual([c for c in calls if c.startswith("lsjson")],
                         ["lsjson -R drive:Collab Kit", "lsjson -R drive:Collab Kit/projects/site/collab-kit"],
                         "the folder, and the site's copy again just before the first mirror writes to it")
        start = "cat drive:Collab Kit/00-START-HERE.md"                # read again just before its setup line is set
        self.assertEqual(calls.count(start), 2)
        reads = [c for c in calls if c.startswith("cat") and c not in (lease, start)]
        self.assertEqual(len(reads), len(set(reads)), f"a file is downloaded at most once a pass: {reads}")
        self.assertIn("cat drive:Collab Kit/_returns/t1.md", reads)

        p, rc, calls = self.run_pass()                               # steady state: nothing new anywhere
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual([c for c in calls if c.startswith("lsjson")], ["lsjson -R drive:Collab Kit"])
        self.assertEqual([c for c in calls if c.startswith("cat") and c != lease], [], "no file downloaded")
        self.assertEqual(sorted(c.split()[0] for c in calls),
                         ["cat"] * 4 + ["lsjson"] + ["rcat"] * 3, f"the lease (4 reads, 2 writes) and the heartbeat: {calls}")
        self.assertGreater(p.cloud.cache_hits, 3)
        self.assertIn("rclone calls: cat 4, lsjson 1, rcat 3", p.summary(1))

        agenda = os.listdir(self.root / "projects/garden/collab-kit/agenda")
        item = next(n for n in agenda if n.startswith("W-002"))
        settled = next(n for n in agenda if n.startswith("W-001"))
        path = self.root / "projects/garden/collab-kit/agenda" / item
        path.write_text(path.read_text().replace("importance = 2", "importance = 1"))   # changed elsewhere
        self.drop("projects/garden/collab-kit/_returns/r2.md",
                  "Project: garden\nChanges v1:\nsettle W-001 \"seeds\" outcome=\"ordered\"\nEnd.\n")
        p, rc, calls = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual([c for c in calls if c.startswith("lsjson")], ["lsjson -R drive:Collab Kit"])
        self.assertEqual(sorted(c for c in calls if c.startswith("cat") and c != lease),
                         ["cat drive:Collab Kit/projects/garden/collab-kit/_returns/r2.md",
                          f"cat drive:Collab Kit/projects/garden/collab-kit/agenda/{settled}",
                          f"cat drive:Collab Kit/projects/garden/collab-kit/agenda/{item}"],
                         "the new return, the item it changes (read as it is now before writing), the item "
                         "changed elsewhere: nothing else")
        pressing = self.s.read("agenda/00-PRESSING.md")
        self.assertNotIn("Order seeds", pressing)
        self.assertIn("Plan beds", pressing.split("## Critical")[1])

    def test_a_session_reads_one_listing(self):
        # a machine without a synced copy (the Studio) reaches the folder through rclone: a brief read
        # every agenda item with its own download, 156 seconds there, over the session hook's 30
        from collab_kit import config as C
        from collab_kit.session import backend_state, open_cloud
        from collab_kit.store import SubStore
        self.drop("projects/garden/collab-kit/_returns/r1.md",
                  "Project: garden\nChanges v1:\nnew-item title=\"Order seeds\"\nnew-item title=\"Plan beds\"\nEnd.\n")
        self.run_pass()
        machine = {"cloud": {"root": "rclone:drive:Collab Kit", "rclone": os.environ["COLLAB_KIT_RCLONE"]}}
        log = self.t / "calls.log"

        def brief():
            log.write_text("")
            store = open_cloud(machine)
            titles = [i.title for i in Unit(SubStore(store, "projects/garden/collab-kit"), "garden").items()]
            live = backend_state(store)["live"]
            store.end_snapshot()
            return titles, live, log.read_text().splitlines()
        titles, live, calls = brief()
        self.assertEqual((titles, live), (["Order seeds", "Plan beds"], True))
        self.assertEqual([c.split()[0] for c in calls].count("lsjson"), 1)
        self.assertEqual(len([c for c in calls if c.startswith("cat")]), 3, "two items and the heartbeat, once")
        self.assertTrue((C.state_dir() / "rclone-cache").is_dir())
        titles, live, calls = brief()                                # the next command: the listing only
        self.assertEqual((titles, live), (["Order seeds", "Plan beds"], True))
        self.assertEqual(calls, ["lsjson -R drive:Collab Kit"])

    def test_a_failed_listing_is_never_an_empty_folder(self):
        # found by the review of W-020: "not found" (exit 3) read as an empty folder emptied the front page
        self.drop("_returns/t1.md", "Project: top\nChanges v1:\nnew-item title=\"Top thing\" importance=2\nEnd.\n")
        self.run_pass()
        os.environ["FAKE_RCLONE_TREE_EXIT"] = "3"
        try:
            p, rc, calls = self.run_pass()
        finally:
            os.environ.pop("FAKE_RCLONE_TREE_EXIT")
        self.assertIn("could not be read in one listing", " ".join(p.problems))
        self.assertIn("Top thing", self.s.read("agenda/00-PRESSING.md"), "read file by file instead")

    def test_a_file_edited_after_the_listing_is_not_overwritten(self):
        # found by the review of W-020: a return applied from the listing's copy of an item would drop
        # an edit made after the listing (kept only in _versions/)
        from collab_kit import apply as A
        from collab_kit.store import RcloneStore
        self.drop("_returns/t1.md", "Project: top\nChanges v1:\nnew-item title=\"Top thing\"\nEnd.\n")
        self.run_pass()
        store = RcloneStore("drive:Collab Kit")
        store.snapshot(self.t / "work" / "rclone-cache")             # the item's copy is in the cache
        unit = Unit(store, "top", home="cloud", top=True)
        path = next((self.root / "agenda").glob("W-001-*.md"))
        path.write_text(path.read_text().replace("Top thing", "Top thing, edited after the listing"))
        self.drop("_returns/t2.md", "Project: top\nChanges v1:\nlog W-001 \"Top thing\" \"a log line\"\nEnd.\n")
        store.refresh("_returns")                                     # it arrived after the listing too
        out = A.apply_file(unit, store.entry("_returns/t2.md"), top=unit)
        self.assertEqual(out.status, "applied", out.message)
        text = path.read_text()
        self.assertIn("edited after the listing", text)
        self.assertIn("a log line", text)
        # a return that changed after the listing settles again rather than being applied
        self.drop("_returns/t3.md", "Project: top\nChanges v1:\nnew-item title=\"Third\"\nEnd.\n")
        store.refresh("_returns")
        self.drop("_returns/t3.md", "Project: top\nChanges v1:\nnew-item title=\"Third, rewritten\"\nEnd.\n")
        out = A.apply_file(unit, store.entry("_returns/t3.md"), top=unit)
        self.assertEqual(out.status, "waiting", out.message)

    def test_the_mirror_looks_again_before_it_writes(self):
        # a cloud edit to a repository-homed copy, made after the listing, is still saved before the
        # repository's version replaces it
        from collab_kit.backend import Pass
        from collab_kit.unit import Unit as U
        from collab_kit.store import SubStore
        self.run_pass()
        p = Pass(self.cfg)
        p.cloud.snapshot(None)
        self.s.write("projects/site/collab-kit/knowledge/README.md", "# site knowledge, edited in the folder\n")
        clone = self.t / "work" / "site" / "collab-kit"
        (clone / "knowledge" / "README.md").write_text("# site knowledge, changed in the repository\n")
        p.mirror("site", clone, U(SubStore(p.cloud, "projects/site/collab-kit"), "site", home="repo"))
        self.assertEqual(self.s.read("projects/site/collab-kit/knowledge/README.md"),
                         "# site knowledge, changed in the repository\n")
        saved = [e.name for e in self.s.files("projects/site/collab-kit/_returns") if "edited-in-the-folder" in e.name]
        self.assertEqual(len(saved), 1, "the folder's edit is kept as a return")

    def test_the_first_renewal_checks_the_lease(self):
        import json
        from collab_kit.backend import LeaseLost, Pass
        p = Pass(self.cfg)
        self.s.write("_backend/lease.json", json.dumps({"holder": "other:1", "expires": "2999-01-01T00:00:00+00:00"}))
        with self.assertRaises(LeaseLost):
            p.renew()                                                 # at once, not two minutes later

    def test_a_dry_run_writes_no_cache(self):
        from collab_kit.backend import Pass
        self.drop("_returns/t1.md", "Project: top\nChanges v1:\nnew-item title=\"Top thing\"\nEnd.\n")
        p = Pass(self.cfg, dry_run=True)
        self.assertEqual(p.run(), 0, p.problems)
        self.assertFalse((self.t / "work" / "rclone-cache").exists())
        self.assertTrue(self.s.exists("_returns/t1.md"))


if __name__ == "__main__":
    unittest.main()

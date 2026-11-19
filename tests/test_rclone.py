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
                  "COLLAB_KIT_RCLONE", "RCLONE_CONFIG_PASS"):
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


if __name__ == "__main__":
    unittest.main()

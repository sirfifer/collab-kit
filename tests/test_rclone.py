"""RcloneStore against a fake rclone (tests/fake_rclone.py): the intake conditions, and the engine's
apply path running over it unchanged."""
from __future__ import annotations

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
        for k in ("FAKE_RCLONE_ROOT", "FAKE_RCLONE_VERSION", "FAKE_RCLONE_DUP", "RCLONE_CONFIG_PASS"):
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

    def test_pinned_version_only(self):
        os.environ["FAKE_RCLONE_VERSION"] = "v1.70.0"
        with self.assertRaises(StoreError):
            RcloneStore("drive:Collab Kit", rclone=self.rclone).list("")

    def test_inherited_rclone_settings_are_stripped(self):
        os.environ["RCLONE_CONFIG_PASS"] = "secret"
        self.store.list("")                                        # the fake exits 9 if it sees it

    def test_duplicates_fail_closed(self):
        self.store.write("_returns/r.md", "x")
        os.environ["FAKE_RCLONE_DUP"] = "r.md"
        with self.assertRaises(StoreError):
            self.store.list("_returns")

    def test_native_files_are_never_read_and_are_set_aside(self):
        (self.t / "drive" / "Collab Kit" / "_returns" / "notes.gdoc-native").write_text("binary")
        unit = Unit(self.store, "top", home="cloud", top=True)
        e = [e for e in unit.pending_returns() if e.name.endswith("native")][0]
        self.assertTrue(e.native)
        with self.assertRaises(StoreError):
            self.store.read("_returns/notes.gdoc-native")
        out = A.apply_file(unit, e)
        self.assertEqual(out.status, "stray")

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

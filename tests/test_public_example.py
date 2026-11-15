"""The public example (examples/the-kit-itself) is current, readable by this kit, and clean.
See tests/public_example.py."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import public_example as PE                              # noqa: E402


class PublicExample(unittest.TestCase):
    def test_committed_example_is_current(self):
        self.assertEqual(PE.check(), [])

    def test_generic_rules(self):
        home = "/" + "Users/sam/"                       # spelled out, so the kit's own path guard stays quiet
        t = PE.clean(f'root = "{home}Library/CloudStorage/GoogleDrive-sam@garden.invalid/My Drive" (sam.lee@garden.invalid)', [])
        self.assertEqual(t, 'root = "~/Library/CloudStorage/GoogleDrive-owner@example.com/My Drive" (owner@example.com)')
        self.assertEqual(PE.leaks(t, []), [])
        self.assertTrue(PE.leaks("write to me at sam@garden.invalid", []))

    def test_ledger_shas_follow_the_cleaned_text(self):
        led = PE.clean_json({"effects": [{"after": "mail sam@garden.invalid", "after_sha": "x", "before": None,
                                          "before_sha": None}]}, [])
        e = led["effects"][0]
        self.assertEqual(e["after"], "mail owner@example.com")
        self.assertEqual(e["after_sha"], PE.sha(e["after"]))

    def test_refresh_refuses_private_words_and_leaves_out_excluded_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ex = tmp / "example"
            ex.mkdir()
            (ex / "snapshot.toml").write_text('name = "garden"\nhuman = "Sam"\nabout = "A garden"\nspoken = "the garden"\n'
                                              'exclude = ["knowledge/draft.md"]\n')
            src = tmp / "live"
            for d in ("agenda", "knowledge", "_returns/applied"):
                (src / d).mkdir(parents=True)
            (src / "agenda" / "W-001-beds (1).md").write_text(
                '+++\nid = "W-001"\ntitle = "Beds"\nkind = "task"\nimportance = 3\nstatus = "open"\ndue = ""\nproject = ""\n+++\n\n'
                "## What's needed\nAsk Bluebell Farms about soil.\n")
            (src / "knowledge" / "draft.md").write_text("unpublished\n")
            (src / "_returns" / "applied" / "r1.md").write_text("Project: garden\nChanges v1:\nknowledge draft.md\n```\nx\n```\nEnd.\n")
            (src / "_returns" / "applied" / "r1.ledger.json").write_text(json.dumps(
                {"id": "r1", "state": "done", "effects": [{"path": "knowledge/draft.md", "after": "x", "after_sha": PE.sha("x")}]}))
            rules = tmp / "rules.toml"
            rules.write_text('deny = ["bluebell"]\n')
            os.environ["COLLAB_KIT_EXAMPLE_RULES"] = str(rules)
            try:
                with self.assertRaises(SystemExit) as cm:
                    PE.refresh(src, example=ex)
                self.assertIn("Bluebell", str(cm.exception))
                self.assertFalse((ex / "collab-kit").exists())          # nothing written
                rules.write_text('deny = ["bluebell"]\n[[replace]]\npattern = "bluebell farms"\nwith = "a farm"\n')
                notes = PE.refresh(src, example=ex)
            finally:
                del os.environ["COLLAB_KIT_EXAMPLE_RULES"]
            self.assertIn("r1", " ".join(notes))
            item = ex / "collab-kit" / "agenda" / "W-001-beds.md"           # Drive's " (1)" dropped
            self.assertIn("Ask a farm about soil.", item.read_text())
            self.assertFalse((ex / "collab-kit" / "knowledge" / "draft.md").exists())
            self.assertFalse((ex / "collab-kit" / "_returns" / "applied" / "r1.md").exists())
            self.assertEqual(PE.check(ex), [])


if __name__ == "__main__":
    unittest.main()

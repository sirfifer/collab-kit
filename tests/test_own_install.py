"""The kit's own repository runs the kit's current install (dogfood): never behind its own engine.

Collab Kit is worked on in Collab Kit. Its install here (tools/collab-kit/, the hooks in
.claude/settings.json, the collab-kit skills, the Collab Kit section of CLAUDE.md and AGENTS.md) must
be exactly what install.py writes from this checkout, so the kit is always tried on itself first.
"""
import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import isolation  # noqa: E402,F401  (first: never the machine's real Collab Kit)
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFRESH = [sys.executable, "install.py", "project", ".", "--name", "collab-kit", "--human", "Richard"]


class OwnInstall(unittest.TestCase):
    def test_the_kits_own_install_is_current(self):
        if not (ROOT / "tools" / "collab-kit" / "project.toml").is_file():
            self.skipTest("this checkout has no install of the kit (a source export)")
        with tempfile.TemporaryDirectory() as home:      # no machine config: the same answer everywhere
            r = subprocess.run([*REFRESH, "--dry-run", "--check"], cwd=ROOT, capture_output=True,
                               text=True, env={**os.environ, "HOME": home}, timeout=120)
        self.assertEqual(
            r.returncode, 0,
            "The kit's own install is behind this checkout. Refresh it and commit the result with the "
            f"change that caused it:\n  python3 {' '.join(REFRESH[1:])}\n\n{r.stdout}{r.stderr}")

    def test_claude_md_and_agents_md_say_the_same(self):
        claude, agents = ROOT / "CLAUDE.md", ROOT / "AGENTS.md"
        if not claude.is_file():
            self.skipTest("this checkout has no CLAUDE.md")
        self.assertEqual(claude.read_text(), agents.read_text(),
                         "CLAUDE.md and AGENTS.md are the same guide for different agents: keep them identical")


if __name__ == "__main__":
    unittest.main()

"""install.py top writes to a path: an rclone remote is refused, never taken for a folder name."""
import isolation  # noqa: F401  (first: no test may reach this machine's real Collab Kit)

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


class Top(unittest.TestCase):
    def run_top(self, folder: str, cwd: Path):
        return subprocess.run([sys.executable, str(KIT / "install.py"), "top", folder, "--human", "Sam", "--dry-run"],
                              cwd=cwd, capture_output=True, text=True)

    def test_an_rclone_remote_is_refused_and_nothing_is_created(self):
        with tempfile.TemporaryDirectory() as t:
            res = self.run_top("rclone:gdrive:", Path(t))
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("not to an rclone remote", res.stderr)
            self.assertEqual(list(Path(t).iterdir()), [], "no folder named after the remote")

    def test_a_path_is_planned_as_before(self):
        with tempfile.TemporaryDirectory() as t:
            res = self.run_top(str(Path(t) / "Collab Kit"), Path(t))
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("00-START-HERE.md", res.stdout)


if __name__ == "__main__":
    unittest.main()

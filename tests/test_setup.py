"""The newcomer's install: `install.py setup`, and the traps a first install used to fall into
(found by the install walk-through of 2026-11-22: knowledge/install-experience-2026-11-22.md)."""
import isolation  # noqa: F401  (first: no test may reach this machine's real Collab Kit)

import builtins
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "engine"))

from collab_kit import guided, installer  # noqa: E402
from collab_kit.store import FolderStore  # noqa: E402
from collab_kit.unit import Unit  # noqa: E402


def git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                    "--allow-empty", "-m", "init"], check=True)
    return path


class Setup(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix="ck-setup-"))
        self.addCleanup(shutil.rmtree, self.t, True)
        self.addCleanup(isolation.restore)
        self.cfg = self.t / "config.toml"
        os.environ["COLLAB_KIT_CONFIG"] = str(self.cfg)
        self.drive = self.t / "My Drive"
        self.drive.mkdir()

    def setup_cli(self, *args: str):
        env = dict(os.environ, COLLAB_KIT_CONFIG=str(self.cfg))
        return subprocess.run([sys.executable, str(KIT / "install.py"), "setup", "--yes", *args],
                              capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)

    def test_one_command_makes_the_folder_this_computer_and_a_repository(self):
        repo = git_repo(self.t / "garden-planner")
        res = self.setup_cli("--folder", str(self.drive / "Collab Kit"), "--human", "Priya", "--repo", str(repo),
                             "--about", "Plans the garden", "--spoken", "the garden")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        folder = self.drive / "Collab Kit"
        self.assertTrue((folder / "00-START-HERE.md").is_file())
        self.assertIn("Priya", (folder / "00-START-HERE.md").read_text())
        self.assertTrue(self.cfg.is_file())
        self.assertTrue((repo / "tools" / "collab-kit" / "ck").is_file())
        self.assertTrue((folder / "projects" / "garden-planner" / "collab-kit" / "00-START-HERE.md").is_file())
        self.assertIn("garden-planner", (folder / "knowledge" / "projects.md").read_text())
        self.assertIn(guided.preference_line("Collab Kit"), res.stdout, "it ends with the line to paste")

    def test_a_missing_answer_with_nobody_to_ask_names_its_flag_and_writes_nothing(self):
        res = self.setup_cli("--folder", str(self.drive / "Collab Kit"))
        self.assertEqual(res.returncode, 2)
        self.assertIn("--human", res.stdout)
        self.assertFalse((self.drive / "Collab Kit").exists())
        self.assertFalse(self.cfg.exists())

    def test_an_existing_folder_is_kept(self):
        folder = self.drive / "Collab Kit"
        self.assertEqual(self.setup_cli("--folder", str(folder), "--human", "Priya").returncode, 0)
        start = (folder / "00-START-HERE.md").read_text()
        res = self.setup_cli("--folder", str(folder), "--human", "Priya")
        self.assertEqual(res.returncode, 0, res.stdout)
        self.assertIn("already a Collab Kit folder", res.stdout)
        self.assertEqual((folder / "00-START-HERE.md").read_text(), start)

    def test_a_dry_run_writes_nothing(self):
        repo = git_repo(self.t / "orchard")
        res = self.setup_cli("--folder", str(self.drive / "Collab Kit"), "--human", "Priya", "--repo", str(repo),
                             "--dry-run")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertFalse((self.drive / "Collab Kit").exists())
        self.assertFalse(self.cfg.exists())
        self.assertFalse((repo / "tools").exists())

    def test_drive_for_desktop_folders_are_found_with_their_accounts(self):
        home = self.t / "home"
        for acct in ("a@example.com", "b@example.com"):
            (home / "Library" / "CloudStorage" / f"GoogleDrive-{acct}" / "My Drive").mkdir(parents=True)
        (home / "Library" / "CloudStorage" / "Dropbox").mkdir()
        found = guided.drive_roots(home)
        self.assertEqual([a for _, a in found], ["a@example.com", "b@example.com"])

    def test_asked_on_a_terminal_the_person_chooses_the_account_and_gives_a_name(self):
        home = self.t / "home"
        for acct in ("a@example.com", "b@example.com"):
            (home / "Library" / "CloudStorage" / f"GoogleDrive-{acct}" / "My Drive").mkdir(parents=True)
        answers = iter(["2", "y", "Maya"])
        out = io.StringIO()
        with mock.patch.object(Path, "home", return_value=home), \
                mock.patch.object(builtins, "input", lambda *_: next(answers)), mock.patch("sys.stdout", io.StringIO()):
            code = guided.run(folder=None, human=None, repos=[], about=[], spoken=[], user_hooks=False,
                              dry=False, interactive=True, out=out)
        self.assertEqual(code, 0, out.getvalue())
        folder = home / "Library" / "CloudStorage" / "GoogleDrive-b@example.com" / "My Drive" / "Collab Kit"
        self.assertIn("Maya", (folder / "00-START-HERE.md").read_text())
        self.assertIn("signed in as b@example.com", out.getvalue())


class FirstInstallTraps(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix="ck-traps-"))
        self.addCleanup(shutil.rmtree, self.t, True)
        self.addCleanup(isolation.restore)

    def test_a_project_is_refused_before_anything_is_written_when_the_machine_has_no_folder(self):
        repo = git_repo(self.t / "orchard")
        plan = installer.install_project(repo, about="Apples")
        self.assertTrue(plan.refused)
        self.assertIn("install.py setup", plan.refused)
        self.assertFalse((repo / "tools").exists(), "no half-install")

    def test_the_wip_folders_own_readme_is_not_an_unfinished_thread(self):
        unit_dir = self.t / "unit"
        (unit_dir / "WIP").mkdir(parents=True)
        (unit_dir / "WIP" / "README.md").write_text("# WIP\n")
        unit = Unit(FolderStore(unit_dir), "orchard", home="cloud")
        self.assertEqual(unit.wip_notes(), [])
        (unit_dir / "WIP" / "2026-11-22-1000-pruning-01.md").write_text("note\n")
        self.assertEqual([e.name for e in unit.wip_notes()], ["2026-11-22-1000-pruning-01.md"])

    def test_ck_by_full_path_answers_for_its_own_project_from_inside_another(self):
        a = git_repo(self.t / "apples")
        b = git_repo(self.t / "berries")
        for r in (a, b):
            self.assertFalse(installer.install_project(r, home="repo").refused)
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        res = subprocess.run([sys.executable, str(b / "tools" / "collab-kit" / "ck.py"), "doctor"], cwd=a,
                             capture_output=True, text=True, env=env)
        self.assertIn("Project berries", res.stdout, res.stdout + res.stderr)


@unittest.skipUnless(shutil.which("python3.9") or Path("/usr/bin/python3").exists(), "no Python older than 3.11 here")
class OldPython(unittest.TestCase):
    def test_an_old_python_gets_a_plain_message_not_a_traceback(self):
        old = shutil.which("python3.9") or "/usr/bin/python3"
        ver = subprocess.run([old, "-c", "import sys; print(sys.version_info >= (3, 11))"],
                             capture_output=True, text=True)
        if ver.stdout.strip() != "False":
            self.skipTest("that Python is 3.11 or newer")
        res = subprocess.run([old, str(KIT / "install.py"), "--help"], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("needs Python 3.11 or newer", res.stderr)
        self.assertNotIn("Traceback", res.stderr)


if __name__ == "__main__":
    unittest.main()

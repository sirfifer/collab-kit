"""Starting a project from a brainstorm in one step, and a new project's repository (DESIGN-0.5.md
section 25; agenda W-037 and W-035). No test reaches GitHub or creates a repository anywhere but in
a temporary folder: `gh` is tests/fake_gh.py, and git's addresses for github.com are rewritten to
folders there. Standard library and git only:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import isolation  # noqa: E402,F401  (first: never the machine's real Collab Kit)

import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
sys.path.insert(0, str(KIT / "engine"))

from collab_kit import apply as A                       # noqa: E402
from collab_kit import backend as BE                    # noqa: E402
from collab_kit import config as C                      # noqa: E402
from collab_kit import repos as RP                      # noqa: E402
from collab_kit import returns as R                     # noqa: E402
from collab_kit.store import FolderStore, SubStore      # noqa: E402
from collab_kit.templates import set_human, top_start_file  # noqa: E402
from collab_kit.unit import Unit                        # noqa: E402

CATALOG = ("# Projects\n\n| Folder | Say | What it is | Where | Status | Collab Kit |\n|---|---|---|---|---|---|\n"
           "| `garden` | \"the garden\" | a garden plan | its Collab Kit folder (no repository) | active | live |\n")
IDEA = ("Project: top\nFrom: Sam\nType: new-project\nTopic: the orchard becomes a project\n\nChanges v1:\n"
        "new-project name=orchard \"Plan the orchard\" about=\"A small orchard behind the house\" "
        "spoken=\"the orchard\"\n```\nTwelve trees fit. Apples and pears first.\nThe slope drains to the east.\n```\nEnd.\n")


def git(*args, cwd=None) -> str:
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise AssertionError(f"git {args}: {res.stderr}")
    return res.stdout


class Folder(unittest.TestCase):
    """A throwaway Collab Kit folder, with returns dropped an hour old (already settled)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name).resolve()
        self.cloud = self.t / "Collab Kit"
        set_human("Sam")
        self.s = FolderStore(self.cloud)
        self.s.write("00-START-HERE.md", top_start_file())
        self.s.write("knowledge/projects.md", CATALOG)
        for d in ("_returns", "agenda", "WIP", "projects/garden/collab-kit/agenda"):
            self.s.mkdir(d)
        self.top = Unit(self.s, "top", home="cloud", top=True)

    def tearDown(self):
        self.tmp.cleanup()

    def drop(self, name: str, text: str):
        self.s.write(f"_returns/{name}", text)
        t = time.time() - 3600
        os.utime(self.cloud / "_returns" / name, (t, t))

    def apply_all(self):
        return [A.apply_file(self.top, e) for e in self.top.pending_returns()]

    def project(self, name: str) -> Unit:
        return Unit(SubStore(self.s, f"projects/{name}/collab-kit"), name, home="cloud")


class OneStep(Folder):
    """W-037: `new-project` may carry the idea itself, so no agenda item has to exist first."""

    def test_a_brainstorm_becomes_a_project_in_one_return(self):
        self.drop("r1.md", IDEA)
        out = self.apply_all()
        self.assertEqual(out[0].status, "applied", out[0].message)
        self.assertEqual(self.top.items(), [], "no top-level item was needed, and none was made")
        first = self.project("orchard").item("W-001")
        self.assertEqual((first.title, first.kind, first.status), ("Plan the orchard", "work-out", "open"))
        self.assertIn("## What's needed\nA small orchard behind the house", first.body)
        self.assertIn("## What we know so far\nTwelve trees fit. Apples and pears first.\nThe slope drains to the east.",
                      first.body)
        self.assertIn("started from a conversation (return r1, from Sam)", first.body)
        row = next(ln for ln in self.s.read("knowledge/projects.md").splitlines() if "`orchard`" in ln)
        self.assertIn("A small orchard behind the house", row)
        self.assertIn("\"the orchard\"", row)
        self.assertIn(A.NO_REPOSITORY, row)
        self.assertIn("Sam calls it \"the orchard\"", self.s.read("projects/orchard/collab-kit/00-START-HERE.md"))
        status = self.s.read("knowledge/status.md")                  # no item to settle: the status says it started
        self.assertRegex(status, r"## \d{4}-\d\d-\d\d \d\d:\d\d UTC, Sam: project orchard started")
        self.assertEqual(self.s.read("00-START-HERE.md"), top_start_file(), "start files stay put")

    def test_text_with_its_own_headings_is_kept_as_written(self):
        self.drop("r1.md", "Project: top\nChanges v1:\nnew-project name=orchard \"Plan the orchard\"\n```\n"
                           "## What's needed\nA plan.\n\n## Open questions\nWhich trees?\n```\nEnd.\n")
        self.assertEqual(self.apply_all()[0].status, "applied")
        body = self.project("orchard").item("W-001").body
        self.assertIn("## Open questions\nWhich trees?", body)
        self.assertEqual(body.count("## What's needed"), 1)
        self.assertIn("## Log", body)

    def test_with_no_body_the_item_says_what_the_project_is(self):
        self.drop("r1.md", "Project: top\nChanges v1:\nnew-project name=orchard \"Plan the orchard\" about=\"An orchard\"\nEnd.\n")
        self.assertEqual(self.apply_all()[0].status, "applied")
        self.assertIn("## What's needed\nAn orchard", self.project("orchard").item("W-001").body)

    def test_from_an_item_works_as_before(self):
        self.drop("r1.md", "Project: top\nChanges v1:\nnew-item kind=project importance=2 title=\"A plan for the orchard\"\nEnd.\n")
        self.apply_all()
        self.drop("r2.md", "Project: top\nChanges v1:\nnew-project name=orchard from=W-001 \"orchard\" "
                           "about=\"Planting the orchard\"\nEnd.\n")
        self.assertEqual(self.apply_all()[0].status, "applied")
        first = self.project("orchard").item("W-001")
        self.assertEqual((first.title, first.importance), ("A plan for the orchard", 2))
        self.assertIn("carried over from the top level's W-001", first.body)
        self.assertEqual(self.top.item("W-001").status, "settled")
        self.assertIsNone(self.s.read("knowledge/status.md"), "with an item to settle, no status line is added")

    def test_what_is_refused(self):
        for line, why in (
                ("new-project name=orchard", "needs the idea"),                      # neither an item nor a title
                ("new-project name=orchard \"   \"", "needs the idea"),
                ("new-project name=orchard about=\"An orchard\"", "needs the idea"),
                ("new-project name=orchard from=W-001", "must repeat part of the idea's title"),
                ("new-project name=orchard \"" + "x" * 201 + "\"", "at most 200 characters"),
                ("new-project name=garden \"Another garden\"", "already taken"),
                ("new-project name=Orchard \"Plan the orchard\"", "lowercase"),
                ("new-project name=test \"Plan the orchard\"", "reserved"),
                ("new-project \"Plan the orchard\"", "needs name="),
                ("new-project name=orchard \"Plan the orchard\" visibility=public", "does not take visibility="),
                ("new-project name=orchard \"Plan the orchard\" public=yes", "does not take public=")):
            with self.subTest(line=line):
                self.drop("r.md", f"Project: top\nChanges v1:\nnew-item kind=project title=\"An idea\"\n{line}\nEnd.\n")
                out = self.apply_all()
                self.assertEqual(out[0].status, "failed", line)
                self.assertIn(why, out[0].message)
                self.assertFalse(self.s.exists("projects/orchard"), "refused whole: nothing was made")

    def test_a_project_inbox_cannot_start_one(self):
        garden = self.project("garden")
        garden.store.write("_returns/r.md", "Project: garden\nChanges v1:\nnew-project name=orchard \"Plan the orchard\"\nEnd.\n")
        out = A.apply_file(garden, garden.pending_returns()[0], top=self.top, force_settled=True)
        self.assertEqual(out.status, "failed")
        self.assertIn("only from the top-level inbox", out.message)

    def test_undo_takes_it_all_back(self):
        self.drop("r1.md", IDEA)
        self.apply_all()
        self.drop("r2.md", "Project: top\nChanges v1:\nundo r1\nEnd.\n")
        out = self.apply_all()
        self.assertEqual(out[0].status, "undone", out[0].message)
        self.assertFalse(self.s.exists("projects/orchard/collab-kit/00-START-HERE.md"))
        self.assertNotIn("`orchard`", self.s.read("knowledge/projects.md"))

    def test_the_daily_limit_covers_both_forms(self):
        for n in range(A.NEW_PROJECTS_PER_DAY):
            self.drop(f"r{n}.md", f"Project: top\nChanges v1:\nnew-project name=plot-{n} \"Plot {n}\"\nEnd.\n")
            self.assertEqual(self.apply_all()[0].status, "applied")
        self.drop("r9.md", "Project: top\nChanges v1:\nnew-project name=plot-9 \"Plot 9\"\nEnd.\n")
        self.assertIn("projects start in one day", self.apply_all()[0].message)

    def test_what_the_start_file_tells_a_conversation_applies(self):
        """The example in the top-level start file, written out as a conversation would, is a return
        this engine applies; and the start file names the phrases that engage the kit."""
        import re
        import textwrap
        section = top_start_file().split("## Starting a project")[1].split("\n## ")[0]
        said = " ".join(section.split())
        for phrase in ("\"make this a project\"", "\"save this to Collab Kit\"", "`new-project name=<name>`",
                       "file one return", "nothing has to be said twice", "always a private one",
                       "every line starting at the left edge", "ask again in a few minutes"):
            self.assertIn(phrase, said)
        self.assertIn(A.NO_REPOSITORY, said, "the words the catalog uses, so a conversation can say which it is")
        self.assertLess(said.index("\"Plan the orchard\""), said.index("from=W-NNN"), "one step comes first")
        example = re.search(r"(?ms)^````\n(.*?)^````$", section).group(1)      # as written: at the left edge
        self.assertIn("\n```\nTwelve trees fit", example)
        self.assertEqual(example, textwrap.dedent(example))
        self.drop("r1.md", example)
        out = self.apply_all()
        self.assertEqual(out[0].status, "applied", out[0].message)
        first = self.project("orchard").item("W-001")
        self.assertEqual(first.title, "Plan the orchard")
        self.assertIn("Open: who prunes, and whether to fence against deer.", first.body)

    def test_a_return_written_indented_is_the_same_return(self):
        """Copied out of a list, every line of a return is indented. It was read as a return with no
        changes and filed away as done (found by the capability walk-through, 2026-11-22)."""
        indented = "\n".join(("   " + ln if ln else ln) for ln in IDEA.split("\n"))
        self.assertEqual(len(R.parse(indented, "r1.md").changes), 1)
        self.drop("r1.md", indented)
        out = self.apply_all()
        self.assertEqual(out[0].status, "applied", out[0].message)
        self.assertIn("The slope drains to the east.", self.project("orchard").item("W-001").body)
        # one indented line among flush ones is still what it was: a continuation, never a change
        quoted = R.parse("Project: top\nVerbatim: he said\n  Changes v1:\n  new-item title=\"x\"\nEnd.\n", "r2.md")
        self.assertEqual((quoted.has_block, quoted.changes), (False, []))

    def test_the_back_end_says_it_takes_the_one_step_form(self):
        self.assertIn("new-project-idea", BE.ACCEPTS)
        self.assertIn("blocks", BE.ACCEPTS)


class Settings(unittest.TestCase):
    """`[new_projects]` in backend.toml: off unless set, and no way to ask for a public repository."""

    def test_off_unless_set(self):
        for cfg in ({}, {"new_projects": {}}, {"new_projects": {"repositories": ""}}, {"new_projects": {"per_day": 2}}):
            self.assertEqual(C.new_projects(cfg), (None, None), cfg)

    def test_set(self):
        s, why = C.new_projects({"new_projects": {"repositories": "~/dev", "github_owner": "sam-example"}})
        self.assertIsNone(why)
        self.assertEqual(s, {"repositories": Path.home() / "dev", "github_owner": "sam-example", "per_day": 3})

    def test_what_is_refused(self):
        for table, why in (({"repositories": "~/dev", "visibility": "public"}, "always private"),
                           ({"repositories": "~/dev", "public": True}, "always private"),
                           ({"github_owner": "sam"}, "needs repositories"),
                           ({"repositories": "dev"}, "full path"),
                           ({"repositories": "~/dev", "github_owner": "sam/../x"}, "GitHub account's name"),
                           ({"repositories": "~/dev", "github_owner": "--public"}, "GitHub account's name"),
                           ({"repositories": "~/dev", "per_day": 500}, "per_day"),
                           ({"repositories": "~/dev", "per_day": 0}, "per_day"),
                           ({"repositories": "~/dev", "per_day": True}, "per_day"),
                           ({"repositories": ["~/dev"]}, "are text")):
            with self.subTest(table=table):
                s, said = C.new_projects({"new_projects": table})
                self.assertIsNone(s)
                self.assertIn(why, said)

    def test_the_config_template_is_valid_and_off(self):
        from collab_kit.installer import BACKEND_TEMPLATE
        import tomllib
        text = BACKEND_TEMPLATE.format(cloud='"x"', work='"y"', human='"Sam"')
        self.assertEqual(C.new_projects(tomllib.loads(text)), (None, None), "off as written")
        lines = text.split("# [new_projects]")[1].split("\n\n")[0].splitlines()[1:]
        on = "[new_projects]\n" + "\n".join(ln[2:] for ln in lines if ln.startswith("# ") and "=" in ln)
        s, why = C.new_projects(tomllib.loads(on))                   # the example, uncommented
        self.assertIsNone(why)
        self.assertEqual((s["github_owner"], s["per_day"]), ("you", 3))


class Repositories(Folder):
    """W-035: with `[new_projects]` set, the back end also makes the project's repository."""

    OWNER = "example-owner"

    def setUp(self):
        super().setUp()
        self.dev = self.t / "dev"
        self.dev.mkdir()
        self.gh = self.t / "github"
        self.bin = self.t / "bin"
        self.bin.mkdir()
        launcher = self.bin / ("gh.cmd" if os.name == "nt" else "gh")
        if os.name == "nt":
            launcher.write_text(f'@"{sys.executable}" "{HERE / "fake_gh.py"}" %*\n')
        else:
            launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{HERE / "fake_gh.py"}" "$@"\n')
            launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
        self.env = dict(os.environ)
        repos = (self.gh / "repos").as_posix() + "/"
        os.environ.update({"FAKE_GH_ROOT": str(self.gh), "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                           "GIT_CONFIG_COUNT": "2",          # github.com is a folder here: nothing leaves the machine
                           "GIT_CONFIG_KEY_0": f"url.{repos}.insteadOf", "GIT_CONFIG_VALUE_0": "https://github.com/",
                           "GIT_CONFIG_KEY_1": f"url.{repos}.insteadOf", "GIT_CONFIG_VALUE_1": "git@github.com:"})
        self.cfg = {"backend": {"cloud": str(self.cloud), "work": str(self.t / "work"), "human": "Sam",
                                "local_roots": [], "deny": ["codename-x"], "lease_settle_seconds": 0},
                    "new_projects": {"repositories": str(self.dev), "github_owner": self.OWNER}}

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        super().tearDown()

    def run_pass(self, **kw):
        p = BE.Pass(self.cfg, **kw)
        return p, p.run()

    def calls(self) -> list[list[str]]:
        f = self.gh / "calls.jsonl"
        return [json.loads(ln) for ln in f.read_text().splitlines()] if f.exists() else []

    def creates(self) -> list[list[str]]:
        return [c for c in self.calls() if c[:2] == ["repo", "create"]]

    def journal(self, name="orchard") -> dict:
        return json.loads((self.t / "work" / "new-projects" / f"{name}.json").read_text())

    def row(self, name="orchard") -> str:
        return next(ln for ln in self.s.read("knowledge/projects.md").splitlines() if f"`{name}`" in ln)

    def bare(self, name="orchard") -> Path:
        return self.gh / "repos" / self.OWNER / f"{name}.git"

    def critical(self) -> list:
        return [i for i in self.top.items() if i.is_open and i.importance == 1]

    # ------------------------------------------------------------------------- off, and on
    def test_with_nothing_set_a_project_is_a_folder_as_before(self):
        del self.cfg["new_projects"]
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue(self.s.exists("projects/orchard/collab-kit/00-START-HERE.md"))
        self.assertIn(A.NO_REPOSITORY, self.row())
        self.assertEqual(list(self.dev.iterdir()), [])
        self.assertEqual(self.creates(), [])
        self.assertFalse((self.t / "work" / "new-projects").exists(), "no journal, no trace of the feature")

    def test_a_local_repository_with_the_kit_and_a_first_commit(self):
        del self.cfg["new_projects"]["github_owner"]
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        repo = self.dev / "orchard"
        self.assertEqual(git("log", "--format=%an: %s", cwd=repo).strip(),
                         f"Collab Kit back end: Start orchard: a README and Collab Kit {(KIT / 'VERSION').read_text().strip()}")
        self.assertEqual(git("status", "--porcelain", cwd=repo), "")
        self.assertEqual(git("branch", "--show-current", cwd=repo).strip(), "main")
        self.assertEqual(git("remote", cwd=repo), "", "not on GitHub: no remote")
        readme = (repo / "README.md").read_text()
        self.assertTrue(readme.startswith("# orchard\n\nA small orchard behind the house.\n"))
        self.assertIn("Sam calls it \"the orchard\"", readme)
        self.assertIn("projects/orchard/collab-kit", readme)
        project = C.project(repo)["project"]
        self.assertEqual((project["name"], project["home"], project["unit"]), ("orchard", "cloud", "projects/orchard/collab-kit"))
        for rel in ("tools/collab-kit/ck", "CLAUDE.md", "AGENTS.md", ".claude/settings.json",
                    ".claude/skills/collab-kit/SKILL.md", ".gitignore"):
            self.assertTrue((repo / rel).is_file(), rel)
        self.assertEqual(self.creates(), [], "no github_owner: gh is never asked to create anything")
        # the report: the catalog says where it lives, the top level and the project say it happened
        self.assertIn(f"repository {RP.shown(repo)} on ", self.row())
        self.assertIn("(not on GitHub)", self.row())
        self.assertNotIn(A.NO_REPOSITORY, self.row())
        status = self.s.read("knowledge/status.md")                  # the heading, which the front page shows, names the place
        self.assertIn(f"the back end: project orchard has a repository: {RP.shown(repo)[:20]}", status)
        self.assertEqual(RP.place_text({"local": str(Path.home() / "dev" / "orchard")}, "studio"), "~/dev/orchard on studio")
        self.assertIn("What happened in the last two days", self.s.read("agenda/00-PRESSING.md"))
        self.assertIn("project orchard has a repository:", self.s.read("agenda/00-PRESSING.md"))
        self.assertEqual(status.count("\n## "), 2, "two lines for a new project: it started, and where it lives")
        self.assertIsNone(self.s.read("projects/orchard/collab-kit/knowledge/status.md"))
        self.assertEqual(self.critical(), [])
        self.assertEqual(self.journal()["state"], "done")
        self.assertFalse((self.t / "work" / "new-projects" / "staging" / "orchard").exists(), "the staging folder moved")
        # the folder where repositories are made counts as taken names, and a second pass changes nothing
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertIn("`orchard`", self.s.read("knowledge/repositories.md"))
        self.assertEqual(len(git("log", "--format=%h", cwd=repo).split()), 1)

    def test_a_private_remote_and_the_first_push(self):
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        repo = self.dev / "orchard"
        self.assertEqual(self.creates(), [["repo", "create", f"{self.OWNER}/orchard", "--private"]])
        self.assertEqual(git("rev-parse", "main", cwd=self.bare()), git("rev-parse", "HEAD", cwd=repo), "the first commit is there")
        self.assertEqual(git("config", "--get", "remote.origin.url", cwd=repo).strip(), f"https://github.com/{self.OWNER}/orchard.git")
        self.assertNotIn("credential", git("config", "--local", "--list", cwd=repo),
                         "the credential setting was for one push, never written to the repository")
        self.assertEqual(json.loads((self.bare().with_suffix(".json")).read_text())["visibility"], "PRIVATE")
        self.assertIn(f"github.com/{self.OWNER}/orchard (private at creation)", self.row())
        heading = next(ln for ln in self.s.read("knowledge/status.md").split("\n") if ln.startswith("## "))
        self.assertIn(f"the back end: project orchard has a repository: github.com/{self.OWNER}/orchard (private), ", heading)
        self.assertEqual(self.critical(), [])
        j = self.journal()
        self.assertEqual((j["state"], j["remote"], j["pushed"]), ("done", f"{self.OWNER}/orchard", True))

    def test_a_project_started_from_an_agenda_item_gets_one_too(self):
        self.drop("r0.md", "Project: top\nChanges v1:\nnew-item kind=project title=\"A plan for the orchard\"\nEnd.\n")
        self.run_pass()
        self.drop("r1.md", "Project: top\nChanges v1:\nnew-project name=orchard from=W-001 \"orchard\" "
                           "about=\"Planting the orchard\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue((self.dev / "orchard" / "README.md").read_text().startswith("# orchard\n\nPlanting the orchard.\n"))
        self.assertEqual(len(self.creates()), 1)

    def test_gh_set_to_ssh_gives_the_ssh_address(self):
        self.gh.mkdir(exist_ok=True)
        (self.gh / "protocol").write_text("ssh\n")
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(git("config", "--get", "remote.origin.url", cwd=self.dev / "orchard").strip(),
                         f"git@github.com:{self.OWNER}/orchard.git")
        self.assertEqual(git("rev-parse", "main", cwd=self.bare()), git("rev-parse", "HEAD", cwd=self.dev / "orchard"))

    def test_only_the_name_and_the_owner_ever_reach_a_command_line(self):
        nasty = "$(touch pwned) `touch pwned` ; touch pwned & --public -- 'x' \\\"y"
        self.drop("r1.md", "Project: top\nFrom: Sam; touch pwned\nTopic: $(touch pwned)\nChanges v1:\n"
                           f"new-project name=orchard \"$(touch pwned) --public\" about=\"{nasty.replace(chr(34), '')}\" "
                           "spoken=\"`touch pwned`, --public\"\n```\n$(touch pwned)\n--public\n```\nEnd.\n")
        ran, real = [], RP._run
        RP._run = lambda args, **kw: (ran.append(list(args)), real(args, **kw))[1]
        try:
            p, rc = self.run_pass()
        finally:
            RP._run = real
        self.assertEqual(rc, 0, p.problems)
        allowed = {"repo", "list", "view", "create", "config", "get", "git_protocol", "auth", "git-credential", "get",
                   "--limit", "500", "--json", "name,visibility", "visibility,isEmpty", "--private", "--host", "github.com",
                   f"{self.OWNER}/orchard"}
        for call in self.calls():
            self.assertLessEqual(set(call), allowed, call)
        self.assertGreater(len([a for a in ran if a[0] == "git"]), 8, "every git command of the step was seen")
        for argv in ran:                                             # git and gh alike: no word of the return
            for word in argv:
                for bit in ("pwned", "touch", "--public", "$(", "`", "Sam;"):
                    self.assertNotIn(bit, word, argv)
        self.assertEqual(self.creates(), [["repo", "create", f"{self.OWNER}/orchard", "--private"]])
        self.assertEqual([str(x) for x in self.t.rglob("pwned")], [], "nothing from the return was ever run")
        self.assertEqual([x.name for x in Path.cwd().glob("pwned")], [])
        self.assertIn("touch pwned", (self.dev / "orchard" / "README.md").read_text(), "it is text in a file, and only that")
        self.assertEqual(json.loads(self.bare().with_suffix(".json").read_text())["visibility"], "PRIVATE")

    def test_no_code_path_asks_for_anything_but_private(self):
        src = (KIT / "engine" / "collab_kit" / "repos.py").read_text() + (KIT / "engine" / "collab_kit" / "backend.py").read_text()
        for word in ("--public", "--internal", "--visibility", "repo\", \"edit", "repo edit"):
            self.assertNotIn(word, src)
        self.assertEqual(src.count("\"--private\""), 1, "one place creates a repository, and it says private")

    # ------------------------------------------------------------------- failures, and retries
    def test_a_folder_of_that_name_makes_the_name_taken(self):
        (self.dev / "orchard").mkdir()                               # where repositories are made, names are taken
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertTrue(any("'orchard' is already taken" in x for x in p.problems), p.problems)
        self.assertFalse(self.s.exists("projects/orchard"), "refused before anything was made")
        self.assertEqual(list((self.dev / "orchard").iterdir()), [])

    def test_a_path_that_exists_is_never_touched_and_the_next_pass_finishes(self):
        (self.dev / "orchard").write_text("keep me")                 # not a folder, so not in the list of taken names
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("already exists" in x for x in p.problems), p.problems)
        self.assertEqual((self.dev / "orchard").read_text(), "keep me")
        self.assertEqual(self.creates(), [])
        self.assertTrue(self.s.exists("projects/orchard/collab-kit/00-START-HERE.md"), "the folder project is ready")
        self.assertIn(A.NO_REPOSITORY, self.row(), "the catalog still says the truth")
        crit = self.critical()
        self.assertEqual([i.title for i in crit], ["Project orchard: its repository could not be made"])
        self.assertIn("tried again on every full pass", crit[0].body)
        self.assertEqual(self.journal()["state"], "pending")
        p, rc = self.run_pass()                                      # still there: said again, no second item
        self.assertEqual(rc, 1)
        self.assertEqual(len(self.critical()), 1)
        (self.dev / "orchard").rename(self.t / "moved-away")
        p, rc = self.run_pass()                                      # the cause is gone: the next pass finishes it
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue((self.dev / "orchard" / ".git").is_dir())
        self.assertEqual(len(self.creates()), 1)
        self.assertEqual(self.critical(), [], "the back end settled its own item")
        self.assertIn("made on a later pass", self.top.item(crit[0].id).fields["outcome"])
        self.assertEqual(self.journal()["state"], "done")

    def test_gh_signed_out_leaves_a_local_repository_the_next_pass_pushes(self):
        self.gh.mkdir(exist_ok=True)
        (self.gh / "signed-out").write_text("")
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        repo = self.dev / "orchard"
        head = git("rev-parse", "HEAD", cwd=repo)
        self.assertEqual(self.journal()["state"], "local")
        self.assertTrue(any("gh auth login" in x for x in p.problems), p.problems)       # said by the pass itself
        self.assertEqual([i.title for i in self.critical()], ["Project orchard: its repository could not be put on GitHub"])
        self.assertIn("gh auth login", self.critical()[0].body)
        self.assertFalse(self.bare().exists())
        (self.gh / "signed-out").unlink()
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(git("rev-parse", "HEAD", cwd=repo), head, "the same repository: not made again")
        self.assertEqual(git("rev-parse", "main", cwd=self.bare()), head)
        self.assertEqual(self.critical(), [])
        self.assertIn("(private at creation)", self.row())

    def test_a_push_that_failed_is_retried_without_creating_again(self):
        self.drop("r1.md", IDEA)
        os.environ["GIT_CONFIG_VALUE_0"] = "https://elsewhere.invalid/"      # the push finds no repository this time
        os.environ["GIT_CONFIG_KEY_1"] = "url.file:///nowhere/.insteadOf"
        os.environ["GIT_CONFIG_VALUE_1"] = "https://github.com/"
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        j = self.journal()
        self.assertEqual((j["state"], j["remote_made"], j.get("pushed")), ("local", True, None))
        self.assertTrue(any("the first push" in x for x in p.problems), p.problems)
        repos = (self.gh / "repos").as_posix() + "/"
        os.environ.update({"GIT_CONFIG_KEY_1": f"url.{repos}.insteadOf", "GIT_CONFIG_VALUE_0": "https://github.com/",
                           "GIT_CONFIG_VALUE_1": "git@github.com:"})
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(len(self.creates()), 1, "created once; the second pass only pushed")
        self.assertEqual(git("rev-parse", "main", cwd=self.bare()), git("rev-parse", "HEAD", cwd=self.dev / "orchard"))

    def test_github_cannot_be_reached_then_can(self):
        self.gh.mkdir(exist_ok=True)
        (self.gh / "create-fails").write_text("")
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("gh could not create" in x for x in p.problems), p.problems)
        (self.gh / "create-fails").unlink()
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(self.journal()["state"], "done")

    def test_a_repository_that_is_not_private_gets_nothing_pushed(self):
        self.gh.mkdir(exist_ok=True)
        (self.gh / "create-public").write_text("")                   # GitHub answers wrongly: the check after creation
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("could not be confirmed private" in x for x in p.problems), p.problems)
        self.assertEqual(git("for-each-ref", cwd=self.bare()), "", "nothing was pushed")
        self.assertEqual(git("remote", cwd=self.dev / "orchard"), "")
        self.assertNotIn("private at creation", self.row())

    def test_a_name_taken_on_github(self):
        other = self.t / "other"
        git("init", "-q", "-b", "main", str(other))
        git("-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "theirs", cwd=other)
        self.bare().parent.mkdir(parents=True)
        git("clone", "-q", "--bare", str(other), str(self.bare()))
        self.bare().with_suffix(".json").write_text(json.dumps({"visibility": "PRIVATE"}))
        theirs = git("rev-parse", "main", cwd=self.bare())
        (self.gh / "signed-out").write_text("")                      # so the name is not in the list of taken names
        self.drop("r1.md", IDEA)
        self.run_pass()
        (self.gh / "signed-out").unlink()
        before = len(self.creates())
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("already exists on GitHub and is not empty" in x for x in p.problems), p.problems)
        self.assertEqual(git("rev-parse", "main", cwd=self.bare()), theirs, "untouched")
        self.assertEqual(len(self.creates()), before, "it was there: nothing was created")
        self.assertEqual(git("remote", cwd=self.dev / "orchard"), "", "and nothing points at it")

    def test_an_empty_private_repository_of_that_name_is_taken_up(self):
        self.bare().parent.mkdir(parents=True)                       # created by an attempt whose answer never arrived
        git("init", "-q", "--bare", "-b", "main", str(self.bare()))
        self.bare().with_suffix(".json").write_text(json.dumps({"visibility": "PRIVATE"}))
        (self.gh / "signed-out").write_text("")
        self.drop("r1.md", IDEA)
        self.run_pass()
        (self.gh / "signed-out").unlink()
        before = len(self.creates())
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(len(self.creates()), before, "it was there, empty and private: taken up, not created")
        self.assertEqual(git("rev-parse", "main", cwd=self.bare()), git("rev-parse", "HEAD", cwd=self.dev / "orchard"))

    @unittest.skipIf(os.name == "nt", "the test builds a PATH with git and no gh the POSIX way")
    def test_gh_missing_is_said_with_the_fix(self):
        (self.bin / ("gh.cmd" if os.name == "nt" else "gh")).unlink()
        no_gh = self.t / "no-gh"                                                  # git, and no gh anywhere,
        no_gh.mkdir()                                                             # even where /usr/bin has one
        for d in ("/usr/bin", "/bin"):
            for tool in Path(d).iterdir():
                if tool.name != "gh" and not os.path.lexists(no_gh / tool.name):   # /bin may be /usr/bin; links may dangle
                    (no_gh / tool.name).symlink_to(tool)
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{no_gh}"
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("gh could not list repositories" in x for x in p.problems), p.problems)
        self.assertTrue(any("gh, is not installed" in x for x in p.problems), p.problems)
        self.assertEqual(self.journal()["state"], "local")
        self.assertTrue(any("gh, is not installed" in x for x in C.new_projects_ready(C.new_projects(self.cfg)[0])))

    # --------------------------------------------------------------------------- the limits
    def test_the_deny_list_covers_the_name_and_what_it_is_about(self):
        self.drop("r1.md", "Project: top\nChanges v1:\nnew-project name=orchard \"Plan the orchard\" "
                           "about=\"The Codename-X orchard\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("denied word" in x for x in p.problems), p.problems)
        self.assertEqual(list(self.dev.iterdir()), [])
        self.assertEqual(self.creates(), [])
        self.assertEqual(self.journal()["state"], "refused")
        self.assertIn("It is not tried again.", self.critical()[0].body)
        p, rc = self.run_pass()                                      # final: not tried, and not said, again
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(len(self.critical()), 1)
        self.cfg["backend"]["deny"] = ["orch"]
        self.drop("r2.md", "Project: top\nChanges v1:\nnew-project name=orchid \"Orchids\"\nEnd.\n")
        self.run_pass()
        self.assertEqual(self.journal("orchid")["state"], "refused", "the name itself")

    def test_at_most_so_many_a_day_and_the_rest_wait(self):
        self.cfg["new_projects"]["per_day"] = 1
        self.drop("r1.md", IDEA)
        self.drop("r2.md", "Project: top\nChanges v1:\nnew-project name=pond \"Dig the pond\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("waits for tomorrow" in x for x in p.problems), p.problems)
        made = sorted(x.name for x in self.dev.iterdir())
        self.assertEqual(len(made), 1)
        self.assertEqual(len(self.creates()), 1)
        self.assertEqual(self.critical(), [], "waiting a day is no emergency")
        waiting = "pond" if made == ["orchard"] else "orchard"
        done = self.journal(made[0])
        done["made_on"] = "2026-01-01"                               # as if that one was made on an earlier day
        (self.t / "work" / "new-projects" / f"{made[0]}.json").write_text(json.dumps(done))
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue((self.dev / waiting / ".git").is_dir())

    def test_settings_that_cannot_be_used_make_nothing(self):
        self.cfg["new_projects"]["visibility"] = "public"
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("always private" in x for x in p.problems), p.problems)
        self.assertTrue(self.s.exists("projects/orchard/collab-kit/00-START-HERE.md"), "the folder project is made")
        self.assertEqual(list(self.dev.iterdir()), [])
        self.assertEqual(self.creates(), [])

    def test_a_project_started_before_the_setting_gets_no_repository(self):
        settings = self.cfg.pop("new_projects")
        self.drop("r1.md", IDEA)
        self.run_pass()
        time.sleep(1.1)                                              # times are kept to the second
        self.cfg["new_projects"] = settings
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(list(self.dev.iterdir()), [], "turning it on changes nothing about the past")
        self.drop("r2.md", "Project: top\nChanges v1:\nnew-project name=pond \"Dig the pond\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual([x.name for x in self.dev.iterdir()], ["pond"])

    def test_a_pass_that_stopped_right_after_applying_is_finished_by_the_next(self):
        self.run_pass()                                              # the setting is on from here
        time.sleep(1.1)
        self.drop("r1.md", IDEA)
        self.assertEqual(self.apply_all()[0].status, "applied")      # applied, and the pass died before the repository
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue((self.dev / "orchard" / ".git").is_dir(), "found in the ledger")

    def test_a_project_undone_first_gets_no_repository(self):
        (self.dev / "orchard").write_text("in the way")              # holds the first attempt up
        self.drop("r1.md", IDEA)
        self.run_pass()
        self.assertEqual(len(self.critical()), 1)
        self.drop("r2.md", "Project: top\nChanges v1:\nundo r1\nEnd.\n")
        (self.dev / "orchard").unlink()
        p, rc = self.run_pass()
        self.assertFalse(self.s.exists("projects/orchard/collab-kit/00-START-HERE.md"))
        self.assertEqual(list(self.dev.iterdir()), [])
        self.assertEqual(self.journal()["state"], "withdrawn")
        self.assertEqual(self.creates(), [])
        self.assertEqual(self.critical(), [], "the back end settled the item it had raised")

    def test_a_project_undone_while_it_waits_for_github_gets_no_remote(self):
        (self.gh / "signed-out").parent.mkdir(exist_ok=True)
        (self.gh / "signed-out").write_text("")
        self.drop("r1.md", IDEA)
        self.run_pass()
        self.assertEqual(self.journal()["state"], "local")
        self.drop("r2.md", "Project: top\nChanges v1:\nundo r1\nEnd.\n")
        (self.gh / "signed-out").unlink()
        before = len(self.creates())
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(self.journal()["state"], "withdrawn")
        self.assertEqual(len(self.creates()), before, "undone: nothing is created on GitHub")
        self.assertFalse(self.bare().exists())
        self.assertTrue((self.dev / "orchard" / ".git").is_dir(), "nothing deletes a repository")
        self.assertIn("project orchard was undone; its repository stays", self.s.read("knowledge/status.md"))
        self.assertFalse(self.s.exists("projects/orchard/collab-kit/00-START-HERE.md"), "nothing was written back into it")
        self.assertEqual(self.critical(), [])
        p, rc = self.run_pass()
        self.assertEqual(len(self.creates()), before)

    def test_one_item_for_a_project_whatever_the_reasons_and_it_is_settled(self):
        (self.gh / "signed-out").parent.mkdir(exist_ok=True)
        (self.gh / "signed-out").write_text("")
        self.drop("r1.md", IDEA)
        self.run_pass()                                              # reason one: gh is signed out
        (self.gh / "signed-out").unlink()
        os.environ["GIT_CONFIG_VALUE_0"] = "https://elsewhere.invalid/"
        os.environ["GIT_CONFIG_KEY_1"] = "url.file:///nowhere/.insteadOf"
        os.environ["GIT_CONFIG_VALUE_1"] = "https://github.com/"
        self.run_pass()                                              # reason two: the push fails
        self.run_pass()                                              # the same again: said on the page only
        crit = self.critical()
        self.assertEqual(len(crit), 1, [i.title for i in crit])
        self.assertEqual(crit[0].body.count("Now: "), 1, "one line on its log for the one new kind of reason")
        self.assertIn("the first push", crit[0].body)
        repos = (self.gh / "repos").as_posix() + "/"
        os.environ.update({"GIT_CONFIG_KEY_1": f"url.{repos}.insteadOf", "GIT_CONFIG_VALUE_0": "https://github.com/",
                           "GIT_CONFIG_VALUE_1": "git@github.com:"})
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(self.critical(), [])
        self.assertEqual(len([i for i in self.top.items() if "its repository could not" in i.title]), 1)

    def test_dropping_the_item_stops_the_attempts(self):
        (self.dev / "orchard").write_text("in the way")
        self.drop("r1.md", IDEA)
        self.run_pass()
        item = self.critical()[0]
        self.assertIn("To stop the attempts, drop this item", item.body)
        self.drop("r2.md", f"Project: top\nFrom: Sam\nChanges v1:\nwithdraw {item.id} \"Project orchard\" reason=\"a folder is enough\"\nEnd.\n")
        (self.dev / "orchard").unlink()
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(self.journal()["state"], "stopped")
        self.assertEqual(list(self.dev.iterdir()), [])
        p, rc = self.run_pass()
        self.assertEqual(list(self.dev.iterdir()), [], "and it stays stopped")
        self.assertTrue(self.s.exists("projects/orchard/collab-kit/00-START-HERE.md"), "the folder project is untouched")

    def test_a_removed_journal_is_opened_again_never_lost(self):
        (self.dev / "orchard").write_text("in the way")
        self.drop("r1.md", IDEA)
        self.run_pass()
        (self.t / "work" / "new-projects" / "orchard.json").unlink()
        (self.dev / "orchard").unlink()
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue((self.dev / "orchard" / ".git").is_dir())

    def test_ledgers_that_are_not_ledgers_stop_nothing(self):
        self.run_pass()
        time.sleep(1.1)
        from collab_kit.text import utcnow
        for n, text in enumerate(("[]", "5", "{", json.dumps({"id": "x", "state": "done", "minted": 5,
                                                                "applied_at": utcnow().isoformat()}),
                                  json.dumps({"id": "y y", "state": "done", "minted": ["project:pond"],
                                              "applied_at": utcnow().isoformat()}),
                                  json.dumps({"id": "z", "state": "done", "minted": [["project:pond"], None, "project:"],
                                              "applied_at": utcnow().replace(tzinfo=None).isoformat()}))):
            self.s.write(f"_returns/applied/odd-{n}.ledger.json", text)
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual([x.name for x in self.dev.iterdir()], ["orchard"], "the real one beside them is made")

    def test_only_the_first_commit_is_pushed_whatever_the_branch_became(self):
        (self.gh / "signed-out").parent.mkdir(exist_ok=True)
        (self.gh / "signed-out").write_text("")
        self.drop("r1.md", IDEA)
        self.run_pass()
        repo = self.dev / "orchard"
        first = git("rev-parse", "HEAD", cwd=repo)
        (repo / "notes.txt").write_text("work done while the push was waiting\n")
        git("add", "-A", cwd=repo)
        git("-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-q", "-m", "mine", cwd=repo)
        (self.gh / "signed-out").unlink()
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(git("rev-parse", "main", cwd=self.bare()), first, "the first commit, and only that")
        self.assertNotEqual(git("rev-parse", "HEAD", cwd=repo), first)

    def test_an_origin_the_back_end_did_not_set_is_left_alone(self):
        (self.gh / "signed-out").parent.mkdir(exist_ok=True)
        (self.gh / "signed-out").write_text("")
        self.drop("r1.md", IDEA)
        self.run_pass()
        repo = self.dev / "orchard"
        git("remote", "add", "origin", "https://example.invalid/mine.git", cwd=repo)
        (self.gh / "signed-out").unlink()
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("already has an origin" in x for x in p.problems), p.problems)
        self.assertEqual(git("config", "--get", "remote.origin.url", cwd=repo).strip(), "https://example.invalid/mine.git")
        self.assertEqual(git("for-each-ref", cwd=self.bare()), "", "nothing was pushed")
        self.assertEqual(self.journal()["state"], "refused")

    def test_a_journal_that_names_another_folder_pushes_nothing(self):
        (self.gh / "signed-out").parent.mkdir(exist_ok=True)
        (self.gh / "signed-out").write_text("")
        self.drop("r1.md", IDEA)
        self.run_pass()
        other = self.t / "other"
        git("init", "-q", "-b", "main", str(other))
        git("-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "theirs", cwd=other)
        j = self.journal()
        j["local"] = str(other)
        (self.t / "work" / "new-projects" / "orchard.json").write_text(json.dumps(j))
        (self.gh / "signed-out").unlink()
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertEqual(git("remote", cwd=other), "", "the other repository was not touched")
        self.assertFalse(self.bare().exists() and git("for-each-ref", cwd=self.bare()))
        self.assertEqual(self.journal()["state"], "refused")

    def test_a_pass_that_died_between_placing_and_saying_so_is_finished(self):
        del self.cfg["new_projects"]["github_owner"]
        self.drop("r1.md", IDEA)
        self.run_pass()
        j = self.journal()
        self.assertEqual(j["state"], "done")
        j["state"] = "placing"                                       # as the journal stood just before the move
        (self.t / "work" / "new-projects" / "orchard.json").write_text(json.dumps(j))
        head = git("rev-parse", "HEAD", cwd=self.dev / "orchard")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(self.journal()["state"], "done", "taken up by its first commit, not refused as a stranger")
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.dev / "orchard"), head)
        self.assertEqual(self.s.read("knowledge/status.md").count("has a repository"), 1, "and said once")

    def test_a_push_that_arrived_unrecorded_is_not_pushed_or_refused(self):
        self.drop("r1.md", IDEA)
        self.run_pass()
        j = self.journal()
        j.update(state="local", pushed=False)                        # the pass died right after the push
        (self.t / "work" / "new-projects" / "orchard.json").write_text(json.dumps(j))
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(len(self.creates()), 1)
        self.assertEqual(self.journal()["state"], "done")
        # but a main that is not this project's first commit is never pushed over
        other = self.t / "other"
        git("clone", "-q", str(self.bare()), str(other))
        git("-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "theirs", cwd=other)
        git("push", "-q", "origin", "HEAD:main", cwd=other)
        theirs = git("rev-parse", "main", cwd=self.bare())
        j.update(state="local", pushed=False)
        (self.t / "work" / "new-projects" / "orchard.json").write_text(json.dumps(j))
        p, rc = self.run_pass()
        self.assertEqual(rc, 1)
        self.assertTrue(any("is no longer empty" in x for x in p.problems), p.problems)
        self.assertEqual(git("rev-parse", "main", cwd=self.bare()), theirs)

    def test_across_file_systems_nothing_of_anyone_elses_is_removed(self):
        import errno
        from unittest import mock
        del self.cfg["new_projects"]["github_owner"]
        (self.dev / ".orchard.collab-kit-new").mkdir()
        (self.dev / ".orchard.collab-kit-new" / "mine.txt").write_text("keep me")
        real = os.rename

        def rename(src, dst, *a, **k):
            if "staging" in str(src):
                raise OSError(errno.EXDEV, "Invalid cross-device link")
            return real(src, dst, *a, **k)
        self.drop("r1.md", IDEA)
        with mock.patch.object(RP.os, "rename", rename):
            p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue((self.dev / "orchard" / "tools" / "collab-kit" / "ck").is_file())
        self.assertEqual(git("status", "--porcelain", cwd=self.dev / "orchard"), "")
        self.assertEqual((self.dev / ".orchard.collab-kit-new" / "mine.txt").read_text(), "keep me")
        self.assertEqual(sorted(x.name for x in self.dev.iterdir()), [".orchard.collab-kit-new", "orchard"],
                         "and its own scratch folder is gone")

    @unittest.skipIf(os.name == "nt", "symbolic links need a privilege on Windows")
    def test_a_link_at_the_destination_is_never_followed(self):
        target = self.t / "elsewhere"
        target.mkdir()
        os.symlink(target, self.dev / "orchard")
        os.symlink(self.t / "nowhere", self.dev / "pond")              # a link to nothing is still a path that exists
        self.drop("r1.md", IDEA)
        self.drop("r2.md", "Project: top\nChanges v1:\nnew-project name=pond \"Dig the pond\"\nEnd.\n")
        p, rc = self.run_pass()
        self.assertEqual(list(target.iterdir()), [])
        self.assertTrue((self.dev / "orchard").is_symlink() and (self.dev / "pond").is_symlink())
        self.assertFalse((self.t / "nowhere").exists())
        self.assertEqual(self.creates(), [])

    def test_off_then_on_again_reaches_back_to_nothing(self):
        self.run_pass()                                              # on
        settings = self.cfg.pop("new_projects")
        time.sleep(1.1)
        self.drop("r1.md", IDEA)
        self.run_pass()                                              # off: a folder project
        time.sleep(1.1)
        self.cfg["new_projects"] = settings
        p, rc = self.run_pass()                                      # on again
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(list(self.dev.iterdir()), [])

    def test_a_forged_ledger_cannot_name_a_path(self):
        self.run_pass()
        time.sleep(1.1)
        from collab_kit.text import utcnow
        for n, name in enumerate(("../escape", "Bad Name", "a/b", "--public", "test")):
            self.s.write(f"_returns/applied/forged-{n}.ledger.json", json.dumps({
                "id": f"forged-{n}", "state": "done", "applied_at": utcnow().isoformat(), "minted": [f"project:{name}"],
                "effects": []}))
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertEqual(list(self.dev.iterdir()), [])
        self.assertEqual([x.name for x in self.t.iterdir() if x.name == "escape"], [])
        self.assertEqual(self.creates(), [])
        self.assertEqual(RP.read_journals(self.t / "work"), [])

    def test_a_dry_run_makes_nothing(self):
        self.drop("r1.md", IDEA)
        p, rc = self.run_pass(dry_run=True)
        self.assertEqual(list(self.dev.iterdir()), [])
        self.assertEqual(self.creates(), [])
        self.assertFalse((self.t / "work" / "new-projects").exists())

    def test_a_failed_install_leaves_nothing_at_the_destination(self):
        from collab_kit import installer
        real = installer.install_project
        installer.install_project = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full"))
        try:
            self.drop("r1.md", IDEA)
            p, rc = self.run_pass()
        finally:
            installer.install_project = real
        self.assertEqual(rc, 1)
        self.assertTrue(any("the kit's installer failed" in x for x in p.problems), p.problems)
        self.assertEqual(list(self.dev.iterdir()), [], "built elsewhere: nothing half-made where repositories live")
        p, rc = self.run_pass()
        self.assertEqual(rc, 0, p.problems)
        self.assertTrue((self.dev / "orchard" / "tools" / "collab-kit" / "ck").is_file())

    # ------------------------------------------------------------------------------ doctor
    def doctor(self) -> subprocess.CompletedProcess:
        cfgdir = Path(os.environ["XDG_CONFIG_HOME"]) / "collab-kit"
        cfgdir.mkdir(parents=True, exist_ok=True)
        np = self.cfg["new_projects"]
        (cfgdir / "backend.toml").write_text(
            f"[backend]\ncloud = {json.dumps(str(self.cloud))}\n\n[new_projects]\n"
            + "".join(f"{k} = {json.dumps(v)}\n" for k, v in np.items()))
        try:
            return subprocess.run([sys.executable, str(KIT / "engine" / "ck.py"), "doctor"], cwd=self.t,
                                  capture_output=True, text=True)
        finally:
            (cfgdir / "backend.toml").unlink()

    @unittest.skipIf(os.name == "nt", "the config folder is found another way on Windows")
    def test_doctor_checks_the_machine_is_ready(self):
        out = self.doctor().stdout
        self.assertIn(f"New projects: a repository in {self.dev}, and a private one under {self.OWNER} on GitHub, "
                      "at most 3 a day: ready", out)
        (self.gh / "signed-out").write_text("")
        res = self.doctor()
        self.assertEqual(res.returncode, 1)
        self.assertIn("NOT READY", res.stdout)
        self.assertIn("run `gh auth login`", res.stdout.split("To fix:")[1])
        self.cfg["new_projects"]["visibility"] = "public"
        self.assertIn("NOT USABLE", self.doctor().stdout)
        self.cfg["new_projects"] = {"repositories": str(self.t / "nowhere")}
        self.assertIn("is not a folder on this machine", self.doctor().stdout)


class OverRclone(unittest.TestCase):
    """The same through rclone (the stand-in): the ledgers are found in the pass's one listing."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name).resolve()
        launcher = t / ("rclone.cmd" if os.name == "nt" else "rclone")
        if os.name == "nt":
            launcher.write_text(f'@"{sys.executable}" "{HERE / "fake_rclone.py"}" %*\n')
        else:
            launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{HERE / "fake_rclone.py"}" "$@"\n')
            launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
        self.env = dict(os.environ)
        os.environ.update(FAKE_RCLONE_ROOT=str(t), COLLAB_KIT_RCLONE=str(launcher))
        self.root = t / "drive" / "Collab Kit"
        set_human("Sam")
        s = self.s = FolderStore(self.root)
        s.write("00-START-HERE.md", top_start_file())
        s.write("knowledge/projects.md", CATALOG)
        for d in ("_returns", "agenda"):
            s.mkdir(d)
        (t / "dev").mkdir()
        self.cfg = {"backend": {"cloud": "rclone:drive:Collab Kit", "work": str(t / "work"), "human": "Sam",
                                "local_roots": [], "lease_settle_seconds": 0},
                    "new_projects": {"repositories": str(t / "dev")}}

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def test_a_local_repository_through_rclone(self):
        self.s.write("_returns/r1.md", IDEA)
        old = time.time() - 3600
        os.utime(self.root / "_returns" / "r1.md", (old, old))
        p = BE.Pass(self.cfg)
        self.assertEqual(p.run(), 0, p.problems)
        self.assertTrue((self.t / "dev" / "orchard" / ".git").is_dir())
        row = next(ln for ln in self.s.read("knowledge/projects.md").splitlines() if "`orchard`" in ln)
        self.assertIn("(not on GitHub)", row)
        self.assertIn("project orchard has a repository", self.s.read("knowledge/status.md"))


if __name__ == "__main__":
    unittest.main()

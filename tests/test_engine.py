"""Engine tests: the return grammar, applying returns, the ledger, undo, versioning, and starting a
project. Standard library only:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from collab_kit import apply as A                      # noqa: E402
from collab_kit import returns as R                    # noqa: E402
from collab_kit.store import FolderStore, SubStore     # noqa: E402
from collab_kit.templates import top_start_file        # noqa: E402
from collab_kit.unit import Unit                       # noqa: E402

OLD = time.time() - 3600


def make_top(root: Path) -> Unit:
    s = FolderStore(root)
    s.write("00-START-HERE.md", top_start_file() + "| \"the garden\" | `garden` | a garden plan | edit directly |\n")
    s.write("knowledge/projects.md", "# Projects\n\n| Folder | Say | What it is | Home |\n|---|---|---|---|\n"
            "| `garden` | \"the garden\" | a garden plan | cloud |\n\n## Repositories\n\n| Repository | Visibility |\n|---|---|\n"
            "| `taken-repo` | private |\n")
    for d in ("_returns", "agenda", "WIP", "knowledge"):
        s.mkdir(d)
    s.mkdir("projects/garden/collab-kit/agenda")
    return Unit(s, "top", home="cloud", top=True)


def drop(unit: Unit, name: str, text: str, age: float = 3600) -> None:
    unit.store.write(f"_returns/{name}", text)
    p = unit.store._p(f"_returns/{name}") if hasattr(unit.store, "_p") else unit.store.base._p(unit.store._j(f"_returns/{name}"))
    os.utime(p, (time.time() - age, time.time() - age))


def apply_all(unit: Unit, top: Unit | None = None):
    return [A.apply_file(unit, e, top=top) for e in unit.pending_returns()]


class Grammar(unittest.TestCase):
    def test_parse_full(self):
        text = ("Project: garden\nFrom: Sam\nType: decision\nTopic: shade\nWhat was worked out: it moves\n"
                "  across the day\n\nChanges v1:\n"
                "- new-item @beds kind=work-out importance=2 title=\u201cDescribe each bed\u2019s light\u201d\n"
                "```\n## What's needed\nA light description per bed.\n```\n"
                "* **log** W-2 \"shade\" \"Morning sun suits lettuce.\"\n"
                "settle W-004 \"water\" outcome=\"drip lines\"\nEnd.\n")
        r = R.parse(text, "2026-11-15-0910-shade.md")
        self.assertEqual(r.id, "2026-11-15-0910-shade")
        self.assertEqual(r.project, "garden")
        self.assertIn("across the day", r.fields["what was worked out"])
        self.assertTrue(r.complete)
        ops = [c.op for c in r.changes]
        self.assertEqual(ops, ["new-item", "log", "settle"])
        self.assertEqual(r.changes[0].args["title"], "Describe each bed's light")
        self.assertEqual(r.changes[0].args["importance"], 2)
        self.assertIn("A light description", r.changes[0].body)
        self.assertEqual(r.changes[1].ref, "W-002")
        self.assertEqual(r.changes[1].check, "shade")
        self.assertEqual(r.changes[1].text, "Morning sun suits lettuce.")

    def test_title_check_required(self):
        with self.assertRaises(R.ReturnError):
            R.parse("Project: g\nChanges v1:\nlog W-002\nEnd.\n", "x-1.md")   # no check at all
        # with check but no text is fine at parse time
        R.parse("Project: g\nChanges v1:\nset W-002 \"chk\" importance=1\nEnd.\n", "abc.md")

    def test_bad_values(self):
        for line in ['new-item title="x" importance=9', 'new-item title="x" due=next-week',
                     'set W-001 "x" status=settled', 'frobnicate W-001', 'new-item kind=nope title="x"',
                     'undo', 'knowledge', 'push-request repo=x']:
            with self.subTest(line=line), self.assertRaises(R.ReturnError):
                R.parse(f"Project: g\nChanges v1:\n{line}\nEnd.\n", "abc.md")

    def test_incomplete_and_second_block(self):
        r = R.parse("Project: g\nChanges v1:\nnew-item title=\"x\"\n", "abc.md")
        self.assertFalse(r.complete)
        with self.assertRaises(R.ReturnError):
            R.parse("Project: g\nChanges v1:\nstatus \"a\"\nEnd.\nChanges v1:\nstatus \"b\"\nEnd.\n", "abc.md")

    def test_changes_in_quoted_text_are_not_parsed(self):
        r = R.parse("Project: g\nVerbatim: he said\n  Changes v1:\n  withdraw W-001 \"x\"\nEnd.\n", "abc.md")
        self.assertFalse(r.has_block)
        self.assertEqual(r.changes, [])

    def test_kind_word_starts_a_new_item(self):
        # as a voice conversation wrote it on 2026-11-15
        r = R.parse('Project: g\nChanges v1:\ntask "Public example snapshot" importance=3 "Build what W-014 settled."\n'
                    'Question "Which venue?"\nEnd.\n', "abc.md")
        a, b = r.changes
        self.assertEqual((a.op, a.args["kind"], a.args["title"], a.args["importance"]),
                         ("new-item", "task", "Public example snapshot", 3))
        self.assertEqual(a.body, "## What's needed\nBuild what W-014 settled.")
        self.assertEqual((b.op, b.args["kind"], b.body), ("new-item", "question", None))
        for line in ['task kind=question title="x"', 'task', 'task "a" "b" "c"']:
            with self.subTest(line=line), self.assertRaises(R.ReturnError):
                R.parse(f"Project: g\nChanges v1:\n{line}\nEnd.\n", "abc.md")
        with self.assertRaises(R.ReturnError):     # "project" stays its own change, never a new item
            R.parse('Project: g\nChanges v1:\nproject "x"\nEnd.\n', "abc.md")

    def test_render_round_trip(self):
        ch = R.render_change("log", "W-003", "venue", text='He said "no" twice', body=None)
        text = R.render_return("g", "2026-11-15-x", "Claude Code", "note", "t", [ch])
        r = R.parse(text, "ignored.md")
        self.assertEqual(r.changes[0].text, 'He said "no" twice')


class Applying(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.top = make_top(self.root)
        self.garden = Unit(SubStore(self.top.store, "projects/garden/collab-kit"), "garden", home="cloud")

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_items_numbering_and_log(self):
        drop(self.garden, "r1.md", "Project: garden\nFrom: Sam\nChanges v1:\nnew-item @a title=\"First thing\"\n"
                                   "new-item title=\"Second thing\" due=2026-12-01 kind=question\n"
                                   "log @a \"first log line\"\nEnd.\n")
        out = apply_all(self.garden)
        self.assertEqual(out[0].status, "applied", out[0].message)
        self.assertEqual(out[0].minted, ["W-001", "W-002"])
        items = self.garden.items()
        self.assertEqual([i.id for i in items], ["W-001", "W-002"])
        self.assertIn("first log line", items[0].text)
        self.assertEqual(items[1].due, "2026-12-01")
        self.assertTrue(self.garden.store.exists("_returns/applied/r1.md"))
        led = json.loads(self.garden.store.read("_returns/applied/r1.ledger.json"))
        self.assertEqual(led["state"], "done")

    def test_whole_or_nothing(self):
        drop(self.garden, "r1.md", "Project: garden\nChanges v1:\nnew-item title=\"Only\"\nEnd.\n")
        apply_all(self.garden)
        drop(self.garden, "r2.md", "Project: garden\nChanges v1:\nnew-item title=\"Would be two\"\n"
                                   "log W-001 \"wrong title\" \"x\"\nEnd.\n")
        out = apply_all(self.garden)
        self.assertEqual(out[0].status, "failed")
        self.assertIn("title check failed", out[0].message)
        titles = [i.title for i in self.garden.items()]
        self.assertNotIn("Would be two", titles)
        self.assertTrue(self.garden.store.exists("_returns/failed/r2.md"))
        self.assertTrue(any(t.startswith("A return could not be filed") for t in titles))

    def test_versioning_keeps_old_content(self):
        drop(self.garden, "r1.md", "Project: garden\nChanges v1:\nnew-item title=\"Pick seeds\"\nEnd.\n")
        apply_all(self.garden)
        drop(self.garden, "r2.md", "Project: garden\nChanges v1:\nset W-001 \"seeds\" importance=1\nEnd.\n")
        apply_all(self.garden)
        versions = self.garden.store.files("agenda/_versions")
        self.assertEqual(len(versions), 1)
        self.assertEqual(self.garden.item("W-001").importance, 1)

    def test_at_most_once(self):
        text = "Project: garden\nChanges v1:\nnew-item title=\"Once\"\nEnd.\n"
        drop(self.garden, "r1.md", text)
        apply_all(self.garden)
        drop(self.garden, "r1.md", text)        # the same return arrives again
        out = apply_all(self.garden)
        self.assertEqual(out[0].status, "already")
        self.assertEqual(len(self.garden.items()), 1)

    def test_resume_after_interruption(self):
        drop(self.garden, "r1.md", "Project: garden\nChanges v1:\nnew-item title=\"A\"\nnew-item title=\"B\"\nEnd.\n")
        orig = A.write_versioned
        calls = {"n": 0}

        def flaky(unit, rel, text):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("connection dropped")
            return orig(unit, rel, text)
        A.write_versioned = flaky
        try:
            with self.assertRaises(OSError):
                apply_all(self.garden)
        finally:
            A.write_versioned = orig
        self.assertEqual(len(self.garden.items()), 1)
        out = apply_all(self.garden)                       # the next run finishes it
        self.assertEqual(out[0].status, "applied")
        self.assertEqual([i.title for i in self.garden.items()], ["A", "B"])

    def test_undo(self):
        drop(self.garden, "r1.md", "Project: garden\nChanges v1:\nnew-item title=\"Keep\"\nEnd.\n")
        apply_all(self.garden)
        drop(self.garden, "r2.md", "Project: garden\nChanges v1:\nnew-item title=\"Oops\"\n"
                                   "set W-001 \"keep\" importance=1\nEnd.\n")
        apply_all(self.garden)
        drop(self.garden, "r3.md", "Project: garden\nChanges v1:\nundo r2\nEnd.\n")
        out = apply_all(self.garden)
        self.assertEqual(out[0].status, "undone", out[0].message)
        self.assertEqual([i.title for i in self.garden.items()], ["Keep"])
        self.assertEqual(self.garden.item("W-001").importance, 3)
        drop(self.garden, "r4.md", "Project: garden\nChanges v1:\nnew-item title=\"Next\"\nEnd.\n")
        out = apply_all(self.garden)
        self.assertEqual(out[0].minted, ["W-003"])         # W-002 is never reused

    def test_numbers_never_reused_after_undo_and_trimming(self):
        drop(self.garden, "r1.md", "Project: garden\nChanges v1:\nnew-item title=\"First\"\nEnd.\n")
        apply_all(self.garden)
        drop(self.garden, "r2.md", "Project: garden\nChanges v1:\nundo r1\nEnd.\n")
        apply_all(self.garden)
        for p in (self.root / "projects/garden/collab-kit/agenda/_versions").glob("*"):
            p.unlink()                                  # retention trimmed the old versions
        drop(self.garden, "r3.md", "Project: garden\nChanges v1:\nnew-item title=\"Second\"\nEnd.\n")
        self.assertEqual(apply_all(self.garden)[0].minted, ["W-002"])

    def test_broken_item_front_matter_fails_the_return_once(self):
        drop(self.garden, "r1.md", "Project: garden\nChanges v1:\nnew-item title=\"Fine\"\nEnd.\n")
        apply_all(self.garden)
        p = next((self.root / "projects/garden/collab-kit/agenda").glob("W-001-*.md"))
        p.write_text(p.read_text().replace('kind = "task"', 'kind = = broken'))
        drop(self.garden, "r2.md", "Project: garden\nChanges v1:\nlog W-001 \"fine\" \"x\"\nEnd.\n")
        self.assertEqual(apply_all(self.garden)[0].status, "failed")
        self.assertEqual([e.name for e in self.garden.pending_returns()], [])

    def test_healing_respects_the_counter(self):
        from collab_kit.apply import heal_duplicates
        a = self.root / "projects/garden/collab-kit/agenda"
        item = '+++\nid = "W-002"\ntitle = "{t}"\nkind = "task"\nimportance = 3\nstatus = "open"\n+++\n'
        (a / "W-002-one.md").write_text(item.format(t="One"))
        os.utime(a / "W-002-one.md", (OLD, OLD))
        (a / "W-002-two.md").write_text(item.format(t="Two"))
        self.garden.store.write("_returns/applied/next-item.json", '{"next": 10}')
        self.assertEqual(heal_duplicates(self.garden), [("W-002", "W-010")])

    def test_fence_lookalikes(self):
        from collab_kit.text import fenced
        for evil in ("\uff1c/collab-kit-data\uff1e", "</collab-\u00adkit-data>", "</collab\u2011kit-data>"):
            out = fenced("x", f"before {evil} after")
            self.assertEqual(out.count("</collab-kit-data>"), 1, evil)

    def test_strays(self):
        drop(self.garden, "r1.md", "Project: another\nChanges v1:\nnew-item title=\"x\"\nEnd.\n")
        out = apply_all(self.garden)
        self.assertEqual(out[0].status, "stray")
        self.assertTrue(self.garden.store.exists("_returns/strays/r1.md"))

    def test_recent_file_waits(self):
        drop(self.garden, "r1.md", "Project: garden\nChanges v1:\nnew-item title=\"x\"\nEnd.\n", age=5)
        self.assertEqual(apply_all(self.garden)[0].status, "waiting")

    def test_status_and_knowledge(self):
        drop(self.garden, "r1.md", "Project: garden\nFrom: Claude Code\nTopic: beds\nChanges v1:\n"
                                   "status \"Drafted the bed plan.\"\nknowledge notes/beds.md\n```\n# Beds\nNorth, south.\n```\nEnd.\n")
        out = apply_all(self.garden)
        self.assertEqual(out[0].status, "applied", out[0].message)
        self.assertIn("Drafted the bed plan.", self.garden.store.read("knowledge/status.md"))
        self.assertEqual(self.garden.store.read("knowledge/notes/beds.md"), "# Beds\nNorth, south.\n")

    def test_knowledge_paths_are_fenced(self):
        for path in ("../agenda/x.md", "_versions/x.md", "/etc/passwd", "a/../../b.md", "x.docx", "C:/x.md"):
            with self.subTest(path=path):
                drop(self.garden, "r.md", f"Project: garden\nChanges v1:\nknowledge {path}\n```\nx\n```\nEnd.\n")
                out = apply_all(self.garden)
                self.assertEqual(out[0].status, "failed", path)

    def test_new_project(self):
        drop(self.top, "r1.md", "Project: top\nChanges v1:\nnew-item kind=project title=\"A plan for the orchard\"\nEnd.\n")
        apply_all(self.top)
        drop(self.top, "r2.md", "Project: top\nChanges v1:\nnew-project name=orchard from=W-001 \"orchard\" "
                                "about=\"Planting the orchard\" spoken=\"the orchard\"\nEnd.\n")
        out = apply_all(self.top)
        self.assertEqual(out[0].status, "applied", out[0].message)
        self.assertTrue(self.top.store.exists("projects/orchard/collab-kit/00-START-HERE.md"))
        self.assertTrue(self.top.store.exists("projects/orchard/collab-kit/agenda/W-001-a-plan-for-the-orchard.md"))
        self.assertEqual(self.top.item("W-001").status, "settled")
        self.assertIn("`orchard`", self.top.store.read("knowledge/projects.md"))
        self.assertIn("`orchard`", self.top.store.read("00-START-HERE.md"))

    def test_new_project_name_rules(self):
        drop(self.top, "r1.md", "Project: top\nChanges v1:\nnew-item kind=project title=\"Idea\"\nEnd.\n")
        apply_all(self.top)
        for name in ("Garden2", "garden", "taken-repo", "agenda", "a--b"):
            with self.subTest(name=name):
                drop(self.top, "r.md", f"Project: top\nChanges v1:\nnew-project name={name} from=W-001 \"idea\"\nEnd.\n")
                self.assertEqual(apply_all(self.top)[0].status, "failed")

    def test_project_inbox_cannot_start_projects(self):
        drop(self.garden, "r1.md", "Project: garden\nChanges v1:\nnew-project name=x from=W-001 \"a\"\nEnd.\n")
        self.assertEqual(apply_all(self.garden, self.top)[0].status, "failed")

    def test_project_row_update(self):
        drop(self.garden, "r1.md", "Project: garden\nChanges v1:\nproject spoken=\"the garden, the beds\" active=no\nEnd.\n")
        out = apply_all(self.garden, self.top)
        self.assertEqual(out[0].status, "applied", out[0].message)
        self.assertIn("\"the beds\"", self.top.store.read("knowledge/projects.md"))
        self.assertIn("(inactive)", self.top.store.read("knowledge/projects.md"))

    def test_undo_cannot_write_outside_the_unit(self):
        """The critical review's attack: a forged ledger, then an undo that climbs out of the folder."""
        led = json.dumps({"id": "x", "state": "done", "effects": [{
            "path": "../../../../outside.txt", "unit": "self", "before": "pwned", "after": None,
            "before_sha": None, "after_sha": None}]})
        drop(self.garden, "r1.md", f"Project: garden\nChanges v1:\nknowledge evil.ledger.json\n```\n{led}\n```\nEnd.\n")
        apply_all(self.garden)
        drop(self.garden, "r2.md", "Project: garden\nChanges v1:\nundo ../../knowledge/evil\nEnd.\n")
        self.assertEqual(apply_all(self.garden)[0].status, "failed")
        self.garden.store.write("_returns/applied/forged.ledger.json", led.replace('"x"', '"forged"'))
        drop(self.garden, "r3.md", "Project: garden\nChanges v1:\nundo forged\nEnd.\n")
        out = apply_all(self.garden)
        self.assertEqual(out[0].status, "failed", out[0].message)
        self.assertRegex(out[0].message, "unsafe path|never writes")
        self.assertFalse(any(p.name == "outside.txt" for p in self.root.parent.rglob("outside.txt")))

    def test_store_refuses_climbing_paths(self):
        from collab_kit.store import StoreError
        for bad in ("../x.md", "a/../../x.md", "/etc/x", "C:/x", *(("a\\b.md",) if os.name == "nt" else ())):
            with self.subTest(bad=bad), self.assertRaises(StoreError):
                self.garden.store.write(bad, "x")

    def test_drive_alias_names(self):
        drop(self.garden, "r1.md", "Project: garden\nChanges v1:\nnew-item title=\"Alias\"\nEnd.\n")
        apply_all(self.garden)
        real = self.root / "projects/garden/collab-kit/agenda/W-001-alias.md"
        real.rename(real.with_name("W-001-alias (1).md"))     # how Drive for desktop shows it
        self.assertEqual(self.garden.item("W-001").title, "Alias")
        drop(self.garden, "r2.md", "Project: garden\nChanges v1:\nlog W-001 \"alias\" \"still works\"\nEnd.\n")
        apply_all(self.garden)
        self.assertIn("still works", (real.with_name("W-001-alias (1).md")).read_text())
        self.assertFalse(real.exists())                         # no second file under the plain name


if __name__ == "__main__":
    unittest.main()

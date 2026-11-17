"""The public example: a sanitized snapshot of Collab Kit's own project, as it would sit in a repository.

Collab Kit's own live channels (agenda, returns, status, WIP) stay in its Drive folder, out of this
public repository (W-014, decided 2026-11-15). The repository carries `examples/the-kit-itself/`
instead: the real work, sanitized, laid out exactly as `install.py project --home repo` lays out
someone else's repository. Two kinds of file live there:

- **generated:** what the installer writes (CLAUDE.md and AGENTS.md sections, hooks, skills, the
  project settings, the unit's start file and channel READMEs). The vendored engine under
  `tools/collab-kit/` is left out: it is `engine/`, byte for byte.
- **snapshot:** the unit's agenda, applied returns with their ledgers, and knowledge, copied from the
  live folder and sanitized.

    python3 tests/public_example.py check
        Fails when the generated files are not what this kit generates now, when this kit's engine
        cannot read the snapshot (an item, a return, or a ledger it would refuse), or when anything
        private is left in it. tests/test_public_example.py runs this, so CI and every release do.
    python3 tests/public_example.py refresh --from "<the project's folder in the cloud drive>" [--fill DIR]
        Takes a fresh snapshot and regenerates the rest. --fill names a folder holding copies of files
        the cloud drive lists but cannot read yet (Drive for desktop sometimes cannot fetch a file a
        phone wrote). Read the diff before committing: rules catch accounts and named private words,
        not every private thought.

Sanitizing rules come in two layers. The generic ones (accounts, local paths, Drive ids) are below and
public. The private ones (words that must never be published, and their replacements) are in a file
of the owner's that never enters a repository: `~/.config/collab-kit/public-example.toml`, or the file
named by COLLAB_KIT_EXAMPLE_RULES, plus the `deny` list of the back end's own config and the file
of words named by KIT_PRIVATE_WORDS (the list tests/dry-run-install.sh checks the whole kit against):

    deny = ["a-private-codename"]          # regexes; refresh refuses to write a snapshot containing one
    [[replace]]
    pattern = 'the a-private-codename\\s+names'   # a regex, applied before the deny check
    with = "names from a private project"

`examples/the-kit-itself/snapshot.toml` says what the snapshot leaves out and how the generated part
is made (the project's name, its spoken names, whose it is).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "engine"))

from collab_kit import returns as R                        # noqa: E402
from collab_kit.installer import install_project           # noqa: E402
from collab_kit.store import FolderStore                   # noqa: E402
from collab_kit.text import sha                            # noqa: E402
from collab_kit.unit import APPLIED, ITEM_FILE_RE, Unit    # noqa: E402

EXAMPLE = KIT / "examples" / "the-kit-itself"
UNIT = "collab-kit"                                         # the unit's folder inside the repository
SNAPSHOT_DIRS = ("agenda", "knowledge", "_returns/applied")
HAND_WRITTEN = {"README.md", "snapshot.toml"}
SKIP_PARTS = {"_versions", "WIP", ".DS_Store", "__pycache__"}
DRIVE_DUPLICATE = re.compile(r" \(\d+\)(?=\.[A-Za-z0-9]+$)")   # Drive for desktop's "name (1).md"

# Generic rules: (pattern, replacement), applied in order to every text file and every string in a ledger.
GENERIC_REPLACE = [
    (re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"), "~/"),
    (re.compile(r"GoogleDrive-[^/\s\"'`]+"), "GoogleDrive-owner@example.com"),     # Drive for desktop's folder
    (re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|net)\b)[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
     "owner@example.com"),
    (re.compile(r"(?<![A-Za-z0-9_-])1[A-Za-z0-9_-]{32}(?![A-Za-z0-9_-])"), "<drive-file-id>"),
]
# Generic deny: nothing like these may remain after the replacements.
GENERIC_DENY = [
    re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|net)\b)[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
    re.compile(r"\b(?:ghp|gho|github_pat|sk-ant|xox[bp])[-_][A-Za-z0-9_-]{10,}"),
]


# ------------------------------------------------------------------------------- rules --

def private_rules() -> tuple[list[tuple[re.Pattern, str]], list[re.Pattern], str | None]:
    """The owner's private rules, if this machine has them: (replacements, deny, where)."""
    path = Path(os.environ.get("COLLAB_KIT_EXAMPLE_RULES") or Path.home() / ".config/collab-kit/public-example.toml")
    replace, deny, where = [], [], None
    if path.is_file():
        cfg = tomllib.loads(path.read_text(encoding="utf-8"))
        replace = [(re.compile(r["pattern"], re.I), r["with"]) for r in cfg.get("replace", [])]
        deny = [re.compile(x, re.I) for x in cfg.get("deny", [])]
        where = str(path)
    words = os.environ.get("KIT_PRIVATE_WORDS")          # the list tests/dry-run-install.sh checks the kit with
    if words and Path(words).is_file():
        deny += [re.compile(x, re.I) for x in Path(words).read_text(encoding="utf-8").split("\n")
                 if x.strip() and not x.startswith("#")]
    backend = Path.home() / ".config/collab-kit/backend.toml"
    if backend.is_file():
        deny += [re.compile(x, re.I) for x in tomllib.loads(backend.read_text(encoding="utf-8"))
                 .get("backend", {}).get("deny", [])]
    return replace, deny, where


def clean(text: str, replace: list[tuple[re.Pattern, str]]) -> str:
    for rx, new in replace + GENERIC_REPLACE:
        text = rx.sub(new, text)
    return text


def clean_json(obj, replace):
    if isinstance(obj, str):
        return clean(obj, replace)
    if isinstance(obj, list):
        return [clean_json(x, replace) for x in obj]
    if isinstance(obj, dict):
        out = {k: clean_json(v, replace) for k, v in obj.items()}
        for side in ("before", "after"):              # keep the ledger true to its own effects
            if f"{side}_sha" in out and side in out:
                out[f"{side}_sha"] = None if out[side] is None else sha(out[side])
        return out
    return obj


def leaks(text: str, deny: list[re.Pattern]) -> list[str]:
    return [m.group(0)[:60] for rx in GENERIC_DENY + deny for m in rx.finditer(text)]


# ---------------------------------------------------------------- topics left out --

HEADING = re.compile(r"^(#{1,6})\s")
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
CHANGES_START = re.compile(r"^Changes v\d+:\s*$")
FIELD_LINE = re.compile(r"^([A-Z][A-Za-z' /-]{0,40}:\s|[a-z_]+\s*=\s)")   # a return's header field, or front matter


def topics(m: dict) -> list[re.Pattern]:
    """The topics the example leaves out entirely (snapshot.toml `leave_out`, case-insensitive regexes)."""
    return [re.compile(x, re.I) for x in m.get("leave_out", [])]


def mentions(text: str, tops: list[re.Pattern]) -> list[str]:
    return [m.group(0) for rx in tops for m in rx.finditer(text)]


def _fence_end(lines: list[str], i: int) -> int:
    """Index after the fenced block opening at i (closed by the same character, at least as long)."""
    mark = FENCE.match(lines[i]).group(1)
    j = i + 1
    while j < len(lines):
        m = FENCE.match(lines[j])
        if m and m.group(1)[0] == mark[0] and len(m.group(1)) >= len(mark) and not lines[j].strip()[len(m.group(1)):]:
            return j + 1
        j += 1
    return len(lines)


def drop_topics(text: str, tops: list[re.Pattern], ids: frozenset[str] = frozenset()) -> str:
    """Text less every part that mentions a topic, or names an item left out (`ids`).

    Markdown: a heading takes its section with it; a list item its indented continuation; a table row or a
    paragraph goes alone; inside a fence the same rules apply. A return's `Changes v1:` block goes change
    by change: a change line takes its fenced body with it, and a kept change keeps its body filtered."""
    idrx = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(ids))) + r")\b") if ids else None

    def hit(s: str) -> bool:
        return bool(mentions(s, tops)) or bool(idrx and idrx.search(s))

    def fenced(block: list[str]) -> list[str]:
        inner = drop_topics("\n".join(block[1:-1]), tops, ids) if len(block) > 2 else ""
        return [block[0]] + (inner.split("\n") if inner else []) + block[-1:]

    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        ln = lines[i]
        if CHANGES_START.match(ln):                         # a return's changes: one change at a time
            out.append(ln)
            i += 1
            while i < len(lines) and lines[i].strip() != "End.":
                j = i + 1
                body = None
                if j < len(lines) and FENCE.match(lines[j]):
                    k = _fence_end(lines, j)
                    body, j = lines[j:k], k
                if not hit(lines[i]):
                    out.append(lines[i])
                    if body:
                        out += fenced(body)
                i = j
            continue
        h = HEADING.match(ln)
        if h:
            if hit(ln):                                     # to the next heading at this level or above
                lvl, i = len(h.group(1)), i + 1
                while i < len(lines) and not ((m := HEADING.match(lines[i])) and len(m.group(1)) <= lvl):
                    i += 1
            else:
                out.append(ln)
                i += 1
            continue
        if FENCE.match(ln):
            j = _fence_end(lines, i)
            out += fenced(lines[i:j])
            i = j
            continue
        item = LIST_ITEM.match(ln)
        if item:
            ind, j = len(item.group(1)), i + 1
            while j < len(lines) and lines[j].strip() and (len(lines[j]) - len(lines[j].lstrip())) > ind:
                j += 1
            if not hit("\n".join(lines[i:j])):
                out += lines[i:j]
            i = j
            continue
        if not ln.strip() or ln.lstrip().startswith("|") or ln.startswith("+++") or FIELD_LINE.match(ln):
            if not (ln.strip() and hit(ln)):
                out.append(ln)
            elif FIELD_LINE.match(ln):                      # a dropped field takes its indented continuation
                while i + 1 < len(lines) and lines[i + 1].strip() and lines[i + 1][:1] in (" ", "\t"):
                    i += 1
            i += 1
            continue
        j = i + 1                                           # a paragraph
        while j < len(lines) and lines[j].strip() and not (
                HEADING.match(lines[j]) or LIST_ITEM.match(lines[j]) or lines[j].lstrip().startswith("|")
                or FENCE.match(lines[j]) or CHANGES_START.match(lines[j]) or FIELD_LINE.match(lines[j])
                or lines[j].startswith("+++")):
            j += 1
        if not hit("\n".join(lines[i:j])):
            out += lines[i:j]
        i = j
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out))


def _item_title(text: str) -> str:
    m = re.search(r'^title\s*=\s*"(.*)"', text, re.M)
    return m.group(1) if m else ""


def _return_topic(text: str) -> str:
    m = re.search(r"^Topic:\s*(.*)$", text, re.M)
    return m.group(1) if m else ""


# ------------------------------------------------------------------------- the example --

def manifest(example: Path = EXAMPLE) -> dict:
    return tomllib.loads((example / "snapshot.toml").read_text(encoding="utf-8"))


def generated(m: dict) -> dict[str, bytes]:
    """What `install.py project --home repo` writes into an empty repository, less the vendored engine."""
    with tempfile.TemporaryDirectory(prefix="ck-example-") as tmp:
        root = Path(tmp) / m["name"]
        root.mkdir()
        install_project(root, name=m["name"], unit=f"projects/{m['name']}/collab-kit", home="repo",
                        human=m["human"], about=m["about"], spoken=m["spoken"])
        out = {}
        for p in sorted(root.rglob("*")):
            rel = p.relative_to(root).as_posix()
            if p.is_file() and not (rel.startswith("tools/collab-kit/") and rel != "tools/collab-kit/project.toml"):
                out[rel] = p.read_bytes()
        return out


def is_snapshot(rel: str) -> bool:
    return any(rel.startswith(f"{UNIT}/{d}/") for d in SNAPSHOT_DIRS) and not rel.endswith("/README.md")


def check(example: Path = EXAMPLE) -> list[str]:
    """Everything wrong with the committed example, as sentences. Empty when it is current."""
    problems = []
    m = manifest(example)
    want = generated(m)
    have = {p.relative_to(example).as_posix(): p for p in example.rglob("*") if p.is_file()
            and not SKIP_PARTS.intersection(p.relative_to(example).parts)}
    for rel, data in want.items():
        if rel not in have:
            problems.append(f"{rel}: the installer writes it; the example lacks it")
        elif have[rel].read_bytes() != data:
            problems.append(f"{rel}: not what the installer writes now (refresh the example)")
    for rel in sorted(set(have) - set(want) - HAND_WRITTEN):
        if not is_snapshot(rel):
            problems.append(f"{rel}: neither generated nor part of the snapshot")
    # this kit's engine must read the snapshot as it reads a live unit
    unit = Unit(FolderStore(example / UNIT), m["name"], home="repo")
    for it in unit.items():
        if not it.fields:
            problems.append(f"{it.path}: front matter this kit cannot read")
            continue
        if it.fields.get("id") != it.id:
            problems.append(f"{it.path}: id {it.fields.get('id')!r} does not match its file name")
        if it.kind not in R.KINDS:
            problems.append(f"{it.path}: kind {it.kind!r} is not one of {', '.join(R.KINDS)}")
        if it.status not in R.STATUSES:
            problems.append(f"{it.path}: status {it.status!r} is not one of {', '.join(R.STATUSES)}")
    if unit.pending_returns():
        problems.append("_returns/ has returns waiting; the snapshot holds applied returns only")
    applied = example / UNIT / APPLIED
    for f in sorted(applied.glob("*.md")) if applied.is_dir() else []:
        try:
            ret = R.parse(f.read_text(encoding="utf-8"), f.name)
        except R.ReturnError as e:
            problems.append(f"{APPLIED}/{f.name}: this kit's grammar refuses it ({e})")
            continue
        led = applied / f"{ret.id}.ledger.json"
        if not led.is_file():
            problems.append(f"{APPLIED}/{f.name}: no ledger ({led.name})")
            continue
        d = json.loads(led.read_text(encoding="utf-8"))
        if d.get("state") != "done":
            problems.append(f"{APPLIED}/{led.name}: state {d.get('state')!r}, not done")
        for e in d.get("effects", []):
            if e.get("after") is not None and e.get("after_sha") != sha(e["after"]):
                problems.append(f"{APPLIED}/{led.name}: an effect's after_sha does not match its text")
    # nothing private, and nothing about a topic the example leaves out
    _, deny, _ = private_rules()
    tops = topics(m)
    for rel, p in sorted(have.items()):
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for hit in leaks(text, deny):
            problems.append(f"{rel}: private material ({hit!r})")
        if rel not in HAND_WRITTEN:
            for hit in sorted(set(mentions(text, tops)) | set(mentions(rel, tops))):
                problems.append(f"{rel}: mentions {hit!r}, a topic the example leaves out")
    return problems


def leave_out_topics(staged: dict[str, str], tops: list[re.Pattern]) -> list[str]:
    """Take every topic in snapshot.toml's `leave_out` out of the staged snapshot, in place: an item whose
    title is about one leaves whole, and so does a return whose topic is; every other file, and every
    before and after text in a ledger, loses the parts that mention one (drop_topics). Returns notes."""
    if not tops:
        return []
    gone_items, gone_paths, gone_returns = [], set(), []
    for rel in [r for r in staged if r.startswith("agenda/") and r.endswith(".md")]:
        if mentions(_item_title(staged[rel]), tops) and (mid := re.match(r"agenda/(W-\d+)", rel)):
            gone_items.append(mid.group(1))
            gone_paths.add(rel)
            del staged[rel]
    for rel in [r for r in staged if r.startswith(f"{APPLIED}/") and r.endswith(".md")]:
        if mentions(_return_topic(staged[rel]), tops):
            gone_returns.append(rel.rsplit("/", 1)[-1][:-3])
            del staged[rel]
            staged.pop(rel[:-3] + ".ledger.json", None)
    def n_changes(rel):
        try:
            return len(R.parse(staged[rel], rel.rsplit("/", 1)[-1]).changes)
        except R.ReturnError:
            return 0
    had = {rel: n_changes(rel) for rel in staged if rel.startswith(f"{APPLIED}/") and rel.endswith(".md")}
    ids = frozenset(gone_items)
    for rel in list(staged):
        if rel.endswith(".ledger.json"):
            led = json.loads(staged[rel])
            led["effects"] = [e for e in led.get("effects", [])
                              if DRIVE_DUPLICATE.sub("", e.get("path", "")) not in gone_paths]
            for e in led["effects"]:
                for side in ("before", "after"):
                    if isinstance(e.get(side), str):
                        e[side] = drop_topics(e[side], tops, ids)
            staged[rel] = json.dumps(led, indent=1, ensure_ascii=False) + "\n"
        elif rel.endswith(".md"):
            staged[rel] = drop_topics(staged[rel], tops, ids)
    for rel in [r for r in staged if r.startswith(f"{APPLIED}/") and r.endswith(".md")]:
        if had.get(rel) and not n_changes(rel):               # every change it made was about a topic
            gone_returns.append(rel.rsplit("/", 1)[-1][:-3])
            del staged[rel]
            staged.pop(rel[:-3] + ".ledger.json", None)
    notes = []
    if gone_items:
        notes.append("items left out (a topic in leave_out): " + ", ".join(sorted(gone_items)))
    if gone_returns:
        notes.append("returns left out (a topic in leave_out): " + ", ".join(sorted(gone_returns)))
    return notes


def refresh(src: Path, fill: Path | None = None, example: Path = EXAMPLE, require_rules: bool = True) -> list[str]:
    """Replace the example's snapshot with a sanitized copy of `src` (the live unit folder) and regenerate
    the rest. Writes nothing when anything private would remain. Returns notes for the person reviewing."""
    replace, deny, where = private_rules()
    if require_rules and not where:
        raise SystemExit("public_example: no private rules on this machine (~/.config/collab-kit/public-example.toml); "
                         "a snapshot without them may publish private words. Pass --no-private-rules to accept that.")
    m = manifest(example)
    exclude = set(m.get("exclude", []))
    staged: dict[str, str] = {}
    notes, unreadable, dropped = [], [], []
    for d in SNAPSHOT_DIRS:
        base = src / d
        for p in sorted(base.rglob("*")) if base.is_dir() else []:
            if p.is_dir() or SKIP_PARTS.intersection(p.relative_to(src).parts):
                continue
            rel = DRIVE_DUPLICATE.sub("", p.relative_to(src).as_posix())
            if rel in exclude or rel.endswith("/README.md"):
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                alt = fill / p.name if fill else None
                if alt and alt.is_file():
                    text = alt.read_text(encoding="utf-8")
                    notes.append(f"{rel}: read from {alt} (the cloud drive could not read it)")
                else:
                    unreadable.append(rel)
                    continue
            staged[rel] = text
    if unreadable:
        raise SystemExit("public_example: cannot read (supply copies with --fill DIR): " + ", ".join(unreadable))
    # a return whose effects touch a file left out would carry that file's text: leave it out too
    for rel in [r for r in staged if r.endswith(".ledger.json")]:
        led = json.loads(staged[rel])
        if any(e.get("path") in exclude for e in led.get("effects", [])):
            stem = rel[: -len(".ledger.json")]
            for r in (rel, stem + ".md"):
                staged.pop(r, None)
            dropped.append(stem.rsplit("/", 1)[-1])
    if dropped:
        notes.append("left out with the files they wrote: " + ", ".join(dropped))
    notes += leave_out_topics(staged, topics(m))
    out, found = {}, []
    for rel, text in staged.items():
        text = (json.dumps(clean_json(json.loads(text), replace), indent=1, ensure_ascii=False) + "\n"
                if rel.endswith(".json") else clean(text, replace))
        found += [f"{rel}: {h!r}" for h in leaks(text, deny)]
        found += [f"{rel}: {h!r} (a topic in leave_out)" for h in set(mentions(text, topics(m)) + mentions(rel, topics(m)))]
        out[f"{UNIT}/{rel}"] = text
    if found:
        raise SystemExit("public_example: private material remains after the rules (add a [[replace]] rule):\n  "
                         + "\n  ".join(found))
    for d in SNAPSHOT_DIRS:                                   # replace the snapshot whole
        for p in sorted((example / UNIT / d).rglob("*"), reverse=True) if (example / UNIT / d).exists() else []:
            rel = p.relative_to(example).as_posix()
            if p.is_file() and is_snapshot(rel):
                p.unlink()
    for rel, data in generated(m).items():
        p = example / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    for rel, text in out.items():
        p = example / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    notes.append(f"{len(out)} snapshot files; private rules: {where or 'none'}")
    return notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    r = sub.add_parser("refresh")
    r.add_argument("--from", dest="src", required=True, type=Path)
    r.add_argument("--fill", type=Path)
    r.add_argument("--no-private-rules", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "refresh":
        for n in refresh(a.src.expanduser(), a.fill, require_rules=not a.no_private_rules):
            print(n)
    problems = check()
    for p in problems:
        print(p)
    print("public_example: the example is current" if not problems else f"public_example: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""A stand-in for the GitHub CLI, gh, in tests: no test ever reaches GitHub or creates a repository.

It keeps its "GitHub" in the folder $FAKE_GH_ROOT: one bare git repository per created repository,
at repos/<owner>/<name>.git, and its visibility in repos/<owner>/<name>.json. Every call appends its
arguments, one JSON list per line, to $FAKE_GH_ROOT/calls.jsonl (what the tests read to check that
only expected arguments ever reached a command line).

Implemented, with gh's shapes: `repo list --json name,visibility`, `repo view <owner>/<name> --json
visibility,isEmpty` (exit 1 when there is none), `repo create <owner>/<name> --private`, `config get
git_protocol`, `auth status`, `auth git-credential` (answers nothing). Switches, as files in
$FAKE_GH_ROOT so a test can flip them between passes:

    signed-out        every command that needs GitHub fails as a signed-out gh does
    create-fails      `repo create` fails (GitHub could not be reached)
    create-public     `repo create` makes the repository public whatever was asked (a wrong answer
                      from GitHub, to prove the check after creation)
    protocol          its content is what `config get git_protocol` prints (default https)

A `repo create` with --public or --internal is never expected: it is recorded and refused.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ["FAKE_GH_ROOT"])
ROOT.mkdir(parents=True, exist_ok=True)
args = sys.argv[1:]
with open(ROOT / "calls.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\n")


def flag(name: str) -> bool:
    return (ROOT / name).exists()


def signed_in() -> None:
    if flag("signed-out"):
        print("To get started with GitHub CLI, please run:  gh auth login", file=sys.stderr)
        sys.exit(4)


def paths(slug: str) -> tuple[Path, Path]:
    owner, name = slug.split("/", 1)
    return ROOT / "repos" / owner / f"{name}.git", ROOT / "repos" / owner / f"{name}.json"


if args[:2] == ["auth", "status"]:
    signed_in()
    print("github.com\n  Logged in to github.com account example (keyring)")
elif args[:2] == ["auth", "git-credential"]:
    sys.stdin.read()
elif args[:3] == ["config", "get", "git_protocol"]:
    p = ROOT / "protocol"
    print(p.read_text().strip() if p.exists() else "https")
elif args[:2] == ["repo", "list"]:
    signed_in()
    out = []
    for meta in sorted((ROOT / "repos").glob("*/*.json")):
        out.append({"name": meta.stem, "visibility": json.loads(meta.read_text())["visibility"]})
    print(json.dumps(out))
elif args[:2] == ["repo", "view"]:
    signed_in()
    bare, meta = paths(args[2])
    if not meta.exists():
        print(f"GraphQL: Could not resolve to a Repository with the name '{args[2]}'. (repository)", file=sys.stderr)
        sys.exit(1)
    refs = subprocess.run(["git", "-C", str(bare), "for-each-ref"], capture_output=True, text=True).stdout
    print(json.dumps({"visibility": json.loads(meta.read_text())["visibility"], "isEmpty": not refs.strip()}))
elif args[:2] == ["repo", "create"]:
    signed_in()
    rest = args[2:]
    if "--private" not in rest or "--public" in rest or "--internal" in rest or len(rest) != 2:
        print("fake gh: only `repo create <owner>/<name> --private` is expected", file=sys.stderr)
        sys.exit(9)
    slug = next(a for a in rest if not a.startswith("--"))
    bare, meta = paths(slug)
    if flag("create-fails"):
        print("error connecting to api.github.com", file=sys.stderr)
        sys.exit(1)
    if meta.exists():
        print("GraphQL: Name already exists on this account (createRepository)", file=sys.stderr)
        sys.exit(1)
    bare.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    meta.write_text(json.dumps({"visibility": "PUBLIC" if flag("create-public") else "PRIVATE"}))
    print(f"https://github.com/{slug}")
else:
    print(f"fake gh: unexpected command {args}", file=sys.stderr)
    sys.exit(2)

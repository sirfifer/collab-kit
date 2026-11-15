#!/usr/bin/env python3
"""install.py: install or upgrade Collab Kit.

Standard library only (Python 3.11+).

Collab Kit 0.5:
    python3 kit/install.py machine --cloud-root "<the Collab Kit folder>" --human "Sam" [--user-hooks]
    python3 kit/install.py top "<the Collab Kit folder>" --human "Sam"      a new top level
    python3 kit/install.py project <repo> [--home cloud|repo] [--dry-run]  a project's repository

The knowledge build from 0.4 (documents split into sections, concepts, the index) is unchanged:

    python3 kit/install.py init  <project> --name "..." --slug x [--profile owner.toml] [options]
                                                                            write tools/kb/config.toml
    python3 kit/install.py apply <project> [--dry-run]                      install or upgrade
    python3 kit/install.py check <project>                                  exit 1 if apply would change anything

What apply writes (see DESIGN.md):
  engine   kit/engine/**  ->  tools/kb/**          replaced on every apply; never edited per project
  managed  kit/templates  ->  skills, agent, curator prompt, folder READMEs and templates
                              rendered from the config; replaced on every apply while the file
                              still carries its "managed by Collab Kit" line
  seed     kit/templates  ->  <out>/CLAUDE.md, <out>/README.md, tools/kb/manifest.toml
                              created once, then the project's own; only the blocks between
                              <!-- kit:start NAME --> and <!-- kit:end NAME --> are refreshed
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

KIT = Path(__file__).resolve().parent
ENGINE = KIT / "engine"
TEMPLATES = KIT / "templates"
VERSION = (KIT / "VERSION").read_text().strip()
# An owner profile (optional, private to its owner, never part of the kit) holds the defaults one
# person applies to every project: their name and pronouns, the parent folder, refused accounts,
# launchd label prefix, worktree and state locations. --profile PATH, or $KB_KIT_PROFILE.
# See examples/owner-profile.toml.

SEED = {"OUT/CLAUDE.md", "OUT/README.md", "tools/kb/manifest.toml"}
PASS_THROUGH = {"CHANGES"}              # placeholders filled at run time (nightly.sh), not here
MANAGED_RE = re.compile(r"^<!-- managed by (?:Collab Kit|the collaboration kit) .*-->\n?", re.M)  # 0.1 wording too
BLOCK_RE = re.compile(r"<!-- kit:start (?P<name>[\w-]+) -->\n.*?<!-- kit:end (?P=name) -->", re.S)
PH_RE = re.compile(r"\{\{(\w+)\}\}")


def load_engine():
    spec = importlib.util.spec_from_file_location("kit_kb", ENGINE / "kb.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["kit_kb"] = mod
    spec.loader.exec_module(mod)
    return mod


KB = load_engine()


# ------------------------------------------------------------------------------ context --

def context(cfg: dict) -> dict[str, str]:
    p, pe, kn, m, cu, sc = (cfg[k] for k in ("project", "people", "knowledge", "mirror", "curator", "schedule"))
    ex = cfg["examples"]
    tiers = cfg["tiers"]
    canon = [t["name"] for t in tiers if t.get("canon")]
    hist = [t["name"] for t in tiers if t.get("history")]
    paths = [str(x).strip("/") for x in p["author_paths"]]
    if len(paths) > 1:
        paths_md = ", ".join(f"`{x}/`" for x in paths[:-1]) + f", or `{paths[-1]}/`"
    else:
        paths_md = f"`{paths[0]}/`" if paths else "the author documents"
    folder = m["folder"]
    if m["kind"] == "google-drive" and not m["root"]:
        where = f"Google Drive in the **{m['account']}** account (`My Drive/{m['parent']}/{folder}`)"
    elif m["kind"] in ("google-drive", "folder"):
        where = f"the folder `{m['root'].rstrip('/')}/{m['parent']}/{folder}`"
    else:
        where = "nowhere yet (no mirror is configured in `tools/kb/config.toml`)"
    refuse = [r for r in m["refuse"] if r]
    state = sc["state_dir"]
    trust = []
    for t in tiers:
        what = "current truth" if t.get("canon") else ("history: never the final word" if t.get("history") else "")
        trust.append(f"- **{t['name']}**{f' ({what})' if what else ''}: {t.get('note', '')}")
    hh, mm = (str(sc["nightly"]).split(":") + ["0"])[:2]
    extra = str(p.get("rules", "")).strip()
    return {
        "kit_version": VERSION,
        "name": p["name"], "name_md": (f"{p['article']} " if p.get("article") else "") + f"**{p['name']}**",
        "short": p["short"] or p["name"], "slug": p["slug"], "repo": p["repo"],
        "spoken_md": ", ".join(f"\"{x}\"" for x in p["spoken"]),
        "parent": m["parent"], "start_file": m["start_file"],
        "preference_line": KB.preference_line(cfg),
        "about": p["about"] or "a project worked on in conversation",
        "main_branch": p["main_branch"], "content_word": p["content_word"],
        "worktree_note": p["worktree_note"],
        # Collab Kit 0.5 keeps the agenda when [knowledge].agenda is false (the knowledge build does not)
        "agenda_dir": f"{kn['out_dir']}/agenda" if kn.get("agenda", True) else "collab-kit/agenda",
        "agenda_new": ('`python3 tools/kb/kb.py new-item <kind> "<title>"`' if kn.get("agenda", True) else
                       '`tools/collab-kit/ck ask "<title>" --kind <kind>` (Collab Kit 0.5 keeps the agenda; '
                       'settle or log items with the collab-kit-return skill, never by editing them)'),
        "author_paths_md": paths_md, "author_paths_list": " ".join(paths),
        "human": pe["human"], "he": pe["he"], "him": pe["him"], "his": pe["his"],
        "assistant": pe["assistant"],
        "out": kn["out_dir"], "max_words": f"{int(kn['max_words']):,}",
        "ex_doc": ex["doc"], "ex_heading_ref": ex["heading_ref"], "ex_line_ref": ex["line_ref"],
        "ex_capture": ex["capture"], "ex_concept": ex["concept"],
        "tier_list": ", ".join(t["name"] for t in tiers),
        "canon_tiers": ", ".join(canon) or "none marked canon in config.toml",
        "history_tiers_phrase": (f"documents in the {', '.join(hist)} tier{'s' if len(hist) > 1 else ''} "
                                 "are thinking in progress and never override canon.") if hist else "",
        "trust_md": "\n".join(trust),
        "mirror_where": where, "folder_name": folder,
        "connector": "the Google Drive connector", "connector_short": "Google Drive",
        "captures_note": (
            "This project commits returns to git (`[returns].captures_in_git = true`): the integration job "
            "(`tools/kb/nightly.sh`) copies each one here exactly as it arrived. Never edited."
            if KB.captures_in_git(cfg) else
            "This project keeps returns out of git (`[returns].captures_in_git = false`): they stay in the "
            "mirror's `_returns/processed/` and are never copied here, so this folder stays empty. The "
            "repository keeps only what was made of them. The rest of this page describes the other setting."),
        "connect_as": f" **as {m['account']}**" if m["kind"] == "google-drive" and m["account"] else "",
        "refuse_note": (" Never mirrored to an account or path containing "
                        + " or ".join(f"`{r}`" for r in refuse)
                        + " (refused in `tools/kb/config.toml`)." if refuse else ""),
        "settle_minutes": str(m["settle_minutes"]),
        "curator_branch": cu["branch"],
        "project_rules": f"\n## Project rules\n\n{extra}\n" if extra else "",
        "state_dir": state,
        "label_nightly": f"{sc['label_prefix']}.{p['slug']}-kb-nightly",
        "label_returns": f"{sc['label_prefix']}.{p['slug']}-kb-returns",
        "nightly_time": f"{int(hh):02d}:{int(mm):02d}",
        "returns_minutes": str(sc["returns_every_minutes"]),
    }


def render(text: str, ctx: dict[str, str], where: str) -> str:
    missing = sorted({k for k in PH_RE.findall(text) if k not in ctx and k not in PASS_THROUGH})
    if missing:
        raise SystemExit(f"template {where}: unknown placeholder(s) {', '.join(missing)}")
    return PH_RE.sub(lambda mm: ctx.get(mm[1], mm[0]), text)


def managed_header() -> str:
    return (f"<!-- managed by Collab Kit {VERSION}: rendered from tools/kb/config.toml by "
            "kit/install.py apply. Edit the config or the kit, not this file. To make it the "
            "project's own, delete this line. -->")


def add_header(text: str) -> str:
    h = managed_header()
    if text.startswith("---\n"):
        end = text.index("\n---\n", 4) + 5
        return text[:end] + h + "\n" + text[end:]
    if text.startswith("+++\n"):
        return text.rstrip("\n") + "\n\n" + h + "\n"
    return h + "\n" + text


# ---------------------------------------------------------------------------- planning --

def target_path(rel: str, out: str) -> str:
    if rel.startswith("OUT/"):
        return f"{out}/{rel[4:]}"
    if rel.startswith("claude/"):
        return ".claude/" + rel[len("claude/"):]
    return rel


def plan(root: Path, adopt: bool = False) -> list[tuple[str, Path, str | None, str]]:
    """[(action, path, new content or None, note)] for everything apply would do."""
    cfg = KB.load_config(root)
    ctx = context(cfg)
    out = cfg["knowledge"]["out_dir"]
    steps = []

    def want(path: Path, content: str, kind: str):
        if not path.exists():
            steps.append(("create", path, content, kind))
        elif path.read_text(encoding="utf-8") != content:
            steps.append(("update", path, content, kind))

    for src in sorted(ENGINE.rglob("*")):
        if src.is_file() and "__pycache__" not in src.parts and src.name != ".DS_Store" \
                and "collab_kit" not in src.relative_to(ENGINE).parts \
                and src.name not in ("ck.py", "ck", "backend.sh"):          # 0.5's: install.py project / backend
            want(root / "tools" / "kb" / src.relative_to(ENGINE), src.read_text(encoding="utf-8"), "engine")
    want(root / "tools" / "kb" / "KIT-VERSION", VERSION + "\n", "engine")

    for src in sorted(TEMPLATES.rglob("*")):
        if not src.is_file() or src.name == ".DS_Store":
            continue
        rel = src.relative_to(TEMPLATES).as_posix()
        if rel.startswith("project/"):
            continue                                       # 0.5 project files: install.py project
        if not cfg["knowledge"].get("agenda", True) and rel.startswith(("OUT/agenda/", "OUT/_returns/")):
            continue                                       # 0.5 keeps the agenda and the inbox (collab-kit/)
        dest = root / target_path(rel, out)
        fresh = render(src.read_text(encoding="utf-8"), ctx, rel)
        if rel in SEED:
            if not dest.exists():
                steps.append(("create", dest, fresh, "seed"))
                continue
            cur = dest.read_text(encoding="utf-8")
            blocks = {mm["name"]: mm[0] for mm in BLOCK_RE.finditer(fresh)}
            new = BLOCK_RE.sub(lambda mm: blocks.get(mm["name"], mm[0]), cur)
            gone = sorted(set(blocks) - {mm["name"] for mm in BLOCK_RE.finditer(cur)})
            if new != cur:
                steps.append(("update", dest, new, "seed blocks"))
            if gone:
                steps.append(("note", dest, None, f"kit block(s) {', '.join(gone)} removed by the project; left alone"))
            continue
        content = add_header(fresh)
        if dest.exists() and not adopt and not MANAGED_RE.search(dest.read_text(encoding="utf-8")):
            if dest.read_text(encoding="utf-8") != content:
                steps.append(("note", dest, None, "owned by the project (no managed line); left alone "
                                                  "(apply --adopt to let the kit manage it)"))
            continue
        want(dest, content, "managed")
    return steps


def show(steps, root: Path, diff: bool):
    for action, path, content, note in steps:
        print(f"{action:7} {path.relative_to(root)}  ({note})")
        if diff and action == "update" and content is not None:
            old = path.read_text(encoding="utf-8").splitlines()
            for line in difflib.unified_diff(old, content.splitlines(), "current", "kit", lineterm="", n=1):
                print("        " + line)


# ---------------------------------------------------------------------------- commands --

def captures_unset(root: Path) -> bool:
    """True (after saying what to add) when the project has not chosen [returns].captures_in_git."""
    if KB.captures_in_git(KB.load_config(root)) is not None:
        return False
    print(f"error: [returns].captures_in_git is not set; {KB.CAPTURES_HELP}. Add to {root / 'tools/kb/config.toml'}:\n\n"
          "  [returns]\n  captures_in_git = true    # or false\n")
    return True


def cmd_apply(a):
    root = Path(a.project).resolve()
    if not (root / "tools" / "kb" / "config.toml").exists():
        print(f"apply: {root}/tools/kb/config.toml not found; run `install.py init` first")
        return 1
    naming = KB.naming_errors(KB.load_config(root))
    if naming:
        for e in naming:
            print(f"apply: {e}")
        return 1
    if captures_unset(root):
        return 1
    steps = plan(root, a.adopt)
    show(steps, root, a.diff)
    writes = [s for s in steps if s[0] in ("create", "update")]
    if not writes:
        print(f"apply: up to date with kit {VERSION}")
        return 0
    if a.dry_run:
        print(f"apply: dry run, {len(writes)} file(s) would change")
        return 0
    for action, path, content, kind in writes:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if kind == "engine" and path.suffix in (".py", ".sh"):
            path.chmod(0o755)
    print(f"apply: {len(writes)} file(s) written (kit {VERSION}). Next:")
    print("  python3 tools/kb/kb.py build && python3 tools/kb/kb.py check")
    if not (root / ".git").exists():
        print("  note: not a git repository; the nightly job needs one")
    return 0


GITHUB_RE = re.compile(r"github\.com[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?/*$")


def remote_visibility(root: Path) -> tuple[str, str] | None:
    """('public' | 'private' | 'unknown', url) for the origin remote, or None without one. Asks `gh`
    when it is installed (it sees private repositories too), else GitHub's public API, where a
    repository that is not public answers 404. KB_KIT_OFFLINE=1 skips the network."""
    try:
        r = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    url = r.stdout.strip()
    if r.returncode or not url:
        return None
    m = GITHUB_RE.search(url)
    if not m or os.environ.get("KB_KIT_OFFLINE"):
        return ("unknown", url)
    repo = f"{m[1]}/{m[2]}"
    if shutil.which("gh"):
        try:
            r = subprocess.run(["gh", "repo", "view", repo, "--json", "visibility", "-q", ".visibility"],
                               capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and r.stdout.strip():
                return ("public" if r.stdout.strip().upper() == "PUBLIC" else "private", url)
        except (OSError, subprocess.TimeoutExpired):
            pass
    import urllib.error
    import urllib.request
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}", headers={"User-Agent": "collab-kit"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            vis = json.loads(resp.read()).get("visibility", "public")
            return ("public" if vis == "public" else "private", url)
    except urllib.error.HTTPError as e:
        return ("private" if e.code == 404 else "unknown", url)
    except (OSError, ValueError):
        return ("unknown", url)


def warn_if_public(root: Path) -> None:
    v = remote_visibility(root)
    if v and v[0] == "public":
        print(f"warning: origin ({v[1]}) is a PUBLIC repository. Returns are committed as captures,\n"
              "  exactly as they arrived (often dictated words), with the curator's responses, proposals and\n"
              "  agenda items. Pushing them publishes them. Keep this repository private, or keep the curator\n"
              "  branch and the knowledge folder's captures off any public remote (README: \"What becomes visible\").")


def cmd_check(a):
    root = Path(a.project).resolve()
    naming = KB.naming_errors(KB.load_config(root))
    for e in naming:
        print(f"error: {e}")
    unset = captures_unset(root)
    steps = [s for s in plan(root) if s[0] in ("create", "update")]
    show(steps, root, False)
    warn_if_public(root)
    sched, swarn = KB.scheduled_report(KB.load_config(root))
    for ln in sched:
        print(f"scheduled: {ln}")
    for w in swarn:
        print(f"warning: {w}")
    if not steps and not naming and not unset:
        print("kit check: OK")
        return 0
    print(f"kit check: FAILED ({len(naming)} naming error(s), {len(steps)} file(s) differ from kit {VERSION}"
          f"{', [returns].captures_in_git not set' if unset else ''})")
    return 1


def toml_str(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(toml_str(x) for x in v) + "]"
    s = str(v)
    if "\n" in s:
        return '"""\n' + s.strip("\n") + '\n"""'
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def cmd_init(a):
    root = Path(a.project).resolve()
    dest = root / "tools" / "kb" / "config.toml"
    if dest.exists():
        print(f"init: {dest} already exists; edit it, then run apply")
        return 1
    if a.captures_in_git is None:
        print("init: choose whether returns are committed to git: --captures-in-git yes, or --captures-in-git no.\n"
              "  yes: every return is committed as a capture, in the exact words it arrived with (often dictated);\n"
              "       kept with the project, and published if the repository is public.\n"
              "  no:  returns stay only in Drive (_returns/processed/); the repository gets what was made of them\n"
              "       (concepts, answers, responses, agenda items), never the returns themselves.\n"
              "  There is no default (README: \"What becomes visible, and to whom\").")
        return 2
    prof_path = a.profile or os.environ.get("KB_KIT_PROFILE", "")
    if prof_path and not Path(prof_path).expanduser().is_file():
        print(f"init: owner profile {prof_path} not found")
        return 2
    prof = tomllib.loads(Path(prof_path).expanduser().read_text(encoding="utf-8")) if prof_path else {}
    P = lambda t, k, d=None: (prof.get(t) or {}).get(k, d)  # noqa: E731
    repo, how, _ = KB.repo_identity(root)
    if a.mirror == "google-drive" and not a.drive_account:
        print("init: --drive-account is required for a Google Drive mirror (name the account "
              "explicitly; ask the owner which one if the project might have its own)")
        return 2
    if a.mirror == "folder" and not a.mirror_root:
        print("init: --mirror-root is required with --mirror folder (the folder that holds the parent)")
        return 2
    refuse = a.refuse if a.refuse is not None else P("mirror", "refuse", [])
    acct = a.drive_account or ""
    if any(r and r in acct for r in refuse):
        print(f"init: {acct} matches a refused account ({', '.join(refuse)})")
        return 2
    pron = (a.pronouns or "/".join(P("people", "pronouns", ["they", "them", "their"]))).split("/")
    parent = a.parent or P("mirror", "parent", KB.DEFAULTS["mirror"]["parent"])
    sections = {
        "project": {
            "name": a.name, "article": a.article or "", "short": a.short or a.name, "slug": a.slug, "about": a.about or "",
            "spoken": list(dict.fromkeys([a.short or a.name, *(a.spoken or [])])),
            "main_branch": a.main_branch,
            "author_paths": a.author_path or ["docs"],
            "content_word": a.content_word,
            "worktree_note": P("project", "worktree_note", KB.DEFAULTS["project"]["worktree_note"]),
            "rules": "",
        },
        "people": {"human": a.human or P("people", "human", "the owner"), "pronouns": pron,
                   "assistant": "Claude"},
        "knowledge": {"out_dir": a.out_dir, "max_words": 1800},
        "returns": {"captures_in_git": a.captures_in_git == "yes"},
        "mirror": {"kind": a.mirror, "account": acct,
                   "account_aliases": a.drive_alias or P("mirror", "account_aliases_for", {}).get(acct, []),
                   "parent": parent, "root": a.mirror_root or "", "refuse": refuse,
                   "settle_minutes": 15},
        "curator": {"branch": "wt/kb-curator", "timeout": 2700,
                    "worktree": P("curator", "worktree", "")},
        "schedule": {"label_prefix": a.label_prefix or P("schedule", "label_prefix", "local.kb"),
                     "nightly": a.nightly, "returns_every_minutes": 20,
                     "state_dir": P("schedule", "state_dir", "")},
    }
    lines = [f"# tools/kb/config.toml: settings for Collab Kit in {a.name}.",
             f"# The knowledge folder in the mirror is <parent>/{repo}: always the repository's name",
             f"# ({how}), never set here.",
             "# Everything that differs between projects lives here. After editing, run",
             "#   python3 <kit>/install.py apply .   (re-renders the kit-managed files)",
             "#   python3 tools/kb/kb.py build && python3 tools/kb/kb.py check",
             "# What each setting does: the kit's DESIGN.md, \"The config surface\".", ""]
    for sec, vals in sections.items():
        lines.append(f"[{sec}]")
        lines += [f"{k} = {toml_str(v)}" for k, v in vals.items()]
        lines.append("")
    lines += ["# Document tiers, in index order. canon = current truth; history = thinking in progress",
              "# (marked in section headers, ranked lower by `find`). Edit freely; the manifest's tiers must match.", ""]
    for t in KB.DEFAULT_TIERS:
        lines.append("[[tiers]]")
        lines += [f"{k} = {toml_str(v)}" for k, v in t.items()]
        lines.append("")
    text = "\n".join(lines)
    tomllib.loads(text)                       # never write a config that does not parse
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    print(f"init: wrote {dest.relative_to(root)} (knowledge folder: {parent}/{repo}). "
          f"Review it, then: python3 {Path(__file__)} apply {root}")
    warn_if_public(root)
    return 0


# ------------------------------------------------------------------------ Collab Kit 0.5 --

def _v05():
    sys.path.insert(0, str(ENGINE))
    from collab_kit import installer
    return installer


def cmd_project(a):
    inst = _v05()
    plan = inst.install_project(Path(a.project), name=a.name, unit=a.unit, home=a.home, human=a.human,
                                python=a.python, dry=a.dry_run, about=a.about or "", spoken=a.spoken or "")
    print(f"project {Path(a.project).resolve()}{' (dry run)' if a.dry_run else ''}:")
    plan.show()
    if a.check:
        return 1 if plan.steps and any(not w.startswith("keep ") for w, _ in plan.steps) else 0
    return 0


def cmd_machine(a):
    inst = _v05()
    plan = inst.install_machine(cloud_root=a.cloud_root, human=a.human, kit_source=a.kit_source,
                                user_hooks=a.user_hooks, python=a.python, dry=a.dry_run)
    print(f"machine{' (dry run)' if a.dry_run else ''}:")
    plan.show()
    return 0


def cmd_top(a):
    inst = _v05()
    plan = inst.install_top(Path(a.folder).expanduser(), human=a.human, dry=a.dry_run)
    print(f"top level {a.folder}{' (dry run)' if a.dry_run else ''}:")
    plan.show()
    return 0


def cmd_migrate(a):
    inst = _v05()
    from collab_kit import migrate
    steps = migrate.migrate_repo(Path(a.project), dry=a.dry_run)
    print(f"migrate {Path(a.project).resolve()} from 0.4 to 0.5{' (dry run)' if a.dry_run else ''}:")
    for st in steps:
        print(f"  {st}")
    if not a.dry_run:
        print("next: python3 install.py project <repo> --home repo; python3 tools/kb/kb.py build && "
              "python3 tools/kb/kb.py check; review and commit")
    return 0


def cmd_backend(a):
    inst = _v05()
    return inst.install_backend(Path(a.config).expanduser() if a.config else None, cloud=a.cloud,
                                human=a.human, apply=a.apply)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    mg = sub.add_parser("migrate-04", help="0.5: move a 0.4 project's repository to the 0.5 layout")
    mg.add_argument("project")
    mg.add_argument("--dry-run", action="store_true")
    mg.set_defaults(fn=cmd_migrate)
    be = sub.add_parser("backend", help="0.5: set up this machine as the back end (config, then the schedule)")
    be.add_argument("--config", help="the back end's TOML (default <config dir>/backend.toml)")
    be.add_argument("--cloud", help="for a new config: the Collab Kit folder (path, or rclone:remote:path)")
    be.add_argument("--human")
    be.add_argument("--apply", action="store_true", help="write and load the schedule (default: show it)")
    be.set_defaults(fn=cmd_backend)
    pr = sub.add_parser("project", help="0.5: install or upgrade Collab Kit in a project's repository")
    pr.add_argument("project")
    pr.add_argument("--name", help="the project's folder name (default: the repository's folder name)")
    pr.add_argument("--unit", help="the unit inside the Collab Kit folder (default projects/<name>/collab-kit)")
    pr.add_argument("--home", choices=["cloud", "repo"], help="where the project's channels live (default cloud)")
    pr.add_argument("--human", help="who the agenda waits on (default: the machine config's human)")
    pr.add_argument("--about", help="--home repo: one sentence for the unit's start file (what the project is)")
    pr.add_argument("--spoken", help="--home repo: what the person calls it, comma-separated")
    pr.add_argument("--python", default="python3", help=argparse.SUPPRESS)
    pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--check", action="store_true", help="with --dry-run: exit 1 if anything would change")
    pr.set_defaults(fn=cmd_project)
    m = sub.add_parser("machine", help="0.5: this machine's settings (and optional user-level hooks)")
    m.add_argument("--cloud-root", help="the Collab Kit folder as this machine sees it (a path, or rclone:remote:path)")
    m.add_argument("--human", help="the person conversations work with")
    m.add_argument("--kit-source", help="where the newest kit is checked out (default: this kit)")
    m.add_argument("--user-hooks", action="store_true",
                   help="add user-level hooks to ~/.claude/settings.json for sessions started in a parent folder")
    m.add_argument("--python", default="python3")
    m.add_argument("--dry-run", action="store_true")
    m.set_defaults(fn=cmd_machine)
    t = sub.add_parser("top", help="0.5: create the top level in a new Collab Kit folder (never overwrites)")
    t.add_argument("folder")
    t.add_argument("--human", required=True)
    t.add_argument("--dry-run", action="store_true")
    t.set_defaults(fn=cmd_top)
    i = sub.add_parser("init", help="write tools/kb/config.toml for a project")
    i.add_argument("project")
    i.add_argument("--name", required=True, help="the project's name in prose")
    i.add_argument("--slug", required=True, help="short id: state folder, launchd labels (e.g. garden)")
    i.add_argument("--short", help="what you call the project when you talk or write: \"let's work on the <short>\"")
    i.add_argument("--spoken", action="append",
                   help="another way you say the project's name (repeatable; listed in the parent's start file)")
    i.add_argument("--profile", help="an owner profile TOML (default $KB_KIT_PROFILE; see examples/owner-profile.toml)")
    i.add_argument("--about", help="one clause: what the project is")
    i.add_argument("--article", help="'the' when the name reads with one (\"working on the <name>\")")
    i.add_argument("--human", help="the person the agenda waits on (profile default)")
    i.add_argument("--pronouns", help="he/him/his, she/her/her, they/them/their (profile default)")
    i.add_argument("--author-path", action="append", help="authored content folder (repeatable; default docs)")
    i.add_argument("--content-word", default="project", help="as in \"<word> content\"")
    i.add_argument("--main-branch", default="main")
    i.add_argument("--out-dir", default="knowledge")
    i.add_argument("--mirror", choices=["google-drive", "folder", "none"], default="google-drive")
    i.add_argument("--drive-account", help="the Google account, named explicitly (required for google-drive)")
    i.add_argument("--drive-alias", action="append", help="another address of the same account")
    i.add_argument("--parent", help="the folder holding every project's knowledge folder (profile default, "
                                    f"else {KB.DEFAULTS['mirror']['parent']!r})")
    i.add_argument("--mirror-root", help="the local folder that holds the parent (required for --mirror folder)")
    i.add_argument("--refuse", action="append", help="substring a mirror may never contain (profile default)")
    i.add_argument("--label-prefix", help="launchd label prefix (profile default)")
    i.add_argument("--nightly", default="02:30", help="time of the daily run, HH:MM")
    i.add_argument("--captures-in-git", choices=["yes", "no"],
                   help="REQUIRED, no default: yes = returns are committed to git as captures; no = they stay in Drive only")
    i.set_defaults(fn=cmd_init)
    p = sub.add_parser("apply", help="install or upgrade the kit in a project")
    p.add_argument("project")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--diff", action="store_true", help="show diffs for updated files")
    p.add_argument("--adopt", action="store_true",
                   help="let the kit manage existing files that lack the managed line (migration; "
                        "run with --dry-run --diff first)")
    p.set_defaults(fn=cmd_apply)
    c = sub.add_parser("check", help="exit 1 if apply would change anything")
    c.add_argument("project")
    c.set_defaults(fn=cmd_check)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())

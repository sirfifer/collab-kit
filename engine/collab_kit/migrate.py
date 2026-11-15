"""Moving a project from Collab Kit 0.4 to 0.5 (DESIGN-0.5 section 15), in its repository.

    0.4                                   0.5
    knowledge/                     ->     collab-kit/knowledge/      (the knowledge build's out_dir)
    knowledge/agenda/W-*.md        ->     collab-kit/agenda/W-*.md   (kept by the 0.5 engine)
    knowledge/captures/            ->     collab-kit/knowledge/captures/ (unchanged otherwise)
    tools/kb/config.toml           ->     out_dir changed; [knowledge].agenda = false
    tools/kb/manifest.toml         ->     knowledge/ paths rewritten

Agenda items change meaning in two fields: importance runs the other way (0.4: 4 critical ... 1 low;
0.5: 1 highest ... 5 lowest) and "done" becomes "settled". Their generated blocks are dropped (the
0.4 build wrote them; nothing keeps them current any more). Every other field is kept.

Refuses while the 0.4 curator branch has work that never reached the main branch, while the
working tree is not clean, or while the 0.4 scheduled jobs are loaded. Everything is a `git mv` or
an edit in the working tree, so the result is reviewed and committed like any other change.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from .text import split_front_matter, set_front_matter, join_front_matter

IMPORTANCE_04_TO_05 = {4: 1, 3: 2, 2: 3, 1: 4}
GEN_RE = re.compile(r"\n*<!-- kb:generated:start.*?<!-- kb:generated:end -->\n*", re.S)


def _git(root: Path, *args, check=True) -> str:
    res = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if check and res.returncode != 0:
        raise SystemExit(f"migrate: git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout


def convert_item(text: str) -> str:
    fields, raw, body = split_front_matter(text)
    if not raw:
        return text
    changes = {}
    imp = fields.get("importance")
    if isinstance(imp, int) and imp in IMPORTANCE_04_TO_05 and "scale" not in fields:
        changes["importance"] = IMPORTANCE_04_TO_05[imp]
    if fields.get("status") == "done":
        changes["status"] = "settled"
    for k in ("due", "project"):
        if k not in fields:
            changes[k] = ""
    raw = set_front_matter(raw, changes) if changes else raw
    body = GEN_RE.sub("\n", body).rstrip("\n") + "\n"
    return join_front_matter(raw, body)


def _set_toml_key(text: str, table: str, key: str, value: str) -> str:
    """Set key = value inside [table] (adding it at the table's end if missing)."""
    m = re.search(rf"^\[{re.escape(table)}\]\s*$", text, re.M)
    if not m:
        return text.rstrip("\n") + f"\n\n[{table}]\n{key} = {value}\n"
    nxt = re.search(r"^\[", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    section = text[m.end():end]
    if re.search(rf"^{re.escape(key)}\s*=", section, re.M):
        section = re.sub(rf"^{re.escape(key)}\s*=.*$", f"{key} = {value}", section, count=1, flags=re.M)
    else:
        section = section.rstrip("\n") + f"\n{key} = {value}\n\n"
    return text[: m.end()] + section + text[end:]


def migrate_repo(root: Path, *, dry: bool = False, label_prefix: str | None = None) -> list[str]:
    import tomllib
    root = root.resolve()
    steps: list[str] = []
    cfgp = root / "tools" / "kb" / "config.toml"
    if not cfgp.is_file():
        raise SystemExit(f"migrate: {cfgp} not found (not a 0.4 install)")
    cfg = tomllib.loads(cfgp.read_text(encoding="utf-8"))
    out = cfg.get("knowledge", {}).get("out_dir", "knowledge").strip("/")
    if out.startswith("collab-kit/"):
        raise SystemExit("migrate: already on the 0.5 layout")
    if _git(root, "status", "--porcelain", "--untracked-files=no").strip():
        raise SystemExit("migrate: the working tree has uncommitted changes; commit or move them first")
    branch = cfg.get("curator", {}).get("branch", "")
    main = cfg.get("project", {}).get("main_branch", "main")
    if branch and _git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False).strip():
        ahead = _git(root, "rev-list", "--count", f"{main}..{branch}", check=False).strip()
        if ahead and ahead != "0":
            raise SystemExit(f"migrate: the 0.4 curator branch {branch} has {ahead} commit(s) not on {main}; "
                             f"merge or drop them first")
    if sys.platform == "darwin":
        slug = cfg.get("project", {}).get("slug", "")
        prefix = label_prefix or cfg.get("schedule", {}).get("label_prefix", "")
        import os
        for job in (f"{prefix}.{slug}-kb-nightly", f"{prefix}.{slug}-kb-returns"):
            res = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{job}"], capture_output=True)
            if res.returncode == 0:
                raise SystemExit(f"migrate: the 0.4 job {job} is loaded; unload it first: "
                                 f"launchctl bootout gui/{os.getuid()}/{job}")
    src, dst = root / out, root / "collab-kit"
    if (dst / "knowledge").exists() or (dst / "agenda").exists():
        raise SystemExit("migrate: collab-kit/knowledge or collab-kit/agenda already exists")

    def mv(a: Path, b: Path):
        steps.append(f"git mv {a.relative_to(root)} {b.relative_to(root)}")
        if not dry:
            b.parent.mkdir(parents=True, exist_ok=True)
            _git(root, "mv", str(a), str(b))
    if (src / "agenda").is_dir():
        mv(src / "agenda", dst / "agenda")
    mv(src, dst / "knowledge")
    adir = (dst / "agenda") if not dry else (src / "agenda")
    if adir.is_dir():
        for p in sorted(adir.glob("W-*.md")):
            new = convert_item(p.read_text(encoding="utf-8"))
            if new != p.read_text(encoding="utf-8"):
                steps.append(f"convert {p.name} (importance scale, done -> settled, generated block dropped)")
                if not dry:
                    p.write_text(new, encoding="utf-8")
        for gen in ("00-AGENDA.md", "01-HOW-ITEMS-ARE-KEPT.md"):
            if (adir / gen).is_file():
                steps.append(f"git rm agenda/{gen} (the 0.4 build's; 0.5 lists the folder and generates 00-PRESSING.md)")
                if not dry:
                    _git(root, "rm", "-q", "-f", str(adir / gen))
    text = cfgp.read_text(encoding="utf-8")
    new = _set_toml_key(text, "knowledge", "out_dir", '"collab-kit/knowledge"')
    new = _set_toml_key(new, "knowledge", "agenda", "false   # the agenda is collab-kit/agenda/, kept by Collab Kit 0.5")
    steps.append("tools/kb/config.toml: out_dir = collab-kit/knowledge, agenda = false")
    if not dry:
        cfgp.write_text(new, encoding="utf-8")
    man = root / "tools" / "kb" / "manifest.toml"
    if man.is_file():
        mt = man.read_text(encoding="utf-8")
        mt2 = re.sub(rf'(pattern\s*=\s*"){re.escape(out)}/', r"\1collab-kit/knowledge/", mt)
        mt2 = re.sub(rf'^(out_dir\s*=\s*"){re.escape(out)}(")', r"\1collab-kit/knowledge\2", mt2, flags=re.M)
        if mt2 != mt:
            steps.append("tools/kb/manifest.toml: collection patterns now under collab-kit/knowledge/")
            if not dry:
                man.write_text(mt2, encoding="utf-8")
    codes = root / "tools" / "kb" / "collection-codes.json"
    if codes.is_file():
        import json
        data = json.loads(codes.read_text(encoding="utf-8"))
        moved = {pre: {(f"collab-kit/knowledge/{k[len(out) + 1:]}" if k.startswith(out + "/") else k): v
                       for k, v in m.items()} for pre, m in data.items()}
        if moved != data:
            steps.append("tools/kb/collection-codes.json: permanent codes follow their files to collab-kit/knowledge/")
            if not dry:
                codes.write_text(json.dumps(moved, indent=1) + "\n", encoding="utf-8")
    start = (dst / "knowledge" / "CLAUDE.md") if not dry else (src / "CLAUDE.md")
    if start.is_file():
        steps.append("knowledge/CLAUDE.md: a note that the unit's start file and agenda moved")
        if not dry:
            t = start.read_text(encoding="utf-8")
            note = ("> **Collab Kit 0.5:** this project's start file is `../00-START-HERE.md`, and its agenda is "
                    "`../agenda/` (one file per item; change items by filing a return). This page describes the "
                    "knowledge in this folder.\n\n")
            if "Collab Kit 0.5:" not in t:
                start.write_text(note + t, encoding="utf-8")
    return steps

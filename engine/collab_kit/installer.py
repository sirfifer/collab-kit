"""Installing Collab Kit 0.5: into a project's repository, onto a machine, and as a new top level.

project  <repo>   tools/collab-kit/ (the engine, vendored; project.toml created once), the Collab
                  Kit section of CLAUDE.md and AGENTS.md, the hooks in .claude/settings.json, the
                  collab-kit skills, and (when the repository is the project's home) collab-kit/.
machine           the machine's config (where the Collab Kit folder is, whose it is, where the kit
                  is), and optionally the user-level hooks that brief sessions started in a parent
                  folder (~/dev) the first time they touch a Collab Kit project.
top <folder>      the top level's start file and channels in a new Collab Kit folder.

Every step is idempotent and shown before it is done (--dry-run). Nothing the project owns is
overwritten: managed files carry a "managed by Collab Kit" line, and CLAUDE.md / AGENTS.md change
only between their collab-kit markers.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

from . import config as C
from . import kit_version
from .templates import replace_block

ENGINE_DIR = Path(__file__).resolve().parent            # engine/collab_kit
KIT = ENGINE_DIR.parent.parent                           # the kit checkout
PROJECT_TEMPLATES = KIT / "templates" / "project"
MANAGED_LINE = "<!-- managed by Collab Kit {v}: replaced on upgrade; delete this line to make the file your own -->"
MANAGED_RE = re.compile(r"^<!-- managed by Collab Kit [^>]*-->\n?", re.M)
HOOK_MARK = "tools/collab-kit/ck"
USER_HOOK_MARK = "collab-kit-machine"
BLOCK_NAME = "agents"


class Plan:
    def __init__(self, root: Path, dry: bool):
        self.root, self.dry, self.steps = root, dry, []

    def write(self, rel: str, text: str, why: str) -> None:
        p = self.root / rel
        old = p.read_text(encoding="utf-8") if p.is_file() else None
        if old == text:
            return
        self.steps.append((("create " if old is None else "update ") + rel, why))
        if not self.dry:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)

    def note(self, what: str, why: str = "") -> None:
        self.steps.append((what, why))

    def show(self, out=sys.stdout) -> None:
        for what, why in self.steps:
            print(f"  {what}" + (f"  ({why})" if why else ""), file=out)
        if not self.steps:
            print("  nothing to change", file=out)


def _render(text: str, ctx: dict) -> str:
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(ctx.get(m.group(1), m.group(0))), text)


def _managed(text: str) -> str:
    """Put the managed line after a skill's front matter (or at the top)."""
    line = MANAGED_LINE.format(v=kit_version())
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[: end + 5] + line + "\n" + text[end + 5:]
    return line + "\n" + text


EXECUTABLE = {"tools/collab-kit/ck"}


def _engine_files() -> dict[str, bytes]:
    files = {"tools/collab-kit/ck.py": (ENGINE_DIR.parent / "ck.py").read_bytes(),
             "tools/collab-kit/ck": (ENGINE_DIR.parent / "ck").read_bytes()}
    for p in sorted(ENGINE_DIR.rglob("*")):
        if p.is_dir() or "__pycache__" in p.parts or p.suffix in (".pyc",):
            continue
        rel = p.relative_to(ENGINE_DIR).as_posix()
        if rel in ("installer.py", "backend.py"):
            continue                       # the back end and the installer stay in the kit
        files[f"tools/collab-kit/collab_kit/{rel}"] = p.read_bytes()
    files["tools/collab-kit/collab_kit/VERSION"] = (kit_version() + "\n").encode()
    return files


def merge_hooks(settings: dict, command_for: dict[str, str], mark: str, matcher: dict[str, str] | None = None) -> dict:
    """Add (or refresh) our hook command per event, leaving every other hook alone."""
    hooks = settings.setdefault("hooks", {})
    for event, cmd in command_for.items():
        groups = hooks.setdefault(event, [])
        for g in groups:
            g["hooks"] = [h for h in g.get("hooks", []) if mark not in h.get("command", "")]
        groups[:] = [g for g in groups if g.get("hooks")]
        entry = {"hooks": [{"type": "command", "command": cmd, "timeout": 30}]}
        if matcher and event in matcher:
            entry["matcher"] = matcher[event]
        groups.append(entry)
    return settings


def remove_hooks(settings: dict, mark: str) -> dict:
    for event, groups in list(settings.get("hooks", {}).items()):
        for g in groups:
            g["hooks"] = [h for h in g.get("hooks", []) if mark not in h.get("command", "")]
        settings["hooks"][event] = [g for g in groups if g.get("hooks")]
        if not settings["hooks"][event]:
            del settings["hooks"][event]
    return settings


def _block_into(path: Path, block: str, title: str, plan: Plan, rel: str) -> None:
    body = f"<!-- collab-kit:begin {BLOCK_NAME} -->\n{block.strip()}\n<!-- collab-kit:end {BLOCK_NAME} -->"
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    if old is None:
        new = f"# {title}\n\n{body}\n"
    else:
        new = replace_block(old, BLOCK_NAME, block.strip())
        if new is None:
            new = old.rstrip("\n") + "\n\n" + body + "\n"
    plan.write(rel, new, "the Collab Kit section (only the text between its markers is the kit's)")


def install_project(root: Path, *, name: str | None = None, unit: str | None = None, home: str | None = None,
                    human: str | None = None, python: str = "", dry: bool = False) -> Plan:
    root = root.resolve()
    plan = Plan(root, dry)
    pfile = root / C.PROJECT_FILE
    if pfile.is_file():
        cfg = C.project(root)
        name = name or cfg["project"]["name"]
        unit = unit or cfg["project"]["unit"]
        home = home or cfg["project"]["home"]
    else:
        name = name or root.name
        unit = unit or f"projects/{name}/collab-kit"
        home = home or "cloud"
        plan.write(C.PROJECT_FILE.as_posix(),
                   f"# Collab Kit settings for this repository (the project's own; never replaced on upgrade).\n"
                   f"[project]\nname = \"{name}\"\nunit = \"{unit}\"\nhome = \"{home}\"   # \"cloud\" or \"repo\"\n\n"
                   f"[session]\nstop_check = true   # ask once before a session ends without recording anything\n",
                   "the project's settings, created once")
    human = human or C.machine().get("human") or "the owner"
    ctx = {"name": name, "human": human, "kit_version": kit_version()}
    # 1. the engine, vendored (byte-identical in every project)
    wanted = _engine_files()
    for rel, data in wanted.items():
        p = root / rel
        if not p.is_file() or p.read_bytes() != data:
            plan.note(("update " if p.is_file() else "create ") + rel, "the kit's engine")
            if not dry:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
        if rel in EXECUTABLE and not dry and os.name != "nt":
            p.chmod(0o755)
    eng = root / "tools" / "collab-kit" / "collab_kit"
    if eng.is_dir():
        for p in sorted(eng.rglob("*")):
            rel = p.relative_to(root).as_posix()
            if p.is_file() and rel not in wanted and "__pycache__" not in p.parts:
                plan.note(f"remove {rel}", "no longer part of the kit")
                if not dry:
                    p.unlink()
    # 2. CLAUDE.md and AGENTS.md
    block = _render((PROJECT_TEMPLATES / "claude-block.md").read_text(encoding="utf-8"), ctx)
    claude = root / "CLAUDE.md"
    imports_agents = claude.is_file() and re.search(r"^@AGENTS\.md\s*$", claude.read_text(encoding="utf-8"), re.M)
    if not imports_agents:
        _block_into(claude, block, name, plan, "CLAUDE.md")
    _block_into(root / "AGENTS.md", block, name, plan, "AGENTS.md")
    # 3. hooks
    sp = root / ".claude" / "settings.json"
    settings = json.loads(sp.read_text(encoding="utf-8")) if sp.is_file() else {}
    before = json.dumps(settings, sort_keys=True)
    cmd = 'sh "$CLAUDE_PROJECT_DIR/tools/collab-kit/ck" hook {}'
    merge_hooks(settings, {"SessionStart": cmd.format("session-start"), "Stop": cmd.format("stop")}, HOOK_MARK,
                matcher={"SessionStart": "startup|resume|clear|compact"})
    if json.dumps(settings, sort_keys=True) != before or not sp.is_file():
        plan.write(".claude/settings.json", json.dumps(settings, indent=2) + "\n",
                   "the session-start brief and the once-per-session check (other settings kept)")
    # 4. skills
    for sk in sorted((PROJECT_TEMPLATES / "skills").iterdir()):
        src = sk / "SKILL.md"
        rel = f".claude/skills/{sk.name}/SKILL.md"
        dest = root / rel
        if dest.is_file() and not MANAGED_RE.search(dest.read_text(encoding="utf-8")):
            plan.note(f"keep {rel}", "the project's own (no managed line)")
            continue
        plan.write(rel, _managed(_render(src.read_text(encoding="utf-8"), ctx)), "a Collab Kit skill")
    # 5. the repository's own collab-kit/, when it is the project's home
    if home == "repo":
        from .templates import project_start_file, returns_readme, set_human
        set_human(human)
        base = "collab-kit"
        if not (root / base / "00-START-HERE.md").is_file():
            plan.write(f"{base}/00-START-HERE.md", project_start_file(name, "", name, home="repo"), "the unit's start file")
        for rel, text in ((f"{base}/_returns/README.md", returns_readme(name)),
                          (f"{base}/knowledge/README.md", f"# {name}\n\nWhat this project knows.\n"),
                          (f"{base}/agenda/README.md", "# Agenda\n\nOne file per item (`W-NNN-...`). Change items by filing a return.\n")):
            if not (root / rel).is_file():
                plan.write(rel, text, "a channel of the unit")
    return plan


# ---------------------------------------------------------------------------- machine --

def data_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "collab-kit"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "collab-kit"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "collab-kit"


def install_machine(*, cloud_root: str | None, human: str | None, kit_source: str | None,
                    user_hooks: bool, python: str = "python3", dry: bool = False,
                    claude_settings: Path | None = None) -> Plan:
    cfgp = C.machine_file()
    plan = Plan(cfgp.parent, dry)
    cfg = C.load_toml(cfgp)
    human = human or cfg.get("human") or "the owner"
    cloud_root = cloud_root or cfg.get("cloud", {}).get("root", "")
    kit_source = kit_source or cfg.get("kit", {}).get("source", "") or str(KIT)
    text = ("# Collab Kit, this machine (see the kit's engine/collab_kit/config.py)\n"
            f"human = {json.dumps(human)}\n\n[cloud]\nroot = {json.dumps(cloud_root)}\n\n"
            f"[kit]\nsource = {json.dumps(kit_source)}\n")
    plan.write(cfgp.name, text, "this machine's settings")
    if user_hooks:
        eng = data_dir() / "engine"
        files = {k.replace("tools/collab-kit/", ""): v for k, v in _engine_files().items()}
        changed = any(not (eng / k).is_file() or (eng / k).read_bytes() != v for k, v in files.items())
        if changed:
            plan.note(f"copy the engine to {eng}", "for the user-level hooks")
            if not dry:
                if eng.exists():
                    shutil.rmtree(eng)
                for k, v in files.items():
                    (eng / k).parent.mkdir(parents=True, exist_ok=True)
                    (eng / k).write_bytes(v)
        sp = claude_settings or Path.home() / ".claude" / "settings.json"
        settings = json.loads(sp.read_text(encoding="utf-8")) if sp.is_file() else {}
        before = json.dumps(settings, sort_keys=True)
        ck = f'sh "{(eng / "ck").as_posix()}"'
        merge_hooks(settings, {"PostToolUse": f"{ck} hook touch  # {USER_HOOK_MARK}",
                               "Stop": f"{ck} hook stop  # {USER_HOOK_MARK}",
                               "SessionStart": f"{ck} hook session-start  # {USER_HOOK_MARK}"}, USER_HOOK_MARK,
                    matcher={"PostToolUse": "Read|Edit|Write|MultiEdit|NotebookEdit",
                             "SessionStart": "compact|clear"})
        if json.dumps(settings, sort_keys=True) != before:
            plan.note(f"update {sp}", "user-level hooks: brief a session the first time it touches a Collab Kit project")
            if not dry:
                sp.parent.mkdir(parents=True, exist_ok=True)
                if sp.is_file():
                    shutil.copy2(sp, sp.with_suffix(".json.before-collab-kit"))
                sp.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return plan


# -------------------------------------------------------------------------------- top --

def install_top(folder: Path, *, human: str, dry: bool = False) -> Plan:
    from .templates import returns_readme, set_human, top_start_file
    set_human(human)
    plan = Plan(folder, dry)
    seeds = {"00-START-HERE.md": top_start_file(),
             "_returns/README.md": returns_readme("the top level").replace("`Project: the top level`", "`Project: top`"),
             "agenda/README.md": "# Agenda\n\nOne file per item (`W-NNN-...`); see the start file.\n",
             "WIP/README.md": "# WIP\n\nCheckpoint notes between saves; see the start file.\n",
             "knowledge/projects.md": ("# Projects\n\nRead this before starting a project (is it new? is the name taken?).\n\n"
                                       "| Folder | Say | What it is | Home |\n|---|---|---|---|\n"),
             "knowledge/status.md": ("# What is going on (the top level)\n\nWritten by work running outside "
                                     "conversations. Newest first.\n")}
    for rel, text in seeds.items():
        if not (folder / rel).exists():
            plan.write(rel, text, "a new Collab Kit folder")
    return plan


# ---------------------------------------------------------------------------- back end --

BACKEND_TEMPLATE = """# Collab Kit back end (see the kit's engine/collab_kit/backend.py for every setting)
[backend]
cloud = {cloud}          # the Collab Kit folder: a path, or "rclone:<remote>:<path>"
work = {work}            # the back end's own clones: never inside ~/dev or the Collab Kit folder
interval_minutes = 60
human = {human}
local_roots = []         # e.g. ["~/dev", "~/projects"]: folder names there count as taken
deny = []                # regexes a pushed change may never contain

# One table per project whose home is a repository:
# [[project]]
# name = "garden-planner"
# repo = "git@github.com:you/garden-planner.git"
# branch = "main"
# push = true
# allow_public = false
"""


def build_runner(dest_dir: Path) -> Path:
    """macOS: build collab-kit-runner (the one program a person grants Drive access to)."""
    import subprocess
    src = KIT / "engine" / "launchd" / "collab-kit-runner.c"
    out = dest_dir / "collab-kit-runner"
    dest_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cc", "-O2", "-o", str(out), str(src)], check=True)
    subprocess.run(["codesign", "-s", "-", "-f", str(out)], check=True, capture_output=True)
    return out


def install_backend(config: Path | None, *, cloud: str | None, human: str | None, apply: bool) -> int:
    import subprocess
    from . import schedule
    config = config or C.config_dir() / "backend.toml"
    if not config.is_file():
        if not cloud:
            print(f"no {config} yet: give --cloud (and --human) to create it", file=sys.stderr)
            return 2
        work = data_dir() / "backend"
        text = BACKEND_TEMPLATE.format(cloud=json.dumps(cloud), work=json.dumps(str(work)),
                                       human=json.dumps(human or "the owner"))
        print(f"create {config}" + ("" if apply else "  (dry run)"))
        if apply:
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text(text, encoding="utf-8")
    cfg = C.load_toml(config) if config.is_file() else {"backend": {"cloud": cloud or ""}}
    minutes = int(cfg.get("backend", {}).get("interval_minutes", 60))
    spec = C.expand(cfg.get("backend", {}).get("cloud", ""))
    runner = None
    if sys.platform == "darwin" and "/Library/CloudStorage/" in spec:
        runner = data_dir() / "collab-kit-runner"
        print(f"the Collab Kit folder is a Drive for desktop folder: launchd starts the back end through {runner}")
        if apply:
            build_runner(runner.parent)
    p = schedule.plan(KIT, config, minutes, runner=runner)
    print(f"schedule on {p['platform']}, every {minutes} minutes:")
    for path, text in p["files"].items():
        print(f"  write {path}")
        if apply:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(text, encoding="utf-8")
    for d in p["mkdir"]:
        if apply:
            Path(d).mkdir(parents=True, exist_ok=True)
    for cmd in p["then"]:
        print(f"  run   {cmd}")
        if apply and not cmd.startswith("loginctl") and not cmd.startswith("schtasks"):
            subprocess.run(cmd, shell=True, check=False)
    if not apply:
        print("(dry run: nothing written; add --apply)")
    elif runner:
        print("\nmacOS: the first run may ask whether collab-kit-runner may access files managed by Google Drive: "
              "Allow. If nothing asks and the log says 'Operation not permitted', give the runner Full Disk "
              "Access (System Settings, Privacy & Security), never /bin/bash or Terminal.")
    return 0

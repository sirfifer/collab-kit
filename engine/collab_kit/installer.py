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
        self.root, self.dry, self.steps, self.info = root, dry, [], []

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

    def tell(self, what: str, why: str = "") -> None:
        """Information, or a next step for someone: shown, never counted as a change (--check)."""
        self.info.append((what, why))

    def show(self, out=sys.stdout) -> None:
        for what, why in self.steps:
            print(f"  {what}" + (f"  ({why})" if why else ""), file=out)
        if not self.steps:
            print("  nothing to change", file=out)
        for what, why in self.info:
            print(f"  {what}" + (f"  ({why})" if why else ""), file=out)


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
        if rel in ("installer.py", "backend.py", "migrate.py", "schedule.py"):
            continue                       # the back end, the installer, and migration stay in the kit
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
                    human: str | None = None, python: str = "", dry: bool = False, about: str = "",
                    spoken: str = "", replace_start: bool = False) -> Plan:
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
                   f"[session]\nstop_check = true   # before a session ends without recording anything, ask (at most every 15 minutes, 3 times)\n",
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
                   "the session-start brief and the end-of-turn check (other settings kept)")
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
        startp = root / base / "00-START-HERE.md"
        fresh = project_start_file(name, about, spoken or name, home="repo")
        if not startp.is_file():
            plan.write(f"{base}/00-START-HERE.md", fresh, "the unit's start file")
        elif replace_start:
            cur = startp.read_text(encoding="utf-8")
            new = keep_description(cur, fresh)
            if new != cur:                            # git keeps the old one
                plan.write(f"{base}/00-START-HERE.md", new, "the start file, from the current template "
                           "(its 'Project:' line kept; carry over anything else added by hand: git has the old one)")
        for rel, text in ((f"{base}/_returns/README.md", returns_readme(name)),
                          (f"{base}/knowledge/README.md", f"# {name}\n\nWhat this project knows.\n"),
                          (f"{base}/agenda/README.md", "# Agenda\n\nOne file per item (`W-NNN-...`). Change items by filing a return.\n")):
            if not (root / rel).is_file():
                plan.write(rel, text, "a channel of the unit")
    # 6. the project's side of the Collab Kit folder: its folder there, and its row in the catalog
    _cloud_side(root, name, unit, home, about, spoken, human, plan, dry, replace_start)
    return plan


def keep_description(current: str, fresh: str) -> str:
    """The current template, keeping the project's own description: the line that starts 'Project: **'."""
    mine = next((ln for ln in current.splitlines() if ln.startswith("Project: **")), None)
    if mine is None:
        return fresh
    return "\n".join(mine if ln.startswith("Project: **") else ln for ln in fresh.split("\n"))


def _cloud_side(root: Path, name: str, unit: str, home: str, about: str, spoken: str, human: str,
                plan: Plan, dry: bool, replace_start: bool = False) -> None:
    """A cloud-homed project gets its folder in the Collab Kit folder (new files only), and every project
    is marked live in the top level's knowledge/projects.md through a return, so the one writer applies
    it (the back end if one runs, else this machine at once). Without the folder in reach: the next step."""
    from .session import Project, open_cloud
    from .store import SubStore
    from .templates import project_start_file, returns_readme, set_human
    machine = C.machine()
    cloud = open_cloud(machine)
    if cloud is None:
        why = ("this machine has no Collab Kit config: run install.py machine first"
               if not machine.get("cloud", {}).get("root") else
               f"the Collab Kit folder ({machine['cloud']['root']}) is not reachable from here")
        plan.tell("next: the project's folder and its catalog row", f"{why}, then run this again")
        return
    if home == "cloud":
        sub = SubStore(cloud, unit)
        cur = sub.read("00-START-HERE.md")
        if cur is not None and replace_start:
            set_human(human)
            new = keep_description(cur, project_start_file(name, about, spoken or name, home="cloud"))
            if new != cur:
                plan.note(f"replace {unit}/00-START-HERE.md with the current template", "its 'Project:' line kept; "
                          "the old one is kept in _versions/ (carry over anything else added by hand)")
                if not dry:
                    from .unit import Unit, write_versioned
                    write_versioned(Unit(sub, name, home="cloud"), "00-START-HERE.md", new)
        if cur is None:
            set_human(human)
            files = {"00-START-HERE.md": project_start_file(name, about, spoken or name, home="cloud"),
                     "_returns/README.md": returns_readme(name),
                     "agenda/README.md": "# Agenda\n\nOne file per item (`W-NNN-...`). Change items by filing a return.\n",
                     "knowledge/README.md": f"# {name}\n\n{about or 'What this project knows.'}\n",
                     "WIP/README.md": "# WIP\n\nCheckpoint notes between saves. See the top-level start file.\n"}
            for rel, text in files.items():
                if sub.read(rel) is None:
                    plan.note(f"create {unit}/{rel}", "in the Collab Kit folder: the project's home")
                    if not dry:
                        sub.write(rel, text)
    from .apply import has_project_row, _col, _table_rows, _cells
    catalog = cloud.read("knowledge/projects.md") or ""
    lines, hi, cells, rows = _table_rows(catalog)
    kcol, fcol = _col(cells, "collab kit", "collab-kit"), _col(cells, "folder")
    state = next((_cells(lines[j])[kcol] for j in rows if fcol is not None and kcol is not None
                  and len(_cells(lines[j])) > max(fcol, kcol) and _cells(lines[j])[fcol].strip("`") == name), None)
    listed = has_project_row(catalog, name)
    if hi is None:
        plan.tell("skip the catalog", "the Collab Kit folder has no knowledge/projects.md table (install.py top)")
        return
    if listed and (kcol is None or state == "live"):
        return
    if not listed and not about:
        plan.tell("next: the catalog row", f"'{name}' is not in knowledge/projects.md: run again with "
                  "--about \"what it is\" (and --spoken \"what you call it\") to add it")
        return
    where = ("a repository; its Collab Kit home is its folder here" if home == "cloud" else
             "a repository; its Collab Kit home is the repository (`collab-kit/` there): the folder here is a copy")
    args = ' collab-kit=live' if kcol is not None else ""
    if not listed:
        args += f' about="{about}" where="{where}"' + (f' spoken="{spoken}"' if spoken else "")
    change = f"project {name}{args}"
    if dry or not (root / C.PROJECT_FILE).is_file():
        plan.note(f"file a return: {change}", "marks the project live in the catalog")
        return
    from .apply import Reject
    try:
        proj = Project(root)
        cu = proj.cloud_unit()
        if proj.route()[0] != "cloud" or cu is None:  # only into the inbox that can reach the catalog
            plan.tell(f"next: file `{change}` from the project's Collab Kit folder",
                      "this repository's returns do not reach it yet (a back end mirrors a repository-homed "
                      "project's folder once its backend.toml lists it)")
            return
        if any(change in (cu.store.read(f"_returns/{e.name}") or "") for e in cu.pending_returns() if not e.native):
            plan.tell(f"already filed: {change}", "waiting in the project's inbox")
            return
        plan.note(f"file a return: {change}", "marks the project live in the catalog")
        text = proj.compose("note", f"{name} is set up in Collab Kit", [change],
                            sender=f"the Collab Kit installer in {name}")
        res = proj.file(text)
        plan.tell(f"  {'applied' if res.get('applied') else 'filed'} ({res['route']})", res.get("message", ""))
    except (Reject, OSError) as e:
        plan.tell("  not filed", str(e))


# ---------------------------------------------------------------------------- machine --

def data_dir() -> Path:
    if os.environ.get("COLLAB_KIT_DATA"):
        return Path(os.environ["COLLAB_KIT_DATA"])
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "collab-kit"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "collab-kit"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "collab-kit"


def install_machine(*, cloud_root: str | None, human: str | None, kit_source: str | None,
                    user_hooks: bool, python: str = "python3", dry: bool = False,
                    claude_settings: Path | None = None, rclone: str | None = None,
                    rclone_config: str | None = None) -> Plan:
    cfgp = C.machine_file()
    plan = Plan(cfgp.parent, dry)
    cfg = C.load_toml(cfgp)
    human = human or cfg.get("human") or "the owner"
    cloud_root = cloud_root or cfg.get("cloud", {}).get("root", "")
    kit_source = kit_source or cfg.get("kit", {}).get("source", "") or str(KIT)
    rclone = rclone if rclone is not None else cfg.get("cloud", {}).get("rclone", "")
    rclone_config = rclone_config if rclone_config is not None else cfg.get("cloud", {}).get("rclone_config", "")
    extra = "".join(f"{k} = {json.dumps(v)}\n" for k, v in (("rclone", rclone), ("rclone_config", rclone_config)) if v)
    text = ("# Collab Kit, this machine (see the kit's engine/collab_kit/config.py)\n"
            f"human = {json.dumps(human)}\n\n[cloud]\nroot = {json.dumps(cloud_root)}\n{extra}\n"
            f"[kit]\nsource = {json.dumps(kit_source)}\n")
    plan.write(cfgp.name, text, f"this machine's settings ({cfgp})")
    def _v(path: str) -> tuple:
        try:
            return tuple(int(x) for x in (Path(C.expand(path)) / "VERSION").read_text().strip().split("."))
        except (OSError, ValueError):
            return ()
    if Path(C.expand(kit_source)).resolve() != KIT.resolve() and _v(kit_source) < _v(str(KIT)):
        plan.tell(f"note: the kit source in the config, {kit_source}, is {'.'.join(map(str, _v(kit_source))) or 'missing'}"
                  f"; this kit is {kit_version()}", f"to use this one, run again with --kit-source \"{KIT}\"")
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

PROJECTS_SEED = (
    "# Projects\n\n"
    "Every project, in Collab Kit or not: what it is, what it is called aloud, where it lives, its state, and\n"
    "whether Collab Kit is set up for it (`not set up`, `requested`, `live`). Each project may have a card in\n"
    "`project-cards/<folder>.md` (its vision, story, and timeline). Read this before starting a project: is it\n"
    "new, and is the name taken?\n\n"
    "| Folder | Say | What it is | Where | Status | Collab Kit |\n|---|---|---|---|---|---|\n")


def install_top(folder: Path, *, human: str, dry: bool = False, replace_start: bool = False,
                setup: str | None = None) -> Plan:
    """A new Collab Kit folder's top level (never overwrites), or, for an existing one: replace a start
    file that predates 0.5.1 with the template (only when asked; the old one is kept in _versions/),
    and set its setup line by hand (`setup`: "none" when a back end is retired, "backend")."""
    from .templates import SETUP_TEXT, get_block, replace_block, returns_readme, set_human, top_start_file
    set_human(human)
    plan = Plan(folder, dry)
    seeds = {"00-START-HERE.md": top_start_file(),
             "_returns/README.md": returns_readme("the top level").replace("`Project: the top level`", "`Project: top`"),
             "agenda/README.md": "# Agenda\n\nOne file per item (`W-NNN-...`); see the start file.\n",
             "WIP/README.md": "# WIP\n\nCheckpoint notes between saves; see the start file.\n",
             "knowledge/projects.md": PROJECTS_SEED,
             "knowledge/status.md": ("# What is going on (the top level)\n\nWritten by work running outside "
                                     "conversations. Newest first.\n")}
    for rel, text in seeds.items():
        if not (folder / rel).exists():
            plan.write(rel, text, "a new Collab Kit folder")
    start = folder / "00-START-HERE.md"
    if start.is_file():
        cur = start.read_text(encoding="utf-8")
        new = cur
        have = get_block(cur.replace("\r\n", "\n"), "setup")
        if have is None:
            if replace_start:
                new = top_start_file(setup or "none")
                plan.note("replace 00-START-HERE.md with the current template (the old one is kept in _versions/: "
                          "carry over anything you added to it by hand)")
            else:
                plan.note("00-START-HERE.md predates Collab Kit 0.5.1 (it has no setup line, and may hold state such "
                          "as due dates or a projects table, which now live on the agenda and in knowledge/projects.md). "
                          "Left as it is; run again with --replace-start to replace it with the template")
        else:
            from .templates import SETUP_BACKEND_MARK, SETUP_NONE_MARK
            line = (SETUP_TEXT[setup] if setup else            # the kit's own wording is brought current;
                    SETUP_TEXT["backend"] if have.strip().startswith(SETUP_BACKEND_MARK) else
                    SETUP_TEXT["none"] if have.strip().startswith(SETUP_NONE_MARK) else
                    have.strip())                              # a line edited by hand is kept
            fresh = replace_block(top_start_file(), "setup", line)
            if fresh != cur:
                if replace_start:
                    new = fresh
                    plan.note("replace 00-START-HERE.md with the current template, keeping its setup line (the old "
                              "one is kept in _versions/: carry over anything you added to it by hand)")
                elif setup and have.strip() != SETUP_TEXT[setup]:
                    new = replace_block(cur, "setup", SETUP_TEXT[setup])
                    plan.note(f"set 00-START-HERE.md's setup line to '{setup}'")
                else:
                    plan.note("00-START-HERE.md is not this kit's template (an older kit's rules, or edits by hand). "
                              "Left as it is; run again with --replace-start to replace it (the old one is kept)")
        if new != cur and not dry:
            from .store import FolderStore
            from .unit import Unit, write_versioned
            write_versioned(Unit(FolderStore(folder), "top", home="cloud", top=True), "00-START-HERE.md", new)
    if replace_start and start.is_file():                  # each project homed here: its start file too
        from .templates import HOME_NOTES, project_start_file
        set_human(human)
        repo_note = HOME_NOTES["repo"].split(".")[0]
        for ps in sorted(folder.glob("projects/*/collab-kit/00-START-HERE.md")):
            cur = ps.read_text(encoding="utf-8")
            if repo_note in cur:                           # a repository's copy: the back end mirrors it
                continue
            name = ps.parent.parent.name
            new_p = keep_description(cur, project_start_file(name, "", name, home="cloud"))
            if new_p != cur:
                rel = ps.relative_to(folder).as_posix()
                plan.note(f"replace {rel} with the current template", "its 'Project:' line kept; the old one is "
                          "kept in _versions/ (carry over anything else added by hand)")
                if not dry:
                    from .store import FolderStore, SubStore
                    from .unit import Unit, write_versioned
                    write_versioned(Unit(SubStore(FolderStore(folder), ps.parent.relative_to(folder).as_posix()),
                                         name, home="cloud"), "00-START-HERE.md", new_p)
    beat = folder / "_backend" / "heartbeat.json"
    if setup == "none" and beat.is_file():                 # a retired back end: sessions apply returns again
        from .text import stamp
        plan.note("retire _backend/heartbeat.json (renamed, kept)", "sessions apply returns themselves again")
        if not dry:
            beat.rename(beat.with_name(f"heartbeat.retired-{stamp()}.json"))
    if not dry:
        from .store import FolderStore
        from .text import utcnow
        from .views import PRESSING, rebuild_without_backend
        store = FolderStore(folder)
        if not store.exists(PRESSING) and folder.is_dir():
            rebuild_without_backend(store, human, utcnow().date())
            plan.note("write agenda/00-PRESSING.md, the agenda's front page (no back end runs yet)")
    return plan


# ---------------------------------------------------------------------------- back end --

BACKEND_TEMPLATE = """# Collab Kit back end (see the kit's engine/collab_kit/backend.py for every setting)
[backend]
cloud = {cloud}          # the Collab Kit folder: a path, or "rclone:<remote>:<path>"
work = {work}            # the back end's own clones: never inside ~/dev or the Collab Kit folder
interval_minutes = 60     # the sweep (pull, mirror, health); a return is applied within a few minutes of arriving (it settles 120 s first)
human = {human}
watch = ""               # optional, macOS: a synced copy of the folder (Drive for desktop); its inboxes ring the doorbell
local_roots = []         # e.g. ["~/dev", "~/projects"]: folder names there count as taken
deny = []                # regexes a pushed change may never contain
account = ""             # the Google account the folder must belong to, e.g. "you@example.com" (checked every run)
rclone = ""              # with an rclone remote: the pinned binary, e.g. "~/.local/bin/rclone" (else found on PATH)
rclone_config = ""       # and its own config file, e.g. "~/.config/collab-kit/rclone.conf"

# Optional: a push notification the moment a critical item (importance 1) appears. The command gets
# COLLAB_KIT_TITLE, COLLAB_KIT_MESSAGE and COLLAB_KIT_ITEM in its environment (docs/notifications.md):
# [notify]
# command = ["sh", "-c", "curl -s --max-time 10 -H \\"Title: $COLLAB_KIT_TITLE\\" --data-raw \\"$COLLAB_KIT_ITEM\\" https://ntfy.sh/<your-long-random-topic>"]

# One table per project whose home is a repository:
# [[project]]
# name = "garden-planner"
# repo = "git@github.com:you/garden-planner.git"
# branch = "main"
# push = true             # false: the back end commits in its own clone only; nothing reaches GitHub
# allow_public = false     # push collab-kit/ to a public repository only if true
# returns_in_git = false   # keep the text of returns from the Collab Kit folder out of git
"""


def build_runner(dest_dir: Path) -> Path:
    """macOS: build collab-kit-runner (the one program a person grants Drive access to), able to
    start exactly this kit's engine/backend.sh and nothing else."""
    import subprocess
    src = KIT / "engine" / "launchd" / "collab-kit-runner.c"
    out = dest_dir / "collab-kit-runner"
    dest_dir.mkdir(parents=True, exist_ok=True)
    script = str((KIT / "engine" / "backend.sh").resolve())
    subprocess.run(["cc", "-O2", f"-DALLOWED_SCRIPT={json.dumps(script)}", "-o", str(out), str(src)], check=True)
    subprocess.run(["codesign", "-s", "-", "-f", str(out)], check=True, capture_output=True)
    return out


def install_backend(config: Path | None, *, cloud: str | None, human: str | None, apply: bool,
                    config_only: bool = False) -> int:
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
        write = apply or config_only
        print(f"create {config}" + ("" if write else "  (dry run; it would hold:)"))
        if write:
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text(text, encoding="utf-8")
            if os.name != "nt":
                config.chmod(0o600)                   # it may hold a notification key later
        else:
            print("".join(f"    {ln}\n" for ln in text.splitlines()), end="")
    elif config_only:
        print(f"{config} exists: left as it is")
    if config_only:
        print(f"next: edit {config} (account, local_roots, deny, a [[project]] per repository-homed project), "
              "then run this again with --apply to load the schedule")
        return 0
    cfg = C.load_toml(config) if config.is_file() else {"backend": {"cloud": cloud or ""}}
    minutes = int(cfg.get("backend", {}).get("interval_minutes", 60))
    spec = C.expand(cfg.get("backend", {}).get("cloud", ""))
    runner = None
    if sys.platform == "darwin" and "/Library/CloudStorage/" in spec:
        runner = data_dir() / "collab-kit-runner"
        print(f"the Collab Kit folder is a Drive for desktop folder: launchd starts the back end through {runner}")
        if apply:
            build_runner(runner.parent)
    watch = schedule.watch_paths(C.expand(cfg.get("backend", {}).get("watch", "")) or None)
    p = schedule.plan(KIT, config, minutes, runner=runner, watch=watch)
    print(f"schedule on {p['platform']}: every minute a cheap check for waiting returns, a full pass when one "
          f"waits or every {minutes} minutes" + (f"; also the moment a file lands in {len(watch)} watched inboxes"
                                                 if watch and sys.platform == "darwin" else ""))
    for path, text in p["files"].items():
        print(f"  write {path}")
        if apply:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(text, encoding="utf-8")
    for d in p["mkdir"]:
        if apply:
            Path(d).mkdir(parents=True, exist_ok=True)
    yours = [c for c in p["then"] if c.startswith(("loginctl", "schtasks"))]   # may need the person's rights
    for cmd in p["then"]:
        if cmd in yours:
            continue
        print(f"  run   {cmd}")
        if apply:
            subprocess.run(cmd, shell=True, check=False)
    if yours:
        print("  the person runs these themselves (they may ask for their password); until then nothing is scheduled:")
        for cmd in yours:
            print(f"    {cmd}")
    if not apply:
        print("(dry run: nothing written; add --apply)")
    elif runner:
        print("\nmacOS: the first run may ask whether collab-kit-runner may access files managed by Google Drive: "
              "Allow. If nothing asks and the log says 'Operation not permitted', give the runner Full Disk "
              "Access (System Settings, Privacy & Security), never /bin/bash or Terminal.")
    return 0

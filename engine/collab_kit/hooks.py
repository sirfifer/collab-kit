"""Claude Code hooks: what makes Collab Kit automatic rather than remembered.

  session-start  (project .claude/settings.json, SessionStart)
      Prints the brief, which Claude Code adds to the session's context before the first prompt,
      and notes where the repository stood, for the check at the end.
  stop           (project .claude/settings.json, Stop; also user-level for parent-folder sessions)
      Once per session: when the session changed project files and recorded nothing in Collab
      Kit (no return filed, no collab-kit/ change), it asks the agent to record what is needed,
      or to say that nothing is. Never twice, never in a loop (stop_hook_active).
  touch          (user-level ~/.claude/settings.json, PostToolUse on Read|Edit|Write|...)
      For sessions that start in a parent folder (e.g. ~/dev), where a project's own hooks never
      run: the first time the session touches a file inside a Collab Kit project, that project's
      brief is added to the context.

Hooks never fail loudly: any error becomes one short line, and the session carries on.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import brief as B
from . import config as C
from .session import (Project, changed_since, claim_once, filed_since, load_session, save_session,
                      snapshot)


def _read_input() -> dict:
    try:
        data = sys.stdin.read()
        return json.loads(data) if data.strip() else {}
    except (ValueError, OSError):
        return {}


def session_start(inp: dict) -> int:
    proj = Project.find(inp.get("cwd") or os.getcwd())
    if not proj:
        return 0
    sid = inp.get("session_id", "")
    if sid:
        state = load_session(sid)
        state.setdefault("repos", {}).setdefault(str(proj.root), {**snapshot(proj.root), "project": proj.name})
        save_session(sid, state)
    sys.stdout.write(B.build(proj))
    return 0


STOP_REASON = (
    "Collab Kit check (once per session): this session changed {n} file(s) in {project} ({examples}) "
    "and recorded nothing in Collab Kit. Before you finish: if the work leaves a question, a decision, "
    "or follow-up for the person, put it on the agenda (`python3 tools/collab-kit/ck.py ask \"...\"`); "
    "if it changes where the project stands, file a status line (`python3 tools/collab-kit/ck.py status "
    "\"...\"`); if it changes what the project knows, update its knowledge. If none of that applies, "
    "say so in one line and finish."
)


def stop(inp: dict) -> int:
    if inp.get("stop_hook_active"):
        return 0
    sid = inp.get("session_id", "")
    if not sid:
        return 0
    state = load_session(sid)
    repos = state.get("repos", {})
    proj = Project.find(inp.get("cwd") or os.getcwd())
    if proj and str(proj.root) not in repos:
        # The session started before the hooks were installed: begin watching from here.
        repos[str(proj.root)] = {**snapshot(proj.root), "project": proj.name}
        save_session(sid, state)
        return 0
    for root_s, snap in repos.items():
        root = Path(root_s)
        if not root.is_dir():
            continue
        p = Project(root)
        if not p.cfg["session"].get("stop_check", True):
            continue
        changed, kit_changed = changed_since(root, snap)
        if not changed or kit_changed or filed_since(p.name, snap.get("at", "")):
            continue
        if not claim_once(sid, "stop-check"):
            return 0
        examples = ", ".join(changed[:3]) + (", ..." if len(changed) > 3 else "")
        print(json.dumps({"decision": "block",
                          "reason": STOP_REASON.format(n=len(changed), project=p.name, examples=examples)}))
        return 0
    return 0


TOUCH_TOOLS = {"Read", "Edit", "Write", "MultiEdit", "NotebookEdit"}


def touch(inp: dict) -> int:
    ti = inp.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ti.get("path")
    if not path:
        return 0
    p = Path(path)
    if not p.is_absolute():
        p = Path(inp.get("cwd") or os.getcwd()) / p
    root = C.find_project_root(p.parent if p.suffix or not p.is_dir() else p)
    if not root:
        return 0
    sid = inp.get("session_id", "")
    if not sid:
        return 0
    state = load_session(sid)
    repos = state.setdefault("repos", {})
    if str(root) in repos:
        return 0                                   # already briefed (or the project's own hook ran)
    proj = Project(root)
    repos[str(root)] = {**snapshot(root), "project": proj.name}
    save_session(sid, state)
    text = B.build(proj)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": inp.get("hook_event_name", "PostToolUse"),
        "additionalContext": "You just started working in a Collab Kit project. " + text}}))
    return 0


def main(event: str) -> int:
    inp = _read_input()
    fn = {"session-start": session_start, "stop": stop, "touch": touch}.get(event)
    if fn is None:
        print(f"collab-kit: unknown hook '{event}'", file=sys.stderr)
        return 0
    try:
        return fn(inp)
    except Exception as e:                         # a hook must never break the session
        if event == "session-start":
            print(f"(Collab Kit: the session brief could not be built: {type(e).__name__}: {e})")
        return 0

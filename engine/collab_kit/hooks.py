"""Claude Code hooks: what makes Collab Kit automatic rather than remembered.

  session-start  (project .claude/settings.json, SessionStart; also user-level for compact/clear)
      Prints the brief, which Claude Code adds to the context before the first prompt, delivers
      returns filed while the Collab Kit folder was unreachable, and notes where the checkout
      stood, for the check at the end of each turn.
  stop           (project .claude/settings.json, Stop; also user-level for parent-folder sessions)
      When the session has changed project files since the last check and recorded nothing in
      Collab Kit since then, it asks the agent once to record what is needed, or to say that
      nothing is yet. It re-arms after each check: at most once every 15 minutes, three times a
      session, never in a loop (stop_hook_active).
  touch          (user-level ~/.claude/settings.json, PostToolUse on Read|Edit|Write|...)
      For sessions started in a parent folder (e.g. ~/dev), where a project's own hooks never run:
      the first time the session touches a file inside a Collab Kit project, a short brief.

Hooks never fail loudly and never hang a session: the brief has a deadline (a cached one is shown
if the folder is slow), and any error becomes one short line.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
import threading
from pathlib import Path

from . import config as C
from .session import (Project, changed_since, claim_once, filed_since, load_session, save_session,
                      snapshot)
from .text import one_line, utcnow

DEADLINE_SECONDS = 10
RECHECK_MINUTES = 15
MAX_CHECKS = 3


def _read_input() -> dict:
    try:
        data = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        val = json.loads(data) if data.strip() else {}
        return val if isinstance(val, dict) else {}
    except (ValueError, OSError):
        return {}


def _cache_path(root: Path) -> Path:
    h = hashlib.sha256(str(root).encode()).hexdigest()[:16]
    d = C.state_dir() / "briefs"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{h}.txt"


def brief_with_deadline(proj: Project, *, compact: bool = False, cwd: str | None = None) -> str:
    """The brief, or, if the folder is too slow, the last good one with its age (or a short note)."""
    from . import brief as B
    box: dict = {}

    def work():
        try:
            box["text"] = B.build(proj, compact=compact, cwd=cwd)
        except BaseException as e:  # noqa: BLE001 (reported below)
            box["error"] = f"{type(e).__name__}: {e}"
    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(DEADLINE_SECONDS)
    cache = _cache_path(proj.root)
    if "text" in box:
        if not compact:
            try:
                cache.write_text(f"{utcnow().isoformat()}\n{box['text']}", encoding="utf-8")
            except OSError:
                pass
        return box["text"]
    why = box.get("error") or f"the Collab Kit folder took longer than {DEADLINE_SECONDS} seconds to read"
    ck = proj.ck(cwd)
    try:
        when, text = cache.read_text(encoding="utf-8").split("\n", 1)
        return (f"(Collab Kit: {why}. This is the brief from {when[:16].replace('T', ' ')} UTC; run `{ck} brief` "
                f"for a fresh one before relying on it.)\n{text}")
    except (OSError, ValueError):
        return (f"## Collab Kit: project {proj.name}\n(Collab Kit: {why}. Run `{ck} brief` before starting, to see "
                f"the project's agenda and inbox.)\n")


def _watch(state: dict, root: Path, name: str, exclude: set[str] | None = None) -> None:
    state.setdefault("repos", {})[str(root)] = {**snapshot(root, exclude), "project": name, "checks": 0,
                                                "last_check": ""}


def session_start(inp: dict) -> int:
    sid = inp.get("session_id", "")
    source = inp.get("source", "startup")
    proj = Project.find(inp.get("cwd") or os.getcwd())
    state = load_session(sid) if sid else {"repos": {}}
    if not proj:
        if sid and source in ("compact", "clear"):
            state["briefed"] = []                   # parent-folder sessions: brief again on next touch
            state["generation"] = int(state.get("generation", 0)) + 1
            save_session(sid, state)
        return 0
    if sid:
        if str(proj.root) not in state.get("repos", {}) or source in ("startup", "clear"):
            _watch(state, proj.root, proj.name)
        state.setdefault("briefed", [])
        if str(proj.root) not in state["briefed"]:
            state["briefed"].append(str(proj.root))
        save_session(sid, state)
    out = brief_with_deadline(proj, cwd=inp.get("cwd"))
    try:
        moved = proj.deliver_offline()
    except Exception:                               # noqa: BLE001
        moved = []
    if moved:
        out += (f"\nDelivered {len(moved)} return(s) filed while the Collab Kit folder was unreachable; their removal "
                f"from collab-kit/_returns/ is a change to commit.\n")
    sys.stdout.write(out)
    return 0


STOP_REASON = (
    "Collab Kit check: since {since}, this session changed {n} file(s) in {project} ({examples}) and recorded "
    "nothing in Collab Kit. If this piece of work is done or paused: put anything left open, or any question or "
    "decision for {human}, on the agenda (`{ck} ask \"...\"`); if it changes where the project stands, file a "
    "status line (`{ck} status \"...\"`); if it settles or advances an item, file that (skill collab-kit-return); "
    "if it changes what the project knows, update its knowledge (`{ck} knowledge`). If the work is still under "
    "way, or nothing needs recording, say so in one line and carry on."
)


def stop(inp: dict) -> int:
    if inp.get("stop_hook_active"):
        return 0
    sid = inp.get("session_id", "")
    if not sid:
        return 0
    state = load_session(sid)
    repos = state.setdefault("repos", {})
    proj = Project.find(inp.get("cwd") or os.getcwd())
    if proj and str(proj.root) not in repos and C.find_project_root(Path(inp.get("cwd") or os.getcwd())):
        _watch(state, proj.root, proj.name)         # the session predates the hooks: watch from here
        save_session(sid, state)
        return 0
    now = utcnow()
    for root_s, snap in list(repos.items()):
        root = Path(root_s)
        if not root.is_dir():
            continue
        p = Project(root)
        if not p.cfg["session"].get("stop_check", True):
            continue
        changed, kit_changed = changed_since(root, snap)
        recorded = kit_changed or filed_since(root, snap.get("at", ""))
        if recorded:
            _watch(state, root, p.name)             # judged afresh from here on
            state["repos"][root_s]["checks"] = snap.get("checks", 0)
            continue
        if not changed:
            continue
        checks = int(snap.get("checks", 0))
        last = snap.get("last_check", "")
        if checks >= MAX_CHECKS:
            continue
        if last and (now - dt.datetime.fromisoformat(last)).total_seconds() < RECHECK_MINUTES * 60:
            continue
        if not claim_once(sid, f"stop-{checks}-{hashlib.sha256(root_s.encode()).hexdigest()[:12]}"):
            return 0                                # a parallel hook (project or user level) already asked
        examples = ", ".join(changed[:3]) + (", ..." if len(changed) > 3 else "")
        since = snap.get("at", "")[:16].replace("T", " ") + " UTC"
        # the next check looks only at what changes after this one
        state["repos"][root_s] = {**snapshot(root), "at": now.isoformat(), "project": p.name,
                                  "checks": checks + 1, "last_check": now.isoformat()}
        save_session(sid, state)
        print(json.dumps({"decision": "block", "reason": STOP_REASON.format(
            since=since, n=len(changed), project=p.name, examples=one_line(examples, 160),
            human=p.machine.get("human") or "the person", ck=p.ck(inp.get("cwd")))}))
        return 0
    save_session(sid, state)
    return 0


WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def touch(inp: dict) -> int:
    ti = inp.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ti.get("path")
    sid = inp.get("session_id", "")
    if not path or not sid:
        return 0
    p = Path(path)
    if not p.is_absolute():
        p = Path(inp.get("cwd") or os.getcwd()) / p
    root = C.find_project_root(p if p.is_dir() else p.parent)
    if not root:
        return 0
    state = load_session(sid)
    if str(root) in state.get("briefed", []):
        return 0
    key = hashlib.sha256(str(root).encode()).hexdigest()[:12]
    if not claim_once(sid, f"brief-{key}-{state.get('generation', 0)}"):
        return 0
    proj = Project(root)
    text = brief_with_deadline(proj, compact=True, cwd=inp.get("cwd"))
    state = load_session(sid)                       # re-read: another hook may have written meanwhile
    if str(root) not in state.get("repos", {}):
        exclude = set()
        if inp.get("tool_name") in WRITE_TOOLS:     # the touching write is this session's own change
            try:
                exclude = {p.resolve().relative_to(root.resolve()).as_posix()}
            except (OSError, ValueError):
                pass
        _watch(state, root, proj.name, exclude)
    state.setdefault("briefed", []).append(str(root))
    save_session(sid, state)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": inp.get("hook_event_name", "PostToolUse"),
        "additionalContext": "You just started working in a Collab Kit project.\n" + text}}))
    return 0


def main(event: str) -> int:
    inp = _read_input()
    fn = {"session-start": session_start, "stop": stop, "touch": touch}.get(event)
    if fn is None:
        print(f"collab-kit: unknown hook '{event}'", file=sys.stderr)
        return 0
    try:
        return fn(inp)
    except BaseException as e:                      # noqa: BLE001 (a hook must never break the session)
        if event == "session-start":
            print(f"(Collab Kit: the session brief could not be built: {type(e).__name__}: {str(e)[:200]})")
        return 0

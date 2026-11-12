#!/usr/bin/env python3
"""kb_mcp.py: the knowledge-base engine as a small set of tools for the unattended curator pass.
Part of Collab Kit: do not edit per project (it is replaced on upgrade).

The nightly curator reads text from outside (returns from conversations), so it runs with no shell
at all. This stdio MCP server is the only way it can run the engine: a fixed list of commands, each
run as `python3 -I <engine> <command> <args>` with no shell, from a read-only copy of the engine
taken from the main branch (nightly.sh makes the copy; the curator cannot write it).

Environment (set by nightly.sh in the --mcp-config it writes):
  KB_ROOT       the curator worktree (the engine works there)
  KB_ENGINE     the read-only kb.py to run
  KB_DIFF_FROM  KB_DIFF_TO   the commit range the run covers (for `changes`); optional

Speaks MCP over stdio (JSON-RPC 2.0, one message per line). Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("KB_ROOT", ".")).resolve()
ENGINE = os.environ.get("KB_ENGINE", "")
DIFF_FROM = os.environ.get("KB_DIFF_FROM", "")
DIFF_TO = os.environ.get("KB_DIFF_TO", "")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
LIMIT = 150_000  # characters of output returned per call

S = {"type": "string"}
# name: (kb.py command or None, {argument: description}, what it does)
TOOLS = {
    "build": ("build", {}, "Rebuild the generated views (python3 tools/kb/kb.py build)."),
    "check": ("check", {}, "Check the knowledge base; must print 'kb check: OK' (python3 tools/kb/kb.py check)."),
    "stats": ("stats", {}, "Document codes, capture codes, open endpoints, oversize warnings (kb.py stats)."),
    "agenda": ("agenda", {}, "The agenda in order (kb.py agenda)."),
    "find": ("find", {"words": "the words to look for"}, "Ranked search: concepts, past answers, headings, text (kb.py find <words>)."),
    "show": ("show", {"ref": "a reference such as CODE#heading-key or CODE@40-90"}, "Show one section or line range (kb.py show <ref>)."),
    "keys": ("keys", {"code": "a document code"}, "The heading keys of one document (kb.py keys <code>)."),
    "new_item": ("new-item", {"kind": "the agenda item's kind", "title": "its title"}, "Create an agenda item (kb.py new-item <kind> <title>)."),
    "new_kb": ("new-kb", {"question": "the question as it was asked"}, "Create a KB answer (kb.py new-kb <question>)."),
    "new_concept": ("new-concept", {"slug": "the concept id: lowercase letters, digits, dashes", "title": "its title"},
                    "Create a concept (kb.py new-concept <id> <title>)."),
    "changes": (None, {"path": "a file path inside the repository, as listed in the prompt"},
                "What changed in one project file during the range this run covers (git diff <from> <to> -- <path>)."),
}


def _out(text: str) -> str:
    return text if len(text) <= LIMIT else text[:LIMIT] + f"\n[... cut at {LIMIT} characters]"


def run(argv: list[str]) -> tuple[str, bool]:
    try:
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=600,
                           env={**os.environ, "KB_ROOT": str(ROOT)})
    except subprocess.TimeoutExpired:
        return "timed out", True
    return _out((r.stdout + r.stderr).strip() or f"(exit {r.returncode}, no output)"), r.returncode != 0


def call(name: str, args: dict) -> tuple[str, bool]:
    if name not in TOOLS:
        return f"no such tool: {name}", True
    cmd, params, _ = TOOLS[name]
    vals = []
    for p in params:
        v = args.get(p)
        if not isinstance(v, str) or not v.strip():
            return f"{name}: '{p}' is required (a non-empty string)", True
        if v.startswith("-") or "\0" in v:
            return f"{name}: '{p}' may not start with '-'", True
        vals.append(v)
    if name == "changes":
        if not (SHA_RE.match(DIFF_FROM) and SHA_RE.match(DIFF_TO)):
            return "no earlier run to compare with; read the file itself", False
        pp = Path(vals[0])
        if pp.is_absolute() or ".." in pp.parts:
            return "changes: the path must be inside the repository (relative, no '..')", True
        return run(["git", "-C", str(ROOT), "--no-pager", "diff", "--no-ext-diff", "--no-textconv",
                    DIFF_FROM, DIFF_TO, "--", vals[0]])
    if name == "find":
        vals = vals[0].split()
    return run([sys.executable, "-I", ENGINE, cmd, *vals])


def tool_list() -> list[dict]:
    return [{"name": n, "description": d,
             "inputSchema": {"type": "object", "properties": {p: {**S, "description": t} for p, t in ps.items()},
                             "required": list(ps)}}
            for n, (_, ps, d) in TOOLS.items()]


def handle(msg: dict) -> dict | None:
    mid, method = msg.get("id"), msg.get("method")
    if mid is None:  # a notification
        return None
    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion") or "2025-06-18"
        res = {"protocolVersion": ver, "capabilities": {"tools": {}},
               "serverInfo": {"name": "kb", "version": "1"}}
    elif method == "ping":
        res = {}
    elif method == "tools/list":
        res = {"tools": tool_list()}
    elif method == "tools/call":
        p = msg.get("params") or {}
        text, err = call(p.get("name", ""), p.get("arguments") or {})
        res = {"content": [{"type": "text", "text": text}], "isError": err}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"unknown method {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": res}


def main() -> int:
    if not ENGINE or not Path(ENGINE).is_file():
        print(f"kb_mcp: KB_ENGINE is not a file: {ENGINE!r}", file=sys.stderr)
        return 1
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            reply = handle(msg) if isinstance(msg, dict) else None
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())

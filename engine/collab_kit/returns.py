"""Returns: the one way anything changes a unit, from any conversation or session.

A return is a plain text file in a unit's `_returns/` folder:

    Project: garden-planner              (the unit's folder name; "top" for the top level)
    Id: 2026-11-15-0910-shade            (optional; the file name without .md otherwise)
    From: Richard
    Type: decision
    Topic: one line
    What was worked out: ...             (any other fields; indented lines continue a field)
    Verbatim: ...

    Changes v1:
    new-item @beds kind=work-out importance=2 title="Describe each bed's light"
    ```
    ## What's needed
    A light description per bed.
    ```
    log W-002 "shade" "Morning sun and afternoon shade suit lettuce."
    settle W-004 "watering" outcome="drip lines on the north beds"
    End.

Rules (DESIGN-0.5 section 8): only the `Changes v1:` block that follows the header is parsed;
curly quotes, bullets, and bold are normalised; dates are absolute (YYYY-MM-DD); a change naming
an item repeats part of its title as a check; multi-line text goes in a fenced body under its
change; the file ends with `End.`. A return is applied whole or not at all, and at most once.

This module only parses. Nothing in a return is ever executed or shown to a model as instructions.
"""
from __future__ import annotations

import dataclasses
import re

from .text import check_date, normalise_line, straighten

GRAMMAR = "v1"
KINDS = ("question", "decision", "work-out", "hole", "task", "project")
STATUSES = ("open", "in-progress", "settled", "dropped")
ITEM_FIELDS = ("title", "kind", "importance", "status", "due", "project")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
ITEM_RE = re.compile(r"^W-?(\d{1,5})$", re.I)
HANDLE_RE = re.compile(r"^@[a-z0-9][a-z0-9-]{0,39}$", re.I)
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z' /-]{0,40}?)\s*:\s?(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

# op -> (allowed keys, required keys)
OPS: dict[str, tuple[set[str], set[str]]] = {
    "new-item": ({"title", "kind", "importance", "status", "due", "project"}, {"title"}),
    "set": (set(ITEM_FIELDS) - {"status"} | {"status"}, set()),
    "log": ({"text"}, set()),
    "settle": ({"outcome"}, {"outcome"}),
    "snooze": ({"until"}, {"until"}),
    "withdraw": ({"reason"}, set()),
    "reopen": ({"reason"}, set()),
    "status": ({"text"}, set()),
    "knowledge": (set(), set()),
    "project": ({"spoken", "about", "active", "collab-kit"}, set()),
    "new-project": ({"name", "from", "about", "spoken"}, {"name", "from"}),
    "undo": (set(), set()),
    "push-request": ({"repo", "branch", "approval"}, {"repo", "approval"}),
}
ITEM_OPS = {"set", "log", "settle", "snooze", "withdraw", "reopen"}
OP_ALIASES = {"newitem": "new-item", "new_item": "new-item", "newproject": "new-project",
              "new_project": "new-project", "push": "push-request", "push_request": "push-request",
              "pushrequest": "push-request", "drop": "withdraw", "close": "settle"}
# A kind word starts a new item of that kind: `task "Order the drip line" importance=2 "What's needed"`.
# Voice conversations write these unprompted. ("project" is not one: it is its own change.)
KIND_OPS = {"question": "question", "decision": "decision", "work-out": "work-out", "workout": "work-out",
            "hole": "hole", "task": "task", "todo": "task"}


class ReturnError(ValueError):
    def __init__(self, msg: str, line: int | None = None):
        super().__init__(f"line {line}: {msg}" if line else msg)
        self.line = line


@dataclasses.dataclass
class Change:
    op: str
    line: int
    ref: str | None = None          # W-012, @handle, a knowledge path, a project name, a return id
    check: str | None = None        # part of the item's title, repeated as a check
    args: dict = dataclasses.field(default_factory=dict)
    text: str | None = None         # a quoted text argument (log text, status text)
    body: str | None = None         # a fenced body

    def describe(self) -> str:
        bits = [self.op]
        if self.ref:
            bits.append(self.ref)
        if self.check:
            bits.append(f'"{self.check}"')
        bits += [f'{k}="{v}"' for k, v in self.args.items()]
        return " ".join(bits)


@dataclasses.dataclass
class Return:
    id: str
    project: str
    fields: dict
    changes: list
    has_block: bool
    complete: bool                  # ends with End.
    source: str

    @property
    def type(self) -> str:
        return self.fields.get("type", "")

    @property
    def topic(self) -> str:
        return self.fields.get("topic", "")


def item_id(token: str) -> str | None:
    m = ITEM_RE.match(token.strip())
    return f"W-{int(m.group(1)):03d}" if m else None


def tokenize(line: str, lineno: int) -> list[tuple]:
    """Words, "quoted strings" (\\" and \\\\ escapes), and key=value / key="value" pairs.
    Apostrophes are ordinary characters (dictated text is full of them)."""
    out, i, n = [], 0, len(line)
    while i < n:
        if line[i].isspace():
            i += 1
            continue
        if line[i] == '"':
            s, i = _quoted(line, i, lineno)
            out.append(("q", s))
            continue
        j = i
        while j < n and not line[j].isspace() and line[j] != "=" and line[j] != '"':
            j += 1
        word = line[i:j]
        if j < n and line[j] == "=" and re.fullmatch(r"[A-Za-z][\w-]*", word):
            j += 1
            if j < n and line[j] == '"':
                s, j = _quoted(line, j, lineno)
            else:
                k = j
                while k < n and not line[k].isspace():
                    k += 1
                s, j = line[j:k], k
            out.append(("kv", word.lower().replace("_", "-"), s))
            i = j
            continue
        if j < n and line[j] == '"' and j == i:
            raise ReturnError("unexpected quote", lineno)
        while j < n and not line[j].isspace():
            j += 1
        out.append(("w", line[i:j]))
        i = j
    return out


def _quoted(line: str, i: int, lineno: int) -> tuple[str, int]:
    buf, j = [], i + 1
    while j < len(line):
        c = line[j]
        if c == "\\" and j + 1 < len(line) and line[j + 1] in '"\\':
            buf.append(line[j + 1])
            j += 2
            continue
        if c == '"':
            return "".join(buf), j + 1
        buf.append(c)
        j += 1
    raise ReturnError("a quoted text is not closed", lineno)


def _dedent(lines: list[str]) -> str:
    ind = min((len(x) - len(x.lstrip()) for x in lines if x.strip()), default=0)
    return "\n".join(x[ind:] for x in lines).strip("\n")


def parse(text: str, name: str = "") -> Return:
    """Parse a return. Raises ReturnError (with a line number) for anything malformed; a return is
    never half-understood."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    lines = text.split("\n")
    fields: dict[str, str] = {}
    last = None
    i = 0
    block_at = None
    complete = False
    while i < len(lines):
        raw = lines[i]
        norm = straighten(raw).strip()
        if norm == "End.":
            complete = True
            break
        if re.fullmatch(r"(\*\*)?Changes v1:?(\*\*)?", norm, re.I) and not raw[:1].isspace():
            block_at = i
            break
        if re.fullmatch(r"(\*\*)?Changes v\d+:?(\*\*)?", norm, re.I) and not raw[:1].isspace():
            raise ReturnError(f"this kit reads Changes {GRAMMAR}; this return uses '{norm}'", i + 1)
        m = FIELD_RE.match(straighten(raw)) if raw[:1] not in (" ", "\t") else None
        if m and m.group(1).strip():
            key = m.group(1).strip().lower()
            fields[key] = m.group(2).strip()
            last = key
        elif last is not None and norm:
            fields[last] = (fields[last] + "\n" + raw.strip()).strip()
        i += 1
    changes: list[Change] = []
    if block_at is not None:
        changes, end_line = _parse_block(lines, block_at + 1)
        complete = end_line is not None
        if complete:
            for j in range(end_line + 1, len(lines)):
                if re.match(r"^\s*(\*\*)?Changes v\d", straighten(lines[j]), re.I):
                    raise ReturnError("a second Changes block after End.; only one is allowed", j + 1)
    rid = fields.get("id") or re.sub(r"\.(md|txt)$", "", name)
    rid = rid.strip()
    if not ID_RE.match(rid):
        raise ReturnError(f"the return's id {rid!r} is not usable (letters, digits, '.', '-', '_')")
    project = fields.get("project", "").strip().strip("`").strip()
    return Return(rid, project, fields, changes, block_at is not None, complete, text)


def _first_word(line: str) -> str:
    m = re.match(r"\s*([A-Za-z][\w\u2013\u2014-]*)", line)
    return (m.group(1) if m else "").lower().replace("\u2013", "-").replace("\u2014", "-")


def _is_commentary(line: str) -> bool:
    """After the changes and a blank line, a voice conversation often adds a note before End.
    ("Verbatim: ...", "Standard (applies beyond W-006): ..."). A line that starts with a capital and is
    not a change ends the changes; the rest is kept in the return as text. A lowercase word that is not
    a change still fails, so a misspelled change is never dropped quietly."""
    w = _first_word(line)
    return bool(line.lstrip()[:1].isupper()) and w not in OPS and w not in OP_ALIASES and w not in KIND_OPS


def _parse_block(lines: list[str], start: int) -> tuple[list[Change], int | None]:
    changes: list[Change] = []
    i = start
    blank_before = False
    while i < len(lines):
        raw = lines[i]
        if straighten(raw).strip() == "End.":
            return changes, i
        if changes and raw.strip() and _is_commentary(normalise_line(raw)) and (
                blank_before or FIELD_RE.match(normalise_line(raw).strip())):
            while i < len(lines) and straighten(lines[i]).strip() != "End.":
                i += 1                                   # commentary to the end: kept in the file, not parsed
            return changes, (i if i < len(lines) else None)
        blank_before = not raw.strip()
        if FENCE_RE.match(raw):
            fence = FENCE_RE.match(raw).group(1)
            body, j = [], i + 1
            while j < len(lines) and not lines[j].strip().startswith(fence):
                body.append(lines[j])
                j += 1
            if j >= len(lines):
                raise ReturnError("a fenced body is not closed", i + 1)
            if not changes:
                raise ReturnError("a fenced body must follow the change it belongs to", i + 1)
            if changes[-1].body is not None:
                raise ReturnError("a change has two fenced bodies", i + 1)
            changes[-1].body = _dedent(body)
            i = j + 1
            continue
        line = normalise_line(raw)
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        changes.append(_parse_change(line.strip(), i + 1))
        i += 1
    return changes, None


def _parse_change(line: str, lineno: int) -> Change:
    toks = tokenize(line, lineno)
    if not toks or toks[0][0] != "w":
        raise ReturnError("a change starts with its name (new-item, set, log, ...)", lineno)
    op = toks[0][1].lower().replace("\u2013", "-").replace("\u2014", "-")
    op = OP_ALIASES.get(op, op)
    kind_word = KIND_OPS.get(op)
    if kind_word:
        op = "new-item"
    if op not in OPS:
        raise ReturnError(f"unknown change '{toks[0][1]}' (known: {', '.join(OPS)}; or a kind word, "
                          f"{', '.join(k for k in KIND_OPS if k not in ('workout', 'todo'))}, for a new item)", lineno)
    allowed, required = OPS[op]
    ch = Change(op, lineno)
    words = [t[1] for t in toks[1:] if t[0] == "w"]
    quoted = [t[1] for t in toks[1:] if t[0] == "q"]
    for t in toks[1:]:
        if t[0] == "kv":
            k, v = t[1], t[2]
            if k not in allowed:
                raise ReturnError(f"'{op}' does not take {k}= (it takes: {', '.join(sorted(allowed)) or 'none'})", lineno)
            if k in ch.args:
                raise ReturnError(f"{k}= given twice", lineno)
            ch.args[k] = v.strip()
    if op in ITEM_OPS:
        if not words:
            raise ReturnError(f"'{op}' needs the item (W-012, or an @handle from this return)", lineno)
        ref = words.pop(0)
        ch.ref = item_id(ref) or (ref.lower() if HANDLE_RE.match(ref) else None)
        if not ch.ref:
            raise ReturnError(f"'{ref}' is not an item number (W-012) or an @handle", lineno)
        if ch.ref.startswith("W-"):
            if not quoted:
                raise ReturnError(f"'{op} {ch.ref}' must repeat part of the item's title in quotes, as a check", lineno)
            ch.check = quoted.pop(0)
        if op == "log":
            if quoted:
                ch.text = quoted.pop(0)
            elif "text" in ch.args:
                ch.text = ch.args.pop("text")
    elif op == "new-item":
        if words and HANDLE_RE.match(words[0]):
            ch.ref = words.pop(0).lower()
        if kind_word:
            if "kind" in ch.args:
                raise ReturnError(f"'{toks[0][1]}' already says the kind; drop kind=", lineno)
            ch.args["kind"] = kind_word
        if "title" not in ch.args and quoted:
            ch.args["title"] = quoted.pop(0)
        if quoted:                                      # a second quoted text: what is needed
            ch.body = f"## What's needed\n{quoted.pop(0)}"
    elif op == "status":
        if quoted:
            ch.text = quoted.pop(0)
        elif "text" in ch.args:
            ch.text = ch.args.pop("text")
    elif op == "knowledge":
        if words:
            ch.ref = words.pop(0)
        elif quoted:
            ch.ref = quoted.pop(0)                      # a path with spaces, in quotes
        else:
            raise ReturnError("'knowledge' needs the file's path inside knowledge/ (e.g. notes/venues.md)", lineno)
    elif op == "project":
        if words:
            ch.ref = words.pop(0)
    elif op == "new-project":
        if quoted:
            ch.check = quoted.pop(0)
        if "from" in ch.args:
            fid = item_id(ch.args["from"])
            if not fid:
                raise ReturnError("new-project from= names the idea's agenda item (W-012)", lineno)
            ch.args["from"] = fid
    elif op == "undo":
        if not words:
            raise ReturnError("'undo' needs the id of the return to undo", lineno)
        ch.ref = words.pop(0)
        if not ID_RE.match(ch.ref):
            raise ReturnError(f"'{ch.ref[:60]}' is not a return id", lineno)
    if words:
        raise ReturnError(f"unexpected '{words[0]}'", lineno)
    if quoted:
        raise ReturnError(f"unexpected quoted text \"{quoted[0][:40]}\"", lineno)
    missing = required - set(ch.args)
    if missing:
        raise ReturnError(f"'{op}' needs {', '.join(sorted(m + '=' for m in missing))}", lineno)
    _validate_values(ch)
    return ch


def _validate_values(ch: Change) -> None:
    a = ch.args
    if "kind" in a:
        k = a["kind"].lower().replace(" ", "-").replace("workout", "work-out")
        if k not in KINDS:
            raise ReturnError(f"kind '{a['kind']}' is not one of {', '.join(KINDS)}", ch.line)
        a["kind"] = k
    if "importance" in a:
        if not re.fullmatch(r"[1-5]", a["importance"]):
            raise ReturnError("importance is 1 (highest) to 5", ch.line)
        a["importance"] = int(a["importance"])
    if "status" in a:
        s = a["status"].lower().replace(" ", "-")
        if s not in STATUSES:
            raise ReturnError(f"status '{a['status']}' is not one of {', '.join(STATUSES)}", ch.line)
        if ch.op == "set" and s in ("settled", "dropped"):
            raise ReturnError(f"use 'settle' or 'withdraw' to make an item {s}", ch.line)
        a["status"] = s
    for k in ("due", "until"):
        if k in a and a[k] != "":
            d = check_date(a[k])
            if not d:
                raise ReturnError(f"{k}= must be a full date, YYYY-MM-DD (got '{a[k]}')", ch.line)
            a[k] = d
    if "active" in a:
        v = a["active"].lower()
        if v not in ("yes", "no", "true", "false"):
            raise ReturnError("active= is yes or no", ch.line)
        a["active"] = v in ("yes", "true")
    if ch.op == "set" and not a:
        raise ReturnError("'set' needs at least one field (title, kind, importance, status, due, project)", ch.line)
    if ch.op in ("status",) and not (ch.text or ch.body):
        pass   # checked after the body is attached (apply time)
    for k, v in a.items():
        if isinstance(v, str) and len(v) > 2000:
            raise ReturnError(f"{k}= is longer than 2000 characters; use a fenced body", ch.line)


def render_change(op: str, ref: str | None = None, check: str | None = None, text: str | None = None,
                  body: str | None = None, **args) -> str:
    """Write one change line (and its fenced body) the way parse() reads it back."""
    def q(s: str) -> str:
        return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'
    bits = [op]
    if ref:
        bits.append(q(ref) if re.search(r'[\s"]', ref) else ref)
    if check:
        bits.append(q(check))
    for k, v in args.items():
        if v is None or v == "":
            continue
        bits.append(f"{k}={q(v)}" if not re.fullmatch(r"[\w.@-]+", str(v)) else f"{k}={v}")
    if text:
        bits.append(q(text))
    out = " ".join(bits)
    if body:
        fence = "~~~" if "```" in body else "```"
        out += f"\n{fence}\n{body.strip(chr(10))}\n{fence}"
    return out


def render_return(project: str, rid: str, sender: str, rtype: str, topic: str,
                  changes: list[str] | None = None, **fields) -> str:
    """A whole return, in the format every conversation and session uses."""
    head = [f"Project: {project}", f"Id: {rid}", f"From: {sender}", f"Type: {rtype}",
            f"Topic: {' '.join(topic.split())}"]
    for k, v in fields.items():
        if v:
            label = k.replace("_", " ").capitalize()
            v = str(v).strip().replace("\n", "\n  ")
            head.append(f"{label}: {v}")
    out = "\n".join(head) + "\n"
    if changes:
        out += "\nChanges v1:\n" + "\n".join(changes) + "\n"
    return out + "End.\n"

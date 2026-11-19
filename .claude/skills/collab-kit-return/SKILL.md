---
name: collab-kit-return
description: File a change to collab-kit's Collab Kit agenda or knowledge as a return (the one way anything changes there). Use whenever work in this repository settles, advances, re-prioritises, or adds an agenda item; raises a question or decision for Richard; finishes or starts something worth a status line; adds a knowledge note; asks for a push; or undoes an earlier return. Also use when a brief, an item, or Richard says "put that on the agenda", "close that item", "log that", "record this".
---
<!-- managed by Collab Kit 0.5.3: replaced on upgrade; delete this line to make the file your own -->

# File a return

Every change to the project's agenda or knowledge is a **return**: a small text file with a
`Changes v1:` block, checked and filed by `tools/collab-kit/ck`. Voice conversations,
chat, Claude Code sessions, and the back end all use this one format, so nothing collides and
everything has a ledger (and can be undone).

## The quick ones

```bash
tools/collab-kit/ck ask "Which database for the sync service?" --kind decision --importance 2 \
    --why "Postgres or SQLite; the choice decides the hosting cost."
tools/collab-kit/ck status "Sync service: first end-to-end run works; retries still missing."
```

## Anything else

```bash
tools/collab-kit/ck return --type note --topic "Sync service retries" \
  --change 'log W-012 "sync" "Retries added: three tries, backoff 2s/4s/8s."' \
  --change 'set W-012 "sync" status=in-progress' \
  --change 'new-item kind=task importance=3 title="Load-test the sync service"'
```

Longer text goes in a fenced body under its change: put the change lines in a file and pass
`--changes-file`, or write the whole return to a file and run `ck file <path>`.

| Change | Example |
|---|---|
| new item | `new-item @h kind=question importance=2 due=2026-12-01 title="..."` (kinds: question, decision, work-out, hole, task, project; importance 1 critical, raised first everywhere, to 5) |
| change fields | `set W-012 "part of its title" importance=1 due=2026-12-01 status=in-progress` |
| add to its log | `log W-012 "part of its title" "what happened"` |
| settle | `settle W-012 "part of its title" outcome="what was decided or done"` |
| snooze | `snooze W-012 "part of its title" until=2026-12-15` |
| drop | `withdraw W-012 "part of its title" reason="..."` |
| reopen | `reopen W-012 "part of its title" reason="..."` |
| status line | `status "..."` |
| knowledge file | `knowledge notes/topic.md` followed by a fenced body (the whole file) |
| push request | `push-request repo=<name> approval="Richard's exact words"` (only with Richard's yes in this session) |
| undo | `undo <return id>` |

- **Every change to an existing item repeats part of its title in quotes.** That check is what stops
  a wrong number from changing the wrong item: look the item up first (`ck items`, `ck show W-012`).
- An `@handle` names an item created earlier in the same return (`log @h "..."`).
- Dates are full dates (`2026-12-01`). Never write an item number you made up; new items get theirs
  when the return is applied.
- `--dry-run` checks a return against the agenda as it is, without filing it.

## What happens next

`ck` prints where the return went:

- **Filed for the back end**, which applies it within a few minutes. This is also where it goes when
  the back end is late or stopped: it waits in the inbox safely; never apply it by hand meanwhile.
- **Applied at once**: the project's home is the Collab Kit folder and no back end was ever set up
  (level 1), so `ck` applies it itself.
- **Filed in this repository's `collab-kit/_returns/`**: the project's home is the repository, or the
  Collab Kit folder cannot be reached from here. Commit it with your work. A back end applies it once
  it reaches the main branch; a session that can reach the folder delivers it.

A refused return says exactly why (a failed title check, an unknown item, a bad date): fix it and
file again. Never edit the agenda's files by hand instead.

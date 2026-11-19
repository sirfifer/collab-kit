<!-- managed by Collab Kit 0.5.3: rendered from tools/kb/config.toml by kit/install.py apply. Edit the config or the kit, not this file. To make it the project's own, delete this line. -->
# The agenda: how items are kept

**What this folder is.** Everything that needs the author and Claude to work it out together. It is not knowledge (that is the rest of this folder), and not a to-do list for agents. It is the third of three channels (see `tools/kb/COLLABORATION-PATTERN.md` in the repository):

1. **Knowledge** flows out to conversations: what the project knows.
2. **Returns** flow back in: what conversations worked out (`_returns/`).
3. **The agenda** flows out: what still needs working out, with the context to start on it.

`00-AGENDA.md` is the list, most pressing first. It is generated; edit the item files.

## Kinds of item

| Kind | What it is | Example |
|---|---|---|
| `question` | A direct question only the author can answer, usually in a minute | Which of two names do we keep? |
| `decision` | A choice between options already laid out, usually in a proposal | Accept the proposed restructure of a document |
| `work-out` | Something to figure out together, over one or more conversations | How two parts of the design fit together |
| `hole` | Something missing: identified empty space between known pieces | Nothing says how A hands its result to B |
| `task` | Work an agent or the author simply does. Tracked only because it blocks, or waits on, the items above; never taken up in conversation | Run the first experiment |

## Priority: importance, blockers, effort

- **Importance:** 4 critical, 3 high, 2 medium, 1 low. How much it matters on its own.
- **Blocks:** the items that cannot be settled until this one is. An item that blocks something **inherits the importance of what it blocks** (a quick, medium question that holds up a critical decision is critical).
- **Effort:** `quick` (a minute or two), `session` (one conversation), `deep` (several).
- **The order** in `00-AGENDA.md`: inherited importance, then blockers before non-blockers, then how much each holds up, then quick before long. Items waiting on an open blocker are listed apart: they cannot be settled yet.

## An item file

`W-NNN-short-title.md`: TOML frontmatter between `+++` lines, then these sections.

- **What's needed:** the question, choice, or missing piece, stated so someone new to it understands.
- **Why it matters:** where it fits in the bigger picture, and what it holds up.
- **What we know so far:** candidate answers with the case for and against each, what has been ruled out. This is where a work-out accumulates across conversations.
- **Done when:** how we will know it is settled. Required for open items.
- **Log:** dated lines, newest last. Never rewrite history; add to it.

Frontmatter: `id`, `title`, `kind`, `importance`, `effort`, `status` (open, done, dropped), `stage` (work-outs and holes: not-started, exploring, converging), `blocks`, `refs` (what to read first: `OL#heading-key`, `OL`, `proposals/x.md`, `concepts/x.md`), `from` (where it came from: a capture code like `C01`), `created`, `updated`, `outcome` (required once done or dropped).

The build adds a generated block at the end of each file: where it stands (what it holds up, what it waits on) and the exact section files to read before talking.

## Rules

- **Numbers are permanent.** Never reuse, renumber, or delete an item. New items: `python3 tools/kb/kb.py new-item <kind> "<title>"` takes the next number.
- **Settled items stay,** with `status = "done"` (or `dropped`) and an `outcome` saying what was decided or learned and where it landed. They are the record.
- **Every open proposal has an open item** that refers to it. The build fails otherwise, so nothing waiting on the author is invisible.
- **Split big items.** When a decision bundles several separate calls, and one of them blocks something, give that one its own item.
- **From outside the repository** (voice, chat, another assistant, a person with only the mirror) you cannot edit these files. Send a return: `Relates to: settles W-001` or `progresses W-002`, or a new item as a return of type `question`, `hole`, or `todo`. Integration does the rest.
- `python3 tools/kb/kb.py agenda` prints the open items in order; `kb.py check` fails on a missing `Done when`, an unknown blocker, a blocking cycle, or a reference that does not resolve.

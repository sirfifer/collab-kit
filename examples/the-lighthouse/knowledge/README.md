# knowledge/: the project's knowledge base

This folder is the official, self-contained body of knowledge for **The Lighthouse**, organized so any collaborator, an AI or a person, can find and load **just the part it needs**. It is one of three channels: this knowledge goes out, returns come back in (`_returns/`), and the agenda (`agenda/`) says what needs working out together.

It is built to be used from outside the repository as well as inside it:

1. **Voice conversations in the Claude app**, the first interface and the most demanding one: hands-free, and able to open only whole files, by name. The folder is mirrored to nowhere yet (no mirror is configured in `tools/kb/config.toml`), and Claude reads it through the Google Drive connector.
2. **Other conversations reading the same mirror:** a typed chat in the Claude app or on the desktop, or another assistant that can read the files and write a text file back.
3. **Claude Code sessions in this repo**, through the `kb-*` skills and the `kb-librarian` agent.
4. **People**, browsing the repository or the mirror, and dropping a plain text return into `_returns/`.

An AI starts at [CLAUDE.md](CLAUDE.md). Everything is found from [01-INDEX.md](01-INDEX.md).

<!-- kit:start layout -->
## Layout: what is authored, what is generated

| Path | What | Edited by |
|---|---|---|
| `CLAUDE.md` | The entry point for any collaborator using the folder, with the voice profile for spoken conversations | hand (its `kit:` blocks are refreshed by the kit) |
| `02-RECENT.md` | Where things stand: most pressing agenda items, how recent returns landed, newest answers | **generated** |
| `01-INDEX.md` | Master lookup: documents, concepts with aliases, answered questions | **generated** |
| `concepts/` | The knowledge graph: one file per idea, typed relations, sources | hand (+ generated block at the end) |
| `kb/` | Answers to questions that took digging, kept for next time | hand (+ generated block) |
| `proposals/` | Suggested changes to the author's documents, waiting for a decision | hand |
| `captures/` | Returns from conversations, exactly as they arrived (never edited; cited as `C01`...) | integration job |
| `_returns/` | The way back in: conversations leave results here, each naming the project (only its README is from the repo; `refused/` holds returns that named another project) | conversations |
| `responses/` | Claude's considered response to each batch of returns: assessment, evidence, next steps, questions | integration |
| `agenda/` | What needs working out together: one file per item (`W-NNN-...`, with context, importance, blockers) and the ranked list `00-AGENDA.md`. Not knowledge | items: hand + integration; list: **generated** |
| `documents/<CODE>-<name>/` | Each document split into section files, plus `CODE-00-contents.md` | **generated** |
| `full/` | Each document as one file | **generated** |
| `graph.json` | The whole graph (documents, concepts, answers, agenda, edges) for tools | **generated** |

The documents themselves are authored where they always have been (`docs/`). [tools/kb/manifest.toml](../tools/kb/manifest.toml) lists which ones are in the official set, with a permanent code and a tier. Everything under `documents/` and `full/` is rebuilt from those sources by [tools/kb/kb.py](../tools/kb/kb.py). Project settings (names, tiers, mirror, schedule) are in [tools/kb/config.toml](../tools/kb/config.toml).

## Why it is shaped this way

- **The unit of loading is a file.** Through a Drive connector an AI can only open whole files, so "load section 5" has to mean "open one small file". Every document is split at its `##` headings (long sections split again at `###`), capped near 1,800 words. Each section file says where it sits, its neighbors, and which concepts it covers.
- **Line ranges for local work.** Every contents table and concept pointer also gives source line ranges, so a Claude Code session can load exactly those lines (`python3 tools/kb/kb.py show OL@40-90`).
- **One place to look.** `01-INDEX.md` combines the document list, every concept with every name it goes by, and every answered question, so a half-remembered idea has one lookup, not several.
- **A graph, kept as plain files.** Concepts carry typed relations (part of, depends on, contrasts with, analogy for...). The build writes the reverse links, so every concept shows what points at it. Relations pointing at concepts that do not exist yet are listed as open endpoints: the knowledge base's own known unknowns.
- **References that survive edits.** References name headings (`OL#heading-key`), not section numbers. If a heading is renamed, `kb.py check` fails and names the broken reference.

## How it stays current

- **During work** (primary): the `kb-integrate` skill folds a session's work in; `kb-capture` records single items; `kb-lookup` writes down any answer that took real digging (if it was not in the knowledge base, it is after you answer it).
- **The gate:** `python3 tools/kb/kb.py check` fails when any generated file is stale or any reference is broken.
- **Nightly** (safety net): [tools/kb/nightly.sh](../tools/kb/nightly.sh) checks in seconds whether anything changed and stops if not. Otherwise it rebuilds, runs one AI curation pass when sources changed or returns arrived, commits to branch `wt/kb-curator`, and mirrors this folder. Install with `tools/kb/launchd/install.sh --apply`.
- **Author documents are never edited automatically.** Changes to what the documents say go to `proposals/` for the author.
<!-- kit:end layout -->

<!-- kit:start interfaces -->
## Working on it from outside the repository

### Voice in the Claude app (the first interface)

The Claude app does **not** read a `CLAUDE.md` in a Drive folder on its own (that is a Claude Code habit). Something has to tell it to open the file. One line in your Claude preferences does that, so a short spoken phrase is enough. The same line works in a typed chat, on the phone or the desktop.

**Once:**

1. Connect Google Drive in the Claude app (Settings, Connectors).
2. Add this line to your personal preferences (Settings, Profile, "What personal preferences should Claude consider in responses?"), **once for all projects**: it points at the parent folder **Project Knowledge**, not at this project, so it never changes when a project is added. It applies to every chat, voice included, and only matters when a project comes up. `python3 tools/kb/kb.py preference-line | pbcopy` copies it:

   > When I say "let's work on" one of my projects, or name one: before answering, use Google Drive to open the file 00-START-HERE.md in my Drive folder "Project Knowledge" and follow it. It says which folder is which project and how to work with me there.

The parent's start file (`Project Knowledge/00-START-HERE.md`) lists every project and the names people say for it (for this one: "the lighthouse book", "the novel"). The nightly job keeps this project's entry current; change the names in `[project].spoken` in `tools/kb/config.toml`.

**Every time:** open the Claude app, tap voice, and say **"Let's work on the the lighthouse book."** Or name a topic right away: "the lighthouse book: let's talk about ..."

**Sending results back (the return channel).** A conversation saves what it worked out as plain text files in this project's `_returns/` folder (format in `CLAUDE.md`, "Sending results back"), each starting with `Project: the-lighthouse` and saying exactly what it builds on or changes. A return that names another project, or none, is moved to `_returns/refused/` and reported, never integrated. 15 quiet minutes after the last one arrives, the integration job (`tools/kb/nightly.sh --returns-only`, checked every 20 minutes) folds them in: knowledge base updates, a considered response in `responses/`, agenda items added or settled, proposals for the author's documents. The processed files move to `_returns/processed/`, and `02-RECENT.md` shows how each one landed. The full nightly run at 02:30 is the safety net.

**Without the preference line** (another account, someone else's phone), say it in full: *"Open 00-START-HERE.md in my Google Drive folder Project Knowledge, and follow it for the the-lighthouse project."*

**Optional:** a Claude project with the same line as its instructions does the same job for chats started inside the project.

### Other interfaces

Anything that can read files from the mirror and write a plain text file back can collaborate the same way: point it at `Project Knowledge/00-START-HERE.md` (or straight at this folder's `CLAUDE.md`), and have it send results to this project's `_returns/` in the format in `CLAUDE.md`, starting with `Project: the-lighthouse`. The voice profile in `CLAUDE.md` applies only to spoken conversations.
<!-- kit:end interfaces -->

## Adding a document to the official set

Add an entry to `tools/kb/manifest.toml` (new permanent code, tier, one-line `about`), then `python3 tools/kb/kb.py build`. For an append-only folder, use a `[[collections]]` entry instead.

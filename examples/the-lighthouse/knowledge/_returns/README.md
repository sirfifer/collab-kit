<!-- managed by Collab Kit 0.5.3: rendered from tools/kb/config.toml by kit/install.py apply. Edit the config or the kit, not this file. To make it the project's own, delete this line. -->
# _returns: what comes back from conversations

**This folder is not part of the knowledge base.** It is the opposite: the way back in. Everything else in this folder is shared knowledge, mirrored from the project and rebuilt automatically. This folder holds what conversations (voice in the Claude app, or any other tool using this folder) send *back*: ideas, decisions, research, drafts, questions, holes, to-do items, and progress on agenda items.

**How a return works**
- One plain text file per item, named `YYYY-MM-DD-short-topic.txt`, created in **this** folder (by its id: every project has a folder named `_returns`). Never edit or delete a file here; send a new one instead (a Drive connector can create files but not edit them).
- **The first line is `Project: the-lighthouse`.** A return without it, or naming another project, is not integrated: it is moved to `refused/` here and reported to the author.
- An optional `From:` line says who the return is from, when it is not the author. The response names it.
- The format is in `CLAUDE.md`, under "Sending results back." Every return says what it relates to (builds-on, refines, contradicts, and so on, with a reference) so it can be integrated accurately.
- About 15 minutes after the last return of a conversation arrives, the project's integration job picks them up. It folds them into the knowledge base, writes a considered response in `responses/`, adds or updates items on the agenda (`agenda/`), and moves the processed files to `processed/` here.
- The next conversation can see how each return landed in `02-RECENT.md`.

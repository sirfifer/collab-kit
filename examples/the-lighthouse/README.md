# The Lighthouse: a sample project

A made-up novel in eight chapters, set up with Collab Kit, so you can see the three channels without
installing anything. A lighthouse keeper's daughter, Maren; her brother Tobias, who may or may not
have known the light would fail; and a conversation that found the draft contradicting itself in
chapter four.

Five minutes, in this order:

1. **The project's own documents**: [docs/outline.md](docs/outline.md), then
   [docs/chapter-04.md](docs/chapter-04.md). This is what the author writes. Nothing else edits it.
2. **Knowledge going out**: [knowledge/01-INDEX.md](knowledge/01-INDEX.md), the map a conversation
   opens first. Each document is split into small files under `knowledge/documents/`, so a
   conversation can load just "where Tobias was" (`CH-03`) and nothing else. Concepts such as
   [Tobias](knowledge/concepts/tobias-hale.md) say where each idea is discussed.
3. **A return coming back**: [the capture](knowledge/captures/2026-11-10-tobias-and-the-logbook.txt).
   A voice conversation worked out that Tobias cannot have been at sea, and saved this file to the
   project's `_returns` folder in Drive. The nightly job brought it in as `C01`.
4. **What was made of it**: the [response](knowledge/responses/2026-11-10-tobias-and-the-logbook.md)
   (the curator's considered answer), a [proposal](knowledge/proposals/2026-11-10-chapter-four-timeline.md)
   for the author's chapter (never applied without them), and the answer
   [KB-0001](knowledge/kb/KB-0001-where-was-tobias-on-the-night-of-the-storm.md).
5. **The agenda going out**: [knowledge/agenda/00-AGENDA.md](knowledge/agenda/00-AGENDA.md). A
   question (W-001) blocks the chapter-four decision (W-003), and so does a quick task (W-005), so
   both rank above their own importance. W-002 is a hole: the winter the outline skips.
   [knowledge/02-RECENT.md](knowledge/02-RECENT.md) is what a conversation reads when the author
   says "where were we?".

[knowledge/CLAUDE.md](knowledge/CLAUDE.md) is what a conversation follows: how to find things, how to
talk about them, and how to send a return. It and the other READMEs are rendered by the kit.

**What is the project's, what is the kit's.** The project wrote `docs/`, `tools/kb/config.toml`,
`tools/kb/manifest.toml`, and in `knowledge/` the concepts, the answer, the agenda items, the capture,
the response, and the proposal (in a real project the nightly pass writes most of those). Everything
else in `knowledge/` the kit rendered or built. `tests/refresh-example.sh` rebuilds it, and
`tests/dry-run-install.sh` fails if the copy here is out of date. This project chose
`captures_in_git = true`, so the return is in the repository; see the kit's README, "What becomes
visible, and to whom".

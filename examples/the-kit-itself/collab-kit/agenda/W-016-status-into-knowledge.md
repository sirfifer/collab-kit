+++
id = "W-016"
title = "Ongoing work writes its status into knowledge"
kind = "task"
importance = 2
status = "open"
due = ""
project = "collab-kit"
+++

## What's needed
When the back end, its sub-agents, Claude Code sessions, or research runs are working on something, they regularly write its status into the knowledge folder: the project's `knowledge/` for project work, the top-level `knowledge/` when it is about no single project or several. A voice conversation must always know what is going on without Richard relaying it.

## What we know so far
Includes a backfill: work already under way (e.g. the ChatGPT and Gemini research, W-008) gets a status entry now.

## Done when
Ongoing work reliably shows up in knowledge, and the backfill is done.

## Log
- 2026-11-14: created from the W-008 discussion. Richard: "you should know what's going on"; "ongoing work regularly updates the knowledge, either at the top level, if it's relevant, or for the project in question."
- 2026-11-15: Built: Claude Code sessions file status with ck status, and a check at the end of a turn asks them to when they changed files and recorded nothing; the back end writes its health into the top-level start file. The overnight build's own status is in knowledge/status.md. (return 2026-11-15-0844-overnight-build-agenda-updates-1406, from Claude Code in collab-kit (wt/v05-dogfood))
- 2026-11-17: 2026-11-16: correction to the 2026-11-15 entry: since 0.5.1 the back end's health is on the agenda's front page, not in the start file. Still to prove: that it is reliable once the back end runs. (return 2026-11-17-0151-claude-code-0-5-2, from Claude Code on the MacBook (collab-kit, wt/v052-nail-down))

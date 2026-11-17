+++
id = "W-002"
title = "Run the hands-free voice test of the Drive actions"
kind = "task"
importance = 1
status = "settled"
due = ""
project = "collab-kit"
+++

## What's needed
In voice mode: open the start file, list a folder, create a plain .md file (not a Google Doc), rename it, move it, trash it, read a file aloud word for word.

## What we know so far
Tested 2026-11-14 evening in Claude voice mode, Google Drive connector on the owner's account. All steps pass:
- open the start file, list folders by parentId;
- create plain .md with conversion disabled (stays text/markdown);
- create folders, rename, move (versioning into `_versions/`);
- trash (the trash tool had to be loaded before first use);
- read a file aloud word for word.
Findings: a per-reply cap on tool calls (about seven worked; more refused); some calls paused for approval or ran in the background before returning; in-place content edit still impossible (W-013).

## Done when
Each step is known to work or not by voice, and the article says so.

## Log
- 2026-11-14: item created when Collab Kit 0.5 was set up.
- 2026-11-14: settled; every step works by voice. The article should say so.

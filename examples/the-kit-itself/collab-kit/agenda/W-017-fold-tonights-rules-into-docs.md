+++
id = "W-017"
title = "Fold the 2026-11-14 evening decisions into the start files and design"
kind = "task"
importance = 2
status = "settled"
due = "2026-11-15"
project = "collab-kit"
outcome = "The start-file templates in the repository now carry every 2026-11-14 evening decision (WIP and save points, retention and pinning, the reply cap, moving items, push requests, status files, the kit version line); the design record has them in section 17."
+++

## What's needed
Bring these into both start-file templates, DESIGN-0.5 (or DESIGN), and the repository:
- WIP channel and batched saves (already in Richard's live start files, 2026-11-14);
- the new version retention and pinning (W-011);
- kit version line in every start file (W-005);
- approved pushes and when to suggest one (W-015);
- status of ongoing work into knowledge (W-016);
- no separate top-level subfolder (W-014);
- moving an item between projects (W-012);
- sharing removed from 0.5 entirely (W-004);
- work within the assistant's per-reply action cap automatically: in voice, one reply can make only about seven tool calls (per reply, not per session; assistant side, not Google's). WIP notes one per turn never hit it; at save time, size saves to the cap without asking, split a big save across consecutive replies, and roll a thread's many notes into one combined WIP note first. Richard: "if you've got a limit and we know what it is, then we need to adjust to it... that should be automatic."

## What we know so far
Details in the items above and in `_returns/2026-11-14-1912-wip-and-batched-saves.md`.

Done 2026-11-15 by the Claude Code design session:
- DESIGN-0.5 section 17 holds every item above (repository branch `wt/v05-design`; knowledge copy updated).
- Live start files: the top level has all of them (WIP, retention and pinning, the reply cap, moving
  items, push requests, status files, "Collab Kit 0.5"); model-fit and the video pipeline have `WIP/`
  folders and the WIP rules; collab-kit already had them.
- W-016 backfill: `knowledge/status.md` here and at the top level.

Left: the start-file templates in the repository, which arrive with the 0.5 engine.

## Done when
The templates and design match what was decided.

## Log
- 2026-11-14: created during the voice agenda review.
- 2026-11-14: action-cap rule, W-012 and W-004 added.
- 2026-11-15: design record and live start files done (Claude Code session); repository templates left for the engine work.
- 2026-11-15: settled: The start-file templates in the repository now carry every 2026-11-14 evening decision (WIP and save points, retention and pinning, the reply cap, moving items, push requests, status files, the kit version line); the design record has them in section 17. (return 2026-11-15-0844-overnight-build-agenda-updates-1406, from Claude Code in collab-kit (wt/v05-dogfood))

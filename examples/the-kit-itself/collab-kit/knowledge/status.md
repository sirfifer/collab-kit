# collab-kit: what is going on

Written by work running outside conversations (Claude Code sessions, research runs, later the back end).
Newest first. Last updated 2026-11-15 21:17 UTC.

## 2026-11-15 21:17 UTC, Claude Code in collab-kit (wt/v05-dogfood): Collab Kit 0.5.0 merged locally

The third review (a check of the overnight fixes) found more gaps; all are fixed with tests (84 tests pass). The kit's local main is now 0.5.0 (merged, not pushed). The project branches and this Mac's user-level hooks carry the same engine. Next steps are in knowledge/go-live-0.5.md.

## 2026-11-15 08:44 UTC, Claude Code in collab-kit (wt/v05-dogfood): Collab Kit 0.5.0 built overnight

Collab Kit 0.5.0 is built and tested; not live yet.

- Built: returns with a grammar (applied whole or not at all, once, undoable); the back end (scripts only: inboxes, repository-homed projects, mirror, health, what is pressing across projects); the kit made native in every project (agents get a brief at session start, put questions on the agenda, and record their work without being asked); the 0.4 to 0.5 migration; scheduling for macOS, Linux, and Windows.
- Tested: 72 unit and end-to-end tests on Python 3.11 and 3.14; the 0.4 suite still passes; and the real Claude Code, twice: the brief reached the agent, and an ordinary task got recorded here unasked.
- Two sceptical reviews found real problems (one a security hole: a forged file could have made the back end write outside the folder). All fixed, each with a test. A third review is checking the fixes.
- Installed on unmerged branches in model-fit, the video pipeline, and the framework (migrated to the 0.5 layout); this note was filed by the kit's own command from the collab-kit repository.
- Waiting on Richard: merge the branches, set up the Studio back end, point the Claude app at the Collab Kit folder, publish the repository. The steps are in knowledge/go-live-0.5.md; notes for the article in knowledge/article-deltas-2026-11-15.md.
- Not live: no back end runs; nothing was pushed.

## 2026-11-15, Claude Code session on the MacBook (the 0.5 design session)

- **Done:** the first phone session's decisions (W-017) are folded into the design record
  (`DESIGN-0.5.md` section 17; the copy in this knowledge folder is updated) and into the live start
  files: the top level (WIP, retention and pinning, the seven-call reply cap, moving items, push
  requests, this status file, "Collab Kit 0.5" in the title) and the model-fit and video-pipeline
  projects (now with `WIP/` folders).
- **Still to fold in:** the start-file templates in the repository (they arrive with the 0.5 engine).
- **Reopened:** W-014. Its original question (does Collab Kit's own `collab-kit/` folder, with its
  agenda and returns, go into the public repository?) is still open; the phone session settled a
  different question (no top-level subfolder), which was already the design.
- **Waiting on Richard:** stopping the framework's old 0.4 jobs on the MacBook (two Terminal commands),
  the preference line in the Claude app (the old start file redirects here meanwhile), then archiving
  the old `Project Knowledge` folder.

## Research: ChatGPT and Gemini (W-008)

- Started 2026-11-14 about 21:40 UTC as a background research run. **No result has come back yet**;
  it may have stalled. If nothing arrives by the next session, it is run again.

## Building 0.5

- Architecture locked 2026-11-14 (two rounds of simulation). The engine work (the Studio back end,
  W-006) has not started; the article (W-001) comes first.

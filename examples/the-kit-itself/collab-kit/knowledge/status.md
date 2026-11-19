# collab-kit: what is going on

Written by work running outside conversations (Claude Code sessions, research runs, later the back end).
Newest first. Last updated 2026-11-19 20:53 UTC.

## 2026-11-19 20:53 UTC, Claude Code on the MacBook (collab-kit): The Studio back end is live (W-006 done); the kit's own install and docs get a full check

2026-11-19: the Studio back end is live and serving the framework (W-006 settled). Collab Kit's own project gets a full check now: its install at the current version, the design against the code, and the docs for AI agents.

## 2026-11-19 05:41 UTC, Claude Code, working in knowledge-distillation-framework: The Studio back end runs (W-006); one kit fix was needed and is on the kit's main line, not released

2026-11-18: the Studio back end is installed and running (W-006). Richard ran the setup script; it stopped at the account check, because rclone has no config userinfo for Google Drive, so a back end over rclone refused every run. Fixed in the kit at commit 6fef702 on both Macs (the check now reads who owns the folder's start file with lsjson --metadata; 123 tests pass; changelog entry under Not yet released, VERSION unchanged). knowledge-distillation-framework is the first repository-homed project on it: a return filed in Drive was applied, pushed and mirrored back in 4 to 10 minutes. A full pass takes about 20 minutes because Drive is read one file at a time; that is worth a look. The used setup script is archived on the Studio.

## 2026-11-17 01:45 UTC, Claude Code on the MacBook (collab-kit, wt/v052-nail-down): Collab Kit 0.5.2: the six voice returns of 2026-11-15 are in; W-019 merged; the Studio prepared

Collab Kit 0.5.2 is in the kit's local main (not pushed): the agenda first in every start file; a catalog of every project; returns applied within a minute or two once a back end runs; an optional push to the phone; voice returns with a note after their changes are accepted. W-019 is merged. The Studio is prepared; its setup script waits for Richard.

## 2026-11-15 23:19 UTC, Claude Code in collab-kit (wt/v05-dogfood): Collab Kit 0.5 merged into the local main of model-fit, dialogue-video-pipeline,

Collab Kit 0.5 merged into the local main of model-fit, dialogue-video-pipeline, knowledge-distillation-framework and the owner's private instructions repository (fast-forward, not pushed); the kit's doctor passes in each. Go-live step 1 done; next: the top-level start file's health block, then the Studio back end.

## 2026-11-15 22:57 UTC, Claude Code on the MacBook (worktree wt/returns-w014-exampl…: The public example snapshot is built (on a branch, not merged)

Both returns in this inbox are applied (W-014 settled; W-018 built). The engine now accepts a kind word as a new item (the voice return used one). The public example is built at examples/the-kit-itself on branch wt/returns-w014-example, not merged; W-019 asks for the review. Files the phone writes cannot be read on the MacBook through Drive for desktop (top-level W-003).

## 2026-11-15 21:17 UTC, Claude Code in collab-kit (wt/v05-dogfood): Collab Kit 0.5.0 merged locally

The third review (a check of the overnight fixes) found more gaps; all are fixed with tests (84 tests pass). The kit's local main is now 0.5.0 (merged, not pushed). The project branches and this Mac's user-level hooks carry the same engine. Next steps are in knowledge/go-live-0.5.md.

## 2026-11-15 08:44 UTC, Claude Code in collab-kit (wt/v05-dogfood): Collab Kit 0.5.0 built overnight

Collab Kit 0.5.0 is built and tested; not live yet.

- Built: returns with a grammar (applied whole or not at all, once, undoable); the back end (scripts only: inboxes, repository-homed projects, mirror, health, what is pressing across projects); the kit made native in every project (agents get a brief at session start, put questions on the agenda, and record their work without being asked); the 0.4 to 0.5 migration; scheduling for macOS, Linux, and Windows.
- Tested: 72 unit and end-to-end tests on Python 3.11 and 3.14; the 0.4 suite still passes; and the real Claude Code, twice: the brief reached the agent, and an ordinary task got recorded here unasked.
- Two sceptical reviews found real problems (one a security hole: a forged file could have made the back end write outside the folder). All fixed, each with a test. A third review is checking the fixes.
- Installed on unmerged branches in model-fit, the video pipeline, and the framework (migrated to the 0.5 layout); this note was filed by the kit's own command from the collab-kit repository.
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


+++
id = "W-014"
title = "Where Collab Kit's own collab-kit folder lives"
kind = "decision"
importance = 4
status = "settled"
due = ""
project = "collab-kit"
outcome = "Richard decided 2026-11-15: the kit's own live channels (agenda, returns, status, WIP) stay out of the public repository; their home is the Drive folder. Instead, the repository carries a static working example laid out exactly as it would sit in someone else's repository. It must be a sanitized snapshot of our real work, not a made-up example. It has to be maintained: any change to the kit that affects folder structure or how things work must be reflected in the example, so it is never stale or contradictory to how the kit actually works."
+++

## What's needed
Collab Kit's repository is public. When the back end brings this project's `collab-kit/` folder into
the repository (its agenda, returns, knowledge, WIP), does that folder go into the public repository,
or stay private (for example, only in Drive, or in a private repository)?

## What we know so far
- The other question that got attached here, whether the top level has its own subfolder, is settled
  (no subfolder; that was already the design).
- This project's agenda and returns hold Richard's working thoughts, verbatim quotes, and plans.

## Done when
Richard decides where this project's own `collab-kit/` lives.

## Log
- 2026-11-14: item created when Collab Kit 0.5 was set up.
- 2026-11-14: settled by Richard on the top-level subfolder question; see `_returns/2026-11-14-1912-wip-and-batched-saves.md`.
- 2026-11-15: reopened by the design session: the subfolder question was a different one; the original question (public repository or private) is still open.
- 2026-11-15: Overnight default (Richard's go-ahead): this project's own channels stay out of the public repository; home is this Drive folder. The kit's install into its own repository is on branch wt/v05-dogfood, separate, because it adds a Collab Kit section to the public CLAUDE.md. (return 2026-11-15-0844-overnight-build-agenda-updates-1406, from Claude Code in collab-kit (wt/v05-dogfood))
- 2026-11-15: settled: Richard decided 2026-11-15: the kit's own live channels (agenda, returns, status, WIP) stay out of the public repository; their home is the Drive folder. Instead, the repository carries a static working example laid out exactly as it would sit in someone else's repository. It must be a sanitized snapshot of our real work, not a made-up example. It has to be maintained: any change to the kit that affects folder structure or how things work must be reflected in the example, so it is never stale or contradictory to how the kit actually works. (return 2026-11-15-voice-w014-public-example, from Claude voice session with Richard)

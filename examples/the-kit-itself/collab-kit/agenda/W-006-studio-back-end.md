+++
id = "W-006"
title = "Make the Studio the back end"
kind = "task"
importance = 2
status = "in-progress"
due = "2026-11-15"
project = "collab-kit"
+++

## What's needed
Prerequisites before it goes live: lease and item counter in git, the back end's own clone and standing push authorization for `collab-kit/` only, Claude Code filing returns instead of minting numbers, the 0.4 path map, a generated list of every repository, the private-to-public guard, account checks.

## What we know so far
All decided in DESIGN-0.5 section 16. Build approved by Richard 2026-11-14; not built yet. Approved pushes of project work are a separate item (W-015).

## Done when
The Studio back end runs with all prerequisites in place.

## Log
- 2026-11-14: item created when Collab Kit 0.5 was set up.
- 2026-11-14: Richard approved the build; the back end takes it from here. Due with the Sunday delivery.
- 2026-11-15: Back end built and tested overnight (ck backend run; install.py backend writes the config and the launchd job; through collab-kit-runner on a Drive for desktop folder). Not running yet: setting it up on the Studio is step 3 of knowledge/go-live-0.5.md. (return 2026-11-15-0844-overnight-build-agenda-updates-1406, from Claude Code in collab-kit (wt/v05-dogfood))

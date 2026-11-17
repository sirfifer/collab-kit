+++
id = "W-006"
title = "Make the Studio the back end"
kind = "task"
importance = 2
status = "in-progress"
due = ""
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
- 2026-11-17: Richard, 2026-11-15 (voice): go ahead with setting up the Studio as the back end. Do everything that does not need him now: go-live step 2 (install.py top), getting the kit onto the Studio, install.py machine, the backend dry run and backend.toml (account, local_roots, deny list, the framework project entry). For the parts that need him (his permissions, sign-ins, macOS prompts such as allowing access to Google Drive files or Full Disk Access for the runner), the standard is a single shell script left on the Studio's desktop that he runs himself; it should say plainly what it will ask and check the result (launchd state, log, health block). Report on the top-level agenda when the script is ready for him and when the back end is healthy. (return 2026-11-15-1958-w006-proceed-studio-desktop-script, from Richard (voice))
- 2026-11-17: 2026-11-16: the kit is on the Studio (~/dev/collab-kit) and its backend.toml is written: rclone remote (the Drive API, W-004), account owner@example.com, local roots, the deny list. Richard's part: run 'Collab Kit back end setup.command' on the Studio's desktop (one Google sign-in; optional Pushover keys). The framework joins after its main is pushed (Richard's yes). knowledge/go-live-0.5.md has the steps. (return 2026-11-17-0151-claude-code-0-5-2, from Claude Code on the MacBook (collab-kit, wt/v052-nail-down))
- 2026-11-17: set due to (none) (return 2026-11-17-0151-claude-code-0-5-2, from Claude Code on the MacBook (collab-kit, wt/v052-nail-down))

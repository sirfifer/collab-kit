+++
id = "W-007"
title = "GitHub Actions as a back end, with rclone"
kind = "task"
importance = 3
status = "open"
due = "2026-11-15"
project = "collab-kit"
+++

## What's needed
Level 2 without a machine: a private runner repository, hourly runs, a separate bot Google account shared on Collab Kit only, rclone pinned and checksum-verified, our own Google sign-in app published to production.

## What we know so far
rclone accepted with conditions (pin 1.76.0+, never selfupdate, only list/copy/move/mkdir, thin wrapper).

## Done when
Richard says it is settled.

## Log
- 2026-11-14: item created when Collab Kit 0.5 was set up.
- 2026-11-14: Richard: keep it on for the Sunday delivery.
- 2026-11-15: Not built. rclone intake review done: accept with conditions (docs/rclone-intake.md); the store meets them. Still needs the bot Google account and our own published OAuth client. (return 2026-11-15-0844-overnight-build-agenda-updates-1406, from Claude Code in collab-kit (wt/v05-dogfood))

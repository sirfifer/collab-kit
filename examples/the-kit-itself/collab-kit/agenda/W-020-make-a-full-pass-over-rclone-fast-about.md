+++
id = "W-020"
title = "Make a full pass over rclone fast (about 20 minutes now)"
kind = "task"
importance = 2
status = "open"
due = ""
project = ""
+++

## What's needed
Make a full pass over rclone fast (about 20 minutes now)

## What we know so far

## Done when

## Log
- 2026-11-19: created (return 2026-11-19-2055-back-end-live-and-full-check, from Claude Code on the MacBook (collab-kit))
- 2026-11-19: Measured 2026-11-18 on the Studio: a full pass takes about 20 minutes because the back end reads Drive one file at a time, one rclone call each. Every arriving return starts a full pass, so a return can wait that long. Look at reading the folder in one call per pass. (return 2026-11-19-2055-back-end-live-and-full-check, from Claude Code on the MacBook (collab-kit))

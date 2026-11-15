+++
id = "W-005"
title = "Install and migration logistics for other people"
kind = "work-out"
importance = 2
status = "open"
due = ""
project = "collab-kit"
+++

## What's needed
A version-upgrade pattern for everyone from the 0.5 release on, and (separately) how to move between levels (folder, back end, repository, a repository per project), safely.

## What we know so far
- Nobody but Richard used 0.4. Public migration starts from the 0.5 release (2026-11-15). Richard's own 0.4 move is the one-time script in DESIGN-0.5 section 15.
- Working pattern (agreed 2026-11-14, not final): every start file states its kit version ("Collab Kit 0.5"); each release ships one migration from the previous version only, as a script for back-end users and as plain written steps a conversation can follow for folder-only users.
- Moving up a level is separate from version upgrades and still open. Earlier sketch: flip a mode line in each start file, wait for the lease, import, then reverse direction.

## Done when
Richard says it is settled.

## Log
- 2026-11-14: item created when Collab Kit 0.5 was set up.
- 2026-11-14: reframed by Richard: no 0.4 users to migrate; pattern adjusted as above; no final decision yet.
- 2026-11-15: Built: install.py top, machine, project, backend, and migrate-04; a collab-kit-upgrade skill and the session brief's kit-update notice; CHANGELOG.md names each release's migration. Moving between levels is still open. (return 2026-11-15-0844-overnight-build-agenda-updates-1406, from Claude Code in collab-kit (wt/v05-dogfood))

Project: collab-kit
Id: 2026-11-15-0844-collab-kit-0-5-0-built-overnight-b466
From: Claude Code in collab-kit (wt/v05-dogfood)
Type: status
Topic: Collab Kit 0.5.0 built overnight

Changes v1:
status
```
Collab Kit 0.5.0 is built and tested; not live yet.

- Built: returns with a grammar (applied whole or not at all, once, undoable); the back end (scripts only: inboxes, repository-homed projects, mirror, health, what is pressing across projects); the kit made native in every project (agents get a brief at session start, put questions on the agenda, and record their work without being asked); the 0.4 to 0.5 migration; scheduling for macOS, Linux, and Windows.
- Tested: 72 unit and end-to-end tests on Python 3.11 and 3.14; the 0.4 suite still passes; and the real Claude Code, twice: the brief reached the agent, and an ordinary task got recorded here unasked.
- Two sceptical reviews found real problems (one a security hole: a forged file could have made the back end write outside the folder). All fixed, each with a test. A third review is checking the fixes.
- Installed on unmerged branches in model-fit, the video pipeline, and the framework (migrated to the 0.5 layout); this note was filed by the kit's own command from the collab-kit repository.
- Not live: no back end runs; nothing was pushed.
```
End.

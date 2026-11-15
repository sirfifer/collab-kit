Project: collab-kit
From: Richard
Type: decision
Topic: WIP folder and batched saves (checkpoint notes instead of versioning every small edit)
What was worked out:
Problem: with the Google Drive connector, every edit is the versioning dance (create, rename, move), several tool calls each. Doing that for every small change by voice is slow and fragile. Richard prefers to work within the current Drive limits rather than switch storage.

Decisions:
1. New channel folder WIP/ (work in progress) beside _returns/ and agenda/, at the top level and in every project's collab-kit/ folder. Created 2026-11-14 at the top level and in the collab-kit project. Main use for now: checkpoint notes; other uses will emerge.
2. The conversation is the working copy; a save is the commit. Small changes are batched, not versioned one by one.
3. Checkpoint notes: while working, write short plain files to WIP/, one call each, holding only what changed or was decided. Name: YYYY-MM-DD-HHMM-<thread-slug>-NN.md, where the date and time are when the thread started, the slug names the doc or part of the system, and NN counts up (01, 02, ...).
4. Save points (stitch the notes into the target, as a new file or by versioning an existing doc): when we move on to another doc or area; when something is settled; when Richard says save; at a safety cap of about five or six changes or ten minutes on one thing; always before wrapping up. Say "saving now" before writing; say what is unsaved if asked.
5. After a stitch, the thread's notes go to Drive trash (recoverable for 30 days), not deleted outright.
6. Leftover notes in WIP/ mean an unfinished thread (e.g. a dropped call): the next conversation offers to finish the stitch.
7. Backstop: the conversation transcript itself persists and can be searched by a later conversation.
8. WIP/ is kept apart from _returns/ so a back end never applies half-finished thinking. Back end ignores WIP/.

Also settled: there is no separate Collab Kit subfolder at the top level; the top-level start file, _returns/, agenda/, knowledge/ and projects/ sit directly in the parent folder (closes W-014's premise). Richard says most other collab-kit agenda items from 2026-11-14 are already settled; they need updating.
Relates to: DESIGN-0.5 sections 2, 6 and 16; W-011 (document versions); W-013 (in-place editing); W-014; both 00-START-HERE.md files (need the WIP rules added)
Verbatim: "we can work for a little while and then save the results"; "let's call it WIP, for work in progress"
End.

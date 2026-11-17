+++
id = "W-015"
title = "Approved pushes of project work to GitHub"
kind = "task"
importance = 2
status = "open"
due = ""
project = "collab-kit"
+++

## What's needed
Long-term real work needs the back end to commit and push project work to GitHub, but only with the user's approval given in a Collab Kit conversation.

## What we know so far
Agreed 2026-11-14:
- On Richard's yes, the conversation files a return with a push request carrying his approval verbatim; a back-end script commits and pushes exactly what was approved. Judgment stays with the person; the back end stays clerical.
- The voice agent is not shy: it suggests a push at natural points (a milestone, a natural break, a good stretch of time since the last push), like save points one level up.
- In addition to the standing authorization to push `collab-kit/` only (DESIGN-0.5 section 16).

## Done when
The push change is in the returns grammar, the script exists, and the start files tell conversations when to suggest a push.

## Log
- 2026-11-14: created from the W-006 discussion. Richard: "it needs to be approved by the user interacting with CollabKit"; "not be shy about maybe asking every once in a while."
- 2026-11-15: push-request in a return now creates an agenda task carrying the approval verbatim; the back end does not push project work by itself yet. (return 2026-11-15-0844-overnight-build-agenda-updates-1406, from Claude Code in collab-kit (wt/v05-dogfood))

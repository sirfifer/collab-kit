+++
id = "W-019"
title = "Review and merge the public example branch"
kind = "decision"
importance = 2
status = "settled"
due = ""
project = ""
+++

## What's needed
The branch `wt/returns-w014-example` of the collab-kit repository holds three things for Richard to review before merging:
1. The grammar change: a kind word starts a new item (`task "title" importance=3 "what's needed"`). The voice return for W-014 was written that way and the old grammar refused it.
2. The public example, `examples/the-kit-itself/`: read it as a stranger would. The rules catch accounts and named private words, not every private thought.
3. Two small test fixes: a `.gitignore`, and the home-path and email guards now skip `__pycache__` (they failed locally whenever the unit tests ran first, on main too).

## Decisions only Richard can make
- **Project names stay in**: model-fit, the framework (knowledge-distillation-framework, a private repository; its address is shown as github.com/owner/...), and the video pipeline appear in the agenda and the go-live notes. Fine to publish, or replace them?
- **Where the private rules live**: only on the MacBook (`~/.config/collab-kit/public-example.toml`). Keep them there, or also in a private repository so the Studio has them?
- The snapshot was taken at 23:20 UTC on 2026-11-15; refresh it just before publishing so it includes tonight's items.

## What we know so far
- Checked in a clean clone: 89 unit tests pass; all 183 checks of the 0.4 dry-run pass, including the private-words check; the example check passes on a machine with no Collab Kit config (as CI has).
- The privacy guard caught a real case: the go-live notes named a private commercial project; the example says "names from a private project" instead.

## Done when
Richard has reviewed the branch and it is merged (or changed as he asks).

## Log
- 2026-11-15: created (return 2026-11-15-2330-claude-code-public-example-built, from Claude Code on the MacBook (worktree wt/returns-w014-exampl…)
- 2026-11-15: Correction: the snapshot was taken at about 22:50 UTC on 2026-11-15, not 23:20 (two of tonight's return ids carry the wrong time too: 2330 and 2335 were written at about 22:55). (return 2026-11-15-2259-claude-code-w019-time, from Claude Code on the MacBook (worktree wt/returns-w014-exampl…)
- 2026-11-15: The branch now also holds a fourth change to review: the folder store reads cloud-only placeholder files (files a phone wrote) from inside Claude Code, where every such read used to fail with 'Resource deadlock avoided'. Root cause and the read-path decision: top-level W-003 (settled) and W-004. 90 tests pass. (return 2026-11-15-2312-claude-code-w019-store-fix, from Claude Code on the MacBook (worktree wt/returns-w014-exampl…)

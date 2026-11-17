+++
id = "W-018"
title = "Public example snapshot"
kind = "task"
importance = 3
status = "in-progress"
due = ""
project = ""
+++

## What's needed
Build what W-014 settled. Proposed approach (Claude's suggestion, Richard said yes to writing it up): a script takes a fresh snapshot of the live Drive folder, sanitizes it (private decisions, account details, anything the private-to-public guard flags), and writes it into the repository's example location; a check fails any release where the example's structure does not match what the kit currently generates. Decide where the example lives in the repository and how sanitizing rules are kept.

## Log
- 2026-11-15: created (return 2026-11-15-voice-w014-public-example, from Claude voice session with Richard)
- 2026-11-15: Started by Claude Code on the MacBook. The voice return that created this item used 'task "..."' in its Changes block, which the grammar refused; the engine now accepts a kind word (task, question, decision, work-out, hole) as a new item, and a second quoted text as What's needed (commit on branch wt/returns-w014-example, test added, 85 tests pass). The voice return itself was applied unchanged. (return 2026-11-15-2250-claude-code-inbox-started, from Claude Code on the MacBook (worktree wt/returns-w014-exampl…)
- 2026-11-15: set status to in-progress (return 2026-11-15-2250-claude-code-inbox-started, from Claude Code on the MacBook (worktree wt/returns-w014-exampl…)

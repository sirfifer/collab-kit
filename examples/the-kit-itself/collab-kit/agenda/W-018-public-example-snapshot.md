+++
id = "W-018"
title = "Public example snapshot"
kind = "task"
importance = 3
status = "settled"
due = ""
project = ""
outcome = "Built 2026-11-15 on branch wt/returns-w014-example of the collab-kit repository (not merged, not pushed). The example lives at examples/the-kit-itself: the generated part (what install.py project --home repo writes) plus a sanitized snapshot of this folder's agenda, applied returns with ledgers, and knowledge. tests/public_example.py refresh takes the snapshot; check fails in the unit tests and in the release workflow whenever the example is not what the kit generates or reads. Sanitizing: generic rules in the script (accounts, local paths, Drive ids); the private never-publish words live on the MacBook only, in ~/.config/collab-kit/public-example.toml. Review and merge: W-019."
+++

## What's needed
Build what W-014 settled. Proposed approach (Claude's suggestion, Richard said yes to writing it up): a script takes a fresh snapshot of the live Drive folder, sanitizes it (private decisions, account details, anything the private-to-public guard flags), and writes it into the repository's example location; a check fails any release where the example's structure does not match what the kit currently generates. Decide where the example lives in the repository and how sanitizing rules are kept.

## Log
- 2026-11-15: created (return 2026-11-15-voice-w014-public-example, from Claude voice session with Richard)
- 2026-11-15: Started by Claude Code on the MacBook. The voice return that created this item used 'task "..."' in its Changes block, which the grammar refused; the engine now accepts a kind word (task, question, decision, work-out, hole) as a new item, and a second quoted text as What's needed (commit on branch wt/returns-w014-example, test added, 85 tests pass). The voice return itself was applied unchanged. (return 2026-11-15-2250-claude-code-inbox-started, from Claude Code on the MacBook (worktree wt/returns-w014-exampl…)
- 2026-11-15: set status to in-progress (return 2026-11-15-2250-claude-code-inbox-started, from Claude Code on the MacBook (worktree wt/returns-w014-exampl…)
- 2026-11-15: settled: Built 2026-11-15 on branch wt/returns-w014-example of the collab-kit repository (not merged, not pushed). The example lives at examples/the-kit-itself: the generated part (what install.py project --home repo writes) plus a sanitized snapshot of this folder's agenda, applied returns with ledgers, and knowledge. tests/public_example.py refresh takes the snapshot; check fails in the unit tests and in the release workflow whenever the example is not what the kit generates or reads. Sanitizing: generic rules in the script (accounts, local paths, Drive ids); the private never-publish words live on the MacBook only, in ~/.config/collab-kit/public-example.toml. Review and merge: W-019. (return 2026-11-15-2330-claude-code-public-example-built, from Claude Code on the MacBook (worktree wt/returns-w014-exampl…)

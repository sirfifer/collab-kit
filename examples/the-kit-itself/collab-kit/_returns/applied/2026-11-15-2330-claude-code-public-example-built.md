Project: collab-kit
Id: 2026-11-15-2330-claude-code-public-example-built
From: Claude Code on the MacBook (worktree wt/returns-w014-example)
Type: status
Topic: The public example snapshot is built (on a branch, not merged)

Changes v1:
settle W-018 "public example" outcome="Built 2026-11-15 on branch wt/returns-w014-example of the collab-kit repository (not merged, not pushed). The example lives at examples/the-kit-itself: the generated part (what install.py project --home repo writes) plus a sanitized snapshot of this folder's agenda, applied returns with ledgers, and knowledge. tests/public_example.py refresh takes the snapshot; check fails in the unit tests and in the release workflow whenever the example is not what the kit generates or reads. Sanitizing: generic rules in the script (accounts, local paths, Drive ids); the private never-publish words live on the MacBook only, in ~/.config/collab-kit/public-example.toml. Review and merge: W-019."
new-item kind=decision importance=2 title="Review and merge the public example branch"
```
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
```
status "Both returns in this inbox are applied (W-014 settled; W-018 built). The engine now accepts a kind word as a new item (the voice return used one). The public example is built at examples/the-kit-itself on branch wt/returns-w014-example, not merged; W-019 asks for the review. Files the phone writes cannot be read on the MacBook through Drive for desktop (top-level W-003)."
End.

Project: collab-kit
Id: 2026-11-15-2319-knowledge-go-live-0-5-md-10fd
From: Claude Code in collab-kit (wt/v05-dogfood)
Type: note
Topic: knowledge: go-live-0.5.md

Changes v1:
knowledge go-live-0.5.md
~~~
# Collab Kit 0.5: going live (Sunday 2026-11-15)

State at 13:30 Pacific: `main` of the local `collab-kit` repository is 0.5.0 (merged; not pushed).
Three sceptical reviews ran overnight and every finding is fixed with a test (84 unit and end-to-end
tests; the 0.4 suite passes; the real Claude Code test passes). This Mac has the user-level hooks.

Written by the overnight build session. Each step says who does it. Steps marked **You** need you
(a decision, a password, a screen prompt, or a publish); the rest a session can do.

## 1. Review and merge the project branches: DONE 2026-11-15

Merged by fast-forward into each repository's local `main` on Richard's go-ahead (nothing pushed),
together with `the owner's private instructions repository` (the worktree-skill step and the `~/dev` instructions line).
`ck doctor` in each main checkout: kit 0.5.0, hooks installed. The framework's main checkout kept its
own uncommitted changes; its other open branch (`wt/architecture-derivation`) does not touch the
moved `knowledge/` folder. Sessions in these main checkouts now get the brief.

What was merged:

Each is an unmerged branch `wt/collab-kit-05` in its repository, in a worktree under
`~/dev/.worktrees/`:

| Project | What the branch does | Home |
|---|---|---|
| model-fit | installs the kit (CLAUDE.md and AGENTS.md section, hooks, skills, `tools/collab-kit/`) | its Drive folder |
| dialogue-video-pipeline | the same | its Drive folder |
| knowledge-distillation-framework | migrates 0.4 to 0.5 (`knowledge/` to `collab-kit/`), upgrades the knowledge build, installs the kit; `CLAUDE.md` now imports `AGENT.md` | the repository |

## 2. Mark the top-level start file for the back end (a session)

```bash
python3 ~/dev/collab-kit/install.py top "~/Library/CloudStorage/GoogleDrive-owner@example.com/My Drive/Collab Kit" --human Richard
```

Adds the health and due-soon blocks the back end keeps current (the older start file goes to
`_versions/`). Nothing else in the folder changes (it only creates channel READMEs that are missing).

Once the back end runs (step 3), also edit the start file's hand-written "What is true right now"
section: it still says "No back end is running yet" and that the framework is read-only. The health
block above it says what is true; the prose should stop contradicting it.

## 3. The Studio as the back end (You, at the Studio or by screen sharing, for step 3d)

a. Get the kit onto the Studio. The repository has no remote yet: either publish it (step 6) and
   clone, or clone from the MacBook: `git clone <macbook>:dev/collab-kit ~/dev/collab-kit` (`main`).
b. `python3 ~/dev/collab-kit/install.py machine --cloud-root "<the Collab Kit folder on the Studio>" --human Richard`
c. `python3 ~/dev/collab-kit/install.py backend --cloud "<the same folder>" --human Richard` (dry run),
   then edit `~/.config/collab-kit/backend.toml`:
   - `account = "owner@example.com"` (every run refuses a folder that is not this account's)
   - `local_roots = ["~/dev", "~/projects"]`
   - `deny = [...]`: the private words that must never reach a public repository (names from a private project, for one)
   - one `[[project]]` table for the framework: `name = "knowledge-distillation-framework"`,
     `repo = "https://github.com/owner/knowledge-distillation-framework.git"`, `branch = "main"`,
     `push = true` (private repository; `allow_public` stays false)
d. `python3 ~/dev/collab-kit/install.py backend --apply`. On a Drive for desktop folder the job runs
   through `collab-kit-runner`; macOS may ask whether it may access files managed by Google Drive:
   **Allow**. If nothing asks and `~/Library/Logs/collab-kit/backend.log` says "Operation not
   permitted", give the runner Full Disk Access (the log names its path), never `/bin/bash`.
e. Check: `launchctl print gui/$(id -u)/org.collab-kit.backend | grep -E 'state|last exit'`, the log,
   and the top-level start file's health block ("A back end runs for this folder ... healthy on").

Using the Drive for desktop folder is the quick start; the design's target is rclone (the API sees the
real names). rclone needs its intake review accepted (`docs/rclone-intake.md`), `brew install rclone`,
and `rclone config` (your Google sign-in, **You**); then set `cloud = "rclone:<remote>:Collab Kit"`.

Rehearsed overnight against a full copy of the live folder (not the live one): one pass wrote the
health and due-soon blocks into the real start file, built `agenda/00-PRESSING.md` across all five
units, mirrored the framework (from its migrated branch) in the 0.5 layout with the old layout kept
in `_versions/before-first-mirror/`; a dictated decision for the framework was applied in its
repository, pushed, and mirrored back; and an idea on the top-level agenda became a new project.

## 4. The framework's cloud copy (a session, after step 3 runs once)

The framework's folder in Drive still has the 0.4 layout (`collab-kit/knowledge/agenda/` and the
rest). The back end's first mirror writes the 0.5 layout and moves anything it does not recognise to
`_versions/` (never deletes). Check the folder after the first run.

## 4b. Your own workflow (You decide; a session merges)

Branch `wt/collab-kit-05` in `the owner's private instructions repository` adds one step to the worktree skill (run a Collab Kit
project's brief) and one line to the `~/dev` instructions. The user-level hooks are already installed
on this Mac (`~/.claude/settings.json`; the previous file is `settings.json.before-collab-kit`); install
them on the Studio with `install.py machine --user-hooks`.

## 5. Your phone and the old folder (You)

- Claude app, Settings, Profile preferences: point the line at `Collab Kit/00-START-HERE.md` (the
  README has the wording).
- Archive the old `Project Knowledge` folder in Drive and the framework's two 0.4 LaunchAgent files
  (`~/Library/LaunchAgents/com.example.kdf-kb-*.plist`; neither is loaded) per the archive-first
  policy.

## 6. Publish the repository (You: the go-ahead and the GitHub settings)

Create `collab-kit` on GitHub, push `main`, enable private vulnerability reporting, the dependency
graph, Dependabot, and branch protection; tag `v0.5.0` (the release workflow attaches the SBOMs and
attestations). The kit repository's own Collab Kit install is a separate commit you may keep or drop
(it puts a Collab Kit section in the public `CLAUDE.md`).

~~~
End.

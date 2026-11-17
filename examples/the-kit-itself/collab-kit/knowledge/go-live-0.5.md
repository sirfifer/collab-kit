# Collab Kit 0.5: going live

Rewritten 2026-11-16 by the Claude Code session that finished 0.5.2. The kit's local `main` is 0.5.2
(merged; not pushed). Steps marked **You** need Richard (a decision, a sign-in, a screen prompt, or a
publish); the rest are done or a session does them.

## Done

- **The project branches** (2026-11-15): Collab Kit merged into the local main of model-fit,
  dialogue-video-pipeline, the framework, and the owner's private instructions repository; upgraded to 0.5.2 on 2026-11-16.
- **The top-level start file** (2026-11-16): replaced with the 0.5.2 template (the agenda first; how a
  conversation works here; no state; one setup line, which says no back end runs yet). The old one is
  in `_versions/`. The step that added a health block is gone: health is on the agenda's front page.
- **The agenda's front page**, `agenda/00-PRESSING.md` (2026-11-16): written; without a back end,
  sessions and conversations keep it current.
- **The catalog of every project**, `knowledge/projects.md` (2026-11-16): 61 projects.
- **The project start files** (collab-kit, model-fit, video pipeline; 2026-11-16): the 0.5.2 template,
  without the old "state as of" lines.
- **Every waiting return applied** (2026-11-16): the eight top-level and six collab-kit returns of
  2026-11-15 (two of them had been refused by the grammar; it now accepts a note after the changes).
- **The framework's old 0.4 job files**: archived (`~/archive/agentic/2026-11-16-kdf-04-launchagents/`).
- **The Studio, prepared** (2026-11-16): the kit is at `~/dev/collab-kit` there, and
  `~/.config/collab-kit/backend.toml` is written (account, local roots, the deny list). A script on
  its desktop does the rest.

## 1. The Studio as the back end (You, at the Studio or by screen sharing)

Run **`Collab Kit back end setup.command`** on the Studio's desktop. It asks for one Google sign-in in
the browser (as owner@example.com) and, optionally, your Pushover keys. It installs rclone v1.76.0
(checked against the kit's hash and GitHub's), connects it to the Collab Kit folder only, checks the
account, installs the schedule, runs the first pass, and shows the front page's health line. The back
end reads Drive only through the API (W-004), so no macOS permission prompt is needed.

Then tell a session "the Studio back end is running": it checks the first pass, and the start file's
setup line will already say a back end runs (the back end sets it once).

## 2. The framework (You: one push)

The framework's local main is 20 commits ahead of GitHub: the kit's own early history (it grew inside
the framework) and the move to Collab Kit 0.5. The back end serves the framework from GitHub, so it
needs that push. On your yes, a session pushes main and uncomments the framework's `[[project]]` table
in the Studio's `backend.toml`. The first pass then mirrors its Drive folder into the 0.5 layout
(anything unrecognised goes to `_versions/before-first-mirror/`, never deleted). Until then, its Drive
copy is the 0.4 one and its items are not on the front page.

## 3. Your phone and the old folder (You)

- Claude app, Settings, Profile preferences: point the line at `Collab Kit/00-START-HERE.md` (the
  kit's README has the wording).
- Archive the old `Project Knowledge` folder in Drive (into `Collab Kit/_archive/`).

## 4. Publish the repository (You: the go-ahead and the GitHub settings)

Create `collab-kit` on GitHub, push `main`, enable private vulnerability reporting, the dependency
graph, Dependabot, and branch protection; tag `v0.5.2` (the release workflow attaches the SBOMs and
attestations). Before that: refresh the public example (`tests/public_example.py refresh`), and decide
whether the kit's own install (branch `wt/v05-dogfood`, a Collab Kit section in the public
`CLAUDE.md`) goes in.

## Next, after 0.5

The back end starting agent work by itself (top-level decision item), approved pushes of project work
(W-015), GitHub Actions as a runner (W-007), OneDrive (W-009), ChatGPT and Gemini (W-008), trimming
old versions by the retention rule.

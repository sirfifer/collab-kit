# Collab Kit 0.5: going live

Updated 2026-11-19 by the Claude Code session on the MacBook that finished 0.5.2. Steps marked
**You** need Richard (a decision, a sign-in, a screen prompt, or a publish).

## Done

- **The project branches** (2026-11-15): Collab Kit merged into the local main of model-fit,
  dialogue-video-pipeline, the framework, and the owner's private instructions repository; upgraded to 0.5.2 on 2026-11-16.
- **The top-level start file, the agenda's front page, the catalog of every project, the project
  start files** (2026-11-16): the 0.5.2 templates.
- **Every waiting return applied** (2026-11-16).
- **The framework's old 0.4 job files**: archived (`~/archive/agentic/2026-11-16-kdf-04-launchagents/`).
- **The Studio is the back end** (2026-11-18, W-006): Richard ran the setup script; the launchd job
  `org.collab-kit.backend` checks the inboxes every minute and makes a full pass at least every hour.
  Drive is read through the API with rclone 1.76.0 (W-004), so no macOS permission prompt is
  needed. One kit fix was needed on the way (the account check over rclone, kit commit 6fef702,
  not yet in a release). The used setup script is archived on the Studio. Its log:
  `~/Library/Logs/collab-kit/backend.log` on the Studio.
- **The framework on the back end** (2026-11-17 and 18): its main is on GitHub and the back end
  serves it. Its Drive folder is in the 0.5 layout; the 0.4 copy is in
  `_versions/before-first-mirror/`. A return filed in Drive reached the repository and came back.

## Left

2. **You, optional: push notifications.** None are set up: the back end pushes nothing to the
   phone yet. The kit's `docs/notifications.md` says how; the keys go into the Studio's
   `~/.config/collab-kit/backend.toml` by your hand.
3. **A session: the full check** (the importance 1 item of 2026-11-19): the kit's own install at the
   current version, the design against the code, the docs for AI agents, then every project brought
   to the same version.
4. **You: publish the repository**: the go-ahead and the GitHub settings (create `collab-kit`, push
   `main`, private vulnerability reporting, the dependency graph, Dependabot, branch protection, tag
   the release; the release workflow attaches the SBOMs and attestations). Before that, refresh the
   public example (`tests/public_example.py refresh`).

## Known issue

- A full pass takes about 20 minutes, because the back end reads Drive one file at a time (its own
  item).

## Next, after 0.5

The back end starting agent work by itself (top-level W-007, your decision), approved pushes of
project work (W-015), GitHub Actions as a runner (W-007), OneDrive (W-009), ChatGPT and Gemini
(W-008), trimming old versions by the retention rule.

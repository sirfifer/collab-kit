---
name: collab-kit-upgrade
description: Upgrade the Collab Kit installed in collab-kit to the newest kit. Use when the session brief says "KIT UPDATE" (a newer Collab Kit is available), when `ck doctor` reports an upgrade, or when asked to upgrade, reinstall, or repair Collab Kit in this repository.
---
<!-- managed by Collab Kit 0.5.0: replaced on upgrade; delete this line to make the file your own -->

# Upgrade Collab Kit in this repository

The kit's files here (`tools/collab-kit/`, the Collab Kit section of `CLAUDE.md` and `AGENTS.md`,
the hooks in `.claude/settings.json`, and the `collab-kit*` skills) are managed: they are replaced
by the installer, never edited by hand. The project's own settings stay in
`tools/collab-kit/project.toml`.

1. Work where you would make any other change (a branch or worktree, per this repository's rules).
2. Find the newest kit: `tools/collab-kit/ck doctor` prints where it is (the machine's
   `[kit].source`).
3. See what changes, then apply:

   ```bash
   python3 <kit>/install.py project . --dry-run
   python3 <kit>/install.py project .
   tools/collab-kit/ck doctor        # the hooks installed, the folder reachable
   ```

4. Read the kit's release notes for this version (`<kit>/CHANGELOG.md`). If they name a migration
   step for projects, do it now.
5. Commit the upgrade on its own ("Upgrade Collab Kit to X.Y.Z"), separate from other work, and
   tell Richard in one line. If the upgrade fails, file it with
   `ck ask "Collab Kit upgrade to X.Y.Z failed: ..." --kind task` and carry on with the task.

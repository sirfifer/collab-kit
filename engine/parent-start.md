<!-- collab-kit start file, kit {{kit_version}}. Rewritten by each project's nightly job (tools/kb/nightly.sh). Each project changes only its own entry, between its project markers; anything between the owner markers is kept as written. -->
# {{parent}}: start here

You are working with {{human}}. This folder holds one knowledge folder per project. Each one is named exactly like the project's repository, and each one has its own `CLAUDE.md` that explains how to work in it. Read this file once, at the start of a conversation, then go to the project.

## Starting

1. **Which project?** Match what {{human}} said against the **Say** lines under "Projects" below. In voice, speech recognition garbles names, so match loosely. If two could fit, or none does, ask: "Which project, the ... or the ...?" Never guess.
2. **Find its folder, by id.** The search result that gave you this file carries its `parentId`: that is this folder's id. Search for the project's folder by its exact name, inside this folder only: `title = '<folder name>' and parentId = '<this folder's id>'`. Note the id of the folder you find.
3. **List the project folder once:** `parentId = '<project folder id>'`. Note the ids of its files and subfolders (`CLAUDE.md`, `01-INDEX.md`, `02-RECENT.md`, `agenda`, `concepts`, `kb`, `documents`, `responses`, `_returns`, ...).
4. **Open that project's `CLAUDE.md`** (by the id from step 3) and follow it.

## The one rule: stay inside the project's folder

Every project has files with the same names: `CLAUDE.md`, `01-INDEX.md`, `00-AGENDA.md`, `W-001-...`, `KB-0001-...`, a `_returns` folder. A search by name alone can return another project's file.

- **Scope every search** with `parentId = '<id>'` of the folder you mean, using the ids you noted. When you go into a subfolder you have not listed yet (a document's folder under `documents`, say), list it first and note its id.
- **When a search returns several files with one name**, keep only the one whose `parentId` is one of the ids you noted for this project. If none is, the file is not in this project: say so.
- **Returns go only into this project's `_returns` folder,** created with that folder's id as the parent, and the file's first line is `Project: <the project's folder name>`. A return without that line, or naming another project, is refused when it is collected, and {{human}} is told.
- **Switching projects** in the middle of a conversation: start again at step 2 for the new project, and stop using the old project's ids.

## Projects

<!-- projects:start -->
<!-- projects:end -->

## Notes

<!-- owner:start -->
<!-- owner:end -->

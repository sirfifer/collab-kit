---
name: kb-maintain
description: Build, check, sync, and health-check the {{name}} knowledge base, and run or inspect the nightly job. Use for "rebuild the knowledge base", "sync the mirror", "is the knowledge base current", "run the nightly", "check the returns", or after editing any document registered in tools/kb/manifest.toml.
---

# Maintain the knowledge base

| Task | Command |
|---|---|
| Regenerate everything generated | `python3 tools/kb/kb.py build` |
| Is anything stale or broken? (writes nothing; exit 1 if so) | `python3 tools/kb/kb.py check` |
| Sizes, counts, open endpoints, warnings | `python3 tools/kb/kb.py stats` |
| Heading keys for writing references | `python3 tools/kb/kb.py keys <CODE>` |
| The effective settings (from `tools/kb/config.toml`) | `python3 tools/kb/kb.py config` |
| Full nightly run now (curate + sync) | `tools/kb/nightly.sh --force` |
| Sync the mirror without AI | `tools/kb/nightly.sh --force --no-ai` |
| See what the nightly would do | `tools/kb/nightly.sh --dry-run --force` |
| Last nightly result | `cat {{state_dir}}/status.json` and `{{state_dir}}/reports/` |

## When to build

Any edit to a registered document, a concept, a KB answer, an agenda item, or the manifest makes generated files stale. Build in the same change and commit authored and generated files together; `check` is the gate.

## Health signals and what to do

- **Errors** (unresolved reference, bad frontmatter): fix them before anything else. A renamed heading breaks `CODE#key` references; `kb.py` suggests near matches.
- **Open endpoints**: relations pointing at concepts with no file. Write the concept (kb-capture) or remove the relation if it was a mistake. A few are healthy; they are the knowledge base's own known unknowns.
- **Index over the configured size** (`[knowledge].index_max_words`): time to shard `01-INDEX.md`; raise it with the kit (the engine is shared).
- **A section file near the size ceiling everywhere in a document**: the document wants more `###` structure; propose that, or set `max_words` for it in the manifest.
- **Concepts with no sources**: they cannot point anyone to text; add sources or mark them `proposed`.

## The nightly job

`tools/kb/nightly.sh` (see its header) stops within seconds when {{main_branch}} has not moved and the mirror's `_returns/` is empty. Otherwise it rebuilds on branch `{{curator_branch}}`, runs one curation pass with the `kb-integrate` skill when sources changed or returns arrived, and mirrors `{{out}}/` to {{mirror_where}}.{{refuse_note}} Curated commits wait on `{{curator_branch}}`; merge them from the main checkout with `git merge --ff-only {{curator_branch}}` after a look at `git log -p {{main_branch}}..{{curator_branch}}`.

Scheduling is two launchd agents, `{{label_nightly}}` (daily at {{nightly_time}}) and `{{label_returns}}` (every {{returns_minutes}} minutes, returns only): `tools/kb/launchd/install.sh` (prints what it will do; `--apply` to install, `--remove` to uninstall).

## The kit

`tools/kb/kb.py`, `tools/kb/nightly.sh`, and `tools/kb/launchd/install.sh` come from Collab Kit (version in `tools/kb/KIT-VERSION`) and are replaced when it is upgraded: change behavior in the kit, settings in `tools/kb/config.toml`. Files that start with a "managed by Collab Kit" line are rendered from the config; to make one of them the project's own, delete that line.

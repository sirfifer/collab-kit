# Collab Kit: design

> **This is the 0.4 design record.** The current design is [DESIGN-0.5.md](DESIGN-0.5.md). This
> document is kept because it is the only reference for the 0.4 knowledge build, which is still part
> of the kit: `tools/kb/` (`kb.py`: documents split into sections, concepts, answers, the index), its
> config table, the manifest, tiers, collection codes, the owner profile, and the upgrade notes.
>
> **Superseded by DESIGN-0.5.md:** the `Project Knowledge` parent folder and its start file ("Many
> projects, one parent folder" below; 0.5 has the Collab Kit folder, with every project listed in its
> `knowledge/projects.md`); the integration job, the nightly AI curator, and their launchd jobs (the
> 0.5 back end is scripts only); and the 0.4 agenda with its importance scale, where 4 is critical
> (0.5 keeps the agenda in `collab-kit/agenda/`, and 1 is critical). The kit layout below is the 0.4
> tree; 0.5 added `engine/collab_kit/` and the `install.py` commands `top`, `machine`, `project`,
> `backend`, and `migrate-04`.
>
> **The knowledge build under 0.5** runs with `[knowledge] out_dir = "collab-kit/knowledge"` and
> `agenda = false` in `tools/kb/config.toml` (`install.py migrate-04` sets both), so it never makes a
> second agenda. A 0.5 back end runs `kb.py build` in each pass for a repository-homed project that
> has the build.

Version 0.4.0, November 2026. The repository is `collab-kit`, and a local clone lives in a folder
of the same name (a local folder's name is always its repository's name). The pattern was first
built by hand for one research project and extracted into this kit so that any project can
install it.

## What it is

Collab Kit is almost entirely about collaboration. It installs the three-channel collaboration
pattern in a project, so the project can be worked on in full collaboration with collaborators who
are not in the repository, through a mirror of its knowledge (a Google Drive folder):

1. **Knowledge** (project to conversation): the project's documents split into loadable sections,
   a concept graph, answers that took digging, one index.
2. **Returns** (conversation to project): plain text files the conversation writes to the project's
   `_returns/` folder, folded in by an integration job about fifteen minutes after the last one
   arrives.
3. **The agenda** (project to conversation): what needs the human, most pressing first, each item
   carrying the context to start on it.

The channels are plain files, so they do not depend on the interface. **Voice** in the Claude app
is the first interface and the most demanding one: hands-free, and able to open only whole files,
by name, through the Drive connector. It shaped the knowledge channel (small files with unique
names) and has its own **voice profile** (the spoken-conversation rules in each project's
`CLAUDE.md`). Typed chat in the Claude app or desktop, Claude Code in the repository, other
assistants, and people are anticipated; each needs only its own profile, never a change to the
channels. Only voice is built and tested today.

Every project's knowledge folder sits inside **one parent folder** in Drive, named exactly like the
project's repository, and the parent carries a start file listing every project. One line in the
Claude app's preferences points at that start file, so adding a project never means touching the
app's settings again.

The pattern itself, its interfaces, its rules, and its prior art are in
[templates/tools/kb/COLLABORATION-PATTERN.md](templates/tools/kb/COLLABORATION-PATTERN.md) (a copy
is installed in every project). This document covers the kit: what it installs, what a project
configures, and how to install, upgrade, and release it.

## Where it lives: an open source repository

The kit is its own open source project, released with the article that describes the pattern
("Talking to My Project"), or before it. It was extracted from a working project, where the pattern
was built by hand first.

**The repository started from a fresh snapshot, not from history.** The extraction's history held
owner-specific files that were moved out before release (an owner profile with real account names,
the original project's configuration), so the public repository began with one initial commit of
the kit's tree.

The supply-chain baseline is part of creating the repository, not a later addition. The files ship
in this folder; the settings are made when the repository is created:

| Practice | How | Where |
|---|---|---|
| Coordinated vulnerability disclosure | [SECURITY.md](SECURITY.md): private reporting through GitHub Private Vulnerability Reporting, supported versions, response and disclosure timelines, scope, contributor expectations | file; enable reporting in the repo settings |
| Dependency updates | Dependabot for the one ecosystem present (GitHub Actions); the kit has no package dependencies by design | [.github/dependabot.yml](.github/dependabot.yml); enable Dependabot alerts and security updates |
| Vulnerability scanning | OSV-Scanner weekly, on pull requests, and on pushes to `main` | [.github/workflows/osv-scanner.yml](.github/workflows/osv-scanner.yml) |
| Posture | OpenSSF Scorecard weekly and on pushes to `main`, results published; target: OSPS Baseline Level 1 at release | [.github/workflows/scorecard.yml](.github/workflows/scorecard.yml) |
| Static analysis | CodeQL for the Python code | [.github/workflows/codeql.yml](.github/workflows/codeql.yml) |
| Tests on every change | the dry-run install on macOS | [.github/workflows/ci.yml](.github/workflows/ci.yml) |
| SBOM per release | CycloneDX and SPDX, generated from the release's source archive and attached to the release | [.github/workflows/release.yml](.github/workflows/release.yml) |
| Signed provenance | build provenance and SBOM attestations for the release archive (GitHub artifact attestations) | release workflow |
| Pinned actions | every action pinned to a full commit hash, with its version in a comment; Dependabot keeps them current | all workflows |
| Least privilege | `permissions: {}` at the top of every workflow, granted per job | all workflows |
| Branch protection | a ruleset on `main`: pull requests required, the `ci` check required, no force pushes, no deletions | repo settings |
| Dependency graph | enabled (it is on by default for public repositories) | repo settings |

The license is **MIT** ([LICENSE](LICENSE)).

How it was created, for anyone setting up a fork the same way:

```bash
# a fresh repository from the current kit/ tree (no history)
mkdir ../collab-kit && cp -R kit/. ../collab-kit/ && cd ../collab-kit
git init -b main && git add -A && git commit -m "Collab Kit 0.4.0"
gh repo create <owner>/collab-kit --public --source . --push
gh api -X PUT repos/<owner>/collab-kit/private-vulnerability-reporting
gh api -X PUT repos/<owner>/collab-kit/vulnerability-alerts
gh api -X PUT repos/<owner>/collab-kit/automated-security-fixes
# then the ruleset on main (Settings, Rules), and the first release:
git tag v0.4.0 && git push origin v0.4.0      # the release workflow builds, attests, and attaches the SBOMs
```

The local folder's name is the repository's name.

## Anatomy

Everything the kit writes into a project is one of four kinds, plus one shared file that lives only
in Drive.

| Kind | What | Written by `install.py apply` | Who edits it |
|---|---|---|---|
| **config** | `tools/kb/config.toml` | never (created by `install.py init`) | the project |
| **engine** | `tools/kb/kb.py`, `tools/kb/nightly.sh`, `tools/kb/launchd/install.sh`, `tools/kb/parent-start.md`, `tools/kb/KIT-VERSION` | replaced on every apply | nobody per project: change the kit |
| **managed** | the four `kb-*` skills, the `kb-librarian` agent, `tools/kb/curator-prompt.md`, `tools/kb/COLLABORATION-PATTERN.md`, and in the knowledge folder `_returns/README.md`, `agenda/01-HOW-ITEMS-ARE-KEPT.md`, `captures/README.md`, `concepts/_TEMPLATE.md`, `kb/_TEMPLATE.md` | rendered from the config and replaced on every apply, while the file still carries its `managed by Collab Kit` line | nobody: change the config or the kit. Deleting the line makes the file the project's own; the kit then leaves it alone |
| **seed** | `<out>/CLAUDE.md`, `<out>/README.md`, `tools/kb/manifest.toml` | created once; afterwards only the text between `<!-- kit:start NAME -->` and `<!-- kit:end NAME -->` is refreshed | the project (outside the blocks) |
| **shared** | the parent folder's start file, `<parent>/00-START-HERE.md` | never: each project's nightly job updates its own entry in it (`kb.py parent --write`) | nobody by hand, except between its owner markers |

Engine files read every setting at run time (`kb.py` from `config.toml`; the shell scripts through
`kb.py config --shell`), so they are byte-identical across projects. Managed files are rendered
once per apply, because Claude Code and the Drive connector read them as plain files. Seed files mix
the two: `knowledge/CLAUDE.md` holds the project's trust order and notes (its own) around the
starting, keeping, voice-profile, agenda, finding, returns, and repository sections (the kit's
blocks).

Generated knowledge (`01-INDEX.md`, `02-RECENT.md`, `agenda/00-AGENDA.md`, `documents/`, `full/`,
`graph.json`, and the generated block at the end of concept, answer, and agenda files) is produced
by `kb.py build` in the project.

## Many projects, one parent folder

### The rules

1. **One parent folder.** Every project's knowledge folder lives inside one folder in Drive
   (`[mirror].parent`, default `Project Knowledge`). The parent may hold other things later; the
   kit only ever writes the start file there and its own project folders.
2. **The knowledge folder has exactly the repository's name**, which is also the GitHub
   repository's name and the local folder's name. The kit derives it (the `origin` remote's
   repository name, else the main checkout's folder name; a worktree's own folder never counts)
   and never takes it from configuration. It is enforced, not advised:
   - `kb.py check` and `install.py check` fail when `[mirror].folder` or `[project].repo` is set to
     anything else; `install.py apply` refuses to run;
   - `nightly.sh` refuses to mirror unless the target folder is named like the repository and sits
     in a folder named like the parent (this also holds for a one-off `KB_MIRROR_DIR`);
   - `kb.py check` warns when the local folder's name differs from the remote repository's.
3. **The preference line points at the parent's start file**, never at a project. It is the same
   for every project; `kb.py preference-line` prints it.

### The collision problem, and the design

File names repeat across projects: every project has `CLAUDE.md`, `README.md`, `01-INDEX.md`,
`00-AGENDA.md`, `W-001-...`, `KB-0001-...`, and above all a `_returns/` folder. The Drive connector
searches all of Drive by name. Without care, a conversation could read another project's
file, or file a return into another project's `_returns`.

The connector's search accepts `parentId = '<id>'`, and every result carries its `parentId`. The
design uses that, in three layers:

| Layer | What it does | Where |
|---|---|---|
| **Start by folder id** | The start file (found by the preference line) tells the conversation: the `parentId` of the start file is the parent's id; find the project folder by its exact name with `parentId = '<parent id>'`; note its id; list it once and note the ids of its files and subfolders; open that project's `CLAUDE.md` by id | `engine/parent-start.md`, rendered into the parent |
| **Stay in the folder** | Every later search is scoped with `parentId = '<id>'`; when a name search returns several files, only the one whose `parentId` is one of the noted ids counts; a subfolder is listed before its first search; switching projects starts again from the parent | the start file, and the `finding` block of each project's `CLAUDE.md` |
| **Check every return** | A return's first line is `Project: <repository name>`. The nightly job checks each return before anything else (`kb.py return-check`): one with no Project line, or naming another project, or a Google Docs file whose text cannot be read, is moved to `_returns/refused/`, listed in the job's report, and never integrated | the `returns` block of `CLAUDE.md`, `_returns/README.md`, `nightly.sh` |

The first two layers make a mistake unlikely; the third makes one harmless.

### Mapping spoken names to folders

"Let's work on the garden" has to find `garden-planner` without opening every project. The start
file lists every project as an entry with its folder name, the names people say for it
(`[project].spoken`, plus `short`), and one line about it. The conversation matches what it heard
against those names and asks when two could fit.

**Where the start file's truth lives.** Not in the kit, and not in any one project:

- each **entry's** truth is that project's own `tools/kb/config.toml` (`repo`, `name`, `about`,
  `spoken`); the project's nightly job rewrites only its own entry, between its
  `<!-- project:<repo> -->` markers, under a machine-wide lock;
- the **frame** (the instructions) comes from the kit's `engine/parent-start.md`; a job running an
  older kit never overwrites a frame written by a newer one, it only updates its own entry;
- the **owner's notes**, between the owner markers, are kept as written;
- the assembled file lives **only in Drive**. If it is lost, each project's next run puts its entry
  back. Nothing about any owner's projects is stored in the kit's repository.

Jobs on two different machines writing the same start file at the same minute could still produce
a Drive conflict copy; the nightly times are per project, so this is unlikely, and the next run
repairs it.

## Kit layout

```
README.md            quick start
LICENSE              MIT
DESIGN.md            this document
SECURITY.md          vulnerability reporting and the security policy
VERSION              the kit's version (kb.py's KIT_VERSION must match)
install.py           init | apply [--dry-run --diff --adopt] | check
engine/              copied verbatim to tools/kb/ (kb.py, kb_mcp.py, nightly.sh, launchd/, parent-start.md)
templates/           rendered with {{placeholders}}; OUT/ = the knowledge folder, claude/ = .claude/
examples/
  owner-profile.toml an example owner profile (copy it somewhere private and fill it in)
  the-lighthouse/    a sample project (a made-up novel): the three channels, readable in five minutes
tests/
  dry-run-install.sh install into a throwaway project and exercise everything end to end
  live-curator-permissions.sh   opt-in: the real Claude Code against the curator's fence
  refresh-example.sh rebuild the sample project's knowledge folder (--check: is it current?)
.github/             CI, OSV-Scanner, Scorecard, CodeQL, release with SBOMs and attestations, Dependabot
```

## What the original project hard-coded, and where it went

Found by reading every generic file in the original project (the build script, the nightly script,
the launchd installer, the four skills, the librarian agent, the curator prompt, and the knowledge
folder's README files and templates).

| Hard-coded there | Now |
|---|---|
| The repository's path | found from the script's own location; `KB_REPO` overrides |
| The curator worktree's path, and its branch | `[curator].worktree` (default `<state_dir>/curator`; `{repo}` and `{slug}` are filled in), `[curator].branch` |
| The main branch | `[project].main_branch` |
| One Google account and its alias | `[mirror].account`, `[mirror].account_aliases`; `init` requires the account, there is no silent default |
| A deprecated account that must never be written to | `[mirror].refuse` (usually from the owner profile); checked for the account and the resolved path before anything runs |
| The Drive folder's name, chosen freely | the repository's name, derived and enforced, inside `[mirror].parent` |
| The preference line naming the project's folder | one line for every project, naming the parent's start file |
| Drive only | `[mirror].kind`: `google-drive`, `folder` (a local folder standing in for My Drive, `[mirror].root`; used by the tests), or `none` |
| The mirror's ownership marker | `[mirror].marker` (default `.<slug>-kb-mirror`) |
| The state folder | `[schedule].state_dir` (default `~/.local/state/<slug>-kb`) |
| launchd labels, 02:30 daily, every 20 minutes | `[schedule].label_prefix`, `[project].slug`, `[schedule].nightly`, `[schedule].returns_every_minutes` |
| 15 quiet minutes before returns are integrated | `[mirror].settle_minutes` |
| Project-named environment variables | `KB_*`, overriding the config for one-off runs and tests |
| The author folders | `[project].author_paths` |
| The knowledge folder `knowledge/` | `[knowledge].out_dir` (the manifest's legacy `[build].out_dir` still wins if present) |
| The tiers and their notes | `[[tiers]]`: name, note, `canon`, `history`, `weight` |
| The history tier's banner and its weight in `find` | any tier with `history = true` gets the banner; `weight` per tier |
| The owner's name and pronouns in generated text | `[people].human`, `[people].pronouns`, `[people].assistant`; templates avoid pronoun-verb agreement so they/them reads correctly |
| `from` codes checked against a fixed list | the code families actually present (collection prefixes, and the letters of numbered codes like `T01`) |
| Which collections appear in 02-RECENT, and the heading | collections with `recent = true`; `[knowledge].recent_heading` |
| The index size warning | `[knowledge].index_max_words` |
| Concept kinds | `[concepts].kinds` |
| Example references in skeletons and skills | `[examples]`, defaulting to the manifest's first document |
| The project's name and subject in prose | `[project].name`, `short`, `about`, `content_word` |
| Where to make changes ("work in a worktree") | `[project].worktree_note` (usually from the owner profile) |
| Project rules for integration | `[project].rules`, rendered into `kb-integrate` and the curator prompt |
| The trust order | seed text in `CLAUDE.md` outside the kit blocks, started from the tiers |
| Names speech recognition gets wrong | seed section "Names speech recognition gets wrong" in `CLAUDE.md` |

Kept fixed on purpose, as part of the pattern rather than the project: the `tools/kb/` location,
the folder and file names in the knowledge folder (`_returns/`, `agenda/`, `captures/`, `concepts/`,
`kb/`, `proposals/`, `responses/`, `CLAUDE.md`, `01-INDEX.md`, `02-RECENT.md`, `00-AGENDA.md`), the
`KB-NNNN` and `W-NNN` id formats, the reference syntax (`CODE#key`, `CODE@a-b`), the agenda kinds,
importance and effort scales, the relation types, the return format, and the `C` collection for
captures.

## The config surface

`tools/kb/config.toml`. Tables merge key by key over the kit's defaults; lists replace.
`python3 tools/kb/kb.py config` prints the effective result, including the derived repository name.

| Key | Default | Meaning |
|---|---|---|
| `[project] name` | `this project` | the project's name in prose ("the X knowledge base") |
| `article` | empty | `the` when the name reads with one: "working with you on the **X framework**" |
| `short` | the name | what the human calls the project: "let's work on the <short>" |
| `spoken` | `[short]` | every name the human uses for the project; listed in the parent's start file |
| `slug` | `kb` | short id: state folder, launchd labels, mirror marker |
| `repo` | derived | the repository's name. Never needs setting; if set, it must match, or check fails |
| `about` | empty | one clause for the first line of `CLAUDE.md` and the start file |
| `main_branch` | `main` | the branch the knowledge base reads |
| `author_paths` | `["docs"]` | authored folders: watched for change, never edited by agents |
| `content_word` | `project` | as in "framework content", "project content" |
| `worktree_note` | "Work on a branch or worktree, not the main checkout." | the sentence the skills use for where to work |
| `rules` | empty | project rules for anyone integrating knowledge; rendered into `kb-integrate` and the curator prompt |
| `[people] human` | `the owner` | the person the agenda waits on |
| `pronouns` | `["they", "them", "their"]` | subject, object, possessive |
| `assistant` | `Claude` | |
| `[knowledge] out_dir` | `knowledge` | the knowledge folder |
| `max_words` | 1800 | ceiling for one section file (about 2,400 tokens) |
| `index_max_words` | 9000 | warn when `01-INDEX.md` grows past this |
| `recent_heading` | `Newest additions` | 02-RECENT heading for collections marked `recent` |
| `agenda` | `true` | `false` under Collab Kit 0.5, which keeps the agenda in `collab-kit/agenda/`: the build reads and writes no agenda (no `agenda/00-AGENDA.md`), `kb.py new-item` points at `ck ask`, and `install.py apply` writes nothing into the knowledge folder's `agenda/` or `_returns/` |
| `[returns] captures_in_git` | **none: required** | `true`: each return is committed as a capture; `false`: returns stay in Drive (`_returns/processed/`), the curator reads them in its prompt, and `check` fails if one is in `captures/`. `init` will not finish, `apply` and `install.py check` fail, and the nightly job stops until it is set |
| `[[tiers]]` | prime, foundation, deep-dive, analysis, reference, source, history | `name`, `note`, `canon` (current truth), `history` (banner, never overrides canon), `weight` (ranking in `find`) |
| `[concepts] kinds` | principle ... project | allowed concept kinds |
| `[examples]` | from the manifest's first document | `doc`, `heading_ref`, `line_ref`, `capture`, `concept` used in skeletons and skills |
| `[mirror] kind` | `none` | `google-drive`, `folder`, or `none` |
| `parent` | `Project Knowledge` | the one folder holding every project's knowledge folder |
| `start_file` | `00-START-HERE.md` | the parent's instructions file, which the preference line opens |
| `folder` | the repository's name | not a setting: anything else fails check |
| `account` | empty | Google account, named explicitly (required for `google-drive`) |
| `account_aliases` | `[]` | other addresses the account's Drive for desktop folder may carry |
| `root` | empty | the local folder that holds the parent: required for `folder`; for `google-drive` it replaces `<account's Drive>/My Drive` |
| `refuse` | `[]` | substrings no account or mirror path may contain |
| `marker` | `.<slug>-kb-mirror` | file marking a mirror folder the job owns (rsync `--delete` only runs where it exists) |
| `settle_minutes` | 15 | quiet minutes before returns are integrated |
| `[curator] branch` | `wt/kb-curator` | where curated work waits for a merge |
| `worktree` | `<state_dir>/curator` | the curator's worktree (`{repo}`, `{slug}` filled in) |
| `timeout` | 2700 | seconds for the AI pass |
| `model` | empty | model for the AI pass (empty: Claude Code's default) |
| `claude` | `claude` | the Claude Code binary |
| `[schedule] label_prefix` | `local.kb` | launchd label prefix |
| `nightly` | `02:30` | the daily full run |
| `returns_every_minutes` | 20 | how often to look for settled returns |
| `state_dir` | `~/.local/state/<slug>-kb` | logs, reports, `status.json` (`{repo}`, `{slug}` filled in) |

Environment overrides for one run: `KB_REPO`, `KB_CURATOR_WT`, `KB_MIRROR_DIR`, `KB_STATE_DIR`,
`KB_AI_TIMEOUT`, `KB_AI_MODEL`, `KB_CLAUDE`, `KB_SETTLE_MIN`, `KB_LOCK_DIR`; `KB_ROOT` points
`kb.py` at another project root.

## The owner profile

The kit's defaults are neutral. Whatever one person applies to all of their projects (their name
and pronouns, the parent folder's name, accounts to refuse, a launchd label prefix, where curator
worktrees go) lives in an **owner profile**: a small TOML file kept somewhere private (dotfiles, a
private config repository), never in the kit and never in a public repository.
[examples/owner-profile.toml](examples/owner-profile.toml) shows every key. `install.py init` reads
it from `--profile <path>` or `$KB_KIT_PROFILE`; its values are written into the new project's
config, where they can still be changed.

## Installing in a new project (the 0.4 procedure)

This is the 0.4 procedure: it sets up the parent folder, the Drive mirror, and the nightly jobs,
which 0.5 replaced. Under 0.5 a project gets Collab Kit with `install.py project` (README), and a 0.4
project moves with `install.py migrate-04` (DESIGN-0.5.md section 15).

1. **Decide which Google account** the project's Drive mirror uses, and name it explicitly. If the
   project might have its own Google Workspace account, ask before creating anything in Drive.
2. **Write the config:**

   ```bash
   python3 <kit>/install.py init . --name "Project Name" --slug short-id --short "what you say" \
     --spoken "another way you say it" --about "one clause: what the project is" \
     --author-path docs --drive-account you@example.com --profile ~/private/owner-profile.toml
   ```

   The knowledge folder will be `<parent>/<repository name>`; `init` prints it. Review
   `tools/kb/config.toml`: tiers, `rules`, `human`, the schedule.
3. **Register the documents** in `tools/kb/manifest.toml` (code, title, source, tier, about), and
   any append-only folders as `[[collections]]`. The captures collection is already there.
4. **Install:** `python3 <kit>/install.py apply .` (run it again after step 3 if the documents were
   registered later, so examples use the project's own codes), then
   `python3 tools/kb/kb.py build && python3 tools/kb/kb.py check`.
5. **Fill in the seed:** in `knowledge/CLAUDE.md`, the trust order and anything out of step; seed
   concepts for the main ideas (`kb.py new-concept`) and the first agenda items (`kb.py new-item`).
   Point the repo's own `CLAUDE.md` or `AGENTS.md` at `knowledge/` and the `kb-*` skills.
6. **Commit** and merge to main (the nightly job reads main), then prove the pipeline once by hand:
   `tools/kb/nightly.sh --dry-run --force`, then `tools/kb/nightly.sh --force --no-ai`. This creates
   the curator worktree, the parent folder if needed, the project's folder (verified file by file),
   and the project's entry in the parent's start file.
7. **Schedule it:** `tools/kb/launchd/install.sh` shows the two jobs; `--apply` loads them.
8. **Interface setup, once per person, not per project.** For voice and chat in the Claude app:
   connect Google Drive as that account, and add the preference line
   (`python3 tools/kb/kb.py preference-line | pbcopy`). A second project under the same parent
   needs nothing here. Then: "Let's work on the <short>." Any other interface is pointed at the
   parent's start file.

`install.py check .` exits 1 whenever the installed files differ from the kit and config, or the
naming rule is broken, so it can sit in CI or a pre-commit hook next to `kb.py check`.

## Upgrading

Update the kit, then in each project `python3 <kit>/install.py apply . --dry-run --diff`, then
without `--dry-run`, then build and check. Engine files are replaced; managed files are re-rendered
unless the project took one over; seed files keep the project's text and get fresh kit blocks.
A seed block the project deleted is reported and left alone.

### 0.3 to 0.4: what a project must know about

- **Choose whether returns go into git.** Add `[returns]` with `captures_in_git = true` (what every
  earlier install did) or `false` to `tools/kb/config.toml`. Until then `apply` and `install.py check`
  fail and the nightly job stops, each naming the setting; `kb.py check` only warns.
- **Item numbers are reserved, not counted.** `new-item` and `new-kb` take a number from a registry
  in the repository's shared git folder (`<git common dir>/collab-kit/numbers.json`, under a lock),
  so no two worktrees or checkouts of one repository on one machine mint the same `W-NNN` or
  `KB-NNNN`. Clones on different machines still can; `check` then names both files and
  `kb.py renumber <file>` gives one a new number and lists what still mentions the old one.
- **Collection codes never move.** `tools/kb/collection-codes.json` records which file has which
  code; a new file gets the next free number whatever its name sorts as, and a gone file's number is
  never reused. The first build records the numbering as it stands, so an existing project keeps its
  codes. `check` reports the file stale when a new file is not yet numbered, and fails when one number
  is given twice. Before this, a late file that sorted earlier shifted every code after it.
- **A mirror the job cannot read is a failure, never an empty inbox.** `nightly.sh` proves the mirror
  readable (each read time-limited, `KB_PROBE_TIMEOUT`, default 60 s) before it scans; `--probe` does
  only that. Scheduled jobs run through `collab-kit-runner`; `launchd/install.sh --probe` runs the
  probe as a real launchd job, and `--apply` ends with it. Every scheduled run leaves
  `last-scheduled.json` in the state folder; `kb.py status` and `install.py check` show the last
  run, the last success, and launchd's exit codes. Re-run `launchd/install.sh --apply` after upgrading.
- **Returns may say who they are from** with an optional `From:` line after `Project:`. It is shown
  in `02-RECENT.md` and the curator names the sender in its response. One human per project is still
  what is tested; this is groundwork for more.

### 0.2 to 0.3: the fenced curator pass

0.3 changes how the nightly AI pass runs (see SECURITY.md, "The unattended pass"); nothing in a
project's configuration changes. After `apply`, commit the new engine files to the main branch
before the next nightly run: the job runs the engine from the main branch's commit
(`tools/kb/kb.py`, `kb_mcp.py`, `parent-start.md`) and stops if they are not there. The job also
needs a Claude Code with `--restricted` (2.1.319 has it); with an older one it stops and says so.
A manifest source outside `[project].author_paths` and the knowledge folder now fails the build:
move the document, or add its folder to `author_paths`.

### Moving an install that predates the parent folder (0.1 to 0.2)

Version 0.1 let a project name its Drive folder freely and pointed the preference line at it. To
move one onto the parent folder:

1. Remove `[mirror].folder` and `[mirror].path` from `tools/kb/config.toml` (use `[mirror].root` for
   a local mirror), set `[mirror].parent`, and add `[project].spoken`. `kb.py check` now passes.
2. `python3 <kit>/install.py apply . --dry-run --diff`, then apply, build, check, commit, merge.
3. Move the old Drive folder into the parent and rename it to the repository's name, in Drive
   itself, so its ownership marker and `_returns/` (with anything waiting there) come along.
4. Run `tools/kb/nightly.sh --force --no-ai` once: it mirrors into the renamed folder and adds the
   project's entry to the start file.
5. Replace the old preference line in the Claude app with the new one
   (`kb.py preference-line | pbcopy`). Until then, conversations look in the old place.

## Verification

- `tests/dry-run-install.sh`: a throwaway project in a temporary folder, a plain folder standing in
  for My Drive (holding the parent, another project's entry in its start file, and this project's
  mirror), an example owner profile, and a stub `claude`. It covers:
  - the kit's own consistency: version, no em dashes, and nothing owner-specific anywhere in the kit;
  - init refusals: no account named, a refused account, a missing profile;
  - install, build, find, show, concepts, and the agenda's priority inheritance and blocker checks;
  - the naming rule: a renamed folder or a wrong declared repository fails both checks, and apply
    refuses;
  - the start file: this project's entry with its spoken names, another project's entry and the
    owner's notes kept, name order, no rewrite when nothing changed, and an older kit keeping a
    newer frame;
  - the nightly mirror with its marker and verification;
  - the returns channel end to end: the settle wait; returns with no Project line or another
    project's name refused, moved to `refused/`, and reported; the good one captured; the curation
    commit on the curator branch; `processed/`; the mirror showing the response; main untouched;
  - the guards: a curator that edits author documents, a folder without the marker, a refused
    account, and a mirror folder not named like the repository;
  - the curator's fence: its flags (no shell, restricted, nothing asked, reads in the worktree only,
    edits in the knowledge folder and manifest only), the read-only engine copy, and a stub curator
    "turned" by a return that tries to run planted code, read a file from outside through the
    manifest, and write outside through `parent --dir` and a concept id; plus the engine's own
    refusals (manifest sources, collection patterns, links, concept ids, the knowledge folder's place);
  - the launchd plists, and an upgrade after a config change.
- `tests/live-curator-permissions.sh` (opt-in; one short `claude -p` on a small model): the real
  Claude Code with the curator's exact flags and kb server. The verdict comes from the file system
  and Claude Code's own record of the session's tools, not from what the model says.
- The original project keeps a private regression next to its own configuration. It exports the
  project at a commit, swaps in this engine, and runs `kb.py check`. Passing means every generated
  file is byte-identical to what the hand-built version produced.

## Limits and next steps

- The nightly job is macOS-only (launchd, `stat -f`, Google Drive for desktop's CloudStorage path).
  Linux would need a systemd timer and `stat -c`.
- The Drive account must be added to Google Drive for desktop on the machine that runs the job.
- The scoping rules depend on the Drive connector's `parentId` search. If the connector changes,
  the start file and the `finding` block are the two places to update.
- One human per project. Owners and need-by dates on agenda items wait until a project needs them.

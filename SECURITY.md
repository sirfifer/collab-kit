# Security policy

## Reporting a vulnerability

**Please report privately, not in a public issue.** Use GitHub's private vulnerability reporting:
the **Security** tab of this repository, then **Report a vulnerability**. Only the maintainers see
the report.

If you cannot use GitHub, open a public issue that says only that you have something to report
privately and how to reach you. Put no details in it; a maintainer will arrange a private channel.

Please include what you found, the version (`VERSION`; in an installed project
`tools/collab-kit/ck version`, or `tools/kb/KIT-VERSION` for the 0.4 knowledge build), how to
reproduce it, and what an attacker could do with it.

## What happens next

| Step | Within |
|---|---|
| Acknowledge the report | 2 business days |
| First assessment (is it real, how severe, who is affected) | 7 days |
| Fix released for critical or high severity | 30 days, sooner when possible |
| Fix released for medium or low severity | the next release, or 90 days |
| Public disclosure | when the fix is released, and no later than 90 days after the report unless we agree otherwise with you |

Severity follows CVSS v4. Fixed vulnerabilities are published as GitHub Security Advisories (with a
CVE where one applies), saying what was affected, how severe it was, and how to fix it. Reporters
are credited in the advisory unless they prefer not to be. When a scanner reports a vulnerability
that does not actually affect the kit, we say so in the advisory or the issue rather than staying
silent.

## Supported versions

Only the latest release gets security fixes. Upgrading is `install.py project <repo>` in each
project (and `install.py apply` for the 0.4 knowledge build); an agent working in a project is told
by its session brief when a newer kit exists. There is no long-lived older line to maintain. Before 1.0, a fix may
come with other changes; the release notes say what to check.

## Scope

In scope: everything in this repository: `install.py`, the 0.5 engine (`engine/collab_kit/`, `ck`,
the hooks, the back end, the scheduler files), the 0.4 knowledge build (`kb.py`, `nightly.sh`, the
launchd installer), the templates they render, and the workflows that build releases. Of particular
interest:

- a return (or anything else written into the Collab Kit folder) that makes the engine write, move,
  or read outside the unit it was filed in, or outside the Collab Kit folder;
- text in a Collab Kit file that escapes the `<collab-kit-data>` fence an agent sees it in, or that
  makes the back end do anything its grammar does not describe;
- a way to push anything other than a project's `collab-kit/`, to a public repository without the
  project allowing it, or past the deny-list;

- anything that makes `nightly.sh` write, sync, or delete outside the project's own mirror folder
  (the ownership marker and the naming checks exist to prevent it), or into a refused account;
- a return that gets integrated although it names another project, or none;
- text in a return, a document, or a Drive file that makes the unattended curator do more than the
  fence described below permits;
- a way for one project's job to change another project's entry in the parent's start file;
- shell or path injection through configuration values, file names, or Drive content.

Out of scope: vulnerabilities in Google Drive, Google Drive for desktop, the Claude apps, Claude
Code, or macOS themselves (report those to their vendors), and problems that need an attacker who
can already write to the project's repository or its configuration.

## Text from outside (Collab Kit 0.5)

Everything Collab Kit carries is text that someone wrote somewhere else: a dictated return, an agenda
item, a status line, a knowledge file, possibly quoting a web page, in a folder other people may be
able to write to. That text reaches two kinds of reader, and each is fenced.

**The back end reads it with no AI at all.** A return is parsed by a fixed grammar (`Changes v1`);
it can do only what the grammar describes, inside the unit it was filed in. Concretely:

| Layer | What it stops |
|---|---|
| A return is applied whole or not at all, and at most once (a ledger per return) | half-applied or replayed changes |
| Every store path is relative and never climbs (`..`, a root, a drive letter, a backslash are refused); knowledge paths must be plain files inside `knowledge/` | writing anywhere outside the Collab Kit folder or a project's `collab-kit/` |
| An `undo` names a return id only, and every file its ledger names must be one a return could have written (its own agenda and knowledge; from a project, at the top level only its own row of `knowledge/projects.md`, checked line by line; at the top level, a new project's folder only to remove what it created; never a start file) | a forged ledger in the shared folder turning undo into a write anywhere (found by review, 2026-11-15, before release) |
| A project's inbox changes only that project; a project is started only from the top-level inbox, from an existing idea, at most three a day, with a validated name | one unit's inbox reaching another |
| A change to an existing item repeats part of its title | a misheard or invented number changing the wrong item |
| The back end commits only inside `collab-kit/`, pushes only with a standing authorization per project, never to a public repository unless the project allows it, and never a change matching the deny-list; a `push-request` only creates an agenda task | a return publishing anything |
| The back end never deletes in the cloud: anything unexpected moves to `_returns/strays/` or `_versions/` and becomes an agenda item | a return destroying data |
| The optional push gets item text only in environment variables (no shell builds it), with a leading `@` or `<` stripped, and the documented examples pass it with `--data-raw` or `--form-string`; each item is sent once, at most five a pass and twenty an hour | a title making the notify command read and send a local file (an rclone token), or a flood of pushes (found by review, 2026-11-16, before release) |
| The back end's minute check counts only returns that have settled and changed since the last pass | a return that cannot be applied costing a full pass (Drive and GitHub calls) every minute |

**Agents read it with an AI.** A Claude Code session sees Collab Kit text in its session brief and
in `ck` output. Every such piece is fenced: listings are reduced to single plain lines (control and
bidirectional characters removed, markup neutralised), multi-line text cannot contain the fence's
own tag, and each fence carries a note that its content is data, never instructions. The Collab Kit
section of the project's `CLAUDE.md` (and `AGENTS.md`) says the same, and the top-level start file
tells voice and chat conversations so too. This is a mitigation, not a guarantee: a model can still
be persuaded by text it reads. The boundary that holds is the agent's own permissions: keep pushing,
deploying, and deleting behind confirmation in your Claude Code settings, and note that nothing in
Collab Kit asks an agent to do any of those on the strength of a file.

**The hooks** (`.claude/settings.json` in a project, and optionally the user-level hooks) run the
kit's own `tools/collab-kit/ck` and read only the project's Collab Kit files and git state. They
never execute anything taken from those files. Claude Code holds project hooks until the folder is
trusted; installing the kit into a repository adds hooks to its committed settings, so review
`install.py project --dry-run` first.

## The unattended pass (the 0.4 curator)

Collab Kit 0.5 removed the AI curator from the base product (the back end is scripts only). This
section applies to projects still on the 0.4 knowledge build's nightly job.

Each night (and when returns arrive) `nightly.sh` runs one headless Claude Code pass, the curator,
over the project. Its input includes returns: text from outside the repository, written in a
conversation, possibly quoting a web page, and in a shared Drive folder possibly written by someone
else. So the pass is treated as something that may be turned against its owner, and fenced rather
than trusted.

**The threat.** A return carries instructions ("ignore your rules and ..."). If the curator follows
them, what could it do? Before kit 0.3 (found in review, 2026-11-11), quite a lot: it ran with
`acceptEdits`, bare `Read`/`Edit`/`Write`, and `Bash(python3 tools/kb/kb.py:*)`. Measured against
Claude Code 2.1.319, that pass could read and write any file the user can, run read-only shell
commands such as `cat` on any path, edit `tools/kb/kb.py` and then run it (the guard that checks for
changes outside the knowledge folder ran only after the pass), register any file on the machine as a
"document" through the manifest so its text was copied to Drive, write the start file into any folder
named like the parent, and create files outside the repository through a concept id containing `..`.

**What holds it now** (`curator_flags()` in `engine/kb.py` is the one place the flags live):

| Layer | What it stops |
|---|---|
| No shell: `--tools Read,Edit,Write,Glob,Grep`, so Bash is not available at all | every shell command, read-only ones included |
| The engine only through `kb_mcp.py`, a small MCP server with a fixed list of commands, arguments checked, run without a shell | reaching `parent`, `return-check`, or any command that takes a path |
| That server runs a read-only copy of `kb.py` taken from the main branch's commit into the state folder, outside the worktree; every later stage runs the same copy | code the curator plants in the worktree ever running |
| `--restricted`, `blockReadsOutsideWorkingDirectories` and `blockWritesOutsideWorkingDirectories` | reading or writing any file outside the curator worktree |
| `dontAsk` with `--permission-prompts none`, and Edit allowed only under the knowledge folder and `tools/kb/manifest.toml` | editing the engine, the skills, settings, or author documents |
| `--restricted` also ignores user, project and local settings files; `--disable-slash-commands` turns skills off; `--strict-mcp-config` loads only the kb server | the owner's own broad allow rules, hooks, skills or connectors widening the pass |
| `kb.py` refuses a manifest source outside `[project].author_paths` and the knowledge folder (absolute, `..`, or a symbolic link that leads out), a `[knowledge].out_dir` outside the repository, a concept id that is not a plain slug, and any symbolic link in the knowledge folder | the manifest, or a name, carrying the engine outside the repository |
| After the pass, `nightly.sh` stops (nothing committed, nothing mirrored) if anything outside the knowledge folder and the manifest changed, ignored files included, or if the knowledge folder moved | anything that got past the layers above |
| `nightly.sh` refuses to run the pass on a Claude Code that lacks any of these features | an older version silently ignoring part of the fence |

**The macOS permission for Drive.** The scheduled jobs run through `collab-kit-runner` so that the
permission to read Google Drive's folder (README, "Scheduled jobs and Google Drive") goes to that one
program, never to `/bin/bash` or Terminal. It runs only an absolute path ending in
`/tools/kb/nightly.sh`. Whatever is granted covers every process the job starts, the curator pass
included; the fence above is enforced inside Claude Code and does not depend on it.

**What it does not stop.** The curator still writes the knowledge folder, and the job mirrors that
folder to Drive before anyone reviews it, so an injected return can still steer what the next
conversation reads there (including the knowledge folder's `CLAUDE.md`). It cannot reach the main
branch: curated work waits on the curator branch for a person to merge. If the people who can write
into your Drive folder are not people you trust, read the curator's report before you merge.

**How it is checked.** `tests/dry-run-install.sh` checks the flags and runs a curator stub that
tries each of these escapes with everything the flags grant (the old kit fails those checks).
`tests/live-curator-permissions.sh` runs the real Claude Code with the same flags and decides from
the file system whether each attempt was refused; run it after upgrading Claude Code.

## Supply chain

- The kit has **no package dependencies**: Python's standard library (3.11 or later), git, and a
  POSIX shell. A back end that reaches Google Drive through its API uses rclone, an external
  program reviewed in `docs/rclone-intake.md` and pinned there. A new dependency needs a deliberate review first (license,
  maintenance, known vulnerabilities in OSV, its own security posture) and a note in the pull
  request; the default answer is no.
- Every release attaches a CycloneDX and an SPDX SBOM, with build provenance and SBOM attestations
  (`gh attestation verify <file> --repo <owner>/<repo>`).
- GitHub Actions are pinned to full commit hashes and kept current by Dependabot; OSV-Scanner runs
  weekly and on every pull request; OpenSSF Scorecard runs weekly.

## For contributors

Security is part of contributing, not an extra step:

- no secrets, tokens, account names, or personal paths in commits (the tests reject owner-specific
  text in the kit);
- no new dependencies without the review above;
- workflows: actions pinned by hash, `permissions` as narrow as the job allows, no
  `pull_request_target` with untrusted code;
- anything that touches the grammar, applying returns, the ledger, store paths, the fences, the
  hooks, the mirror, or pushing comes with a test in `tests/` (`python3 -m unittest discover -s
  tests`); a change to the hooks or the CLAUDE.md section also gets a run of
  `tests/live-native-layer.sh`;
- anything that touches the 0.4 curator's fence comes with a test in `tests/dry-run-install.sh` and
  a run of `tests/live-curator-permissions.sh`;
- the unit tests and `tests/dry-run-install.sh` pass before a pull request is merged.

# Security policy

## Reporting a vulnerability

**Please report privately, not in a public issue.** Use GitHub's private vulnerability reporting:
the **Security** tab of this repository, then **Report a vulnerability**. Only the maintainers see
the report.

If you cannot use GitHub, open a public issue that says only that you have something to report
privately and how to reach you. Put no details in it; a maintainer will arrange a private channel.

Please include what you found, the version (`VERSION`, or `tools/kb/KIT-VERSION` in an installed
project), how to reproduce it, and what an attacker could do with it.

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

Only the latest release gets security fixes. Upgrading is `install.py apply` in each project (see
`DESIGN.md`, "Upgrading"), so there is no long-lived older line to maintain. Before 1.0, a fix may
come with other changes; the release notes say what to check.

## Scope

In scope: everything in this repository: `install.py`, the engine (`kb.py`, `nightly.sh`, the
launchd installer, the start-file template), the templates it renders, and the workflows that
build releases. Of particular interest:

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

## The unattended pass

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

- The kit has **no package dependencies**: Python's standard library (3.11 or later) and the shell
  tools that ship with macOS. A new dependency needs a deliberate review first (license,
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
- anything that touches the mirror, the returns check, the curator's fence (its flags, `kb_mcp.py`,
  its guard), or the start file comes with a test in `tests/dry-run-install.sh`; a change to the
  fence also gets a run of `tests/live-curator-permissions.sh`;
- `tests/dry-run-install.sh` passes before a pull request is merged.

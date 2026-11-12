# Collab Kit

Collab Kit installs a collaboration pattern in a project: three channels that let collaborators
outside the repository work on it in full. **Knowledge** goes out (the project's documents, split so
any piece can be loaded on its own, with a concept graph and an index), **returns** come back in
(what a conversation worked out, saying exactly what it relates to), and the **agenda** goes out
(what needs working out together, most pressing first).

The channels are plain files in a Google Drive mirror, so they do not depend on the interface.
Voice in the Claude app is the first interface and the most demanding one (hands-free, whole files
only, found by name), and has its own profile of rules. Typed chat, Claude Code, other assistants,
and people are anticipated; nothing in the structure assumes voice.

Every project's knowledge folder sits in one parent folder, named exactly like the project's
repository; one line in the Claude app's preferences covers every project. Python 3.11+ standard
library and bash; the nightly job runs on macOS (launchd). MIT licensed.

- See it first: [examples/the-lighthouse](examples/the-lighthouse/README.md), a sample project you can
  read in five minutes (a novel, a return that found a contradiction, and the agenda it produced)
- What and why: [DESIGN.md](DESIGN.md) (anatomy, the parent folder, the config surface, install,
  upgrade, release)
- The pattern itself: [templates/tools/kb/COLLABORATION-PATTERN.md](templates/tools/kb/COLLABORATION-PATTERN.md)
- Reporting a vulnerability: [SECURITY.md](SECURITY.md)
- License: [LICENSE](LICENSE) (MIT)

## What you need

- A Claude plan with the **Google Drive connector** turned on in the Claude app (that is how a
  conversation reads the knowledge folder and saves returns).
- **Claude Code** on the machine that runs the nightly job, signed in. The unattended pass needs a
  version with `--restricted` (2.1.319 has it); with an older one the job stops and says so.
- **macOS** for the scheduled job (launchd). The engine itself is plain Python.
- **Google Drive for desktop**, signed in to the account that holds the knowledge folder, and
  **one permission for the scheduled jobs** to read it (next section).
- **Python 3.11 or later** (standard library only; nothing to install) and **git**.

## Scheduled jobs and Google Drive

macOS does not let a background job read Google Drive's folder (`~/Library/CloudStorage`) by default,
and it does not say so: the job just cannot read it. Measured on macOS 26.5: a launchd job running
`/bin/bash` was refused at once ("Operation not permitted"), while the same commands run from
Terminal worked. A job that cannot read the folder would never see a return, so the nightly job now
proves it can read the folder first, and fails loudly (and `install.py check` shows it) when it cannot.

The scheduled jobs therefore run through a small program of the kit's own, `collab-kit-runner`
(built by `tools/kb/launchd/install.sh` into `~/.local/share/collab-kit/`). It runs only a project's
`tools/kb/nightly.sh`, and it is the one program you give permission to, so that `/bin/bash` and
Terminal never need it. Then, at the Mac:

```bash
tools/kb/launchd/install.sh --probe     # runs a real launchd job that tries to read the folder
```

- **If macOS asks** whether collab-kit-runner may access files managed by Google Drive, click
  **Allow**. That is the narrowest grant there is: Google Drive's files, for this one program. (With
  the runner, the read waited for an answer rather than being refused, which is what macOS does when
  it is asking; whether the question reaches the screen is what the probe tells you.)
- **If nothing asks** (the probe fails with no answer, or "Operation not permitted"), give the runner
  Full Disk Access: System Settings, Privacy & Security, Full Disk Access, click **+**, press
  **Cmd+Shift+G**, paste `~/.local/share/collab-kit/collab-kit-runner`, add it, and switch it on.
  macOS has no narrower switch a person can give a background program for that folder. Give it to
  the runner only, never to `/bin/bash` or Terminal, which would cover every script on the Mac.

Run the probe again until it says OK. Whatever is granted covers everything the job runs, the
nightly AI pass included (its own fence still applies; see [SECURITY.md](SECURITY.md)). The runner is
rebuilt only when its source changes, and a rebuild needs the permission again (`install.sh` says so).

## What it costs

The kit is free; the AI work is yours. Two scheduled jobs run on your machine:

- **The nightly pass** runs Claude Code once a day, and only when something changed: a project
  document on the main branch, or returns waiting. Otherwise it stops in seconds without calling
  Claude. When it runs, it uses your Claude Code usage (your plan's limits, or API billing if Claude
  Code is set up that way). `[curator].model` and `[curator].timeout` in `tools/kb/config.toml`
  bound it.
- **The returns job** checks the returns folder every 20 minutes. Checking costs nothing; when
  returns have arrived and settled, it runs the same AI pass.

Conversations in the Claude app use your Claude plan as usual.

## What becomes visible, and to whom

Read this before you install, especially if your repository is public.

- **Google Drive.** The knowledge folder is copied to your Google Drive: the full text of every
  document you register, plus the concepts, answers, agenda, responses, and proposals. Whoever you
  share that folder (or the parent folder) with can read it. The parent folder's start file lists
  every project in it, with the names you say for each.
- **Git: your choice, made at install.** `install.py init` will not finish until you choose
  `--captures-in-git yes` or `no`. With **yes**, every return is committed to the repository as a
  capture, exactly as it arrived (often your own dictated words): the project keeps its full history,
  and a public repository publishes it with every push. With **no**, returns stay only in your Drive
  folder (`_returns/processed/`) and the repository gets only what was made of them. Either way the
  curator's responses, proposals, concepts, and agenda items are committed, and they say what each
  return was about. `install.py init` and `install.py check` warn when the `origin` remote is a public
  GitHub repository.
- **Claude.** Conversations and the nightly pass send what they read to Claude, as any use of Claude
  does.
- **People who can write to your Drive folder** can send returns. Returns are treated as text from
  outside, and the nightly pass is fenced accordingly: see [SECURITY.md](SECURITY.md), "The
  unattended pass".

## What the channels look like

A **return**: a plain text file a conversation saves in the project's `_returns` folder
(`2026-11-11-partial-shade.txt`):

```
Project: garden-planner
From: Sam  (optional: who sent it, when it is not you)
Type: hole
Topic: partial shade is not one thing
What was worked out: shade moves across the day; the plan treats "partial shade" as fixed.
  Morning sun with afternoon shade suits lettuce; the reverse scorches it.
Relates to:
  refines GP#light-requirements
  progresses W-002
Why it matters: the planting suggestions for the north beds are wrong half the year
Sources used: documents/GP-light/GP-03-light-requirements.md
Claude's additions: a sun-hours count per bed would settle it (unverified: the hours for this site)
Verbatim: "shade isn't a property of a bed, it's a schedule"
```

An **agenda item** (shortened): a file in `agenda/`, kept by the nightly pass and listed, most pressing first,
in `agenda/00-AGENDA.md` (`W-002-how-to-describe-shade.md`):

```
+++
id = "W-002"
title = "How should the plan describe shade?"
kind = "work-out"             # question | decision | work-out | hole | task
importance = 3
effort = "session"
status = "open"
stage = "exploring"
blocks = ["W-005"]
refs = ["GP#light-requirements"]
from = ["C01"]
+++

## What's needed
A way to describe a bed's light that the planting rules can use.

## What we know so far
"Partial shade" is too coarse (C01). Candidates: sun hours per season, or morning/afternoon sun.

## Done when
Every bed has a light description and the rules use it.
```

## Quick start

```bash
python3 <kit>/install.py init <project> --name "Project Name" --slug short-id --short "what you say" \
  --drive-account you@example.com --captures-in-git yes|no [--profile <your owner profile>]
# register documents in <project>/tools/kb/manifest.toml, then:
python3 <kit>/install.py apply <project>
cd <project> && python3 tools/kb/kb.py build && python3 tools/kb/kb.py check
python3 tools/kb/kb.py preference-line     # the one line for the Claude app (voice or chat), the same for every project
```

The knowledge folder in Drive is `<parent>/<repository name>`, always. Name the Google account
explicitly; if the project might have its own account, ask before creating anything in Drive.
Personal defaults (your name, the parent folder's name, accounts to refuse) go in a private owner
profile: see [examples/owner-profile.toml](examples/owner-profile.toml).

## Commands

| | |
|---|---|
| `install.py init <project> ...` | write `tools/kb/config.toml` (never overwrites) |
| `install.py apply <project> [--dry-run] [--diff] [--adopt]` | install or upgrade |
| `install.py check <project>` | exit 1 if the installed files differ from the kit and config, or the naming rule is broken |
| `tools/kb/kb.py return-check <file>` | is this return for this project? (exit 3 if not) |
| `tools/kb/kb.py parent [--write]` | the parent folder's start file, with this project's entry |
| `tools/kb/kb.py preference-line` | the line for the Claude app's preferences |
| `tools/kb/kb.py renumber <file>` | give an agenda item or answer a new number (after a merge brought in a duplicate) |
| `tools/kb/kb.py status` | the scheduled jobs: the last run launchd started, the last success, launchd's last exit codes (also in `install.py check`) |
| `tools/kb/launchd/install.sh [--apply\|--probe\|--remove]` | schedule the two jobs; `--probe` checks a launchd job can read the mirror |

## Tests

```bash
tests/dry-run-install.sh     # throwaway install; all three channels, the parent folder, the guards, the curator's fence
tests/live-curator-permissions.sh   # opt-in, a few cents of usage: the real Claude Code against the curator's fence
```

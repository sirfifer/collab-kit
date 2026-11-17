# Changelog

## 0.5.2 (2026-11-16)

Richard's decisions of 2026-11-15, from his phone and voice sessions (DESIGN-0.5.md section 20).

**The agenda first, always.** Every conversation reads the start file, then the agenda (before `WIP/`
and before anything else in a project): it is the one source kept up to date. The start files now say
how a conversation works here: follow through instead of offering to look; say only what you saw;
check the inbox before filing, so nothing is filed twice; and when setup needs the person's own hands,
everything else is done first and they get one script to run. Conversations never trash anything (each
trash asks for approval on the phone and stops hands-free work): finished notes move to `WIP/_done/`,
and old versions are kept. `install.py top --replace-start` now replaces any start file that is not
this kit's template, keeping its setup line and the old file in `_versions/`.

**One catalog of every project.** `knowledge/projects.md` lists every project, in Collab Kit or not,
with where it lives, its state, and a Collab Kit column (`not set up`, `requested`, `live`); a card per
project goes in `knowledge/project-cards/`. `project <folder> collab-kit=requested` asks for an
existing project to be brought in. Fixed: a `project` change filed in the top-level inbox was always
refused.

**Returns are event driven.** The back end runs every minute and does a full pass only when a return
waits (`ck backend run --if-waiting`: one listing of every inbox) or the hourly sweep is due; on macOS,
`watch` lets a synced copy's inboxes start it the moment a file lands. Its read path is the Drive API
(rclone). Upgrade: run `install.py backend --apply` again to rewrite the schedule.

**Fixed before release** (a sceptical review of this version): the minute check counted returns a pass
leaves in place, so one stuck return cost a full pass every minute (it now looks for settled changes
since the last pass); the push example in `backend.toml` was not valid TOML and its `-d` would have let a
title name a local file to send; push bookkeeping resent or dropped items after a failure or a cap; a
`collab-kit=` change on a list without that column did nothing (now refused); the "add to an earlier
return" advice could lose changes (now: never change a filed return; file what is new and name it);
the setup line kept the kit's older wording on `--replace-start`; a Google Doc in an inbox was set aside
before a conversation could move it; a refused pass counted as a pass; Windows opened a console window
every minute (now `pyw`); the example's filter could empty a front-matter block or a return's header.

**Returns: a note after the changes is fine.** Voice conversations add "Verbatim: ..." or a sentence
after the last change, before `End.`; two of Richard's returns of 2026-11-15 were refused for it. A line
that starts with a capital and is not a change now ends the changes when it follows a blank line or
reads as a field ("Verbatim: ..."); the note stays in the return. A misspelled change still fails.

**Optional push notifications.** The first time a critical item appears, the back end runs one
command of yours (`[notify]` in `backend.toml`; ntfy, Pushover, and Telegram examples in
docs/notifications.md). Item text reaches it in environment variables, never on a command line.

**New: the kit itself, as an example.** `examples/the-kit-itself/` is a sanitized snapshot of Collab
Kit's own project (its agenda, applied returns with ledgers, and knowledge), laid out as
`install.py project --home repo` lays out a repository. `tests/public_example.py refresh` takes a new
snapshot (generic rules for accounts, paths, and Drive ids; the owner's private never-publish words
from a file outside the repository); `check` fails, in the tests and before every release, when the
example is not what this kit generates or reads.

**Fixed: files another device wrote could not be read in a Claude Code session.** In a synced
folder, a file written elsewhere (by a phone conversation, say) is a cloud-only placeholder until read,
and processes started under Claude Code inherit a macOS policy that forbids that download: every read
failed at once with "Resource deadlock avoided". The folder store now allows the download for its
process and reads again.

**Returns: a kind word starts a new item.** `task "Order the drip line" importance=2 "What's needed"`
means `new-item kind=task`; so do `question`, `decision`, `work-out`, and `hole`. A second quoted text on
a new item is its What's needed. Voice conversations write these unprompted.
The example leaves out whole topics (`leave_out` in its snapshot.toml): the article stays out of it.

## 0.5.1 (2026-11-15)

**Start files stay put; what is going on is on the agenda** (DESIGN-0.5.md section 19). A start file
is the one consistent way in and changes only at setup. It now says how every conversation starts
(the start file, `WIP/`, the agenda's front page, and `knowledge/projects.md` when a project comes
up) and holds no state: no health or due-soon blocks, no projects table. `agenda/00-PRESSING.md`
opens with the back end's health ("up to date as of", what it could not handle), then deadlines,
critical items, work in progress, and important items. Importance 1 means critical, raised first
everywhere; the back end files its own failures at importance 1. The Claude Code brief and
`ck items` use the same order, and the brief says plainly when a back end has stopped.
The front page exists at every level: without a back end, Claude Code sessions rebuild it and
conversations keep it current. The back end sets the start file's setup line once, on its first run,
and leaves a hand-edited line alone; `install.py top --replace-start` replaces a start file from
before 0.5.1 (the old one is kept), and `--setup` sets the line by hand. Projects are listed only in
`knowledge/projects.md`. Start files name the kit's series (0.5), so a patch release never changes
them. A review of this change found that a forged ledger could still reach across units through
`undo`: a project's ledger now reaches the top level only for its own row in the projects list.

## 0.5.0 (2026-11-15)

The release that makes Collab Kit work from a phone for weeks without touching the back end
(VISION.md), and makes it a native part of every project an AI agent works in. The design record is
DESIGN-0.5.md.

**New: the layout.** One Collab Kit folder: a top level (`00-START-HERE.md`, `_returns/`, `agenda/`,
`knowledge/`, `WIP/`) and `projects/<name>/collab-kit/` shaped the same way. A project's home is
either that folder or its repository (`collab-kit/` in the repository).

**New: returns with a grammar.** Every change to an agenda or knowledge is a return with a
`Changes v1:` block (`new-item`, `set`, `log`, `settle`, `snooze`, `withdraw`, `reopen`, `status`,
`knowledge`, `project`, `new-project`, `push-request`, `undo`), applied whole or not at all, at most
once, with a ledger. Conversations apply their own returns when no back end runs (level 1);
otherwise the back end does.

**New: the back end is scripts only.** `ck backend run`: a lease (one runner at a time), every inbox
applied, repository-homed projects pulled, applied, committed (`collab-kit/` only), pushed under
guards (private repositories only unless allowed, a deny-list), and mirrored to the cloud folder
(copy, never sync; an edit to a mirror is saved as a return first). It writes the top-level start
file's setup line once, and `agenda/00-PRESSING.md` across every project (0.5.1: with its health). Scheduled by
launchd (through `collab-kit-runner` when the folder is a Drive for desktop folder), a systemd user
timer, or Task Scheduler: `install.py backend`.

**New: native in every project.** `install.py project <repo>` installs, into the repository:
`tools/collab-kit/` (the engine and the `ck` command), a Collab Kit section in `CLAUDE.md` and
`AGENTS.md`, hooks in `.claude/settings.json` (a session-start brief: the inbox, what is in progress
and due, recent status, other unmerged work, a kit-update notice; and a check that asks the agent to
record its work in Collab Kit when it changed files and recorded nothing), and the `collab-kit`,
`collab-kit-return`, and `collab-kit-upgrade` skills. `install.py machine --user-hooks` adds
user-level hooks so sessions started in a parent folder are briefed the first time they touch a
project. Verified with the real Claude Code (`tests/live-native-layer.sh`).

**New: starting a project by voice** (`new-project`, from an idea on the top-level agenda), moving
items between projects, approved pushes as agenda tasks, versioning by name with retention and
pinning (in the start file), WIP checkpoint notes, the seven-call reply cap.

**Changed.** The 0.4 AI curator leaves the base product. The 0.4 knowledge build (`kb.py`) stays for
projects that split their documents into sections; with `[knowledge].agenda = false` it leaves the
agenda to 0.5.

**Moving from 0.4.** `install.py migrate-04 <repo>` (channels to `collab-kit/`, agenda items
converted: importance runs the other way and `done` becomes `settled`), then
`install.py project <repo> --home repo`. Unload the 0.4 scheduled jobs first.

**Security and integrity.** Text from outside is fenced wherever an agent reads it; the back end
validates every path a return or a ledger names (a forged-ledger traversal was found and fixed in
review before release); every unpushed commit is checked against the deny-list and its paths before
a push; a failed push loses nothing. See SECURITY.md, "Text from outside", and DESIGN-0.5.md section
18.

## 0.4.0 (2026-11-11)

The parent folder, the fenced curator pass, captures in git as a forced choice, the launchd runner
for Google Drive access. See DESIGN.md.

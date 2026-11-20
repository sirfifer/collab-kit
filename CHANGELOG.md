# Changelog

## Not yet released

**A full pass over rclone takes seconds, not 20 minutes** (agenda W-020). A back end reaching the
folder through rclone read every file with its own `rclone cat`, 4 to 16 seconds each, and the front
page alone reads every agenda item: a pass took 20 to 30 minutes, and every arriving return started
one. A pass now lists the whole folder once (`lsjson -R` with md5s) and downloads a file only when
its md5 is not in the back end's cache (`<work>/rclone-cache/`); every other listing and read comes
from the listing and the cache, and writes go through rclone as before and update both. Before
writing what it decided from the listing, a pass looks again: a return reads each file it changes as
it is now (and plans again if one moved on), a return changed since the listing settles again, and the
mirror lists its project's copy again. The lease is always read as it is now, checked once before the
first project and renewed every two minutes; the mirror's state file is written only when it changed. A name Drive holds twice still fails closed, and a Google-native file is still
never read. Every pass ends with one log line: how long it took and its rclone calls. Sessions on a
machine that reaches the folder through rclone read it the same way (the cache in the machine's
state folder), so a brief there takes seconds rather than minutes, inside the session hook's 30.
Through a synced folder nothing changed. See DESIGN-0.5 section 22.

**A back end writes nothing to a folder that is not a Collab Kit folder.** Before taking its lease,
a pass looks at the folder's top; without `00-START-HERE.md` or `agenda/` it refuses to run, names
the folder, and writes nothing. Found on the Studio on 2026-11-20: answering Yes to rclone's "Shared
Drive" question on a reconnect empties `root_folder_id`, which points the remote at another drive.
The docs now say to answer No, and to check the remote with `rclone lsf <remote>: --max-depth 1`
after any reconnect.

## 0.5.3 (2026-11-19)

The kit dogfooded on itself, and checked the way an agent meets it: an AI agent with no context
installed, used, upgraded, broke and repaired Collab Kit in a sandbox from the documentation alone,
and an audit compared every design statement with the code. What they found is fixed here.

**For agents: one procedure.** [docs/for-agents.md](docs/for-agents.md) is the step-by-step for
installing, upgrading, checking and repairing Collab Kit, linked from the README's first lines. The
kit's own repository now has a `CLAUDE.md` and `AGENTS.md` for agents working on the kit itself.

**The kit runs on itself.** Collab Kit is installed in its own repository (`tools/collab-kit/`, the
hooks, the skills, the Collab Kit section), and `tests/test_own_install.py` fails whenever that
install falls behind the engine.

**Installing a project creates its folder.** `install.py project` used to stop at the repository: a
project whose home is the Collab Kit folder had no folder there, so its returns waited in the
repository and nobody delivered them. It now creates the project's folder (new files only), and files
a return that marks the project live in `knowledge/projects.md`, adding its row from `--about` and
`--spoken` when it is not listed. The `project` change can add a missing row when it says what the
project is (`about=`; a misheard name without it adds nothing), and takes `where=`.

**A late back end keeps its inbox.** Once a back end has run for a folder, sessions never apply
returns themselves, even when it is late or stopped: they file, the returns wait for the back end and
its lease, and the brief and `ck doctor` say to tell the person. Before, a session applied them
itself, without the lease, and overwrote the front page's warning that the back end had stopped.
`install.py top --setup none` (retiring a back end) now retires its heartbeat, so sessions apply
again.

**Upgrades in one command per place.** `install.py top --replace-start` also brings the start file of
each project homed in the folder current (keeping its `Project:` line), and `install.py project
--replace-start` does the same for one project. Old versions are kept.

**Tools that say what to do.**
- `ck doctor` prints where the kit's checkout is, lists each failure with the command that fixes it,
  and exits 1 when anything needs fixing.
- `ck apply` with no folder applies this project's own waiting returns (level 1 only). With a folder,
  it refuses one that is not a unit, and refuses when no waiting return names the given unit, where
  it used to set every return aside as a stray.
- A damaged engine in a project prints the command that repairs it instead of a traceback; in a hook,
  the agent sees it.
- `install.py backend --config-only` writes `backend.toml` and stops, for review; the dry run shows the
  config it would write. On Windows, and for systemd's lingering, it says plainly that the person
  runs the printed commands.
- `install.py machine` says when the config's kit source is older than the kit being run.
- The back end's dry run says which returns are still settling (they wait 120 seconds).
- The brief says the back end checks the inboxes every minute; it used to say "every 60 minutes".

**Fixed before release** (an independent review of the changes above):
- The tests read this machine's real Collab Kit config, and the public example's generator could
  reach the live folder. Every test module now imports `tests/isolation.py` first, which points the
  kit at a machine config that does not exist and a throwaway state folder. (The suite also runs in
  half the time.)
- `install.py project` crashed on a quote in `--about`, and could raise on a folder error after the
  repository side was written: values are now quoted for the grammar, and any folder error is reported
  as "run this again". A name the kit refuses (capitals, `repo--task`) now installs nothing and
  suggests one, and a worktree takes its main checkout's name, so no stray folder is made in the
  Collab Kit folder. The start file is written last, so an interrupted first install is finished by
  the next run. `--dry-run --check` decides the catalog step exactly as a real run does.
- A heartbeat that cannot be read just now (an rclone timeout, a Drive placeholder) counts as a back
  end that may be running: sessions file and never apply.
- `top --replace-start` reads through the store (Drive placeholders retried), skips a file it cannot
  read instead of stopping, and retires a heartbeat before the loop. `keep_description` tolerates
  extra blank lines and keeps only the description of a start file whose shape it does not know.
- `ck apply` rebuilds the front page at level 1 and accepts the top level's names (`Collab Kit`);
  the shared-client check finds rclone's default config on Windows and with `XDG_CONFIG_HOME`; the
  repair message expands `~` and gives the right advice for the kit's own checkout.
- Then a check of those fixes found more, also fixed: curly quotes and line breaks in `--about` are
  filed the way the grammar reads them back; a catalog row older than the Collab Kit column gets the
  column; `--name` never contradicts an existing `project.toml` (rename a project there), and a unit
  that is not `projects/<name>/collab-kit` is never written to; a worktree of a bare repository or a
  submodule must be named; a subfolder of a repository keeps its own name; the top start file is read
  through the store; `ck apply`'s front-page rebuild cannot fail the apply; and the repair advice for
  the kit's own checkout never suggests discarding work.

**Fixed: a back end over rclone refused every run.** Its account check asked rclone for the signed-in
account (`config userinfo`), which rclone does not support for Google Drive, so the answer was always
empty. The check now reads who owns the folder's start file (`lsjson --metadata`) and compares that
with `account` in `backend.toml`. This is the folder's owner, not the signed-in account: a folder
shared from another account is refused, which is what the setting promises. Found on the first real
run on a second machine (2026-11-18); the test stand-in for rclone had never been asked that question.

**The back end reports rclone's shared Google client.** A Google Drive remote with no OAuth client of
its own uses rclone's shared one, which Google retires during 2026 (the back end would then stop) and
which is rate-limited across every rclone user. The back end now lists it as a problem on the front
page; [docs/rclone-intake.md](docs/rclone-intake.md) says how to give the remote its own client.
An rclone error now shows its cause (the end of rclone's message, without its notices): on the first
real back end every error was cut off after the shared-client notice.

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
every minute (now `pyw`, and no window for the programs it starts); the example's filter could empty a
front-matter block or a return's header. A check of those fixes then found: the first version of the
note rule could drop a change that came after a note (now refused); a return that settled while a pass
ran waited for the hourly sweep (only what was settled when the pass began counts as seen); a
repository-homed inbox set a fresh Google Doc aside without the settle wait; a dead pass's lease on the
same machine could be taken from a same-named machine (now only once it is five minutes stale); an item
briefly unreadable was pushed again (the back end now remembers an item for a week).

**Returns: a note after the changes is fine.** Voice conversations add "Verbatim: ..." or a sentence
after the last change, before `End.`; two of Richard's returns of 2026-11-15 were refused for it. A line
that starts with a capital and could not be a change now ends the changes when it follows a blank line
or reads as a field ("Verbatim: ..."); the note stays in the return. Nothing is ever dropped quietly: a
line that could be meant as a change ("Settled W-3", "New item ...", "Mark W-3 settled") is parsed as one
and refused if it is not, and a return with a change after its note is refused.

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

# Changelog

## Not yet released

**The repository is on GitHub, and its CI runs green on every system.** `github.com/sirfifer/collab-kit`
is public from 2026-11-23; until then it had never been pushed, so the CI matrix had never run. Its
first run found what only other systems show: Windows checked text out with CRLF line endings (a new
`.gitattributes` keeps every text file LF), the lease test asked Windows for a check it does not have
(skipped there, as the engine already skips it), a test wrote CRLF where Drive holds LF, and the
"gh is not installed" test could not hide a runner's own `gh`. One was a real fault: in the
project list, a new project's place named its local path and machine before its GitHub address, so a
long path or machine name cut the address off. It now comes first, as the status line already had it.

**The README is the project's home page.** About three quarters of its old length, in the order a
newcomer needs: what it is, what a session is like, what you need, how it works, where it stands,
how to try it. It says who it is for, what it needs (a Claude plan whose voice mode can use
connectors, Google Drive, a computer once), and that the project is independent of Anthropic.
Four pictures drawn to be read on a phone: the loop (`docs/images/the-loop.svg`), why a big project
fits in a voice talk (`only-what-the-talk-needs.svg`), the steps from a folder upward
(`start-with-a-folder.svg`), and one day round the loop (`one-day-round-the-loop.svg`, in
`docs/how-it-works.md`). Setting up past the folder, what an agent in a project sees, platforms and
the test commands moved to a page of their own, `docs/setup.md`. New: `CONTRIBUTING.md` and
`CODE_OF_CONDUCT.md`.

**The pages say what the code does.** A check of every claim on the public pages against the code:
the document index is an extra for a project that lives in a repository with the knowledge build and
a back end on a machine, and every project gets small named files; an agent's brief shows what is
waiting, due and in progress, not what was decided; a return can be undone while nothing has changed
its files since. `docs/for-agents.md` had `returns_in_git` the wrong way round and told agents they
could give `install.py top` an rclone remote: it now refuses one instead of creating a local folder
of that name.

**An icon for the kit's pushes.** `docs/images/collab-kit-icon.svg`, with a 1024 by 1024 and a
72 by 72 PNG: a first version, for a Pushover application of the kit's own, so its pushes are told
from everything else on a phone at a glance. `docs/notifications.md` says how.

**From a brainstorm to a project with a repository** (agenda W-035, W-037, decided in W-038;
DESIGN-0.5 section 25). Starting something new is now possible from a phone in one return. Both parts
are additive: older returns and a back end with nothing set behave as before.

- **One step.** `new-project` may carry the idea itself, so no agenda item has to exist first:
  `new-project name=<name> "<the idea, as a short title>" about="..." spoken="..."`, with what the
  talk worked out in a fenced block under it. That text becomes the project's first agenda item,
  and the top level's status says the project started. `from=W-NNN` works exactly as before. The
  start file's "Starting a project" is one step, and covers a talk that began with no project:
  say "make this a project" or "save this to Collab Kit" and the whole brainstorm goes into one
  return. The line for the Claude app's preferences (README, quick start) now names those phrases.
- **A repository, when the machine is set to.** Off unless a back end's `backend.toml` has
  `[new_projects]`. With `repositories = "~/dev"`, a project started by a return also gets a git
  repository at `<repositories>/<name>`: the kit installed, a README, a first commit. With
  `github_owner = "you"` as well, `<owner>/<name>` is created on GitHub, **always private**, and the
  first commit is pushed (needs the `gh` command, signed in; reviewed in
  [docs/gh-intake.md](docs/gh-intake.md)). The catalog then says where the project lives. A failure
  leaves the folder project ready and nothing half-made: it is said on the front page, raised as
  one critical item, and tried again on every full pass until it works, the project is undone, or
  you drop that item. At most `per_day` (3) repositories a
  day; the back end's `deny` list covers the name and the description. Only a checked project name
  and the configured owner ever reach a command line. The kit never creates a public repository
  and never changes one's visibility. `ck doctor` on the back end's machine checks that it is
  ready. Tested against a stand-in for GitHub (`tests/fake_gh.py`), not yet against a real account.
- **Fixed: undoing a `new-project` return.** Since 0.5.0 the undo failed while it ran and then
  stayed in the inbox, failing on every pass. It now takes the project's folder back.
- **Fixed: a file in `_returns/applied/` that is not a ledger** stopped every later `new-project`
  return from being applied. It is now skipped.
- **Fixed: a return written indented.** A return whose every line was indented (copied out of a
  list) was read as a return with no changes and filed away as done. It is now read as the return
  it is.
- A back end says in its heartbeat that it takes the one-step form (`"accepts"` lists
  `new-project-idea`). One that is a release behind refuses it clearly ("'new-project' needs
  from="): the return goes to `_returns/failed/` with a critical item, and nothing is made.

**To take this up:** the back end's machine pulls the kit **first**; then the folder's start file is
replaced (`install.py top "<folder>" --human "<name>" --replace-start`), since it now tells
conversations to write the one-step form; then each project is upgraded as usual. The person adds
the two phrases to the line in the Claude app's preferences. The repository setting is a separate,
later choice: add `[new_projects]` to `backend.toml` on the back end's machine and run `ck doctor`
there.

**The round trip can be heard** (agenda W-030, W-031, W-032; DESIGN-0.5 section 24). A day's
walk-through by voice found the loop working and silent in three places. All three are additive:
older returns, items, and back ends keep working.

- **What finished is said.** The agenda's front page gains "What happened in the last two days":
  status lines from every project, items settled or dropped, and returns still waiting in an
  inbox, at most six lines of each. The start files tell a conversation to read the page again
  each time the talk moves to another project, or when asked, and to say what is new on it. Opt-in, `status = true`
  under `[notify]`: one push for each new status line, under the same limits as critical items.
  Every push now carries `COLLAB_KIT_KIND` (`critical`, `blocked`, or `status`), so a phone can
  give each its own priority and sound ([docs/notifications.md](docs/notifications.md) has a
  Pushover example); a command that ignores it works as before.
- **A blocked agent's question reaches the person, and the answer reaches the agent.** The Collab
  Kit section agents read, and both skills, now say: when the work cannot go on, file the question
  as critical. `ck ask "..." --blocks W-012` does that and names the item that waits (a new,
  optional `blocks=` on `new-item` and `set`; the front page, `ck show`, `ck items` and the brief
  show the link). Settling the question also logs the answer on the item that waited.
  `ck wait W-015` (or `ck wait <the id ck ask printed>`) waits until the question is settled (exit
  0), dropped (3), or the time is up (4), and prints the answer as data, never as an instruction.
  A session that has ended is not resumed: its successor's brief shows the answer.
  A back end now says in its heartbeat which additions it accepts; until yours is updated,
  `ck ask --blocks` writes the link as text in the question, so nothing is refused.
- **A back end that is down can be heard.** The front page's health is a time (the last full pass),
  not a date. The minute check writes the time of every check to a small file,
  `agenda/00-HEARTBEAT.md` (one write a minute; the page itself is not rewritten). The start files
  tell a conversation to say first that the back end is down, and that new items have no numbers
  yet, when that time is more than about ten minutes old or has not moved between two readings (a
  conversation may not know the time of day: a phone test, agenda W-036); and to say so when a
  return is still waiting ten minutes on. The session
  brief and `ck doctor` report a stale heartbeat. Opt-in, `[heartbeat]` in `backend.toml`: a
  dead-man ping after each successful check, so a service outside the machine can alert the phone
  when the checks stop ([docs/notifications.md](docs/notifications.md)). `install.py top --setup
  none` retires the heartbeat file with the back end.

**To take this up:** each back end pulls the kit (`git pull`, then `ck doctor` in a project); the
schedule did not change. The folder's start files change: `install.py top "<folder>" --human
"<name>" --replace-start` (the old ones are kept). Each project's install is refreshed as usual
(skill `collab-kit-upgrade`).

**The capability walk-through is the kit's end-to-end test.**
[docs/capability-walkthrough.md](docs/capability-walkthrough.md) defines it: one invented user (a
researcher working hands-free from a phone for a whole day), her day in ten steps, twenty-one
capabilities with what each needs (the folder, a back end, or a machine with agents), four
verdicts, and the results of its runs (2026-11-22, first run: about 40% hands-free, 25% only by
typing, 35% not possible; second run, with the round-trip changes: 13 of 21 hands-free, 1 by typing,
7 not possible). A skill in this repository, `capability-walkthrough`, runs it the same way each
time and records regressions first. VISION.md gains a principle, "Simple first, and the base is
for everyone": the folder and a conversation work for everyone with nothing configured, and
everything heavier is turned on by the person who needs it. The agent guide (CLAUDE.md, AGENTS.md)
carries both as rules 9 and 10. No behaviour changed.

**The documentation explains the project to someone new** (agenda W-022). The README now opens with
what Collab Kit is for (long, fully informed working sessions about a complex project, hands-free, by
voice), what a session is like, and why voice mode cannot do that alone, and says plainly what works
today and what does not yet. Two new pages: [docs/how-it-works.md](docs/how-it-works.md) follows one
session round the whole loop (what is loaded when, one return's life, how fast, why the back end has
no AI), with a diagram of the flow (`docs/images/how-collab-kit-works.svg`);
[docs/folder-structure.md](docs/folder-structure.md) shows every folder and file, who writes and
reads each, and the ten rules the layout follows. VISION.md gains "What it makes possible". No
behaviour changed.

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

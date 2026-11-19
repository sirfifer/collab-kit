# Collab Kit 0.5: design record

The current design record of Collab Kit 0.5. 0.5.0 and 0.5.1 shipped on 2026-11-15 and 0.5.2 on
2026-11-16; section 21 describes 0.5.3. Every decision here was made or confirmed by the owner, and
every decision is measured against [VISION.md](VISION.md). [DESIGN.md](DESIGN.md) is the 0.4 record,
kept because it is the only reference for the 0.4 knowledge build (`tools/kb/`), which is still part
of the kit.

**Status.** The architecture was locked on 2026-11-14, after two rounds of simulation. Where a later
section revised an earlier one, the earlier one says so; anything not built is marked "not built yet
(planned)". Done: the Collab Kit folder has been in use since 2026-11-14 (section 17), the back end
has run on the Studio since 2026-11-18, and rclone's dependency intake review concluded "accept with
conditions" on 2026-11-15 ([docs/rclone-intake.md](docs/rclone-intake.md), section 6). Still open,
without changing the architecture: which assistants beyond Claude can use it (research in progress).

## What 0.4 could not do

Every channel belonged to a project that already existed. Nothing could start new work, nothing
saw across projects, and curated work waited for a merge at the machine. The vision's test (weeks
or months without touching the back end) failed on all three.

## Decisions

### 1. The name is Collab Kit, everywhere

The product, the repository, and the top folder in storage are all Collab Kit (the folder was
`Project Knowledge`). Inside a project, the folder holding the project's channels is `collab-kit/`,
in storage and in the repository alike (it was `knowledge/` in the repository and the bare project
folder in Drive). "Knowledge" now means only the knowledge channel.

### 2. The layout (settled 2026-11-14)

```
Collab Kit/                    the system's folder, wherever the person keeps it
  00-START-HERE.md             the one file an assistant is pointed at
  _returns/                    the top-level inbox
  agenda/                      the top-level agenda
  WIP/                         checkpoint notes between saves (section 17)
  knowledge/                   the top-level knowledge (one file, or many)
  _backend/                    the back end's own: lease.json, heartbeat.json, mirror state (when one runs)
  projects/
    <project>/
      collab-kit/              the project's channels, shaped like the top level
        00-START-HERE.md
        _returns/
        agenda/
        WIP/
        knowledge/
      ...                      the project itself, if it lives here (documents, music, data, anything)
```

- **The top level is the system.** Its channels sit at the top, beside `projects/`.
- **A project folder is the project.** `collab-kit/` is how it is collaborated on; everything beside
  it is the project itself. A project with its own repository usually has only `collab-kit/` here,
  a copy of the repository's `collab-kit/` folder. A project without one keeps all of itself here.
- **The back end writes only inside the channel folders and its own `_backend/`** (and start files
  only when it creates or mirrors them, plus once the top-level start file's setup line: section 19).
  It never touches a project's own files, so there are no reserved names in a project.
- **Moving a project into a repository later:** the project's own files move to the repository;
  `collab-kit/` stays and becomes the copy of the repository's `collab-kit/`.
- **The top level needs no name.** A conversation that names no project is at the top level: "what's
  on my agenda", "I have an idea for something new".

**The top level's channels:**

| Channel | At the top level |
|---|---|
| Knowledge | the person's whole world of work: every project (what it is, its state, its names), standards and procedures, skills, resources, their AI setup (assistants, machines, local models), personal and professional status |
| Returns (the inbox) | anything about no single project, or several; ideas; project requests |
| WIP | checkpoint notes between saves (section 17) |
| Agenda | items about no single project; ideas growing into projects (no name needed yet); and, generated, its front page `00-PRESSING.md`: the back end's health, then the pressing items from every project, deadlines first (section 19) |

### 3. Source control: one choice at setup, two answers

**Not built yet (planned).** As built, the top level always lives in the cloud folder: the back end
and the agenda's front page treat it as cloud-homed, there is no top-level repository, and setup
offers no choice. Only a project can have a repository as its home (sections 7 and 18). The plan:

| Mode | The top-level repository holds | For |
|---|---|---|
| **Projects separate** | everything except `projects/` (one ignore line) | people whose projects have their own repositories |
| **All in one** | the whole tree | everyone else; or no repository at all |

In "projects separate" mode a project may have its own repository or live only in storage; nothing
is mixed inside the top repository either way. Moving a project to its own repository is to be a
skill (section 13; not built yet either). The top-level repository's suggested name is
`<github-user>-collab-kit`, unique by construction; the kit's own repository is `collab-kit`.
Projects keep the naming rule: a project's folder is named exactly like its repository.

### 4. Open formats only: a cloud drive is just a drive (Decided)

Everything Collab Kit stores is an open, portable file: `.md`, `.txt`, `.html`, `.csv`, `.json`,
images and the like. Never Google Docs, Sheets, or Slides, or any other service's native format.

Verified 2026-11-14 with the Claude Google Drive connector: creating a text file **converts it to a
Google Doc by default** (the test file came out as an empty Google Doc); with
`disableConversionToGoogleType` set, it is a real `.md` file and reads back correctly. So every
instruction file tells the assistant to create files with conversion disabled, and anything in a
native format is refused, never processed.

### 5. The ladder: start with a folder, upgrade one step at a time (Decided)

| Level | What it is | Who does the filing |
|---|---|---|
| 1 | **A folder in a cloud drive.** The base product. | the conversation, with the person present |
| 2 | + a back end (a machine, or a scheduled cloud run) | scripts |
| 3 | + the top level in a repository (**not built yet (planned)**, section 3) | scripts |
| 4 | + each project in its own repository | scripts |

Each step up is meant to be one migration, never a rebuild. Built: level 1 to 2 is
`install.py backend`; a project's repository becomes its home with `install.py project <repo> --home repo`
and a `[[project]]` table in `backend.toml` (level 4 does not need level 3). Not built yet (planned):
level 3, and moving a project's existing channels from the folder into its repository. The folder on
the phone itself was researched and set aside (sections 6 and 17); a cloud folder is the floor.

**One set of operations, two ways to apply them.** The operations (create an item, set a field,
log, settle, add knowledge, start a project, ...) are defined once. At level 1 the conversation
applies them itself, following the instruction files. At level 2 and up the conversation writes
them into a return and scripts apply them. Same names, same rules, same results.

### 6. What a conversation can do to files (verified, and the editing question)

Verified 2026-11-14 with the Claude Google Drive connector (typed; voice passed the same evening,
section 17): search and list by folder, read, create a plain file, create a folder, rename, move, and
trash. **It cannot change an existing file's content.** The connector is built and run by Google;
its `update_file` changes only metadata (name, folder, star, lock). Google's own Drive MCP reference
(developer preview) lists no content-update tool either. This is a gap in Google's connector today,
not a Drive limit: the Drive API can replace a file's content in place.

**Decided: editing is versioning by name.** Without in-place editing, "edit" and "keep a version"
become the same act, which is also the version history that units without source control need:

1. Create the new content under the original name, with conversion disabled.
2. Move the older file to the folder's `_versions/`, renamed with the UTC time to the second
   (`knowledge/projects.md` becomes `knowledge/_versions/projects.20261114T153000Z.md`).
3. Keep every version. Conversations never trim or trash anything; trimming by the retention rule
   in section 17 is back-end work, not built yet.

(Revised 2026-11-16, section 20: this first said rename first, then create, and trash older
versions. Section 16 made it create first; section 20 stopped all trashing.)

Consequences, stated as rules: a file's **name** is its identity, never its Drive id (ids change on
every edit); readers ignore `_versions/`; if step 2 fails, the name has two live files, and the
newer by creation time is current (whoever sees the older moves it to `_versions/`, section 16). Two
conversations editing one file: the later one wins and the earlier is in `_versions/`. No
third-party connectors and no connector of our own.

**Watched:** Google adding content updates to its Drive connector. When it does, editing becomes an
in-place update plus the same `_versions/` copy, and nothing else changes. Where a connector already
updates in place (OneDrive), the same rule applies: copy to `_versions/`, then update.

**The folder on the phone itself (research, 2026-11-14).** Not possible with the stock apps today:
the Claude app on Android and iOS has no access to the phone's files or a chosen folder, connectors
run in Anthropic's cloud and cannot reach the phone, and Gemini and ChatGPT only take one-off
attachments. Android's on-device equivalent of connectors (AppFunctions) is an experimental preview.
What exists:

- **A copy of the folder kept on the phone** (Android: a sync app such as Syncthing-Fork or a
  FolderSync-type app; iOS: iCloud "Keep Downloaded" cannot reach Drive), while the assistant still
  works through the cloud connector. Gives an offline copy, not on-device work.
- **iOS Siri + Shortcuts:** dictate, read a file, "Ask Claude", append the reply to a file, speak it.
  Hands-free single turns over files on the phone; not a conversation. Worth a hand test.
- **Our own app (an upgrade, Android first):** folder access granted once by the user, the Claude API
  with file tools, speech in and out (Anthropic has no speech API, so a speech service too). The only
  route to the whole structure on the device, by voice. Later it can offer its tools to other
  assistants (Android AppFunctions, iOS App Intents).

**Decided for 0.5:** the cloud folder is the base; the own app is recorded as a future upgrade.
(Revised the same evening, section 17: the on-device app is dropped.)

### 7. One source of truth per unit, one direction per folder (Decided)

Found by all four simulations. Every unit (the top level, or a project) has a home: a repository or
the cloud folder.

- **Home is a repository:** `knowledge/` and `agenda/` flow repository to cloud; `_returns/` flows
  cloud to repository. Returns are applied in the repository, committed, and mirrored out.
- **Home is the cloud folder:** the cloud folder is the truth for everything; git, if any, is to keep
  a one-way history of it (not built yet (planned), with level 3; today the folder's `_versions/`
  is its only history).
- The back end **never deletes** in the cloud. Anything unexpected moves to `_returns/strays/` and
  becomes an agenda item. A git checkout never lives inside a synced folder.

### 8. The back end is scripts, and only scripts (Decided), with a real grammar (Decided)

The conversation does the thinking; the back end files. Returns carry a versioned `Changes v1:` block.
Simulation showed the first sketch was far too small for real returns. v1 as built
(`engine/collab_kit/returns.py`, `OPS`):

- **items:** `new-item` (optionally with a temporary handle, `new-item @headcount ...`; fields
  `title=`, `kind=`, `importance=`, `status=`, `due=`, `project=`), `set` (the same six fields; it
  never makes an item settled or dropped), `log`, `settle ... outcome=`, `snooze ... until=`,
  `withdraw ... reason=`, `reopen ... reason=`. A kind word starts a new item of that kind:
  `question`, `decision`, `work-out` (or `workout`), `hole`, `task` (or `todo`), as in
  `task "Order the drip line" importance=2 "What's needed"` (a second quoted text is its What's needed);
- **status:** `status "text"`, an entry in the unit's `knowledge/status.md`;
- **knowledge:** `knowledge <path>` writes one whole plain file inside `knowledge/` from the fenced
  body under it (in a repository-homed unit, never a file the knowledge build generates);
- **the project:** `project [<name>]` with `spoken=`, `about=`, `active=`, `collab-kit=`, `where=`
  changes a row of the top level's `knowledge/projects.md` (a project's inbox only its own row); a
  missing row is added only when `about=` is given (0.5.3, section 21); `new-project name= from=W-NNN
  "part of the idea's title"`, with `about=` and `spoken=`, starts a project (section 11);
- **push-request** `repo= approval=` (and `branch=`): an approved push becomes an agenda task
  carrying the approval verbatim (sections 17 and 18);
- **undo** `<return id>` of a whole earlier return;
- multi-line text in fenced bodies.

Aliases: `drop` is `withdraw`, `close` is `settle`, `push` is `push-request`, and `newitem`,
`new_item`, `newproject`, `new_project`, `push_request`, `pushrequest` are read as the hyphenated
names. The header names the unit (`Project:`, `top` for the top level); an `Id:` line is optional
(otherwise the file's name without `.md` is the id). Not built yet (planned): concepts and answers,
proposals against a document, and registering a document as changes of their own.

Rules: a return is applied whole or not at all, and at most once (a ledger of applied returns, kept
with the effects); only the block right after the header is parsed; curly quotes, bullets and bold
are normalised; dates are absolute (the conversation reads them back); a change naming an item
repeats part of its title as a check; every return has a unique id and ends with `End.`.

**The 0.4 AI curator (Decided):** leaves the base product (done: the 0.5 back end runs no AI). Not
built yet (planned): scripts that take the mechanical part (exactly which concepts and answers went
stale when a document changed; registering new documents) and raise one "review these" agenda item
per project, and an optional reviewer for the judgment part, whose only output is a return through
the same parser. Today the back end runs the knowledge build (`kb.py build`) in each pass for a
repository-homed project that has it, and nothing flags stale concepts.

### 9. Runners (Decided)

| Runner | 0.5 |
|---|---|
| A machine (laptop or always-on), macOS launchd; Linux systemd | build |
| GitHub Actions, hourly (fits the free tier on a private repository) | build |
| Claude Code scheduled cloud sessions | **dropped.** It would put an AI between incoming text and the credentials (all four reviews) |
| A container | later |

- **One runner at a time:** a lease file in the cloud folder; any other runner exits. Only the back
  end mints item numbers, never reused. A backup runner is advanced configuration.
- **Cloud credentials:** a separate Google account for the bot, shared as editor on `Collab Kit/`
  only (a leak reaches that folder, not the person's Drive); creating repositories only on a machine
  runner. Cloud runners reach the API through rclone (decided; the dependency intake review accepted
  it with conditions on 2026-11-15, [docs/rclone-intake.md](docs/rclone-intake.md)).
- **Health is visible:** the agenda's front page (`agenda/00-PRESSING.md`) opens with the date the back
  end is current as of and anything it could not handle. (Revised 2026-11-15: not in the start file;
  section 19.)

### 10. The person hears what matters first (Decided)

The agenda's front page carries the back end's health, anything that failed to file, anything overdue
or due within two weeks, and critical items (importance 1). The start file sends every conversation
there right after itself, and the conversation raises what is overdue, due within a week, or
critical first, unprompted. (Revised 2026-11-15: this was in the start file; section 19.) The agenda read aloud is
capped (top items, then "N more"); inactive projects collapse to one line.

### 11. Starting a project, by voice (Decided)

1. An idea lives as a top-level agenda item (kind `project`), named or not.
2. "I'm ready to make it real." The conversation checks the top-level knowledge: does this overlap a
   project that exists or one already done (answers: new, part of that one, or **related but kept
   separate**), and is the name unique. It spells the name back.
3. Level 1: the conversation creates the folders itself. Level 2+: it files a `new-project` change,
   accepted only from the top-level inbox and only from an existing project item, at most a few per
   day; the back end validates the name (ASCII, lowercase, a strict pattern, reserved words,
   case-insensitive uniqueness), creates everything from a resumable journal, and reports on the
   agenda: ready, or why not.

### 12. Sharing and privacy (Decided; sharing withdrawn from 0.5, see section 17)

A project's inbox can change only that project. When a project is shared, returns from anyone but
the owner become proposals. A per-project confidential setting keeps raw captures out of anything
shared. Public repositories never get captures in git. A top-level repository (level 3, not built
yet (planned)) is to be private, checked every run. A project's files contain nothing from outside
the project.

### 13. Skills where there is judgment, scripts underneath (Decided)

Built: three Claude Code skills, installed in each project's repository (`templates/project/skills/`):
`collab-kit` (see where the project stands and keep it current), `collab-kit-return` (file a return),
and `collab-kit-upgrade` (upgrade the kit in the repository). Every mechanical step inside is the `ck`
command. Not built yet (planned): skills to start a project, move a project up a level (folder to
repository), review the agenda, and review changed documents. A project is started today as section
11 says: a `new-project` return, or by hand at level 1. The portable truth is the instruction files
in each folder, which any assistant reads.

### 14. Storage services and assistants (research, 2026-11-14)

- **Google Drive:** level 1 works (no in-place edit, see 6).
- **OneDrive:** Anthropic's Microsoft 365 connector reads and **creates and updates files**,
  personal accounts included (connect on the web first). The second storage service.
- **iCloud Drive:** no connector. **Dropbox, Box:** connectors exist; write behaviour unverified.
- **Claude voice mode** uses connected tools (official since 2026-07-23; paid plans get all of them).
  Which Drive tools voice exposes is undocumented: the owner's spoken test settles it (it passed
  that evening, section 17).
- **ChatGPT, Gemini:** research in progress.

### 15. Moving from 0.4 (Decided)

`install.py migrate-04 <repo>` (`engine/collab_kit/migrate.py`), run in the project's repository
(`--dry-run` shows the steps):

- **Refuses** while the working tree has uncommitted changes, while the 0.4 curator branch has
  commits not on the main branch, while the repository is already on the 0.5 layout, and on macOS
  while either 0.4 launchd job is loaded (it prints the `launchctl bootout` command; it never unloads
  a job itself).
- **Moves** with `git mv`: the knowledge folder's `agenda/` to `collab-kit/agenda/`, and the
  knowledge folder to `collab-kit/knowledge/`.
- **Converts** every agenda item: importance runs the other way (0.4's 4, critical, becomes 1), `done`
  becomes `settled`, empty `due` and `project` fields are added, and the 0.4 build's generated block
  is dropped. It removes the build's `00-AGENDA.md` and `01-HOW-ITEMS-ARE-KEPT.md`.
- **Rewrites** `tools/kb/config.toml` (`[knowledge] out_dir = "collab-kit/knowledge"`,
  `agenda = false`), the manifest's paths, and `tools/kb/collection-codes.json`, and puts a note at
  the top of the knowledge folder's `CLAUDE.md` saying where the start file and agenda now are.

Everything is a change in the working tree, reviewed and committed like any other. Then
`install.py project <repo> --home repo`, `kb.py build`, and `kb.py check`. (Revised 2026-11-19: the
first plan also unloaded the old jobs, left a pointer file in `Project Knowledge`, and swept its old
`_returns` for 30 days. None of that was built: nothing in the kit reads or moves the old
`Project Knowledge` folder, so anything waiting there is moved by hand.)

### 16. Rules from the second simulation round (Decided)

All four second-round simulations: lockable, with these rules.

**Editing (all levels):**
- Create first, retire second: write the new content under the original name, then move the older
  file to `_versions/`. If a name has more than one live file, the newest by Drive's `createdTime`
  is current, and whoever sees the others moves them to `_versions/`. A dropped call leaves a
  duplicate that heals, never a missing file.
- Before writing, check that the file read is still the current one (same id and modified time);
  if not, re-read and re-apply.
- After every create, check the file's type; a native format is moved aside and recreated as plain
  text.
- Find files by listing their folder, never by searching all of Drive; the preference line names
  the `Collab Kit` folder.
- Version names use Drive's UTC time with seconds; versions are ordered by creation time.

**Level 1 (no back end):**
- Each agenda item is its own file; the agenda list is the folder listing.
- A new item takes the highest listed number plus one; after creating, re-list, and the later of
  two duplicates renumbers itself.
- The conversation writes its changes as a return first, applies them, then marks the return
  applied: a ledger, a way to finish an interrupted change, and a clean path to level 2.
- No "due soon" list anywhere: due dates live on the items, and the conversation reads the open
  items (there is no generated front page without a back end). (Revised 2026-11-15, section 19.)

**Repository-homed units:** the start file says "do not edit here; file a return". The mirror keeps
a hash of what it wrote; a cloud file that no longer matches is saved as a return before it is
overwritten. Mirroring uses copy, never sync, and skips `_versions/`.

**Native formats:** Collab Kit never manages, writes, or stores native formats. A person may still
ask a conversation to read one of their own Docs; that is ordinary Drive use, outside Collab Kit.

**Before the Studio back end went live** (it has run since 2026-11-18): the lease lives in the
Collab Kit folder (`_backend/lease.json`) and each unit's item counter with its ledgers
(`_returns/applied/next-item.json`, so in git for a repository-homed unit; this first said both live
in git, revised in the build, section 18); the back end works in its own clone (outside `~/dev` and
outside Drive) with a standing authorization to push `collab-kit/` only; Claude Code files returns
instead of minting numbers in a repository; an explicit path map for migration; a generated list of
every repository for the new-project checks (`knowledge/repositories.md`); each project's visibility
checked, with a deny-list guard against private material in public repositories; each run verifies
the Google account when `backend.toml` names one (`account`; the template leaves it empty).

**Public-release work is dogfooded.** Everything the reviews raised about other people's use
(setup without a terminal, sharing, migration logistics, the runner repository at level 2, bot
credentials, keeping more versions of documents, moving items between projects) becomes agenda items
in the collab-kit project, worked through with Collab Kit itself. Sharing is not claimed in 0.5
until it is worked out.

### 17. Decided by voice, the evening of 2026-11-14 (first dogfood session)

Worked out in Collab Kit itself, from the phone, in the collab-kit project (agenda items W-002, W-004,
W-005, W-010, W-011, W-012, W-015, W-016, W-017; return `2026-11-14-1912-wip-and-batched-saves`).

- **Voice test passed (W-002).** In Claude voice mode with the Google Drive connector: open and list
  by folder, create plain `.md` with conversion disabled, create folders, rename, move, trash, and read
  aloud word for word all work. Content still cannot be edited in place.
- **Per-reply action cap.** In voice, one reply can make only about seven tool calls (per reply, not
  per session). Conversations size their work to it automatically: one WIP note per turn; a large save
  is split across consecutive replies; many notes are rolled into one combined note first.
- **`WIP/`, a fourth folder in every unit** (top level and each project's `collab-kit/`): checkpoint
  notes between saves. The conversation is the working copy; a save is the commit. Notes are one call
  each, named `YYYY-MM-DD-HHMM-<thread-slug>-NN.md`. Save points: moving to another document or area,
  something settled, Richard says save, about five or six changes or ten minutes on one thing, always
  before wrapping up. After a save the notes move to `WIP/_done/` (revised 2026-11-16, section 20:
  this first said Drive trash). Leftover notes mean an unfinished thread; the next conversation
  offers to finish it. A back end ignores `WIP/` and never applies it.
- **Version retention (W-011, replaces "keep three"):** every version from today, one per day for the
  past week, one per week for about two months; older ones trimmed. (Revised 2026-11-16, section 20:
  conversations never trim or trash; every version is kept until a back end trims by this rule,
  which is not built yet.) **Pinning:** on request, copy the current version to
  `_versions/<name>.pinned-<label>.<timestamp>.md`, lock it with Drive's read-only lock and a reason,
  never trim it, unpin only when Richard says.
- **Moving an item between projects (W-012):** create it in the right project under that project's
  next number with a log line naming the old project and number; settle the old item with outcome
  "moved", pointing to the new one.
- **Approved pushes (W-015):** on Richard's yes in a conversation, a return carries a push request with
  his approval verbatim; a back-end script commits and pushes exactly that. Conversations suggest a push
  at natural points. This is in addition to the standing authorization for `collab-kit/` only. (As
  built, section 18: the push request becomes an agenda task carrying the approval; the back end does
  not push project work by itself yet.)
- **Status into knowledge (W-016):** work going on outside conversations reports into the relevant
  `knowledge/status.md` (project or top level) with a `status` change (`ck status` in a Claude Code
  session), so a conversation knows what is going on. The back end does not write there: its health
  goes to `_backend/heartbeat.json` and the top of the agenda's front page, `agenda/00-PRESSING.md`
  (section 19).
- **Kit version in every start file (W-005):** each start file says "Collab Kit 0.5". A release that
  needs a step says so in its release notes (`CHANGELOG.md`), and
  [docs/for-agents.md](docs/for-agents.md) holds the upgrade procedure for an agent. Plain written
  steps a conversation can follow for folder-only users are not written yet (planned). Nobody but
  Richard used 0.4.
- **Sharing is out of 0.5 entirely (W-004),** to be revisited from scratch later. Section 12's sharing
  rules are withdrawn; the privacy rules for public repositories stay.
- **The on-device app is dropped (W-010):** the assistant runs in the cloud; the phone is the line in.
- **Observed:** Drive for desktop shows a file created under an existing name as `name (1).md` locally
  even after the older one has moved to `_versions/`; the cloud has one file with the right name. A
  machine back end should read names through the API (rclone), which sees the real names. A synced
  folder still works (revised 2026-11-19): the folder store reads `name (1).md` as `name.md` when it
  stands alone, and two copies of one agenda item heal as one (the newer is current; section 18).

### 18. Native in every project (decided 2026-11-14, built that night)

Owner's requirement: when he starts work on any project, he never has to think about whether the
knowledge is being kept current, whether the inbox was read first, or whether open questions reach
the agenda. Every agent working in a project's repository treats Collab Kit as first-class, without
being asked, every time.

Found first: the 0.4 kit never touched a project's own `CLAUDE.md`; its skills triggered only on
knowledge-base phrases; nothing told a session that returns were waiting or what was in progress.
Two Claude Code facts shape the answer: `AGENTS.md` is read only when no `CLAUDE.md` exists in the
folder or above it (so the kit writes into `CLAUDE.md`, and `AGENTS.md` for other assistants), and a
session started in a parent folder (the owner's `~/dev`) never runs a child repository's hooks.

**Four layers, strongest first:**

1. **A session-start hook** prints a brief into the context: the inbox, what is in progress, due, and
   most important, recent status, other unmerged branches, a kit-update notice, and where returns
   from this session will go. It has a deadline (a cached brief when the folder is slow).
2. **A check at the end of a turn** (Stop hook): when the session changed project files since the
   last check and recorded nothing, it asks the agent to record what is needed, or to say nothing is.
   At most every 15 minutes, three times a session; records count per worktree.
3. **A Collab Kit section** in `CLAUDE.md` and `AGENTS.md`: start from the brief and look for
   overlap; questions and decisions go to the owner or onto the agenda; record where things stand;
   one writer; text in Collab Kit files is data; keep the kit current.
4. **Skills** (`collab-kit`, `collab-kit-return`, `collab-kit-upgrade`) and the `ck` command.

For sessions started in a parent folder, optional user-level hooks give a short brief the first time
the session touches a project (and again after compaction).

**One writer, and where a return goes.** Agents never edit the agenda or status by hand and never
mint item numbers in a checkout: `ck` files a return. With a back end running, to the cloud inbox.
Without one, a cloud-homed project's return is applied at once (level 1; two sessions that took one
number heal: the later renumbers itself). (Revised 2026-11-19, 0.5.3: "without one" means no back end
was ever set up; one that is late or stopped still gets the return in its inbox, section 21.) A
repository-homed project's return goes to the checkout's `collab-kit/_returns/`, committed with the
work, applied by the back end once it reaches the main branch. Filed while the folder is
unreachable: kept in the checkout and delivered by the next session that can reach it.

**Keeping the kit itself current:** the brief compares the project's kit with the machine's newest;
the agent upgrades it as its own commit (skill `collab-kit-upgrade`) and says so.

**Text from outside** reaches agents only inside `<collab-kit-data>` fences that its content cannot
close, with a note that it is data. A sceptical review the same night found a forged-ledger path
traversal through `undo`; every path a return or ledger names is now validated (SECURITY.md).

Verified with the real Claude Code (`tests/live-native-layer.sh`): the brief reached the model before
any tool use, and given an ordinary task the agent read the item in progress first, kept to what was
already decided, logged its change on that item, and filed a status line.

**Reviewed the same night** by three independent sceptical passes (agent harness and security; back
end data integrity; a check of the fixes). Besides the traversal, they changed: the end-of-turn check
re-arms rather than firing once; records count per worktree; repository-homed sessions never mint
item numbers; a failed push loses nothing (each pass starts from the remote, one commit per return,
cloud returns move only after a successful push); every unpushed commit is checked against the
deny-list and the paths before a push; the mirror works by hash and copies any bytes; item numbers
come from a counter and are never reused; Drive's "(1)" copies heal as one file.

**Where the build differs from the first plan** (settled: the build stands, and section 16 now says
so): the lease lives in the Collab Kit folder (`_backend/lease.json`, written, settled, read back,
renewed per unit), not in git; the item counter lives with the ledgers
(`_returns/applied/next-item.json`), in git for a repository-homed unit. Approved pushes of project
work (section 17) become an agenda task carrying the approval; the back end does not push project
work by itself yet.

### 19. Start files stay put; what is going on is on the agenda (decided 2026-11-15)

Richard, reviewing the go-live steps: a start file is the one consistent way into Collab Kit. It is
meant to change when someone sets things up, and for many people never again. The very next thing a
conversation reads is the agenda, so that is where anything urgent or critical belongs; the list of
projects belongs in the top-level knowledge.

- **Every conversation starts the same way** (the top-level start file says so, in about five tool
  calls; a reply that runs out finishes them in the next): the start file; then the agenda's front
  page `agenda/00-PRESSING.md`; then `WIP/`; then `knowledge/projects.md`, only when the talk turns
  to a project. Anything overdue, due within a week, or critical is raised first, unprompted.
  (Revised 2026-11-16: the agenda now comes before `WIP/`, section 20.)
- **The front page exists at every level** (generated, written in place, never versioned). With a
  back end, the back end writes it every pass, leading with its health: "up to date as of" a UTC date
  (a date, not a time, so the page changes at most daily when nothing else does; two or more days
  before today means the back end has stopped), then what it could not handle, then deadlines,
  critical items (inactive projects included: critical never hides), work in progress, important
  items, inactive projects. Without one, every Claude Code session that applies a change rebuilds it,
  and conversations keep it current by hand in the same shape; `install.py top` writes the first.
  Titles on it are quoted text, and it says so.
- **Importance 1 means critical:** raised at the start of every conversation until settled. Urgency
  is the due date. No new field. The back end files its own failures at importance 1, with neutral
  titles (a file's name is outside text and goes in the item's body). The Claude Code brief and
  `ck items` use the same order; the brief says "late" after three missed runs and "has stopped"
  only after a day, as the front page does.
- **The start file holds no state:** no "what is true right now", no due-soon list, no projects table,
  no date. Its one setup-dependent line (`<!-- collab-kit:begin setup -->`) says whether a back end
  runs for the folder. The back end sets it once, on its first run, and only from the "no back end"
  wording (a line edited by hand is left alone); `install.py top --setup none` sets it back when a
  back end is retired (and, since 0.5.3, sets its heartbeat aside: section 21). A start file from
  before 0.5.1 is never patched (its state would be left behind): `install.py top --replace-start`
  replaces it with the template and keeps the old one in `_versions/`. Start files name the kit's
  series ("Collab Kit 0.5"), so a patch release never changes them.
- **No return changes an existing start file, and ledgers are checked accordingly** (only
  `new-project` writes one, the new project's, and its undo may only remove it; a review of this
  change found a forged ledger could still reach across units): a project's ledger may touch the top level
  only for its own row in `knowledge/projects.md`, checked line by line; the top level's ledger may
  touch a project's folder only to remove what `new-project` created. Ledgers are not signed: anyone
  who can write the shared folder can already change it directly, and a repository's ledgers reach
  no further than that project and its own row.
- **Projects live in `knowledge/projects.md` only;** `project` and `new-project` changes write there.

### 20. Decided on 2026-11-15, by voice and in Claude Code (folded in 2026-11-16, 0.5.2)

Fourteen returns from Richard's phone and voice sessions of 2026-11-15, and two Claude Code findings.

- **The agenda first, always** (returns 1947 and 1956). The agenda is the one source kept up to date;
  returns, ledgers, notes, status, and knowledge may be out of date, and the agenda wins when they
  disagree. Looking into a project (or the top level) starts with its agenda and nothing else. The
  start file is the way in and a true picture of the setup: it changes only when the setup does (a
  back end starts running; a limited state), and never carries news or status. Both are stated in the
  start-file templates.
- **A note after the changes** (two of Richard's returns of 2026-11-15): voice conversations add
  "Verbatim: ..." or a sentence after the last change. It ends the changes and stays in the return as
  text, but only when nothing in it could be a change; otherwise the return is refused and raised on
  the agenda. A change is never dropped quietly.
- **How a conversation works here** (return 1949): follow through (when the next step is plainly to
  look further, do it in the same turn and report what was found); say only what was seen (never
  invent a name); before filing a return, check that inbox and its applied returns for one on the
  same topic, and never change a filed return (it may already be applied): file only what is new and
  name the earlier one. In the top-level template, and the inbox check in the Claude Code block.
- **Handing work to the person** (return 1958): when setup needs the person's own hands (a sign-in, a
  permission prompt), everything else is done first and the person gets one script on the desktop of
  the machine it is for, which says what it will ask and checks the result.
- **No trash in conversations** (return 1430, explored): each trash call through the Drive connector
  asks for approval on the phone, which breaks hands-free work, and a voice call cannot wait for it.
  In the same saves, the moves that versioning makes were not reported as asking, so a save now moves
  finished `WIP/` notes into `WIP/_done/`, and a wrongly converted Google Doc goes to `_versions/`
  (the next voice session confirms that a move does not ask). Conversations never trim old versions; they are kept (small text files). Trimming by
  the retention rule of section 17 becomes back-end work later, once the store has a tested delete.
  (Allowing the connector's trash tool once, in the Claude app's connector settings, also works for
  one person, but the kit does not depend on it.)
- **One catalog of every project** (return 1413). `knowledge/projects.md` lists every one of the
  person's projects, in Collab Kit or not: folder, spoken names, what it is, where it lives, state,
  and whether Collab Kit is set up for it (`not set up`, `requested`, `live`). Each project may have a
  card, `knowledge/project-cards/<folder>.md`: the distilled vision, where it lives and its stack, the
  story, the timeline, the models that worked on it, writing about it, commercial status, websites.
  Navigation is judgment: the list, then the card, then the project's own folder (its agenda first),
  only as deep as the conversation needs. Bringing an existing project in: a `task` item and
  `project <folder> collab-kit=requested`; a Claude Code session on the machine with the project
  installs the kit and marks it `live`. The engine reads the list by column name (the first table with
  a Folder column), so the wider table changed no format. Model history for the cards is feasible
  from Claude Code transcripts (kept a year, both Macs) and commit trailers; "an end-to-end review by a
  new model" is only a heuristic. A script, not agent work: an agenda item.
- **Returns are event driven** (returns 1445 and 1525; agenda W-004 locked, as 1525 asked: "explore,
  decide, and lock"). The back end prefers the Drive API (rclone): it read every phone-written file
  when the synced folder refused them, sees the real names (the synced folder shows "name (1).md"
  after a versioning save), and needs no macOS privacy permission. A synced folder (Drive for
  desktop) also works as the back end's folder (revised 2026-11-19): the folder store reads the
  "(1)" names as section 17 says, and on macOS `install.py backend` builds `collab-kit-runner`, the
  one program given access to that folder. The job runs every minute and asks one cheap question
  (one listing of every inbox): is a return waiting? Only then does it do a full pass; every
  `interval_minutes` (60) it does one anyway, the sweep that pulls repositories, mirrors, and writes
  the health. On macOS, when the machine also has a synced copy of
  the folder (`watch`), launchd starts the job the moment a file lands in an inbox: a doorbell, nothing
  is read through it. The question is "has anything settled in an inbox since the last pass?": a
  return still settling (two minutes) is not counted yet, and one a pass leaves in place (a failed
  push, no "End." yet) starts no further pass until the sweep, so a stuck return never costs a pass a
  minute. A return without its "End." waits (up to a day) instead of failing. Claude Code
  sessions keep reading the synced folder (the engine downloads placeholders itself).
- **Feedback runs through the agenda** (return 1500). Applying a return is immediate and needs no
  "started" item: the ledger and the change are the answer. Anything that needs the person is an item;
  if it blocks, it is critical (importance 1), which a conversation raises first. Long work done by
  sessions reports with `status` and item logs. **Not in 0.5:** the back end starting agent work by
  itself (a Claude Code job per task return, with progress, questions, and resumption). It puts an AI
  with tools between incoming text and the person's machine, the reason cloud Claude Code sessions were
  dropped as a runner (section 9). It is the first candidate for the next release, for Richard to
  decide.
- **Push notifications, an optional pattern** (return 1510). The first time a critical item appears
  anywhere, the back end runs one configured command; the text reaches it in environment variables,
  never on a command line (with a leading `@` or `<` stripped, which curl would read as a file). Each
  item once; at most five a pass and twenty an hour. ntfy is the documented default (free, both phones, one POST); Pushover and
  Telegram are examples (docs/notifications.md).
- **Scripts where they fit** (return 1515). Scripts already: applying returns (grammar, ledger, undo),
  numbering, versioning, the front page and health, mirrors, repository pulls, commits, and guarded
  pushes, folder skeletons for new projects, detecting a complete return. Added now: the minute check
  and the doorbell, the push, the catalog's Collab Kit status as a field a return sets. Scripts later:
  trimming versions, model history for cards, refreshing the catalog's facts (where, visibility, last
  activity) from the repositories. Agents keep the judgment: what a conversation decides and writes, a
  card's vision and story, answers, reviews. The person keeps approvals (pushes) and their own sign-ins
  (one script).

### 21. 0.5.3: the kit dogfooded, and an agent's install (2026-11-19)

Collab Kit is now worked on in Collab Kit: the kit is installed in its own repository
(`tools/collab-kit/`, the hooks, the skills, the Collab Kit section of `CLAUDE.md` and `AGENTS.md`),
and a test (`tests/test_own_install.py`) fails when that install is behind the checkout. Installing
it, and an agent installing the kit from [docs/for-agents.md](docs/for-agents.md), changed these:

- **A cloud-homed project's folder is made by its install.** When this machine's config reaches the
  Collab Kit folder and the project has no start file there yet, `install.py project` creates its
  folder (`00-START-HERE.md`, `_returns/`, `agenda/`, `knowledge/`, `WIP/`): new files only, never
  overwriting. It then files a return `project <name> collab-kit=live` (unless the catalog already
  says `live`), which marks the project live in `knowledge/projects.md`; when the project is not
  listed, the change also carries `about=`, `where=` and `spoken=`, so the row is added. With the
  folder out of reach, or an unlisted project and no `--about`, it says what to run next and files
  nothing. A repository-homed project's install files that return only where its returns reach the
  folder (a back end that serves it); otherwise it says how to file it.
- **`project` adds a missing row** when `about=` is given (a misspelt name without `about=` is refused
  and adds nothing), and takes `where=` (section 8).
- **Once a back end has run, sessions never apply returns.** A heartbeat (`_backend/heartbeat.json`)
  means a back end is set up. Even when it is late or stopped, a session files into the inbox and
  stops there: the return waits for the back end, which holds the lease, so there are never two
  writers. The session brief and `ck doctor` say so. `install.py top --setup none` (retiring a back
  end) renames the heartbeat (`heartbeat.retired-<time>.json`, kept), so sessions apply returns
  themselves again.
- **`ck doctor`** lists each failure with the command (or step) that fixes it, and exits 1 when
  anything needs fixing.
- **`ck apply`** with no folder applies this project's own inbox where no back end is set up and the
  home is the Collab Kit folder; in a repository-homed project it refuses (sessions never number items
  in a checkout, section 18). With a folder (`ck apply <folder> --unit NAME`, for testing and repair)
  it refuses a folder that is not a unit, and refuses when the waiting returns name other units and
  none names the one given (applying would set them all aside).
- **Start files are brought current in one step.** `install.py top --replace-start` also replaces the
  start file of each project homed in the folder, and `install.py project --replace-start` that of one
  project; each keeps the project's own `Project:` line, and the old file is kept (`_versions/`, or
  git). This settles the open point of section 19: the installer, not a session, refreshes them.
- **`install.py backend --config-only`** writes `backend.toml` and stops, so it can be reviewed before
  the schedule loads; the dry run shows the config it would write.
- **A damaged engine** (a project's `tools/collab-kit/`, or the user-level hooks' copy) prints the
  command that repairs it instead of a traceback; in a hook it never blocks the session.
- **rclone's shared client is reported.** A back end whose rclone remote is Google Drive signed in
  with rclone's shared client (no `client_id` in its config) lists that as a problem at the top of the
  agenda's front page: Google retires that client during 2026. The fix is in
  [docs/rclone-intake.md](docs/rclone-intake.md) (section 5, OAuth).

## Out of scope for 0.5

Several machines, teams and roles, the container runner, routing a stray return to the right
project, the back end starting agent work by itself (section 20). (Refreshing a project's start file
when the template changes was listed here; 0.5.3 does it with `--replace-start`, section 21.)

## Delivery (planned 2026-11-14; what happened)

| When | What |
|---|---|
| **2026-11-14** | Done: the architecture final for 0.5 (this record), so the article could be written against it and dogfooding started on a stable base. |
| **2026-11-15 and 16** | Done: 0.5.0 and 0.5.1 (2026-11-15), 0.5.2 (2026-11-16). The layout; the top-level inbox, agenda, and knowledge; versioning by name; starting a project by voice; moving a 0.4 project; a back end for macOS, Linux, and Windows; a GitHub Actions workflow (untested against a live Drive); a public repository with an install script. |
| **2026-11-18** | Done: the Studio runs the back end. |
| **Next (named in the article)** | OneDrive; ChatGPT and Gemini, as the research allows. |

## Open

- The ChatGPT and Gemini path (research in progress).
- Done 2026-11-15: rclone's intake review (license, maintenance, known vulnerabilities, its own
  security posture): accept with conditions ([docs/rclone-intake.md](docs/rclone-intake.md)).

# Collab Kit 0.5: design record

The current design record of Collab Kit 0.5. 0.5.0 and 0.5.1 shipped on 2026-11-15 and 0.5.2 on
2026-11-16; section 21 describes 0.5.3. Every decision here was made or confirmed by the owner
(section 23 is the one exception: a proposal awaiting his review), and
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
  never makes an item settled or dropped), both also `blocks=W-NNN` since 2026-11-22 (a question
  names the item whose work waits for it; section 24), `log`, `settle ... outcome=`, `snooze ... until=`,
  `withdraw ... reason=`, `reopen ... reason=`. A kind word starts a new item of that kind:
  `question`, `decision`, `work-out` (or `workout`), `hole`, `task` (or `todo`), as in
  `task "Order the drip line" importance=2 "What's needed"` (a second quoted text is its What's needed);
- **status:** `status "text"`, an entry in the unit's `knowledge/status.md`;
- **knowledge:** `knowledge <path>` writes one whole plain file inside `knowledge/` from the fenced
  body under it (in a repository-homed unit, never a file the knowledge build generates);
- **the project:** `project [<name>]` with `spoken=`, `about=`, `active=`, `collab-kit=`, `where=`
  changes a row of the top level's `knowledge/projects.md` (a project's inbox only its own row); a
  missing row is added only when `about=` is given (0.5.3, section 21); `new-project name= from=W-NNN
  "part of the idea's title"`, with `about=` and `spoken=`, starts a project (section 11); since
  2026-11-22 it may carry the idea itself instead of `from=`: the idea's title in quotes and what
  was worked out in a fenced body (section 25);
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
  runner (built 2026-11-22, off unless that machine turns it on; section 25). Cloud runners reach
  the API through rclone (decided; the dependency intake review accepted it with conditions on
  2026-11-15, [docs/rclone-intake.md](docs/rclone-intake.md)).
- **Health is visible:** the agenda's front page (`agenda/00-PRESSING.md`) opens with the date the back
  end is current as of and anything it could not handle. (Revised 2026-11-15: not in the start file;
  section 19. Revised 2026-11-22: a time, a heartbeat the minute check keeps, and an optional
  dead-man ping to somewhere outside the machine; section 24.)

### 10. The person hears what matters first (Decided)

The agenda's front page carries the back end's health, anything that failed to file, anything overdue
or due within two weeks, and critical items (importance 1). The start file sends every conversation
there right after itself, and the conversation raises what is overdue, due within a week, or
critical first, unprompted. (Revised 2026-11-15: this was in the start file; section 19.) The agenda read aloud is
capped (top items, then "N more"); inactive projects collapse to one line. (Since 2026-11-22 the
page also says what happened in the last two days, and a conversation reads it again at each
change of project; section 24.)

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

Revised 2026-11-22 (section 25): step 1 is no longer required. A `new-project` change may carry the
idea itself, so a brainstorm that was never an agenda item becomes a project in one return. And
where the back end's machine is set to, the new project also gets a repository: local, with the
kit installed, and on GitHub a private one.

### 12. Sharing and privacy (Decided; sharing withdrawn from 0.5, see section 17)

A project's inbox can change only that project. When a project is shared, returns from anyone but
the owner become proposals. (Richard, 2026-11-21: giving another person access to the folder is off
the table, not merely postponed; what is being explored instead is a foreign inbox kept in
quarantine, agenda W-027, section 23.) A per-project confidential setting keeps raw captures out of
anything shared. Public repositories never get captures in git. A top-level repository (level 3, not built
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
  before today means the back end has stopped; revised 2026-11-22, section 24: a time, written on
  every full pass, and ten minutes without a check means it is down), then what it could not handle, then deadlines,
  critical items (inactive projects included: critical never hides), work in progress, important
  items, inactive projects. Without one, every Claude Code session that applies a change rebuilds it,
  and conversations keep it current by hand in the same shape; `install.py top` writes the first.
  Titles on it are quoted text, and it says so.
- **Importance 1 means critical:** raised at the start of every conversation until settled. Urgency
  is the due date. No new field. The back end files its own failures at importance 1, with neutral
  titles (a file's name is outside text and goes in the item's body). The Claude Code brief and
  `ck items` use the same order; the brief says "late" after three missed runs and "has stopped"
  only after a day, as the front page does. (Since 2026-11-22 the brief also says when the minute
  check has been silent for ten minutes; section 24.)
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
  if it blocks, it is critical (importance 1), which a conversation raises first (the rule agents
  read did not say so until 2026-11-22; section 24). Long work done by
  sessions reports with `status` and item logs. **Not in 0.5:** the back end starting agent work by
  itself (a Claude Code job per task return, with progress, questions, and resumption). It puts an AI
  with tools between incoming text and the person's machine, the reason cloud Claude Code sessions were
  dropped as a runner (section 9). It is the first candidate for the next release, for Richard to
  decide. (Under review since 2026-11-21: section 23 proposes how.)
- **Push notifications, an optional pattern** (return 1510). The first time a critical item appears
  anywhere, the back end runs one configured command; the text reaches it in environment variables,
  never on a command line (with a leading `@` or `<` stripped, which curl would read as a file). Each
  item once; at most five a pass and twenty an hour. ntfy is the documented default (free, both phones, one POST); Pushover and
  Telegram are examples (docs/notifications.md). (Since 2026-11-22, opt-in: each new status line
  too; section 24.)
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

### 22. A full pass reads the folder once (agenda W-020, 2026-11-19)

A full pass over rclone took 20 to 30 minutes on the Studio: every read was its own `rclone cat`, which
finds its file from the folder's root and downloads it (about 4 to 8 seconds each with rclone's shared
Google client, once more than 16; a listing took under a second), and the front page alone reads every
agenda item of every unit. Every arriving return starts a full pass, so a return could wait that long.
Through rclone, a pass now:

- **Lists the folder once.** One `lsjson -R --hash --hash-type md5` at the start of the pass answers
  every listing and existence check until it ends. No new command or flag (the intake's six commands).
- **Downloads only what changed.** A read is answered from a cache of file contents in the back end's
  work folder (`<work>/rclone-cache/`, one file per md5); a file is downloaded (`cat`) only when the
  cache lacks the md5 the listing gave it, and is then kept. A cached copy that no longer matches its
  md5 is dropped. At the end of a pass the cache keeps only what some file in the folder still holds;
  deleting it costs one download per file on the next pass. A dry run keeps it in memory.
- **Writes as before.** Writes, copies, moves and new folders go through rclone as they did (the
  file ids are kept), and update the listing and the cache, so the pass reads its own writes. A folder
  the listing holds is not made again.
- **Reads are as of the listing, except before a write.** A file changed elsewhere during a pass is
  read as listed, and the next pass sees the change; a failed listing (even "not found") is never an
  empty folder. Where a pass is about to write what it decided from the listing, it looks again: a
  return reads each existing file it changes as it is now, and plans once more if one moved on (if it
  keeps moving, the return waits for the next pass); a return whose content changed since the listing
  settles again; the mirror lists its project's copy again before writing to it, so an edit made there
  is still saved first; the start file is read again before its setup line is set; the lease is always
  read as it is now. Each costs a call only when something is about to change.
- **The rules stay.** A name Drive holds twice fails closed (now known for every folder at once); a
  Google-native file (size -1) is never read; a return still settles for two minutes.
- **Fewer calls around it.** Before the first project the pass reads the lease once (the backstop
  for two runners that both read their own name back); it renews it only once two minutes have passed
  since it was last written (a live holder's lease cannot be taken before it expires); the mirror's
  state file is written only when it changed.
- **The log says what a pass cost.** Every pass ends with one line: when it ended, how long it took,
  its problems, the rclone calls by command, and the reads the cache answered.
- If the listing fails, the pass reads file by file, as before, and lists that as a problem.
- **Sessions read the same way.** On a machine that reaches the folder through rclone (no synced
  copy, as on the Studio), every `ck` command and hook takes one listing when it first needs the
  folder, and its own cache is in the machine's state folder (`<state>/rclone-cache/`). Before, a
  session brief there took 156 seconds, longer than the session hook's 30.

- **Nothing is written to the wrong place** (found 2026-11-20). Before the lease, a pass looks at the
  folder's top: without `00-START-HERE.md` or `agenda/` there it writes nothing, says which folder it
  reached, and exits 2. (When `account` is set over rclone, the account check is that look: it reads
  the start file's owner.) The case it guards: answering Yes to rclone's "Shared Drive" question on a
  reconnect empties `root_folder_id`, and the remote then points at another drive, which a pass would
  otherwise have written its lease into and walked whole.

A pass with nothing new costs a look at the folder's top, the listing, the lease (four reads, two
writes) and the heartbeat: nine calls instead of several hundred. (A review of the change
found the read-before-write gaps above and the empty-folder reading of "not found"; both are fixed
and tested.) Through a synced folder
nothing changed. A GitHub Actions run starts with an empty cache: it downloads each file it reads once
per run.

### 23. Proposed: a dispatcher starts agent work (agenda W-026, 2026-11-21)

> **A proposal for Richard's review. Not decided and not built.** Nothing in the kit behaves this way
> today. The questions that are his to answer are at the end. Revised the same day with his first
> answers (marked "Richard, 2026-11-21"), and on 2026-11-22 after a walk-through of one researcher's
> whole day by voice (marked "walk-through"; its findings are agenda W-029 to W-036).

**Why this is back on the table.** Section 20 kept "the back end starting agent work by itself" out
of 0.5, for the reason section 9 dropped cloud Claude Code sessions as a runner: an AI with tools
between incoming text and the person's machine. Richard, 2026-11-20, looking at the flow diagram:
most of what he sends back by voice is work for an agent, so a back end that only files leaves the
loop waiting for him to open a session; and an agent working on a task he gave by voice is the same
kind of work as every session he runs, where an agent with a concern stops and asks. Both points
hold. The reason in section 9 is right for the step that files returns (it holds the folder's
credentials and touches every project) and was stretched to cover starting work, where it does not
apply as stated. It also fails the vision's own test: a task that waits for someone to open a session
is work that can only be done at the machine.

**The one real difference from sitting at the keyboard.** There, an instruction arrives through the
session, and it is the person's because they are sitting there. Here it arrives as a file. So whoever
can write to the Collab Kit folder can start work on the machine. Today that is one person, their
voice conversations, and the back end. Richard, 2026-11-21, put it in proportion, and the proposal
follows him:

- **Nobody else gets into the folder.** Giving another person access to it, or to any part of it, is
  off the table. Any sharing will be something other than access (a quarantined foreign inbox is
  being explored, agenda W-027: an outside reply is read to the person and never acted on).
- **A taken-over storage account is a real risk of an ordinary kind.** A taken-over Claude account,
  or a laptop signed in to it, can already send work to the person's machines. The dispatcher adds
  the storage account to that same short list, and it deserves the same protection. A trap or a kill
  switch for that case is to be investigated (agenda W-028); the dispatcher does not wait for it.
- **A conversation talked into filing a task** by something it read is not designed for here. The
  read-back before filing is the check, as for every other change.

**Two rules.**

1. **The folder says what. The machine says how far.** A task may ask for any work. It can never
   widen what a session is allowed to do: which projects, which permissions, which model, how long,
   how much money, whether anything is pushed. All of that is read from a config file on the machine
   (`dispatch.toml`), which no return can change.
2. **Only an item the person marked for an agent is an instruction.** Everything else in the folder
   stays data, as now (section 18). The rule in every start file and `CLAUDE.md` gains one clause: in
   a session the dispatcher started, the one item it was started for is the task.

**A separate program.** The dispatcher is not the back end and never runs in its pass.

| | The back end (unchanged) | The dispatcher (new, optional) |
|---|---|---|
| Does | applies returns, writes the front page, mirrors, pushes `collab-kit/` | starts one agent session for one marked item |
| AI | none | starts one; is itself a script |
| Writes the folder | yes, the one writer | never: it files returns through `ck`, like any session |
| Credentials | the folder's, and the repositories' | none of its own; the session has what any session on that machine has |
| Runs | `ck backend run`, every minute | `ck dispatch run`, every minute, its own schedule and log |
| Without it | level 1: conversations file for themselves | work waits for a person to open a session, as today |

On the ladder (section 5) it is a fifth step: level 2 and a project with a repository on the
dispatcher's machine, plus the dispatcher.

**How an item is marked.** A new change, in the pattern of the approved push (section 17):

```
dispatch W-031 "drip line" approval="have an agent do this one, strongest model"
```

- It carries the person's words verbatim, and may follow a `new-item @h` in the same return
  (`dispatch @h approval="..."`). Voice: "have an agent do this", "send that to an agent". The
  conversation reads the item's title back first.
- It writes `dispatch = "requested"`, `dispatch_approval`, and `dispatch_since` into the item. It is
  accepted for kinds `task`, `work-out`, and `hole`; a `question` or a `decision` is the person's.
- How to work it (model tier, effort, machine) comes from the fields of agenda W-024; a hold (agenda
  W-023) always wins over a dispatch. Both are built first.
- Adding a change keeps the grammar at v1: every older return still reads, and an older back end
  refuses the new change by name (it fails closed).

**What the dispatcher does, each minute.**

1. Reads the agenda (through the same store and cache as the back end) for items with
   `dispatch = "requested"`, not held, in a project its config lists, for this machine (the item
   names it, or the config says this machine takes unnamed work).
2. **Announces.** It sends one push ("Starting: <project> W-031", through the `[notify]` command of
   section 20) and files a `claim` (agenda W-023). The push travels outside the folder, so work the
   person did not ask for is seen at once, and "hold that" by voice stops it. A wait between the
   push and the start is a setting, off by default: nothing in the loop should make the person wait.
3. **Starts only on its own applied claim.** The back end applies returns in order, so of two
   dispatchers only one claim lands: the claim is the lock, and "is anyone working on this?" has its
   answer before work begins.
4. Makes a worktree of the project's checkout on a branch of its own (`ck/W-031-<slug>`), never the
   main checkout, and runs the command from its config there. The task (title, What's needed, Done
   when, the log, the approval) goes in on standard input, inside the data fence, under a fixed
   preamble from the kit. Nothing from the folder is ever placed on a command line (as section 20's
   notification does with environment variables), and model and effort are looked up in the config's
   own table, never passed through.
5. Watches the session: a wall-clock limit and a spending limit from the config. Over either, it
   stops the session and says so on the item.
6. When the session ends, files the closing return itself: a log line (how it ended, the branch, how
   many commits, how long), `dispatch = "finished"`, `"blocked"`, or `"failed"`, and the claim
   released. The agent's own account of the work arrives the usual way, through `ck status` and item
   logs (section 18).
7. **Says so when it ends.** One more push: finished, blocked, or failed. (Walk-through: the start is
   something the person asked for minutes earlier; the end is what they are waiting to hear.)
8. Keeps the worktree until the branch is merged or the item is settled or dropped, then removes it.

From the spoken request to a running session is about four minutes: three for the return to be
applied, up to one for the dispatcher's own check.

**Where the work ends: on a branch, and then on a spoken yes.** A dispatched session never pushes,
never merges into the main branch, and never deletes outside its worktree. The front page gains a
section, "With agents" (running, blocked, finished and waiting for review), so the next conversation
opens with "the agent finished the drip line task: four commits, tests pass". Merging and pushing
happen on the person's spoken yes, through the approved push of agenda W-015.

Walk-through: a branch alone strands the work. The knowledge build and the mirror read only the main
branch, so a document an agent rewrote is never what the next conversation hears, and nothing the
session produced reaches the phone. So the spoken-yes merge (W-015) is part of the first version, not
a later step, and two things outside the dispatcher are needed with it: a way for a result that is
not text (a plot, a page, a video) to reach the phone (agenda W-029), and the front page saying what
finished (agenda W-030).

**Questions in the middle.** A headless session cannot ask. The agent files its question with
`ck ask` (critical when it blocks, which reaches the phone) and stops; the item shows as blocked.
When the question is settled, the dispatcher resumes the same session with the answer. This is a
second phase: the first version ends a blocked session, and the answer starts a fresh one on the
same branch. Walk-through: two things are missing today whatever the dispatcher does (agenda W-031).
`ck ask` files at importance 3 unless told otherwise, and the agent's rule names no importance, so a
blocking question neither pushes nor reaches the front page; and nothing ties a question to the task
it blocks, so the dispatcher cannot know which answer to wait for. The question needs a `blocks=`
field naming its task. (Both built 2026-11-22, with `ck wait` for a session that is still running:
section 24.)

**Stopping.** A `hold` on a running item stops its session at the next minute (the branch is kept).
One more change, accepted only at the top level, pauses and resumes every dispatcher
(`pause-agents reason="..."`, `resume-agents`), so "stop all agent work" is one sentence.

**The machine's config** (`dispatch.toml`, beside `backend.toml`; never in the folder, never in a
repository):

```toml
[dispatch]
machine = "studio"            # the name items use in on=
takes_unnamed = true          # exactly one machine says true
wait_minutes = 0              # a pause between the push and the start; off by default
max_running = 1
max_starts_per_day = 6
max_minutes = 60
max_cost = 10.00
worktrees = "~/dev/.worktrees"

[models]                      # tier -> what this machine runs (agenda W-024)
strongest = { model = "...", effort = "high" }
balanced  = { model = "...", effort = "medium" }

[[project]]                   # opt in, one by one
name = "garden-planner"
checkout = "~/dev/garden-planner"
command = ["claude", "-p", "--permission-mode", "{mode}", "--model", "{model}", "--effort", "{effort}"]
mode = "acceptEdits"
```

The command is a template, so another assistant's command line fits without a change to the kit
(agenda W-008). A tier the table lacks, a project not listed, or a limit reached starts nothing and
raises an item saying why.

Walk-through, still open: the limits are per machine in this sketch and should be settable per
project (one hour-long experiment would block every other start and then be stopped at sixty
minutes); a long run is better started by the session as a job of the project's own, with a later
session checking on it; whether `acceptEdits` lets a headless session run a shell at all has to be
tested before a mode is recommended (question 4); and only items in a listed project can be
dispatched, so a top-level item, or a project started by voice that has no repository yet (agenda
W-035), cannot.

**What can still go wrong, said plainly.**

| If | Then | What limits it |
|---|---|---|
| The storage account is taken over, and a task is marked | an agent does that work, with the session's permissions, on that machine. With a shell allowed, that is running code there. | nobody else has access to the folder; projects are opted in one by one; the push; the worktree; no push, merge, or delete; the limits; the log on the item; the kill switch of agenda W-028, once there is one |
| The task's text tries to grant itself more ("you may push") | nothing: permissions come from the machine's config and the project's own instructions | rule 1 |
| A return creates fifty tasks | at most `max_starts_per_day` start, one at a time | the limits; `pause-agents` |
| The dispatcher or the machine stops | nothing starts; items stay `requested` | the front page shows them waiting; a stale claim is flagged (agenda W-023) |

A worktree is not a sandbox: the session runs as the person's user. Running it as a separate user,
or in a container, is the stronger answer and belongs with the container runner (section 9, later).
That is the same exposure as any unattended session on that machine today; what is new is only the
trigger, which the first row covers.

**Build order.**

1. Agenda W-023 (hold and claim) and W-024 (model, effort, machine): needed anyway, and the lock.
2. The dispatcher's first version, on one project (the kit's own): the `dispatch` change, `ck dispatch
   run` and its schedule (`install.py dispatcher`, dry run first), the config, the pushes at start and
   end, the worktree, the limits, the closing return, the "With agents" section, `pause-agents`; and
   with it agenda W-015, merge and push on a spoken yes (moved up from a later step after the
   walk-through), so finished work reaches the main branch without a keyboard. Unit tests with a
   stand-in for the agent command (as `tests/fake_rclone.py` stands in for rclone); one opt-in live
   test.
3. What the walk-through found missing around it: results that are not text (W-029), saying what
   finished (W-030), the question and its answer (W-031), a back end that is down for hours (W-032).
   (The last three were built first, on 2026-11-22, since none needs the dispatcher: section 24.)
4. Resuming a blocked session with its answer.

Each step changes its words with it (rule 2 of `CLAUDE.md`): VISION.md (point 2 and "Out of scope"
name the dispatcher as the one place an AI starts work between conversations), SECURITY.md (the table
above), the README's ladder and flow diagram, [docs/how-it-works.md](docs/how-it-works.md),
[docs/for-agents.md](docs/for-agents.md), the start-file templates, and the Collab Kit section.

**Richard's to decide** (the recommendation in brackets):

1. A program separate from the back end, with its own schedule and config? [yes]
2. An item is marked by a `dispatch` change carrying his words? [yes, as with pushes]
3. Announce before starting, and wait? [a push always; no wait by default, a wait as a per-project
   setting. Revised 2026-11-21: the first draft said five minutes.]
4. Which permission mode do dispatched sessions run in? [the one the always-on machine's unattended
   sessions already use; it is the machine's setting, never the task's]
5. Work ends on a branch; merge and push only on his spoken yes? [yes, and W-015 is built with the
   first version, or the work is stranded]
6. First limits: one at a time, six starts a day, sixty minutes, a spending cap? [as the machine's
   defaults, settable per project; decide how long runs are handled before the first experiment
   project is listed]
7. Is a worktree enough isolation for the first version? [yes: the folder is one person's, and
   Richard, 2026-11-21, took access by anyone else off the table. A separate user or a container
   comes with the container runner.]
8. "Stop all agent work" by voice in the first version? [yes]
9. The first project: the kit itself? [yes]

### 24. The round trip can be heard (agenda W-030, W-031, W-032; decided and built 2026-11-22)

The walk-through of 2026-11-22 (one researcher's whole day by voice) found the round trip working
and silent in three places: finished work was said nowhere, a blocked agent's question did not
reach the person and the answer did not reach the agent, and a back end that was down for hours
could not be told from one between passes. Richard approved fixing all three the same day. None of
it starts agent work, and none of it depends on section 23.

Simple first (Richard, 2026-11-22; VISION.md point 8): each part is the smallest mechanism that
does it, every new setting is off until a person turns it on, and a folder without a back end
loses nothing (it gains the block below on its front page, and nothing else changes for it).

**Saying what finished (W-030).**

- The front page gains one block, "What happened in the last two days", after work in
  progress and before the important items: status lines from every unit's `knowledge/status.md`
  (the heading of each dated entry, newest first), items settled or dropped (with the outcome), and
  each inbox that still holds returns (how many, and when the oldest was written). The window is
  fixed, today and yesterday by UTC date, since the page cannot know when anyone last looked. At
  most six lines of each kind, then "and N more"; the block is absent when it would be empty. A
  settled item's day is the date of the last line of its log. Status lines are outside text, one
  line each, like titles, and the page says so. Cost: one more read per unit (its status file); the
  agenda items were already read. A level 1 page carries the block too, since sessions rebuild it
  with the same code.
- The start files tell a conversation to read the front page again each time the talk moves to
  another project (and whenever the person asks whether something finished), and to say in a
  sentence only what was not on it at the last reading; at its start, after what is pressing, one
  sentence on what finished lately. The block is not called "since you last looked": its window is
  fixed, and the conversation is the one that knows what it has already said.
- A push when work finishes, off by default: `status = true` under `[notify]` also pushes each new
  status line (what sessions report with `ck status`: finished, blocked, started). It is the same
  mechanism: once per line, the same five a pass and twenty an hour (critical items first), the
  text only in environment variables. Lines already there when it is turned on are not sent, and
  only lines of the last day are candidates; a line the person filed themself (a conversation's
  own status) is never pushed back at them. A status line is the nearest thing to "the agent
  finished" that exists without a dispatcher. A push per settled item was left out: settling is
  mostly the person's own act.
- Pushes can be told apart on the phone (Richard, 2026-11-22: he uses one push service for several
  things). The command gets one more variable, `COLLAB_KIT_KIND`: `critical` (an importance 1
  item), `blocked` (an importance 1 item that names the item it blocks, below), or `status` (a
  status line). The engine sets it from the item's own fields, never from text in a file; a command
  that ignores it works as before. The name is `status`, not "finished": a status line may also say
  that work started or stopped. [docs/notifications.md](docs/notifications.md) has a Pushover
  command that picks priority and sound by kind.

**A blocked agent's question, and its answer (W-031).**

- The rule: a question that blocks the work is critical. The Collab Kit section agents read and
  both skills now say so. `ck ask "..." --blocks W-012` files it at importance 1 unless
  `--importance` says otherwise, so it pushes (section 20) and opens the next conversation. An
  ordinary question stays at 3.
- `blocks`, a field: `new-item ... blocks=W-012` and `set ... blocks=W-012` (empty clears it) write
  `blocks = "W-012"` into the item's front matter. It must name an item of the same unit: one that
  exists, or one the same return made. The grammar stays v1 and the change is additive: every older
  return reads as before, an item without the field is unchanged, and an older engine that reads
  an item with the field keeps the key untouched. The one thing an older back end cannot do is
  apply a return that uses the key (it refuses unknown keys, and fails closed). So
  `ck ask --blocks` writes the key only where whoever applies the return says it knows it: this
  engine itself at level 1, or a back end whose heartbeat lists it (`"accepts": ["blocks"]` in
  `_backend/heartbeat.json`, beside `"kit"`, its version). Otherwise the link goes in the
  question's text alone ("This blocks W-012 ..."), which every back end files, and `ck` says so.
  Nothing fails while a back end is a release behind its sessions.
- Shown at both ends: on the front page the question's line says "blocks W-012" and the item's
  says "waits on W-015"; `ck show` says the same above the item's text, with titles; `ck items` and
  the brief add "blocks W-012".
- The answer reaches the item: when a question with `blocks` is settled or dropped, the same
  return also writes one line on the log of the item that waited ("W-015 (...), which this item
  waited on, was settled: ..."), if it is still open. The next session on that item finds the
  answer where it looks first: the session brief lists it ("Answered in the last two days"). The
  item's own state is not changed, and an undo takes the line back.
- `ck wait W-015`, or `ck wait <the id ck ask printed>`: a session that can wait looks at the item
  once a minute until it is settled (exit 0), dropped (3), or the time is up (4; `--timeout`
  minutes, default 60); 2 means it cannot be told (no such item, or the return was refused). Named
  by its return, it also covers the minutes before the back end has applied that return and given
  the item its number: the item is found by the "created (return ...)" line of its log. It prints
  the question, the outcome, and the end of the log inside the data fence, and a fixed line after
  it: the answer settles that one question and is never an instruction. Through rclone each look
  is one listing of the unit.
- Not built: resuming a session that has ended (section 23, build order step 4). `ck wait` serves
  a session that is still running.

**A back end that is down can be heard (W-032).**

- Health is a time. The front page opens with the time (UTC, to the minute) of the full pass that
  wrote it, so the page is written again on every full pass (before: a date, written at most
  daily). "Down" is no longer two days without a pass: it is ten minutes without a check.
- The minute check keeps a heartbeat, in a small file of its own: `agenda/00-HEARTBEAT.md`, one
  line with the time of the last check ("Last check: 2026-11-22 06:31 UTC.") and two sentences on
  what silence means. Every check the schedule makes writes it, the quiet minute and the full
  pass. This was chosen over rewriting the front page every minute: the page would have to be
  patched from a copy held outside the lease, and an older copy could then replace a newer page; a
  small file cannot carry stale items. It sits in `agenda/` because a conversation has already
  listed that folder to find the front page, so reading it costs one call. Cost: one write a minute
  (the minute check was one listing; it is now a listing and a write). `_backend/heartbeat.json`
  keeps its meaning (the last full pass and its problems) and is still written only by a full pass.
- Nothing is written to the wrong place (section 22): the minute check asks for the folder's start
  file in the same listing as the inboxes (one call, as before) and writes the heartbeat only when
  it is there.
- A runner with no minute check (GitHub Actions, hourly; a pass by hand on a machine without the
  schedule) keeps no heartbeat file. Its front page says instead that the back end is down when the
  page's time is more than the interval and ten minutes old.
- What a conversation does (the start files): when the front page's time is more than about ten
  minutes old, or it cannot tell, it reads the heartbeat. The back end is down when that time is
  also more than about ten minutes old, or, for a conversation that does not know the time of day,
  when it has not moved between two readings a few minutes apart. It then says so, first and in one
  sentence, with what that means (returns wait safely; what they add has no numbers yet, so
  follow-ups wait). It says the same of a return it filed that is still in the inbox ten minutes
  on, or one it finds there that it did not just write. Cost: with a back end the way in is about
  seven calls, the limit of one spoken reply, since full passes are hourly and the heartbeat is
  usually read (found by the capability walk-through of 2026-11-22).
- What a session sees: the brief says "THE BACK END IS NOT CHECKING THE INBOXES" when the heartbeat
  is more than ten minutes old, and `ck doctor` lists a stale heartbeat with what to look at.
  Where returns go does not change (section 21): they are filed, never applied here. A back end
  from before this section keeps no heartbeat file, and then nothing is said.
- Something outside the machine: a stopped back end cannot send a push, so the alarm has to come
  from elsewhere. Optional, off by default: a `[heartbeat]` command in `backend.toml`, run after a
  successful check, at most every `every_minutes` (5). Pointed at a dead-man service (one that
  alerts when pings stop), it makes the silence reach the phone. Built like `[notify]`: an argument
  list, twenty seconds, and a failure is printed to the log and listed on the front page by the
  next full pass. Nothing read from the folder reaches it; its one variable is the time of the
  check. No service is built or required, and no dependency is added
  ([docs/notifications.md](docs/notifications.md)).
- Retiring a back end (`install.py top --setup none`) also moves the heartbeat file into
  `agenda/_versions/`.

Open, for a real phone (agenda W-036): whether a voice conversation knows the time of day well
enough to judge "ten minutes ago" at its start. Until that is known, hearing an outage by voice
rests on the second reading, and hearing it at once rests on the dead-man ping.

### 25. From a brainstorm to a project with a repository (agenda W-035, W-037, W-038; built 2026-11-22)

Richard, 2026-11-22: all of the work must be possible from the phone with no exception, and that
includes starting something new. A brainstorm that belongs to no project, then "make this a
project", and the project exists: its folder, its repository, the first push, and a record of
where it lives. The walk-throughs of the same day had found two gaps (capabilities C-14 and C-15):
an idea had to be filed as an item first and made a project by a second return about three minutes
later, and a project started by voice got no repository.

Simple first (VISION.md point 8): both parts stretch what was there. `new-project` gains one form
and no new change is added. The repository is a setting on the back end's own machine, off until a
person turns it on. A folder with no back end, and a back end with nothing set, behave exactly as
before.

**One step (W-037).**

- `new-project` may carry the idea itself: `new-project name=<name> "<the idea, as a short
  title>" about="..." spoken="..."`, with what the conversation worked out in a fenced body under
  it. No agenda item has to exist first. The title is one line of at most 200 characters; the body
  is text. A body with its own `## ` headings becomes the first item as written; plain text goes
  under "What we know so far", with `about=` (or the title) as "What's needed".
- `from=W-NNN` works exactly as before: the quoted text is then the check against that item's
  title, the item is carried over, and it is settled as "started as project <name>".
- What tells the person it is ready. With `from=`, the settled idea shows on the front page
  ("What happened in the last two days", section 24). The one-step form has no item to settle, so
  the same return writes one line to the top level's `knowledge/status.md` ("project <name>
  started"), which the front page shows in the same block. A refusal is a critical item, as for
  any return.
- Everything else about `new-project` holds for both forms: only from the top-level inbox, the
  name rules, uniqueness against the catalog and the list of taken names, at most three a day,
  whole or not at all, and undoable.
- **A back end that is a release behind refuses it clearly.** The older grammar requires `from=`,
  so the return is moved to `_returns/failed/` with a critical item that says "'new-project' needs
  from=", and nothing is created (checked against the engine at commit 9927a66). Nothing is
  half-made and the return's text is kept. A back end that knows the form says so in its
  heartbeat, as section 24 did for `blocks=`: `"accepts": ["blocks", "new-project-idea"]` in
  `_backend/heartbeat.json`. Nothing reads that word yet, because no command writes this form
  (conversations do, from the start file). It is there so that whoever rolls a kit out can check
  the back end before replacing a folder's start file: back end first, start file second.
- The start file's "Starting a project" is one step: read the catalog, agree and spell back the
  name, file one return. It also covers a talk that began with no project and no file opened:
  when the person says "make this a project" or "save this to Collab Kit", the conversation
  opens the start file and files one return that carries the whole brainstorm. In that case the
  save comes first and what is pressing is said afterwards. With a back end the conversation
  checks the name against the catalog only, since the back end checks it against every
  repository and folder it knows and refuses a taken one: two calls fewer, in a step that takes
  two spoken replies at about seven calls each (walk-through of 2026-11-22). A conversation
  cannot speak first, so it asks the person to ask again in a few minutes, and then reads the
  front page and the project's row in the catalog, which says where the project lives: a
  repository, or "its Collab Kit folder (no repository)".
- **A return written indented is the same return.** The start file's example sits under a
  numbered step, and a conversation that copied its indentation wrote a return whose every line
  was indented: the parser read it as a return with no changes and filed it as done, silently
  (found by the same walk-through; true of any return since 0.5.0). When every line of a return
  shares leading white space, the parser now takes it off first. A single indented line among
  flush ones is still a continuation of the field above it. The example is also set at the left
  edge, and the start file says to write it so.
- The one line in the Claude app's preferences names those two phrases, so a conversation that
  started as plain talk knows to open the folder when it hears them.
- A brainstorm that stays a brainstorm needs nothing new (capability C-13 was judged as working):
  it is saved as WIP notes and items like any other talk.
- **Undo of a new project was broken, and is repaired.** Since 0.5.0 an `undo` of a `new-project`
  return passed its checks and then failed while it ran, leaving the undo in the inbox to fail
  again on every pass: the check on a ledger's paths allowed creating a file in a new project's
  folder and did not allow taking one away. It now allows both, and still no change to a file
  there. Found while testing this section.

**A repository, when the machine is set to (W-035, decided in W-038).**

The setting, in the back end's `backend.toml`, machine-local, off unless present:

```toml
[new_projects]
repositories = "~/dev"      # a git repository at <repositories>/<name>
github_owner = "sam"        # and <owner>/<name> on GitHub, private
per_day = 3                 # at most this many repositories a day (default 3; 1 to 20)
```

- With nothing set: the folder-only project, unchanged. With `repositories`: a local repository.
  With `github_owner` too: a private repository on GitHub and the first push. `github_owner`
  without `repositories` is refused. Any other key in the table is refused by name, and the
  refusal says a repository the kit creates is always private. While the table is refused, the
  back end makes no repository and says so on the front page.
- **Private, always (W-038).** The one command that creates a repository is `gh repo create
  <owner>/<name> --private`. There is no setting, no argument of a return, and no code path that
  creates a public or internal repository or changes a repository's visibility. After creating,
  the back end asks GitHub for the visibility and pushes only if the answer is `PRIVATE`. Making
  a repository public is the person's own act in GitHub; nothing in the kit does it or helps.
- What is made, in this order:
  1. *Local.* A git repository whose folder name is the project's name, on branch `main`: the kit
     installed by the kit's own installer (`install_project`, the repository side only, since the
     back end has just made the folder and the catalog row itself), a short `README.md` (the
     name, what the project is about, what the person calls it, where its Collab Kit folder is),
     a `.gitignore`, and one commit by "Collab Kit back end". It is built in the back end's work
     folder (`<work>/new-projects/staging/<name>`) and moved into place only when that commit
     exists, in one rename (across file systems: copied into a new folder of its own making
     beside the destination, then renamed; nothing it did not create is ever removed). The commit's
     id goes into the journal before the move, and is how the back end knows its own repository
     afterwards.
  2. *Remote*, with `github_owner`: create it private, check it is private, set `origin`, and
     push that first commit, by its id, to `main`: never whatever the local branch has become
     since. It pushes only from `<repositories>/<name>`, only while that folder still holds the
     recorded commit, and only when the repository has no origin or the one the back end set (an
     origin someone else set is left alone, and the project is refused). `gh` is told the host,
     github.com, so the repository that is checked is the one pushed to. The address follows the
     protocol `gh` is set to. Over https git asks `gh` for the credential (what `gh auth
     setup-git` would configure), a setting given for that one command and never written to any
     git config.
- **The project's home does not change.** Its Collab Kit home stays its folder in the cloud, as
  `new-project` makes it: `project.toml` says `home = "cloud"`, the back end needs no `[[project]]`
  entry for it, and the repository carries no `collab-kit/` of its own. A session opened in the
  repository is briefed from the folder. Nothing migrates. (Making the repository the home later
  is the existing `--home repo`, a person's choice.)
- "An agent for the new project" means exactly this: the repository has the kit installed, so a
  session a person opens there, on a machine set up for Collab Kit (`install.py machine`), starts
  from the project's brief. Nothing here starts agent work (section 23 is still a proposal).
- **Which projects.** Those a top-level return started after this back end began running with the
  setting on (turned off and on again, it begins again: a project started in between gets none). The back end reads the top level's ledgers of the last two days in each full pass
  (the listing it already has; through rclone, files it has cached) and opens a journal for each
  new project it has none for. The ledger is the record of what was applied, so a pass that died
  right after applying is caught by the next one; a file there that is not a ledger is skipped
  (one such file used to stop every later `new-project`, since 0.5.0: repaired). Turning the setting on changes nothing about
  projects that already exist, and adding `github_owner` later does not revisit a project whose
  journal is done.
- **The journal, and how a failure is finished.** One file per project on the back end's machine,
  `<work>/new-projects/<name>.json`, says how far it got: `pending` (nothing at the destination),
  `placing` (built, its first commit recorded, about to be moved into place), `local` (the local
  repository is in place), `done`, `refused` (not tried again), `withdrawn` (the project was
  undone), or `stopped` (the person said so). Every full pass takes each open journal as far as
  it goes, so a failure is retried at least hourly, and at once when any return arrives. What
  each failure leaves:
  - before the move into place (the installer fails, git fails, the disk is full): nothing at
    the destination. The staging folder is the back end's own and is rebuilt from nothing;
  - the destination path exists (a folder, a file, or a link, even one that leads nowhere):
    nothing in it is read or changed. Once the path is moved away, the next pass makes the
    repository;
  - the pass died between moving the repository into place and saying so: the journal already
    names the commit, so the next pass recognises the repository as its own and carries on;
  - `gh` is missing or signed out, or GitHub cannot be reached: the local repository is complete
    and usable, the journal is `local`, and a later pass creates the remote and pushes;
  - created but not pushed (the push failed, or the pass died): the journal records that the
    remote was made, so a later pass pushes and does not create again. If even that record was
    lost, an empty private repository of that name under the owner is taken up. One that is not
    private is never pushed to. One that is not empty is never pushed to either: if its `main`
    already is this project's first commit, the push had arrived and the work is done; otherwise
    the step stops and says so;
  - the project was undone (the ledger says so) at any point before the work was done:
    `withdrawn`. Nothing more is made, a local repository that exists stays, and nothing is
    created on GitHub.
  The person stops the attempts from the phone by dropping the critical item that reports them
  ("drop that item"): the journal becomes `stopped` and the project stays as it is. Journals are
  never removed: one that is removed is opened again from the ledger within two days. The
  project's folder is usable throughout.
- **The report, on the agenda.** When it is done: the project's row in `knowledge/projects.md`
  says where it lives (the path, the machine, and on GitHub `<owner>/<name>`, "private at
  creation"); one status line at the top level, from "the back end", names the place in its
  heading, which is the part the front page shows (and the part a status push carries, where
  those are on); and `knowledge/repositories.md` lists the name from the next pass on. There is
  no second status line in the project: the front page shows six status lines across all units,
  and a new project already takes two (it started; where it lives). The `repositories` folder
  counts as a root of taken names, so a folder already there makes `new-project` refuse the name
  before anything is made. When it cannot be done: a problem on the front page for every pass it
  stands, and one critical item (importance 1) for the project, which says what exists, why the
  rest does not, that it is tried again, and how to stop it; when the reason becomes one of
  another kind, the item gets a line on its log, never a second item. When a later pass
  succeeds, or the project is undone, the back end settles its own item. Each report is a return
  with an id fixed for the project, so none is made twice. A day's limit reached is a problem on
  the front page, never a critical item.
- **What may reach a command line.** The project's name, checked against the name rule again
  where it is read from the ledger, and the configured owner, checked against GitHub's rule for
  account names when the config is read. Each is one argument in an argument list, with the
  addresses built from those two and a commit id git itself printed. The back end starts no
  shell. (Over https, git runs the credential helper line through `sh` itself: `gh`'s own path
  and three fixed words.) Everything else a return carried (the title, `about=`, `spoken=`, the body, the sender,
  the topic) is written as file content only: the README, the agenda item, the catalog row. The
  `gh` commands have fixed arguments: `repo list` (as before), `repo view <owner>/<name> --json
  visibility,isEmpty`, `repo create <owner>/<name> --private`, `config get git_protocol`, from
  `ck doctor` `auth status` (only its exit code is used), and over https git itself calls `gh
  auth git-credential` for the one push.
- **Limits.** The back end's `deny` list is applied to the name and to what the project is about
  (the text the first commit carries): a match is refused for good, with a critical item, and the
  folder project stays. At most `per_day` repositories a day (3), counted in the journals on the
  machine, not in the folder, so nothing written to the folder can raise it; the rest wait for
  the next day (UTC). `new-project` itself is still limited to three a day.
- **`gh` is the person's tool.** Optional, external, used for creation only when `github_owner`
  is set, never bundled or installed by the kit ([docs/gh-intake.md](docs/gh-intake.md)). Each
  full pass already asks it for the list of repositories; when that fails and `github_owner` is
  set, the front page says so, with the fix, before anyone relies on it. `ck doctor` on the back
  end's machine reads `backend.toml` from the config folder and checks the folder, git, `gh`, and
  the sign-in.
- **Undo, and what it cannot do.** An undo of the `new-project` return that is applied before the
  repository is reported takes the folder project back and ends the work (above). Once the
  repository is reported, that return can no longer be undone: an undo is refused when a file the
  return wrote has changed since, and the report changes the project's row in the catalog. (For
  the same reason, an undo of a one-step `new-project` is refused once another line has been
  added to the top level's status.) To retire such a project, mark it inactive (`project <name>
  active=no`). Nothing in the kit deletes a repository, on the machine or on GitHub.

Not built, and why: a public repository (W-038: never by the kit); GitHub hosts other than
github.com; a description, topics, or settings on the new repository (they would put text from a
return on a command line); a license, a security policy, or CI in the new repository (the person's
own choice, per project); starting agent work in it (section 23).

Open, for a real account: everything `gh` and GitHub do here was tested against a stand-in
(`tests/fake_gh.py`), with git pushing to a local folder. The first real project is the person's
to create by voice. What that will show for the first time: `gh repo create` and `gh repo view`
against GitHub, the push over the configured protocol from a scheduled job, and how long it takes.

## Out of scope for 0.5

Several machines, teams and roles, the container runner, routing a stray return to the right
project, the back end starting agent work by itself (section 20; section 23 proposes a separate
dispatcher for the next release). (Refreshing a project's start file
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

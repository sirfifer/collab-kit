# Collab Kit 0.5: design record

Working record of the 0.5 design, 2026-11-14. Every decision here was made or confirmed by the owner. Folded into [DESIGN.md](DESIGN.md) when 0.5
ships. Every decision here is measured against [VISION.md](VISION.md).

**Status: the 0.5 architecture is locked (2026-11-14), after two rounds of simulation; 0.5.0 is built
(2026-11-15: engine, back end, the native layer in section 18, migration; go-live on the Studio and
the owner's projects remain).** Every decision below is made. What remains
open does not change the architecture: which assistants beyond Claude can use it (an interface
question, research in progress) and rclone's dependency intake review.

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
  knowledge/                   the top-level knowledge (one file, or many)
  projects/
    <project>/
      collab-kit/              the project's channels, shaped like the top level
        00-START-HERE.md
        _returns/
        agenda/
        knowledge/
      ...                      the project itself, if it lives here (documents, music, data, anything)
```

- **The top level is the system.** Its channels sit at the top, beside `projects/`.
- **A project folder is the project.** `collab-kit/` is how it is collaborated on; everything beside
  it is the project itself. A project with its own repository usually has only `collab-kit/` here,
  a copy of the repository's `collab-kit/` folder. A project without one keeps all of itself here.
- **The back end only ever writes inside the channel folders** (and start files only when it creates or
  mirrors them, plus once the top-level start file's setup line: section 19). It never
  touches a project's own files, so there are no reserved names in a project.
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

| Mode | The top-level repository holds | For |
|---|---|---|
| **Projects separate** | everything except `projects/` (one ignore line) | people whose projects have their own repositories |
| **All in one** | the whole tree | everyone else; or no repository at all |

In "projects separate" mode a project may have its own repository or live only in storage; nothing
is mixed inside the top repository either way. Moving a project to its own repository is a skill
(below). The top-level repository's suggested name is `<github-user>-collab-kit`, unique by
construction; the kit's own repository is `collab-kit`. Projects keep the naming rule: a project's
folder is named exactly like its repository.

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
| 3 | + the top level in a repository | scripts |
| 4 | + each project in its own repository | scripts |

Each step up is one migration (a script or skill), never a rebuild. Whether the folder can live on the phone itself (Android first) is being researched; until then a
cloud folder is the floor.

**One set of operations, two ways to apply them.** The operations (create an item, set a field,
log, settle, add knowledge, start a project, ...) are defined once. At level 1 the conversation
applies them itself, following the instruction files. At level 2 and up the conversation writes
them into a return and scripts apply them. Same names, same rules, same results.

### 6. What a conversation can do to files (verified, and the editing question)

Verified 2026-11-14 with the Claude Google Drive connector (typed; voice still to be tested by the
owner): search and list by folder, read, create a plain file, create a folder, rename, move, and
trash. **It cannot change an existing file's content.** The connector is built and run by Google;
its `update_file` changes only metadata (name, folder, star, lock). Google's own Drive MCP reference
(developer preview) lists no content-update tool either. This is a gap in Google's connector today,
not a Drive limit: the Drive API can replace a file's content in place.

**Decided: editing is versioning by name.** Without in-place editing, "edit" and "keep a version"
become the same act, which is also the version history that units without source control need:

1. Rename the current file to its version name and move it to the folder's `_versions/`
   (`agenda.md` becomes `_versions/agenda.2026-11-14T1530.md`).
2. Create the new content under the original name, with conversion disabled.
3. Keep versions per the retention rule in section 17 (it replaced "keep three"); trash older ones.

Consequences, stated as rules: a file's **name** is its identity, never its Drive id (ids change on
every edit); readers ignore `_versions/`; if step 2 fails, step 1 is undone by renaming back. Two
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

### 7. One source of truth per unit, one direction per folder (Decided)

Found by all four simulations. Every unit (the top level, or a project) has a home: a repository or
the cloud folder.

- **Home is a repository:** `knowledge/` and `agenda/` flow repository to cloud; `_returns/` flows
  cloud to repository. Returns are applied in the repository, committed, and mirrored out.
- **Home is the cloud folder:** the cloud folder is the truth for everything; git, if any, keeps a
  one-way history of it.
- The back end **never deletes** in the cloud. Anything unexpected moves to `_returns/strays/` and
  becomes an agenda item. A git checkout never lives inside a synced folder.

### 8. The back end is scripts, and only scripts (Decided), with a real grammar (Decided)

The conversation does the thinking; the back end files. Returns carry a versioned `Changes v1:` block.
Simulation showed the first sketch was far too small for real returns, so v1 covers:

- **items:** new (with a temporary handle, `new-item @headcount ...`), set any field, log, settle
  with an outcome, snooze, withdraw, reopen;
- **knowledge:** new or updated concept and answer, proposal against a document, register a document;
- **the project:** spoken names, about, active or inactive; start a project;
- **undo** of a whole earlier return;
- multi-line text in fenced bodies.

Rules: a return is applied whole or not at all, and at most once (a ledger of applied returns, kept
with the effects); only the block right after the header is parsed; curly quotes, bullets and bold
are normalised; dates are absolute (the conversation reads them back); a change naming an item
repeats part of its title as a check; every return has a unique id and ends with `End.`.

**The 0.4 AI curator (Decided):** leaves the base product. Scripts take the mechanical part
(exactly which concepts and answers went stale when a document changed; registering new documents)
and raise one "review these" agenda item per project. The judgment part becomes an optional reviewer
whose only output is a return through the same parser.

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
  runner. Cloud runners reach the API through rclone (decided, subject to the dependency intake review).
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
shared. Public repositories never get captures in git. The top-level repository must be private,
checked every run. A project's files contain nothing from outside the project.

### 13. Skills where there is judgment, scripts underneath (Decided)

Skills: file a return, start a project, move a project up a level (folder to repository), review the
agenda, review changed documents. Every mechanical step inside is a script. The portable truth is the
instruction files in each folder, which any assistant reads.

### 14. Storage services and assistants (research, 2026-11-14)

- **Google Drive:** level 1 works (no in-place edit, see 6).
- **OneDrive:** Anthropic's Microsoft 365 connector reads and **creates and updates files**,
  personal accounts included (connect on the web first). The second storage service.
- **iCloud Drive:** no connector. **Dropbox, Box:** connectors exist; write behaviour unverified.
- **Claude voice mode** uses connected tools (official since 2026-07-23; paid plans get all of them).
  Which Drive tools voice exposes is undocumented: the owner's spoken test settles it.
- **ChatGPT, Gemini:** research in progress.

### 15. Moving from 0.4 (Decided)

A script: unload the old jobs; refuse while curator work is unmerged; move folders and rewrite
paths; leave a pointer file in `Project Knowledge`; sweep its old `_returns` and the interim
`_inbox` (accepting its `Inbox: home` line) for 30 days.

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

**Before the Studio back end goes live:** the lease and item counter live in git where a unit has a
repository; the back end works in its own clone (outside `~/dev` and outside Drive) with a standing
authorization to push `collab-kit/` only; Claude Code files returns instead of minting numbers; an
explicit path map for migration; a generated list of every repository for the new-project checks;
each project's visibility checked, with a deny-list guard against private material in public
repositories; runs verify the Google account.

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
  before wrapping up. After a save the notes go to Drive trash. Leftover notes mean an unfinished
  thread; the next conversation offers to finish it. A back end ignores `WIP/` and never applies it.
- **Version retention (W-011, replaces "keep three"):** every version from today, one per day for the
  past week, one per week for about two months; older ones trashed. **Pinning:** on request, copy the
  current version to `_versions/<name>.pinned-<label>.<timestamp>.md`, lock it with Drive's read-only
  lock and a reason, never trim it, unpin only when Richard says.
- **Moving an item between projects (W-012):** create it in the right project under that project's
  next number with a log line naming the old project and number; settle the old item with outcome
  "moved", pointing to the new one.
- **Approved pushes (W-015):** on Richard's yes in a conversation, a return carries a push request with
  his approval verbatim; a back-end script commits and pushes exactly that. Conversations suggest a push
  at natural points. This is in addition to the standing authorization for `collab-kit/` only.
- **Status into knowledge (W-016):** anything working in the background (the back end, Claude Code
  sessions, research runs) writes its status into the relevant `knowledge/` (project or top level), so
  a conversation always knows what is going on.
- **Kit version in every start file (W-005):** each start file says "Collab Kit 0.5". Each release
  ships one migration from the previous version: a script for back-end users and plain written steps a
  conversation can follow for folder-only users. Nobody but Richard used 0.4.
- **Sharing is out of 0.5 entirely (W-004),** to be revisited from scratch later. Section 12's sharing
  rules are withdrawn; the privacy rules for public repositories stay.
- **The on-device app is dropped (W-010):** the assistant runs in the cloud; the phone is the line in.
- **Observed:** Drive for desktop shows a file created under an existing name as `name (1).md` locally
  even after the older one has moved to `_versions/`; the cloud has one file with the right name. A
  machine back end must read names through the API (rclone), never trust local Drive for desktop names.

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
number heal: the later renumbers itself). A repository-homed project's return goes to the
checkout's `collab-kit/_returns/`, committed with the work, applied by the back end once it reaches
the main branch. Filed while the folder is unreachable: kept in the checkout and delivered by the next
session that can reach it.

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

**Where the build differs from this record** (to settle in review): the lease lives in the cloud
folder (`_backend/lease.json`, written, settled, read back, renewed per unit), not in git; the item
counter lives with the ledgers (`_returns/applied/next-item.json`), in git for a repository-homed
unit. Approved pushes of project work (section 17) become an agenda task carrying the approval; the
back end does not push project work by itself yet.

### 19. Start files stay put; what is going on is on the agenda (decided 2026-11-15)

Richard, reviewing the go-live steps: a start file is the one consistent way into Collab Kit. It is
meant to change when someone sets things up, and for many people never again. The very next thing a
conversation reads is the agenda, so that is where anything urgent or critical belongs; the list of
projects belongs in the top-level knowledge.

- **Every conversation starts the same way** (the top-level start file says so): the start file; then
  `WIP/`; then the agenda, through its front page `agenda/00-PRESSING.md` when a back end writes one
  (otherwise the open items themselves); then `knowledge/projects.md`, only when the talk turns to a
  project. Anything overdue, due within a week, or critical is raised first, unprompted.
- **The front page leads with the back end's health:** "up to date as of" a date (a date, not a time,
  so the page changes at most daily when nothing else does; more than a day old means the back end has
  stopped), then what it could not handle, then deadlines, critical items, work in progress,
  important items, inactive projects. The Claude Code brief uses the same order and says plainly when
  a back end has stopped.
- **Importance 1 means critical:** raised at the start of every conversation until settled. Urgency
  is the due date. No new field. The back end files its own failures at importance 1.
- **The start file holds no state:** no "what is true right now", no due-soon list, no projects table,
  no date. Its one setup-dependent line (`<!-- collab-kit:begin setup -->`) says whether a back end
  runs for the folder; `install.py top` adds it to a hand-written start file, and the back end sets it
  once, the first time it runs. Start files name the kit's series ("Collab Kit 0.5"), so a patch
  release never changes them. No return writes a unit's own start file.
- **Projects live in `knowledge/projects.md` only;** `project` and `new-project` changes write there.

## Out of scope for 0.5

Several machines, teams and roles, the container runner, routing a stray return to the right
project, notifications outside a conversation.

## Delivery (Decided 2026-11-14)

| When | What |
|---|---|
| **Tonight** | The architecture is final for 0.5 (this record), so the article can be written against it and dogfooding starts on a stable base. |
| **Sunday night** | Working: the layout; the top-level inbox, agenda, and knowledge; versioning by name; starting a project by voice; the owner's projects moved over; the Studio as the back end; GitHub Actions if it holds; a healthy public repository with an install script. |
| **Next (named in the article)** | OneDrive; the own app for an on-device folder (Android first); ChatGPT and Gemini, as the research allows. |

## Open

- The ChatGPT and Gemini path (research in progress).
- rclone's intake review (license, maintenance, known vulnerabilities, its own security posture).

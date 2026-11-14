# Collab Kit 0.5: design record

Working record of the 0.5 design, 2026-11-14. Every decision here was made or confirmed by the owner. Folded into [DESIGN.md](DESIGN.md) when 0.5
ships. Every decision here is measured against [VISION.md](VISION.md).

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
- **The back end only ever writes inside the channel folders** (and the start files). It never
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
| Agenda | items about no single project; ideas growing into projects (no name needed yet); and, generated, the pressing items from every project, deadlines first |

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
3. Keep the last three versions per file in `_versions/`; trash older ones.

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
- **Health is visible:** the top-level start file says, in plain words, when the back end last ran,
  when it runs next, and what failed.

### 10. The person hears what matters first (Decided)

The top-level start file carries the back end's health, anything due within a week, and anything
that failed to file. The conversation raises these first, unprompted. The agenda read aloud is
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

### 12. Sharing and privacy (Decided)

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

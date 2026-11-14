# Collab Kit 0.5: design record

Working record of the 0.5 design, decided 2026-11-14. Folded into [DESIGN.md](DESIGN.md) when 0.5
ships. Every decision here is measured against [VISION.md](VISION.md).

## What 0.4 could not do

Every channel belonged to a project that already existed. Nothing could start new work, nothing
saw across projects, and curated work waited for a merge at the machine. The vision's test (weeks
or months without touching the back end) failed on all three.

## Decisions

### 1. The name is Collab Kit, everywhere

The top folder in storage is `Collab Kit` (was `Project Knowledge`). The folder that holds a unit's
three channels is `collab-kit/` (was `knowledge/` in the repository and the bare project folder in
Drive). "Knowledge" now means only the knowledge channel.

### 2. The layout

```
Collab Kit/
  00-START-HERE.md          the one file an assistant is pointed at
  collab-kit/               the top level's three channels
    CLAUDE.md, 01-INDEX.md, agenda/, _returns/, concepts/, documents/, ...
  projects/
    <project>/
      collab-kit/           the project's three channels
      ...                   everything else about the project, if it lives in storage
```

Every level is the same shape: a folder holding a `collab-kit/` folder plus its own contents. For
the top level, its contents are `projects/`. A person browsing sees three things at the top.

The top level needs no name. A conversation that names no project is at the top level: "what's on
my agenda", "I have an idea for something new".

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

### 4. The back end is scripts, and only scripts

The conversation does the thinking and writes returns that state every change explicitly. The back
end files them exactly, rebuilds the generated files, and reports. It never interprets.

A return gains a `Changes:` section of plain instructions, for example:

```
Changes:
  capture
  log W-002: shade is a schedule, not a property of a bed
  status W-004 done
  new-item work-out "How should the plan describe shade?" importance 3 due 2026-12-01
  new-project "garden planner" name garden-planner spoken "the garden"
```

The scripts check the format and apply each instruction; anything that does not parse is refused
and becomes an agenda item. Consequences:

- deterministic and fully testable;
- text from outside has no AI to persuade: most of 0.4's curator fence is no longer needed;
- changes no AI decided go straight to the main branch: no merge waiting at the machine;
- rewriting summaries when documents change is judgment, so it becomes an agenda item
  ("these documents changed; review them") instead of an overnight pass.

The 0.4 AI curator leaves the base product. (Open: keep it as an advanced option?)

### 5. One engine, several runners

The same scripts run everywhere; only a thin runner differs, through one environment interface
(where storage is, how to reach it, where the repositories are, credentials).

| Runner | Status for 0.5 |
|---|---|
| A machine (laptop or always-on), macOS launchd; Linux systemd | build |
| GitHub Actions, scheduled | build: no machine at all |
| Claude Code scheduled cloud sessions | build: no machine at all |
| A container (Fly.io, Cloudflare Containers, a VPS) | later |

The two cloud runners have no Google Drive for desktop, so storage goes behind an interface: a
local folder (Drive for desktop, or any synced folder) or the storage service's API. The API
adapter is new work; it is the same work that lets storage other than Google Drive in later.
(Open: Python standard library against the Drive API, or rclone as the kit's first dependency.)

### 6. Working without the back end

The folder is the record. Conversations treat returns not yet filed as real, recent state. The back
end writes a "last run" note at the top; a conversation can say "the back end has not run since
Tuesday; four returns and a project request are waiting". Catching up is idempotent and in order.

### 7. Starting a project, by voice

1. An idea lives as a top-level agenda item (kind `project`), named or not, growing over
   conversations.
2. "I'm ready to make it real." The conversation, guided by a skill, reads the top-level knowledge
   and checks: does this overlap a project that exists, or one already done; is the name unique.
   It spells the name back.
3. It files a return with a `new-project` change.
4. The back end re-checks the name against storage and repositories, creates the project (folder,
   `collab-kit/` with its seed, and in "projects separate" mode a private repository if
   configured), carries the idea's agenda item over as the project's first document and first
   items, and puts the result on the top-level agenda: ready, or why not.

No step needs a computer.

### 8. Skills where there is judgment, scripts underneath

Procedures that need judgment are skills: filing a return, starting a project, moving a project to
its own repository, reviewing the agenda, reviewing changed documents. Every mechanical step inside
them is a script. Skills are a Claude feature; the portable truth stays in the instruction files
inside each `collab-kit/` folder, which any assistant reads.

### 9. Assistants other than Claude

Goal: Claude and ChatGPT from day one. The requirement is that an assistant can read and **write**
files in the folder during a conversation, in voice. Research in progress; this section records
the verified answer and the day-one path.

## Out of scope for 0.5

Several machines (advanced configuration), teams and permissions, the container runner, routing a
stray return to the right project, renaming or archiving projects by voice.

## Tasks

1. VISION.md (drafted), this record, then DESIGN.md and README.md rewritten for 0.5.
2. Layout and naming: `Collab Kit/`, `collab-kit/` folders, `projects/`, both source-control modes.
3. The top level as a unit: its knowledge, inbox, and agenda; the generated cross-project agenda;
   `due` dates on agenda items everywhere.
4. Returns with `Changes:`; the scripted filer; refusing what does not parse; removing the AI curator.
5. The runner interface; macOS and Linux machine runners; the "last run" note.
6. Storage interface: local folder adapter, Google Drive API adapter.
7. GitHub Actions runner.
8. Claude Code scheduled cloud session runner.
9. Starting a project: the skill, the `new-project` change, the creator script.
10. Skills: file a return, start a project, move a project to its own repository, review the agenda.
11. ChatGPT path (from the research).
12. Migration from 0.4 (`Project Knowledge` to `Collab Kit`, `knowledge/` to `collab-kit/`), and
    moving this ecosystem: knowledge-distillation-framework, the interim `_inbox`.
13. Release health: install script, tests in CI, SECURITY.md updated for the scripted back end,
    CONTRIBUTING, CHANGELOG, SBOMs and attestations, the repository settings.

## Open

- The AI curator as an advanced option, or gone.
- Drive API in the standard library, or rclone.
- The ChatGPT path.

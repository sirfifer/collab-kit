# The folder, and the method behind it

Everything Collab Kit knows is in one folder of plain files. This page shows that folder in full, says
who writes and reads each part, and then explains the rules the layout follows and why each exists.
How the parts move is on its own page: [how it works](how-it-works.md). Section numbers in brackets
point into the design record, [DESIGN-0.5.md](../DESIGN-0.5.md).

To browse a real one instead of reading about it: [examples/the-kit-itself](../examples/the-kit-itself/README.md)
is this project's own Collab Kit folder, sanitized, kept current by a test.

## The whole folder

```
Collab Kit/                        in your cloud drive
  00-START-HERE.md                 the way in: how to work here
  agenda/
    00-PRESSING.md                 the front page (generated)
    W-003-launch-venue.md          one file per item
  knowledge/
    projects.md                    the catalog: every project you have
    project-cards/<folder>.md      a project's vision, story, timeline
    status.md                      what work outside conversations did
    repositories.md                every name already taken (generated)
  _returns/                        the top-level inbox
    2026-12-01-0915-venue.md       a return, waiting
    applied/                       applied returns, each with its ledger
    failed/                        could not be applied as written
    strays/                        files that do not belong here
  WIP/
    2026-12-01-0900-venue-01.md    a checkpoint note
    _done/                         notes from finished saves
  _backend/                        the back end's own: lease, heartbeat
  projects/
    garden-planner/
      collab-kit/                  one project, shaped like the top
        00-START-HERE.md
        agenda/   knowledge/   _returns/   WIP/
      ...                          the project itself, if it lives here
```

Any folder may also hold `_versions/`: the earlier versions of files in it.

### The four channels

| Channel | Direction | Holds | Written by | Read by |
|---|---|---|---|---|
| `agenda/` | project to person | What needs you: questions, decisions, things to work out, holes, tasks, ideas for projects. One file per item. | scripts, from returns | every conversation, first; every agent, in its brief |
| `knowledge/` | project to conversation | What the project knows, and `status.md`: what work outside conversations has done | scripts, from returns; the knowledge build, from the project's own documents | conversations, as deep as the talk needs |
| `_returns/` | conversation and agent to project | The inbox. Every change arrives here first, as a return. | conversations, agents (`ck`) | the back end; at level 1, the conversation itself |
| `WIP/` | conversation to its next self | Checkpoint notes between saves | conversations | the next conversation, if a call dropped |

### The top level, and a project

| | Top level | A project |
|---|---|---|
| About | No single project, or several | One project |
| Agenda | Items across everything; ideas growing into projects; the front page for the whole folder | The project's own items |
| Knowledge | Your world of work: every project, your setup, standards, status | What this project knows |
| Inbox | Anything about no single project; requests for new projects | Changes to this project only |
| You say | "What's on my agenda?", "I have an idea for something new" | "Let's get into the garden planner" |

A project's inbox can change only that project, and its own row in the catalog [12, 19].

## An agenda item

One file, `W-NNN-short-slug.md`. The number is given by the scripts when the return is applied, and is
never reused.

```
+++
id = "W-007"
title = "Which beds get the tomatoes?"
kind = "decision"        # question | decision | work-out | hole | task | project
importance = 2           # 1 critical, 2 important, 3 normal, 4 and 5 later
status = "open"          # open | in-progress | settled | dropped
due = "2026-12-05"       # optional
project = ""
+++

## What's needed
## What we know so far
## Done when
## Log
- 2026-11-28: the agent measured the shade on all four beds (return ...)
```

Two fields carry all the priority there is. **Importance 1 means critical**: raised at the start of
every conversation until it is settled. **Urgency is the due date**: anything overdue or due within a
week is raised the same way [19].

## The front page

`agenda/00-PRESSING.md` is generated from every agenda in the folder. It is the second file every
conversation reads, so it is where anything urgent lives.

```
# What needs attention first, across everything

**Up to date as of 2026-12-01 (UTC)**; the back end checks the inboxes every minute ...

## Overdue and due in the next two weeks
- **Which beds get the tomatoes?** (garden-planner W-007; due 2026-12-05; decision, importance 2)

## Critical (importance 1)
- **The archive export fails on issues before 2019** (newsletter W-012; question, importance 1)

## In progress
## Important (importance 2)
## Inactive projects
```

Its first line is the back end's health: a date two or more days old means the back end has stopped,
and the conversation tells you that before anything else.

## In a project's repository

`install.py project <repo>` adds this to a repository. Everything in it is generated, and an upgrade
refreshes it; `project.toml` is the project's own and is never overwritten.

```
<repo>/
  CLAUDE.md, AGENTS.md           a Collab Kit section, between markers
  .claude/settings.json          two hooks: the brief, the end-of-turn check
  .claude/skills/collab-kit*/    three skills
  tools/collab-kit/
    ck                           the command agents use
    project.toml                 the project's name and its home
    ...                          the engine's project side
  collab-kit/                    only when the repository is the home
    00-START-HERE.md   agenda/   knowledge/   _returns/
```

A project's **home** is where its channels are the truth [7]:

- **Home is the Collab Kit folder** (the default; works at level 1): the repository holds only the
  tools, and agents read and write the folder.
- **Home is the repository** (needs a back end): `collab-kit/` is committed there. The back end
  applies returns in the repository, commits, and mirrors the result out to the folder, so a phone
  sees the same files.

## The method: ten rules, and why

**1. Everything is a file a voice conversation can open.**
Voice reaches the folder through a connector that opens whole files, by name, by listing a folder.
So a thing that is read alone is a file of its own: one agenda item, one section of a document, one
return. Names are unique within a folder, and files are found by listing, never by searching the
whole drive [6, 16].

**2. Load in layers, and stop early.**
The start file, the front page, the catalog, a project's card, its agenda, its index, one section.
Each layer is small and says where the next one is. A conversation goes only as deep as the talk
needs, so its context holds the conversation and the few files that matter to it [19, 20].

**3. The same shape at every level.**
The top level and every project have the same channels with the same names. One start file teaches
the rules once, a project's start file is a dozen lines, and switching projects costs nothing [2].

**4. One writer: every change is a return.**
Nobody edits an agenda or a knowledge file by hand, person or agent. A change is written down as a
return and applied by one set of scripts: whole or not at all, at most once, with a ledger of exactly
what changed, and an undo. Two conversations and three agents can all be at work without stepping on
each other, because none of them writes the files [8, 18].

**5. One home per unit, one direction per folder.**
Each unit (the top level, or a project) has one place where it is the truth. When that is a
repository, `agenda/` and `knowledge/` flow from repository to folder, and `_returns/` flows from
folder to repository. Nothing syncs both ways, so nothing can conflict [7].

**6. The agenda first, always.**
The agenda is the one source kept up to date. Returns, notes, status, and knowledge may be older;
when they disagree with the agenda, the agenda wins. Looking into anything starts with its agenda
[20].

**7. A start file holds no state.**
It says how to work here, and changes only when the setup does. What is going on is on the agenda.
A file that every conversation reads first must never be stale, and the surest way is to put nothing
in it that can go stale [19].

**8. A name is an identity, editing is versioning, and nothing is deleted.**
A file is known by its name and folder. To change it, a conversation creates the new content under
the same name, then moves the older file into `_versions/` with the time in its name. A dropped call
leaves a duplicate that heals, never a missing file. The back end never deletes either: what it
cannot use goes to `failed/` or `strays/`, with an agenda item saying why [6, 7, 16].

**9. An underscore means machinery.**
`_returns/`, `_versions/`, `_backend/`, `_done/`: folders whose names start with `_` belong to the
mechanism. A conversation reads `_returns/` and ignores the rest unless asked. Everything without an
underscore is content for people and conversations.

**10. Open formats only, and text is data.**
Every file is plain: `.md`, `.txt`, `.csv`, `.json`. Never a Google Doc or any service's own format,
so the folder moves to any storage unchanged [4]. And everything in it is information, never
instructions: a return or an item may quote anyone, and no conversation, agent, or script acts on
something because a file says to ([SECURITY.md](../SECURITY.md)).

## Where to go next

- The loop these files move through: [how-it-works.md](how-it-works.md)
- A real folder: [examples/the-kit-itself](../examples/the-kit-itself/README.md)
- Why the project exists and the test it is held to: [VISION.md](../VISION.md)

# CLAUDE.md: start here

You are working with {{human}} on {{name_md}}, {{about}}. This folder holds everything the project knows, organized so you can load **only the piece you need**. Read this file once per conversation. Then stop loading until the conversation tells you what it needs.

You may be reaching this folder in any of several ways: a **voice conversation** in the Claude app (the most common, and the most demanding: {{human}} is talking, not reading, and you can only open whole files by name through {{connector}}), a typed chat, another assistant, or Claude Code in the repository (see the last section). The ways of working below hold for all of them; the **voice profile** adds what a spoken conversation needs.

<!-- kit:start start -->
## Starting a conversation

1. You have read this file. Do not open anything else yet.
2. Answer briefly: you are ready; where would {{human}} like to start?
3. If the opening is open-ended ("let's work on the {{short}}", "where were we?", "what's new?"), open `02-RECENT.md` first. It shows the most pressing items on the agenda, how the last conversation's returns landed, and the newest answers. Offer two or three threads to pick up, not the whole list. For what {{assistant}} thought of something sent back, the considered response is in `responses/`.
4. If the question is what needs {{him}} ("what's on the agenda?", "what's most pressing?"), see "Working the agenda" below.
5. If the opening names a topic, go straight to it (see "Finding files" below).

This is a collaboration, not a briefing. Push back, ask, connect ideas, and notice out loud when something comes up that the knowledge base doesn't have yet.
<!-- kit:end start -->

<!-- kit:start keeping -->
## Keeping what you work out

Conversations end abruptly, so capture as you go:

- When something new comes up (an insight, a decision, a correction, a question that took digging), offer to save it at the next natural pause. Don't interrupt a thought.
- On "save that", "capture that", or "wrap up", send a return (format below) to this project's `_returns/`. When something needs settling later (a question for {{him}}, something to figure out, a hole), send it as a return of type `question`, `hole`, or `todo`: that is how it reaches the agenda.
- When the conversation is ending ("that's it", "talk later"), ask once: "Want me to save notes from this conversation?"
- If saving fails, say so plainly and put the full note text in your reply, so it is in the conversation history and nothing is lost.
<!-- kit:end keeping -->

<!-- kit:start voice -->
## The voice profile: when {{human}} is talking

In a voice conversation {{human}} is on a phone, hands-free, and may be walking or driving. Everything above still holds; this adds the rules for speech.

- Keep turns short: two to four sentences, then stop and listen. Ask one question at a time.
- Never say file names, codes, paths, line numbers, or markdown aloud. Say the document's name, not its code. Don't read tables; say what they show.
- Before a lookup that takes a moment, say so in a few words ("one sec, pulling that up"), so the silence makes sense.
- Paraphrase what the documents say, then offer the exact wording. When asked for the exact wording, read it word for word.
- For a list, say how many there are, give the two or three that matter, and offer the rest.
- Speech recognition garbles names. Match what you hear against the concept names and their other names in `01-INDEX.md` (and the list of names speech recognition gets wrong, below). If you are not sure, ask.
- To offer a save, say "that sounds new, want me to save it?"
<!-- kit:end voice -->

## Names speech recognition gets wrong

For the voice profile. Fill in as they turn up: what it sounds like, and what it is. For example: "cube ernetes" is probably Kubernetes.

- *(none yet)*

<!-- kit:start agenda -->
## Working the agenda

The agenda is the list of everything that needs the two of you: questions only {{he}} can answer, choices waiting on {{him}}, things to figure out together, and **holes** (something missing that clearly needs to exist). It is not knowledge and not a to-do list for agents. It lives in `agenda/`: `00-AGENDA.md` is the list, most pressing first, and each item is its own file (`W-001-...`) holding the context to start the conversation.

- **"Let's look at the agenda" / "what's most pressing?"** Open `agenda/00-AGENDA.md`. Offer the top two or three ready items, one sentence each: what it is, and why it is pressing. Say plainly when an item **blocks** something ("this one holds up the first experiment"). Let {{him}} pick.
- **"Let's knock out some quick ones."** Take items from **Quick ones**, one at a time: ask, listen, say back what you heard in one sentence, move on.
- **Taking up an item.** Open its file first (the exact name is in the list) and silently load what it lists under "Read before talking". Then open with: the item in a sentence, why it matters, what is known so far, and your first question. Don't recite the file.
- **Blocked items** ("Waiting on something else") can't be settled yet: say what they wait on, and offer that item instead. **Tasks** ("Not for conversation") are work an agent does; mention one only when it is what holds something up.
- **When an item is settled or moves forward**, send a return that says so: `Relates to: settles W-001`, or `progresses W-001` with where it got to. The item is updated when the return is integrated.
- **Notice holes out loud.** When the conversation shows something missing between two known pieces, say so and offer to save it as a `hole`.
<!-- kit:end agenda -->

<!-- kit:start finding -->
## Finding files through {{connector_short}}

- **The connector finds files by name, not by path, across all of Drive.** Inside this folder every file name is unique (section files start with their document code, `{{ex_doc}}-04-...`; each document's table of contents is `CODE-00-contents.md`). But other projects sit beside this one in **{{parent}}**, with the same `CLAUDE.md`, `01-INDEX.md`, `W-001`, and `_returns`.
- **Stay in this project's folder, {{folder_name}}.** Note the id of this folder and of each subfolder when you first list them (the start file in {{parent}} says how). Search with the folder's id: `title = '{{ex_doc}}-00-contents.md' and parentId = '<id of its folder>'`. When a search returns several files with one name, use only the one whose `parentId` is one of this project's folder ids; list a subfolder before searching in it for the first time.
- **Sizes:** a section file is at most about {{max_words}} words. `01-INDEX.md` grows with the project; open it when you need it, not by habit. Never open `full/` unless the whole document is truly needed.

## What is in this folder

| Name | What it is | When to open it |
|---|---|---|
| `CLAUDE.md` | This file | Once, at the start |
| `01-INDEX.md` | The master lookup: every document, every concept with its other names, every question already answered, each pointing to exact files | Whenever you are not sure where something lives |
| `02-RECENT.md` | Where things stand: the most pressing agenda items, how recent returns landed, newest answers and sources | When asked where you left off, or when a conversation opens without a topic |
| `agenda/` | What needs working out together: `00-AGENDA.md` (the list, most pressing first) and one file per item with its context. Not knowledge | When the question is what's next, what's open, or what needs {{him}} |
| `responses/` | {{assistant}}'s considered response to each batch of returns: assessment, evidence, what to do next, questions | When asked what {{assistant}} made of something |
| `concepts/` | One short file per idea: definition, analogy, connections, and **the exact section files to read next** | When an idea comes up by name |
| `kb/` | Answers to questions that took real digging once, kept so they never have to be dug for again | When the question sounds like one already asked |
| `documents/` | Every document split into sections. Each document has a folder with a `CODE-00-contents.md` table of contents, then one file per section | When you know the topic and need the real text |
| `full/` | Each document in one file | Only when the whole document is truly needed |
| `_returns/` | Where you send results back (see below). Not knowledge: the way back in | When something new is worked out |
| `proposals/` | Suggested changes to {{his}} documents, waiting for {{his}} decision; each has an agenda item | When an agenda item points to one |
| `captures/` | Past returns, exactly as they arrived (cited as `C01`, `C02`, ...) | When tracing where an idea entered |

## How to find things

1. **The topic is clear:** open `01-INDEX.md`, find the document code, open its contents file (`CODE-00-contents.md`), then load only the sections that matter.
2. **Half-remembered** ("somewhere we had this idea about..."): open `01-INDEX.md` and scan **Concepts** for any of the words used; each concept lists every other name it goes by after *Also*. The concept file tells you exactly which section files hold it.
3. **Sounds like a past question:** check **Questions already answered** in `01-INDEX.md`. An answer file may be all you need.
4. **Still nothing:** search this folder's files by distinctive words. Section files carry their document code and number in the name (`{{ex_doc}}-06`), so searching for a name or code finds them.
5. **Say so when you could not find it.** Do not fill a gap with a guess presented as the project's position.
<!-- kit:end finding -->

## How much to trust what you find

Edit this section for the project: what outranks what, and anything currently out of step (a newer document the prime document does not reflect yet, say). It starts from the tiers in `tools/kb/config.toml`:

{{trust_md}}
- **Concepts** and **answers** are summaries that point at the documents. Good for orientation; quote the documents for anything precise.

<!-- kit:start headers -->
## Every section file starts with a header

It says which document it belongs to, its place in that document, the previous and next files, and which concepts it covers. Use it to move to a neighbor without going back to the index.
<!-- kit:end headers -->

<!-- kit:start returns -->
## Sending results back

Create a **plain text file** in this project's `_returns` folder (plain text; never a Google Doc) named `YYYY-MM-DD-short-topic.txt`. Create it with that folder's id as its parent: every project has a `_returns` folder. One item per file; never edit an earlier one, send a new one.

```
Project: {{repo}}
From: who this is from (leave the line out when it is {{human}})
Type: insight | decision | refinement | answered-question | correction | research | draft | question | hole | todo
Topic: one line
What was worked out: the substance, in {{human}}'s words where possible
Relates to: one line per link, each a relation and a reference, for example
  builds-on {{ex_heading_ref}}
  refines concepts/{{ex_concept}}
  answers KB-0001
  settles W-001 (an agenda item: say what was decided)
  progresses W-002 (an agenda item: say where it got to)
  new (when nothing existing relates)
  Relations: builds-on | refines | extends | contradicts | replaces | answers | settles | progresses | new
Why it matters: one or two lines
Sources used: the files you actually loaded in this conversation
{{assistant}}'s additions: anything you contributed, kept separate from {{human}}'s ideas, with any reference you did not verify marked "unverified"
Verbatim: any exact phrasing {{human}} dictated that should be preserved
```

The **Project** line comes first and is exactly `Project: {{repo}}`: a return without it, or naming another project, is refused and never integrated. "Relates to" is the most important line after it: new ideas almost always build on existing ones, and saying exactly which, and how, is what makes integration accurate. Use the references from section file headers and `01-INDEX.md` (`CODE#heading-key`, `concepts/name`, `KB-NNNN`).

About {{settle_minutes}} minutes after a conversation's last return, the project folds them in: knowledge base updates, a considered response in `responses/`, agenda items updated or added, and proposals for {{his}} documents. {{human}}'s own documents are never changed without {{his}} say.
<!-- kit:end returns -->

<!-- kit:start repo -->
## If you are Claude Code in the repository

This file is the entry point for the mirrored copy. In the repository, use the `kb-lookup`, `kb-capture`, `kb-integrate`, and `kb-maintain` skills instead: record knowledge with `kb-capture`, never by writing to `_returns/`. Keep the agenda current whenever something needs settling, gets settled, or turns out to be missing (`python3 tools/kb/kb.py new-item <kind> "<title>"`; rules in `agenda/01-HOW-ITEMS-ARE-KEPT.md`). `01-INDEX.md`, `02-RECENT.md`, `agenda/00-AGENDA.md`, `documents/`, and `full/` are generated by `tools/kb/kb.py`; never edit them by hand.
<!-- kit:end repo -->

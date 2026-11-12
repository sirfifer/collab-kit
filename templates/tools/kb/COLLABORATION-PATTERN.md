# The collaboration pattern: knowledge, returns, agenda

A reusable pattern for working on a project in full collaboration with collaborators who are
**not** in the repository: an AI in another tool, or a person. They reach a mirror of the
project's knowledge (a Google Drive folder), work something out, and send it back. The pattern is
about the collaboration, not the interface. It was first built for one research project (November
2026), for voice conversations with Claude on a phone; projects install it with Collab Kit.

It has three channels. Each has one job, one place, and checks that keep it honest.

| Channel | Direction | Job | Where | Kept by |
|---|---|---|---|---|
| **1. Knowledge** | project → conversation | What the project knows, organized so a conversation can load only the piece it needs, in real time | `{{out}}/` (index, concepts, answers, documents split into sections) | the build, the curator |
| **2. Returns** | conversation → project | What a conversation worked out, with exactly what it relates to | mirror `_returns/` → `{{out}}/captures/` | conversations write; integration digests |
| **3. Agenda** | project → conversation | What still needs working out together, most pressing first, each item carrying the context to start on it | `{{out}}/agenda/` | integration, sessions, the build |

The loop: a conversation reads the knowledge and the agenda, works something out, and sends returns.
About fifteen minutes after its last return, integration folds the returns into the knowledge,
writes a considered response, settles or advances agenda items, and adds new ones. The next
conversation starts from the result.

## Interfaces: voice first, not voice only

The channels are plain files: markdown out, plain text back. Any interface that can read files
from the mirror and write one text file back can collaborate. Each interface gets a **profile**:
the rules that interface needs on top of the channels, never a change to them.

| Interface | How it connects | Its profile |
|---|---|---|
| **Voice in the Claude app** (the first, and the most demanding) | the Drive connector, through one preference line | short spoken turns, nothing read aloud that is meant for eyes (paths, codes, tables), misheard names matched against the index, saves offered at natural pauses. Its limits shaped the knowledge channel: it can open only whole files, found by name, so sections are small files with unique names |
| **Typed chat** (the Claude app or desktop) | the same connector and the same preference line | the channels as they are; no voice rules |
| **Claude Code in the repository** | the files themselves, the `kb-*` skills, the `kb-librarian` agent | records knowledge directly (`kb-capture`, `kb-integrate`) instead of sending returns |
| **Another assistant** | any tool that can read the mirror and write a text file | point it at the start file or the project's `CLAUDE.md` |
| **A person** | the mirror in Drive | browse it; drop a plain text return into `_returns/` |

Only voice is built and tested today. The others are anticipated: nothing in the names or the
structure assumes voice, and a new interface should need only its own profile.

## 1. Knowledge

The project's documents, split at their headings into files of about 1,800 words (a voice
conversation through a Drive connector can only open whole files), plus a concept graph (one file per idea, with every name it goes by, so a
misheard or half-remembered word still finds it), answers to questions that took digging, and one
index. `CLAUDE.md` at the top is the entry point: how to start and keep what is worked out, how to find
things, how much to trust each kind of document, and the voice profile. Details: `{{out}}/README.md`.

## 2. Returns

One plain text file per item in `_returns/`, never edited. Its first line names the project
(`Project: {{repo}}`); a return that names another project, or none, is refused, moved to
`_returns/refused/`, and reported instead of integrated. Each says its type, what was worked out,
and a **Relates to** line per link (builds-on, refines, contradicts, replaces, answers, settles,
progresses, new), each with a reference. A scheduled job digests a batch once it has been quiet for
fifteen minutes; processed files move to `_returns/processed/`. Format: `{{out}}/CLAUDE.md`,
"Sending results back".

## 3. Agenda

Everything that needs the human and the AI together. Five kinds: **question** (only the human can
answer), **decision** (options already laid out), **work-out** (figure it out together), **hole**
(something missing between known pieces), and **task** (work an agent just does, tracked only
because it blocks or waits on the others; never taken up in conversation).

Each item is a file with: what's needed, why it matters, what we know so far, done when, a log, and
references to read first. Frontmatter carries importance (1 to 4), effort (quick, session, deep),
`blocks`, and where it came from. The build computes the rest: what each item holds up, what it waits
on, and the order. **A blocker inherits the importance of what it blocks**, so a one-minute question
that holds up the most important decision rises to the top. Rules: `{{out}}/agenda/01-HOW-ITEMS-ARE-KEPT.md`.

In conversation (voice is the hardest case): "let's look at the agenda" gets the top two or three ready items with why each is
pressing; "let's knock out some quick ones" runs through the quick questions one at a time; taking up
an item means loading its context silently and opening with the item, why it matters, what is known,
and a first question. Settling or advancing an item is a return (`settles W-001`).

## Many projects, one parent folder

Every project's knowledge folder sits inside one parent folder in Drive (here: **{{parent}}**), and
is named exactly like the project's repository (here: **{{repo}}**). `kb.py check` and
`install.py check` fail when the name differs, and the nightly job refuses to mirror.

- **One preference line for every project.** The line in the Claude app opens the parent's start
  file (`{{parent}}/{{start_file}}`), never a project folder, so adding a project never means
  editing the app's settings. The start file lists every project with the names people say for it
  ("{{spoken_md}}" for this one); each project's nightly job rewrites only its own entry.
- **File names repeat across projects** (`CLAUDE.md`, `01-INDEX.md`, `W-001`, `_returns/`), and
  the connector searches all of Drive by name. So a conversation finds the project folder by name
  inside the parent (by the parent's id), notes the ids of the project folder and its subfolders,
  scopes every later search to those ids, and writes returns only into that project's `_returns`
  folder, each naming the project. The job that collects returns checks that name.

## Prior art, and what we took from it

Researched 2026-11-08 before building the agenda. Nothing found does all three channels for a voice
collaborator, but each piece has a mature ancestor.

| Prior art | What it is | What we took |
|---|---|---|
| **LLM Wiki** (Andrej Karpathy, a GitHub gist, April 2026) | A persistent markdown wiki an LLM maintains: raw sources, the wiki, and a schema file (CLAUDE.md or AGENTS.md); an index read first; an append-only log; ingest, query, and **lint** operations, where lint finds contradictions, orphans, missing pages, and gaps | Channel 1 is this pattern (index first, schema file, compiled once and kept current). Lint became the curator's hunt for **holes**, filed on the agenda instead of left in a report |
| **IBIS** (Issue-Based Information System; Rittel and Kunz, 1970) and **dialogue mapping** | Structures group discussion of ill-defined problems as issues (questions), positions (candidate answers), and arguments for and against | A work-out's "What we know so far" holds positions with the case for and against each, so a conversation resumes where the last one stopped |
| **Beads** (`bd`, Steve Yegge, 2025) | A git-backed issue tracker for coding agents. Only the `blocks` dependency affects readiness; agents ask for the **ready frontier** (open, no open blockers) instead of scanning everything; `discovered-from` records provenance | `blocks`, the ready-versus-waiting split, and `from`. We did not adopt the tool itself: its users are agents at a command line, while our reader is a voice model that can only open files by name |
| **TBD/TBR tracking** (NASA Systems Engineering Handbook) | Unknown values in requirements are marked To Be Determined or To Be Resolved, each with a best estimate, the action that closes it, an owner, and a date | The **hole** kind and the required **Done when**: an identified gap is not finished until we know what closes it |
| **Open Problem Garden** (an open-problems wiki for mathematics) | Each problem has an importance rating (four levels, outstanding to low), a statement, status, related problems, and a "recommended for undergraduates" flag | Four importance levels, and **effort** as the analogue of the suitability flag: what can be taken up in a minute versus a session |
| **Hill charts** (Basecamp's Shape Up) | Work moves uphill while unknowns are being figured out and downhill once only execution remains; resolve the unknowns first | The split between conversation items (uphill: figuring out) and tasks (downhill: doing), and `stage` for work-outs (not started, exploring, converging) |
| **RAID logs** and research logs | Project logs that keep risks, assumptions, issues, and dependencies as distinct records; research logs that review open questions before new searches and name a concrete next action | Distinct kinds that never blur; settled items kept with their outcome as the record of what was learned |
| **Priority inheritance** (real-time scheduling) | A low-priority job that holds a resource a high-priority job needs runs at the high priority until it releases it | A blocker inherits the importance of what it blocks |

Considered and not adopted (yet): owners and need-by dates (one human owner today; add dates when
deadlines appear), a visual hill chart, and running an existing tracker (Beads, GitHub Issues,
Linear): all are built for people or agents at a screen or a command line, not for a voice model
reading files through a connector.

Sources:
[Karpathy's LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) ·
[IBIS (Wikipedia mirror)](https://ipfs.ssi.eecc.de/ipns/en.wikipedia-on-ipfs.org/wiki/Issue-based_information_system) ·
[IBIS and dialogue mapping, Eight to Late](https://eight2late.com/category/issue-based-information-system/page/6) ·
[Beads repository](https://github.com/steveyegge/beads) ·
[Beads on the Thoughtworks Radar](https://www.thoughtworks.com/en-us/radar/tools/beads) ·
[NASA SE Handbook, Appendix C (TBD and TBR)](https://www.nasa.gov/seh/appendix-c-how-to-write-a-good-requirement) ·
[Open Problem Garden, problem structure](https://openproblemgarden.org/op_structure) ·
[Shape Up, the hill chart](https://basecamp.com/shapeup/3.4-chapter-12) ·
[RAID log template, Lucid](https://lucid.co/templates/raid-log) ·
[Research log practice](https://www.atlasworkspace.ai/blog/research-log)

## Reusing it in another project

This copy was installed by Collab Kit (version in `tools/kb/KIT-VERSION`). The kit's
`DESIGN.md` describes what is generic and what each project configures; in short:

- **Generic, from the kit:** the three channels and their rules; `tools/kb/kb.py` (build, check,
  find, agenda, new-item); `tools/kb/nightly.sh` (curator, returns-only mode, mirror with its
  ownership marker and upload verification); the launchd jobs; the `kb-*` skills and the
  `kb-librarian` agent; the shape of `{{out}}/CLAUDE.md` (its `kit:` blocks).
- **Generic, owned by no project:** the parent folder's start file. Its frame comes from the kit;
  each entry comes from that project's own `tools/kb/config.toml`; it lives only in Drive.
- **This project's own:** `tools/kb/config.toml` (names and spoken names, people, tiers, mirror
  account and parent folder, schedule, curator rules), `tools/kb/manifest.toml` (the documents and their codes), the trust
  order and project notes in `{{out}}/CLAUDE.md`, and everything the knowledge base holds.

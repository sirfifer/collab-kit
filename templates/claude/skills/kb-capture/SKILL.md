---
name: kb-capture
description: Add or update a single entry in the {{name}} knowledge base: a new answered question (KB article), a new or corrected concept, or a missing alias or link. Use when a specific piece of knowledge should be recorded right now ("add this to the knowledge base", "remember that we decided...", "that should be a concept", "make a KB entry for that"), or when kb-lookup finds a gap. For a whole session's worth of work, use kb-integrate instead.
---

# Capture one piece of knowledge

{{worktree_note}} All writes go to `{{out}}/concepts/`, `{{out}}/kb/`, `{{out}}/proposals/`, or `{{out}}/agenda/`. Formats are defined by the templates: `{{out}}/concepts/_TEMPLATE.md` and `{{out}}/kb/_TEMPLATE.md`.

## Decide what kind of thing it is

| It is... | Write... |
|---|---|
| A question that was answered and might be asked again | a KB answer: `python3 tools/kb/kb.py new-kb "<question as asked>"` |
| A named idea, mechanism, principle, analogy, or problem in the project | a concept: `python3 tools/kb/kb.py new-concept <id> "<Title>"` |
| A new name for an existing idea | add it to that concept's `aliases` |
| A connection between two ideas | add a typed relation in one concept's `[relations]` (the build shows the reverse on the other) |
| A change to what the documents *say* | a proposal in `{{out}}/proposals/`, plus an agenda item that refers to it (author documents are {{human}}'s; never edit {{author_paths_md}} to capture) |
| Something that needs {{human}}: a question, a choice, a hole | an agenda item: `python3 tools/kb/kb.py new-item <kind> "<title>"` |

**Check first** with `python3 tools/kb/kb.py find <words>` so you update the existing entry instead of making a near-duplicate.

## Rules that keep the graph useful

- **Ids are permanent.** Never rename a concept id or reuse a KB or agenda number. If an idea is superseded, set `status = "superseded"`, add `supersedes` on the new one, and keep both.
- **Every entry points at text.** `sources` must name where the idea is actually discussed, primary first (`CODE#heading-key`, `CODE@first-last`; list keys with `python3 tools/kb/kb.py keys CODE`). If the idea exists only in this conversation, it is not yet project knowledge: write a proposal, or ask {{human}} whether it belongs in a document first.
- **Aliases are for recall.** Include the informal ways {{human}} refers to it, older names, and the analogy's name. Never give one alias to two concepts (the build warns).
- **Summaries stand alone.** `summary` / `short_answer` must make sense read aloud with no context.
- Concept files stay under ~350 words; link out instead of re-explaining neighbors.
- No em dashes, en dashes as dashes, or double hyphens. Plain, direct language.

## Finish

```bash
python3 tools/kb/kb.py build
python3 tools/kb/kb.py check      # must print: kb check: OK
```

Commit the authored files and the regenerated ones together.

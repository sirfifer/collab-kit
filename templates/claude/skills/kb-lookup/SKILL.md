---
name: kb-lookup
description: Find where something lives in the {{name}} knowledge base and load only that piece. Use whenever a question, idea, or half-remembered reference about the project comes up ("where did we say...", "somewhere we had this idea...", "what do the documents say about X", "remind me how Y works"), before reading whole documents. If the answer is not already in the knowledge base and takes real digging, this skill ends by writing it down so it never has to be dug for again.
---

# Look it up in the knowledge base

The knowledge base is `{{out}}/` (start page `{{out}}/CLAUDE.md`, master lookup `{{out}}/01-INDEX.md`). Its rule is the same for you as for any collaborator reading the mirror (a voice conversation is the strictest case): **load the smallest piece that answers the question.** For a lookup that would pull a lot of text into this conversation, hand it to the `kb-librarian` agent instead and keep only its answer.

## 1. Search the structure, cheapest first

```bash
python3 tools/kb/kb.py find <the words that were used>      # ranked: concepts, past answers, headings, text
```

- A **concept** hit: read `{{out}}/concepts/<id>.md`. Its "Where to read more" names the exact section files and source line ranges.
- An **answer** hit (`KB-NNNN`): read the answer file. It may be all you need.
- A **heading** or **text** hit: load just that section, either the section file under `{{out}}/documents/` or the source lines directly:

```bash
python3 tools/kb/kb.py show {{ex_heading_ref}}    # one heading and its subsections
python3 tools/kb/kb.py show {{ex_line_ref}}       # a source line range
```

Try two or three phrasings (synonyms, the older name, the analogy) before concluding it is not there. In `{{out}}/01-INDEX.md` each concept lists all its other names after *Also*.

## 2. Answer, citing what you loaded

Say which document and section the answer came from. Documents in the canon tiers ({{canon_tiers}}) outrank concept and answer summaries; {{history_tiers_phrase}} If documents disagree, say so.

## 3. If it took real digging, write it down (the ticket protocol)

A lookup "took real digging" when `find` did not surface the answer in the first try or two and you had to read around, grep, or reason across several sections. Then, before moving on:

1. `python3 tools/kb/kb.py new-kb "<the question as it was actually asked>"`, then fill it in: `also_asked` (the other phrasings you tried), `short_answer` (two or three sentences that stand alone), `concepts`, `sources` (primary first; list keys with `python3 tools/kb/kb.py keys CODE`), the Answer, and "How this was found" (where it was *not*, which tells the next person what index entry was missing).
2. Fix the miss at its root as well: if a concept exists but lacked the words used, add them to its `aliases`; if the idea has no concept file and is a real idea, use the `kb-capture` skill to add one.
3. `python3 tools/kb/kb.py build && python3 tools/kb/kb.py check` must end with `kb check: OK`.

Writing these files is real work in a git repo. {{worktree_note}} Never edit anything generated, or anything under {{author_paths_md}}. No em dashes in anything you write.

## If it is truly not there

Say so plainly. Do not present a guess as the project's position. If the gap matters, it is a candidate for a proposal or an agenda item of kind `hole` (see `kb-integrate`).

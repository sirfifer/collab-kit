---
name: capability-walkthrough
description: Run Collab Kit's end-to-end capability test - an agent lives one demanding day as an invented user (a researcher working hands-free by voice from a phone) and judges, capability by capability, what works, what needs typing, and what is missing. Use before a release, after a change to the start-file templates, the grammar or the back end's behaviour, and when asked to "run the walk-through", "run the capability test", "run the persona", "check the round trip end to end", or "what can't be done from the phone yet".
---

# Run the capability walk-through

The test is defined in [docs/capability-walkthrough.md](../../../docs/capability-walkthrough.md):
the user, her day, the capability table, the four verdicts, the rules for the judge, and the last
run. Read it in full first. This file is only the procedure. It belongs to the kit's own
repository and is written by hand (the installer does not manage it).

## 1. Before the run

```bash
tools/collab-kit/ck brief        # what is open, what is in progress
tools/collab-kit/ck doctor       # the health of the folder and the back end, today
git log --oneline -15            # what changed since the last run
```

Note the kit version (`VERSION`), the commit, and the date of the last run (the History table).
The walk-through reads; it changes no code. If you find something to fix, it becomes an agenda
item, not an edit made during the run.

## 2. Walk the day

Hand the walk to **one subagent** with a fresh context, so the verdicts are not coloured by
whatever this session has been building. Give it:

- the path of `docs/capability-walkthrough.md`, to read in full;
- what to read as evidence: `engine/collab_kit/templates/` (what a conversation is told to do),
  `engine/collab_kit/` (what the engine and the back end do), `DESIGN-0.5.md` (what is decided
  and what is only proposed), `README.md` and `docs/` (what is promised);
- the instruction to be her for the whole day, in order, step by step: for each step, what she
  says, what the conversation would do (which files, how many tool calls), what the back end and
  an agent would do, how long she waits, and what she is told;
- the rules for the judge from the page, word for word in spirit: evidence or it did not happen;
  built, not proposed; count the cost; the docs are under test too; simple first;
- what to return: a verdict and its evidence (`file:line`) for every capability in the table, the
  score overall and for each level, the gaps worst first, every place a document overstates, and
  anything only a real phone can answer.

It is read-only: it runs no installer, files no return, and starts no server.

## 3. Check what came back

A walk-through is a report, not proof. Before recording anything:

- Open the evidence for every verdict that **changed** since the last run, and for every `no`.
  A verdict whose evidence you cannot find is `unknown`, not `works`.
- Any capability that went from `works` to something worse is a regression: find the commit that
  caused it and say so first.
- Drop a proposed fix that adds machinery where a smaller change would do, or that would make the
  base need something only some people have.

## 4. Record the result

Everything goes through `ck` (skill `collab-kit-return`), in one return:

- **A regression:** `new-item` of kind `hole`, importance 1.
- **A new gap:** `new-item` (kind `hole`, `task` or `work-out`), with the evidence in its text.
- **A known gap:** `log` on its item with what this run saw. Check `ck items` first, so nothing is
  filed twice.
- **A capability that now works:** `log` on its item saying so. Settling it is the owner's call
  once it has been tried on a real phone.
- **A knowledge note** `walk-through-YYYY-MM-DD.md`: the score, the day in short, the gaps, what
  changed since the last run. Written for a voice conversation to read aloud: short, no file
  names, no code.
- **A status line** with the score.
- **Anything that is the owner's to decide:** `ck ask`, at importance 1 only if it blocks work.

Then, in the repository (in a worktree, as for any change): update the "Last run" column and add
a row to the History table in `docs/capability-walkthrough.md`; correct any document the run found
overstating; add capabilities and steps the run showed are missing from the day, marked
"not yet walked". Run the unit tests, commit.

## 5. Tell the owner

Regressions first, then the score against the last run, then the gaps worst first, then decisions
that are theirs. Name each file as a link. Say what was not checked.

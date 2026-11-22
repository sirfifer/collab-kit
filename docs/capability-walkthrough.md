# The capability walk-through: Collab Kit's end-to-end test

The unit tests check that the engine does what its code says. This test checks something else:
**can a person get the work done?** An agent lives through one demanding day as an invented user,
step by step, and says for each thing she tries whether the system lets her do it, what gets in the
way, and what is missing.

It is the kit's regression test for capabilities. A capability is not a function that returns the
right value: it is a piece of work a person can finish, such as "hear that the experiment ended" or
"turn an idea into a project with a repository". Run it the same way each time, compare with the
last run, and the kit can never quietly lose something a person relied on.

An agent runs it with the skill `capability-walkthrough`
(`.claude/skills/capability-walkthrough/SKILL.md`). This page is the test itself: the user, her
day, the capabilities, how each is judged, and the result of the last run.

## The user

A researcher on world-model designs for AI. She has three projects in Collab Kit:

- a research framework: long documents, split into indexed sections;
- an experiments repository: runs that take from minutes to an hour;
- a public site with explainer videos, made by a rendering pipeline.

She spends a whole day walking through Paris with her phone in a pocket: six to eight hours of
real work, by voice, touching the screen only to look at something. An always-on machine at home
runs her back end and holds her repositories.

She is invented so that the test can be hard on purpose. Every part of her day is something the
kit's owner does or wants to do.

## Her day

1. **Morning.** She asks what is pressing, then has a long talk about one theory, drawing on her
   own sections.
2. **She rewrites two sections** of the framework by talking, and wants to hear the result.
3. **She starts work:** "run the ablation", "make an explainer video of this".
4. **The metro.** The call drops, then there is no signal at all for ten minutes.
5. **Midday.** She wants to know whether the ablation finished, to see its plot, and to watch the
   video.
6. **An agent is stuck:** the render needs to know which narration to use. She answers by voice.
7. **A park bench.** She starts thinking aloud about something that belongs to no project. Half an
   hour later she says: make this a project. She expects a folder, a repository, and an agent that
   can work in it.
8. **The back end is down for two hours** in the afternoon. She keeps working.
9. **Seven hours in,** the conversation is long and slow. She starts a fresh one and expects it to
   know where she was.
10. **Evening.** "Is everything saved? What is still running? Stop the render." Then she approves
    a merge and a push of the day's work.

## The capabilities

Each step of the day tests one or more of these. **Needs** says what a person must have turned on
for it: the *folder* alone (everyone has this), a *back end*, or a machine with *agents* and the
person's repositories. The base must work for everyone; the heavier capabilities are for those who
turn them on, and the test reports each level on its own.

| # | She can | Needs | Last run |
|---|---|---|---|
| C-01 | Hear what is pressing, across every project, without asking twice | folder | works |
| C-02 | Talk in depth from a project's own knowledge, down to one section | folder | works |
| C-03 | Think aloud and have it saved as she goes | folder | works |
| C-04 | Switch between projects in one conversation | folder | works |
| C-05 | Lose the call and lose almost nothing | folder | works |
| C-06 | Keep capturing with no signal at all | folder | no |
| C-07 | Change a document by voice and hear the new text | agents | no: W-015 |
| C-08 | Start agent work (an experiment, a render, an edit) | agents | typing: W-026 |
| C-09 | Hear a text result when she asks | back end | works |
| C-10 | Learn that work finished without asking | back end | no: W-030 |
| C-11 | See a plot, a page, or a video on the phone | agents | no: W-029 |
| C-12 | Be told an agent is stuck, and have her answer reach it | back end | no: W-031 |
| C-13 | Start a brainstorm that belongs to no project, with no ceremony | folder | not yet walked |
| C-14 | Turn an idea into a project by saying so | back end | works, in two steps |
| C-15 | Get a repository and a working agent for the new project | agents | no: W-035 |
| C-16 | Know within minutes that the back end is down | back end | no: W-032 |
| C-17 | Hand a long conversation over to a fresh one | folder | no: W-033 |
| C-18 | Ask "is everything saved" and get a short, true answer | folder | slow: W-034 |
| C-19 | Stop or pause running work by voice | agents | no: W-026 |
| C-20 | Approve a merge and a push by voice, and have them happen | agents | no: W-015 |
| C-21 | Tell at a glance which push on the phone needs her now | back end | not yet walked |

"W-" numbers are items on the kit's own agenda.

## How each capability is judged

One of four verdicts, each with its evidence:

| Verdict | Meaning |
|---|---|
| **works** | She can do it hands-free today. |
| **typing** | She can do it only by taking the phone out and typing, or by going to a machine. |
| **no** | She cannot do it from the phone at all. |
| **unknown** | Only a real phone can say. It goes on the list of phone tests, not in the score. |

Rules for the judge:

- **Evidence or it did not happen.** Every verdict names what makes it true: the line of a start
  file a conversation would follow, the function in the engine, the entry in the design record.
  "The docs say so" is not evidence; the code and the templates are.
- **Built, not proposed.** A capability that exists only as a proposal is `no` or `typing`, with
  the proposal named.
- **Count the cost.** Note the tool calls and the waiting each step takes. A step that needs more
  calls than one voice reply allows, or a wait nobody tells her about, is a finding even when the
  step works.
- **The docs are under test too.** Where the README, the diagrams, or the start files promise
  more than the code does, say where. Overstated documents are a failure of this test.
- **Simple first.** When something is missing, the smallest change that would give her the
  capability is the one to propose. A capability that only some people need is proposed as
  something to turn on, never as a new requirement of the base.

## What a run produces

1. **The verdict table** above, filled in again, with what changed since the last run first: any
   capability that went from `works` to something worse is a regression and is reported before
   anything else.
2. **The score:** the share of the day that works hands-free, works only by typing, and does not
   work, overall and for each level (folder, back end, agents).
3. **The gaps, worst first,** each with its evidence. A new gap becomes an agenda item; a known one
   gets a log line on its item. Nothing is left only in the report.
4. **A knowledge note** in the project's Collab Kit folder, so a voice conversation can talk about
   the result, and a status line.
5. **This page, updated:** the "Last run" column and the history below, committed.

A run changes nothing else. It reads the repository and, for the health of the round trip, the
back end's own report (`ck doctor`); it never writes to the Collab Kit folder except through `ck`.

## When to run it

- Before every release.
- After any change to what a conversation is told to do (the start-file templates), to the grammar,
  or to what the back end does with a return.
- When the owner asks, or when a new kind of work shows up that the day does not cover yet.

## Growing the test

The day is meant to grow. When a new need appears (a new kind of work, a new way of starting or
finishing it), add a step to the day and a capability to the table in the same change, marked
"not yet walked" until the next run. Capabilities are never removed: one that no longer matters is
marked retired, with the reason, so the history stays readable.

## History

| Run | Hands-free | Typing only | Neither | Notes |
|---|---|---|---|---|
| 2026-11-22 (kit 0.5.3) | about 40% | about 25% | about 35% | The first run. Ten gaps; nine filed as agenda items W-026 and W-029 to W-035, with W-015. C-13 and C-21 were added afterwards and are not yet walked. |

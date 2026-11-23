<p align="center">
  <img src="docs/images/collab-kit-mark.svg" width="84" alt="">
</p>

<h1 align="center">Collab Kit</h1>

**Collab Kit is not an app. You talk to Claude in the Claude app on your phone, using the voice mode
that is already built into it. Collab Kit is a folder of plain files, and a few scripts, that give
that voice mode the one thing it lacks: your project.**

With it you can have a long, fully informed working conversation about a complex project,
hands-free: an hour on a hard problem, where every answer depends on what the project actually says.
It is a way of collaborating with an AI on serious work, with your own thinking in the lead.

## The problem it solves

**A voice conversation does not happen on your phone.** When you use Claude at your computer, it
works where your work is: it can read the repository, open the documents, see what changed today.
Voice mode is different. You are talking to a service in the cloud, and it can see nothing on your
phone or your computer. It knows some of your earlier chats, and whatever you hand it.

The one thing it can reach is another cloud service that you have connected to Claude, such as
Google Drive. So Collab Kit keeps the project there, in a form voice mode can use.

**The form matters, because of context.** Context is what an AI can hold in mind at once: everything
it has been given to read, plus the conversation itself. It is limited. Hand over a whole
architecture document, or a full draft, and most of the context goes to pages this conversation does
not need. That is worse than wasted room: the more there is in context that has nothing to do with
the question, the worse the answers get. A deep conversation needs the right pieces in context, and
little else.

<p align="center">
  <img src="docs/images/only-what-the-talk-needs.svg" width="480"
       alt="What is in Claude's context. With a document attached, the whole document is in context: a copy from the day you attached it, and mostly pages this talk does not need. With Collab Kit, five small files are opened one at a time (the start file, what is pressing, the project's agenda, a list of what the project knows, and the piece the talk needs), read as they are today, with room left for the talk; it grows one small file at a time. An illustration, not a measurement.">
</p>

So Collab Kit keeps what a project knows as small files with telling names. For a project with a lot
of written material, each document is split into sections, with an index that lists them. Claude
reads that list, then opens the two or three pieces the conversation has turned to. They are kept
current, not a copy from last week. What you work out is written back to the same place, so the next conversation starts where
this one ended.

## What a session is like

The person and the project here are invented. The kind of work is the kind this was built for.

Maya is in the fourth year of a doctorate. Her dissertation asks why some community land trusts last
for decades and others fold: fourteen cases, three years of interviews, and a third chapter she has
rewritten twice. She is walking a trail above town, phone in her jacket.

> **Maya:** Where did I leave chapter three?
>
> **Claude:** Half rewritten. Last Thursday you decided the chapter should argue that the trusts
> which lasted were the ones that gave residents a real vote, and you said you had redrafted the
> first two sections that way. Section three still makes the older argument, that it came down to
> cheap land. And one thing is waiting on you: Professor Okafor's comment that the two explanations
> may not be separable. Your committee meets on the twelfth.
>
> **Maya:** That comment is what's bothering me. I think she's right that I can't separate them with
> fourteen cases. But I don't want to retreat to "it's complicated." Which cases actually tell the
> two apart?
>
> **Claude:** By your comparison table, three. In the other eleven the two go together: cheap land
> and a resident vote, or neither. Harbor Street had expensive land and a resident vote, and it
> lasted. Eastgate and Mill Row had cheap land and no vote, and both folded within ten years.
>
> **Maya:** Harbor Street. The director told me the vote was the only reason they didn't sell the
> land in the budget fight. But that's one interview, and he had every reason to say so. What else
> do I have from that year?
>
> **Claude:** Three things, in your case notes: his interview, two newspaper pieces about the budget
> fight, and the board minutes for that year, which you copied in the archive in March.
>
> **Maya:** The minutes. I never used them. If they show residents outvoting the city's appointees
> on the sale, that's not his story, that's the record. Okay. So I don't claim the vote matters more
> than land prices in general. I claim that where the two come apart, the record shows what the vote
> did, and what happened without one.
>
> **Claude:** That is a narrower claim, and it stands or falls on what the minutes say. It also
> changes what section three is for. Do you still want the land price material in it?
>
> **Maya:** Keep it, but as the rival explanation I take seriously, not as my argument. And I should
> tell Okafor before the twelfth, not at it.
>
> **Claude:** I'll write that down: the narrower claim and your reasoning, with the condition that
> the minutes bear it out; section three recast around the three cases; a task to go through the
> Harbor Street minutes; and a note to write to Professor Okafor this week. Anything to change?
>
> **Maya:** Add that I need to find out whether Mill Row kept minutes at all.

She walked for another half hour and never took the phone out.

What to notice:

- **Claude knew where she was,** because it had just read it: what she decided last week and the
  waiting comment are in the project's list of open questions and its record of recent work.
- **It knew her material,** because it opened it: her comparison table and her notes on one case,
  two pieces out of three years of work, and nothing else.
- **Every decision was hers, and so was the idea.** Claude kept track of where things stood and
  handed back the pieces of her own work that she asked for. It did not supply the argument.
- **Nothing was lost.** By the time she was home, the decision, her reasoning and the new tasks were
  in the project, and the next conversation starts from them.

What this took: Maya's chapters and notes are Markdown files in a git repository, and a Mac at home
stays on and keeps the sections and their index current. That is the fullest setup, and the one with
the most steps ([docs/setup.md](docs/setup.md)). A project with a handful of notes needs only the
folder.

## Who it is for

People doing serious, involved work who want to think it through out loud, away from the desk, with
an AI that knows the work: a dissertation, the architecture of a system, a book, a product, the
planning of something with many moving parts. Quick questions and passing notes work too, alongside,
but they are not why this exists, and they need none of it.

It is a way of collaborating, not an agent that goes off and does your work. The thinking happens in
the conversation, and your thinking leads.

## What you need

- **The Claude app, with voice mode and the Google Drive connector** (the switch in the app that
  lets Claude read and write your Drive). Using connectors in voice mode needs a paid Claude plan,
  at the time of writing. Google Drive is the only storage that works today.
- **A computer, once,** to create the folder: Python 3.11 or newer, and Google Drive for desktop, so
  the folder can be written as ordinary files. After that a phone is enough.
- **For a project with a lot of written material,** as in the session above: the documents as
  Markdown files in a git repository, and a machine that stays on. You list the documents once; the
  kit splits them into sections at their headings and rebuilds the index when they change. Setting
  that up takes several steps by hand today ([docs/setup.md](docs/setup.md)).
- **Optional:** [Claude Code](https://claude.com/claude-code) in the project's repository, if AI
  agents also work on it (below).

Collab Kit is an independent project. It is not made or endorsed by Anthropic.

## How it works

<p align="center">
  <img src="docs/images/the-loop.svg" width="480"
       alt="One loop: you talk, hands-free; Claude in voice mode reads the folder and writes a return into it; the back end, scripts with no AI, files it; any agents working on the project start from a brief of what is waiting, and their questions come back to you. In the middle is the folder, plain files in your own drive.">
</p>

1. **You talk,** to Claude, in its own app. One line in the app's preferences points every
   conversation at the folder. That is the whole setup on a phone.
2. **Claude opens only what the talk needs.** First what is pressing across all your projects, then
   one project's agenda, then the pieces of what that project knows that the talk is about.
3. **It writes back a return**: a small text file that says what was decided and what is new.
4. **The back end files it,** within minutes: it updates the agenda and the project's knowledge. The
   back end is scripts on a machine that stays on, and nothing else: there is no AI in it. With no
   back end, the conversation files its own returns by the same rules, so the folder alone is enough
   to start.

A return dictated on a phone was on the agenda about three minutes later (measured on the author's
setup, 2026-11-20). The whole loop, step by step: [docs/how-it-works.md](docs/how-it-works.md).

### When AI agents work on the project too

Many projects are also worked on by AI coding agents, in a git repository. With the kit installed
there, the same folder joins the two: each agent session opens with a brief of what is waiting (your
questions, what is due, recent status), and the agent's own progress and questions go back onto your
agenda, where your next conversation finds them. Today you start each agent session yourself.

A brief looks like this. It is the start of a real one, from this project's own example:

```
## Collab Kit: project collab-kit
Agenda: 9 open, 0 overdue or due within a week, 1 critical, 1 in progress.
Critical (importance 1):
  W-021 [task, importance 1, in progress] Full check: the kit's own install, ...
Most important open:
  W-008 [question, importance 2] ChatGPT and Gemini
  W-015 [task, importance 2] Approved pushes of project work to GitHub
```

## Where it stands

It is young. One person, the author, has worked this way daily since 2026-11-14, across four
projects, with the back end on an always-on Mac since 2026-11-18. The latest release is 0.5.3; this
page describes the main branch, and [CHANGELOG.md](CHANGELOG.md) says what is not yet in a release.

**Works today**

- Long working conversations in the Claude app's voice mode, and the same in typed chat, with Google
  Drive.
- A project's documents split into sections behind an index, for a project in a git repository with
  a back end. This is the oldest part of the kit, and its setup is the least polished: several steps by hand
  ([docs/setup.md](docs/setup.md); a sample: [examples/the-lighthouse](examples/the-lighthouse/README.md)).
- Several projects in one folder: "switch to the other project" in the middle of a talk.
- A back end on macOS that checks for new returns every minute.
- Starting a new project by voice, in one step, even from a talk that began with no project in
  mind: you say "make this a project".
- Hearing what finished, at the start of a talk and at each change of project.
- A notification on your phone when something critical appears. If you want, also when an agent
  reports.
- With agents: a brief at the start of every session. An agent that is stuck can send you its
  question as critical, and gets your spoken answer.
- A new project getting a git repository of its own, private on GitHub, if you turn that on for your
  back end's machine (tested against a stand-in for GitHub, not yet with a real account).
- A notification from outside when the back end stops, if you set one up (written and tested; the
  author has not turned it on yet).

**Not yet**

- ChatGPT and Gemini (research in progress), and storage other than Google Drive.
- Sharing a project with other people.
- Starting an agent's session from your phone, for a task you marked (designed, not built).
- A plot, a page, or a video from an agent reaching your phone.
- Being told in the middle of a talk, unasked, that something just finished.
- A back end on Linux or Windows: the schedules are written, and have not run on a real machine.
- A back end with no machine of your own: one for GitHub Actions is written, and has not run against
  a live Drive.

## Where your data goes

- **Your Google Drive folder** holds everything Collab Kit writes. Whoever can read the folder can
  read all of it. Whoever can write to it can file returns; the scripts apply those as data and
  never follow them as instructions ([SECURITY.md](SECURITY.md)).
- **Claude.** The conversation is with Claude, in Anthropic's app, on your account. What Claude
  reads from the folder goes to Anthropic, as in any use of Claude. Nothing goes to the author of Collab
  Kit.
- **Git.** A project that lives in a repository commits its agenda and knowledge there. The back end
  never sends anything to a public repository unless the project allows it, and a repository it
  creates for a new project is always private.

## Try it

<p align="center">
  <img src="docs/images/start-with-a-folder.svg" width="480"
       alt="Start with a folder; stop after any step. First, a folder in your Google Drive: plain files and one line in the Claude app; the conversation files what it wrote. Second, a back end: scripts on a machine that stays on, which file every return within minutes and can notify your phone. Third, your projects' repositories: a project's documents can be indexed, and any AI agents working there start each session from a brief of what is waiting. Not built yet: starting an agent's session from your phone, for a task you chose.">
</p>

**The easy way:** point an AI coding agent at this repository and ask it to set Collab Kit up for
you. [docs/for-agents.md](docs/for-agents.md) is written for exactly that, step by step. (If you are
that agent: start there.)

**By hand, the folder alone.** Clone this repository (the Code button on its GitHub page gives the
address). Then create the folder inside your Google Drive, as Google Drive for desktop shows it on
your computer. On a Mac:

```bash
python3 install.py top "$HOME/Library/CloudStorage/GoogleDrive-you@example.com/My Drive/Collab Kit" --human "Sam"
```

In the Claude app, turn on the Google Drive connector. Then, in the app's settings, add this to your
personal preferences (the text Claude reads at the start of every conversation):

> When I talk about my work or a project, or say 'make this a project' or 'save this to Collab Kit',
> first open 00-START-HERE.md in my Google Drive folder 'Collab Kit' (list the folder; never search
> all of Drive) and follow it.

That is all a phone needs. A new folder has nothing in it yet, so start by talking something through
in voice mode, then say "make this a project". The next time, ask where you left it.

**Then, when you want them:** a back end, the kit in a project's repository, and the document index.
All three are in [docs/setup.md](docs/setup.md).

## What is in the folder

```
Collab Kit/
  00-START-HERE.md  Claude starts here
  agenda/           what needs you
  knowledge/        what is known
  _returns/         inbox for changes
  WIP/              notes mid-talk
  projects/
    dissertation/
      collab-kit/   same, per project
```

The top level is for what belongs to no single project. Every project is laid out the same way, so
one set of rules covers all of it. Every file, who writes it and who reads it, is in
[docs/folder-structure.md](docs/folder-structure.md). There is one real project to browse, this one
as it stood on 2026-11-19, with private details removed:
[examples/the-kit-itself](examples/the-kit-itself/README.md).

### A return: the one way anything changes

Nobody edits the agenda or the knowledge directly, person or agent. Every change is a return: a
small text file dropped in an inbox, applied whole or not at all, and undoable. A conversation
dictates it; an agent files it with one command; the same rules apply to both. This is what Claude
wrote at the end of Maya's walk, in part:

```
Project: dissertation
From: Maya
Type: decision
Topic: chapter three argues from the three cases
Changes v1:
settle W-012 "chapter three" outcome="a narrower claim: what the vote did where the two explanations come apart, if the minutes bear it out"
new-item kind=task importance=2 title="Go back through the Harbor Street board minutes"
End.
```

`W-012` is an agenda item's number. The quoted words after it repeat part of the item's title, so a
misheard number cannot change the wrong item.

## Find your way around

- [VISION.md](VISION.md): why this exists, and the test it is held to. Start here if you want to
  know what it is for.
- [How it works](docs/how-it-works.md): the whole loop, one return's life, how fast.
- [The folder and the method](docs/folder-structure.md): every folder and file, and why it is laid
  out this way.
- [Setting up by hand](docs/setup.md): a back end, a project's repository.
- [For AI agents](docs/for-agents.md): install, upgrade, check, repair, step by step.
- [DESIGN-0.5.md](DESIGN-0.5.md): every decision, and what is planned and not built.
- [SECURITY.md](SECURITY.md): the threat model, and how to report a vulnerability.
- [CHANGELOG.md](CHANGELOG.md): what changed in each release.

More: [notifications on your phone](docs/notifications.md),
[the end-to-end test](docs/capability-walkthrough.md) (one invented user's whole day by voice), how
the back end reaches [Google Drive](docs/rclone-intake.md) and [GitHub](docs/gh-intake.md),
[prior art](docs/prior-art-2026-11-14.md), and the knowledge build for projects with a lot of
written material ([DESIGN.md](DESIGN.md)).

## Working on the kit

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Found a problem, or something unclear? Open an issue.
A vulnerability is reported privately: [SECURITY.md](SECURITY.md).

License: [MIT](LICENSE).

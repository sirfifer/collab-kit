# Collab Kit: vision

## The vision

**Real, extensive work, from a phone, hands-free, in both directions, by voice.**

A person should be able to do serious work (brainstorm, decide, write, plan, start new projects,
keep many projects moving) by talking with an AI assistant, without sitting at a computer. Not
"it works on a phone, but the real work happens at the desk": the full capability, from the phone.

Typed chat, dictation, Claude Code, other assistants, and other people are all supported. Voice
on a phone is the hardest case, so it is the one every decision is measured against. What works
hands-free works everywhere.

## What it makes possible

**A long, fully informed working session about an involved project, entirely by voice.**

Much of what Collab Kit does can be done more simply: a note dictated, a list kept, a question asked.
That is not what it is for. It is for the conversation that today needs the desk: an hour on a hard
problem, in a project with real depth, where every answer depends on what the project actually says.

The voice is not Collab Kit's. Collab Kit is not an app and adds none: the person talks to the
assistant in its own app, in the voice mode built into it (today, Claude's, in the Claude app on a
phone). Collab Kit is the files and the scripts behind that conversation.

Voice mode alone cannot hold that conversation, and the reason is where it runs. At a computer, the
assistant works where the work is: it can read the repository and the documents. A voice session is
a conversation with a service in the cloud, which can see nothing on the phone or the computer. It
has some memory and some history, and it can be handed a document. Then it knows only what it was
handed, as of that moment, and handing it over already took your hands. What an AI can hold in mind
at once, its context, is limited, and pages the talk does not need make its answers worse, not only
its context fuller. Collab Kit gives the conversation the project itself: indexed, current, and
loaded a piece at a time, so the context holds the talk and the few files that matter to it. It does
this for every project at once, so moving from one project to the next is a sentence.

And the aim is that nothing waits. Today, what a conversation works out is filed within minutes, the
next agent session starts from it, and an agent's questions are on the agenda before the next
conversation begins. Starting that agent session still takes a person; closing that gap is the next
step (DESIGN-0.5.md, section 23).

## The test

**Weeks or months of work without touching the back end**, including starting new projects.
If something can only be done at the machine, the kit is not finished.

The test is run, not only stated: an agent lives one demanding day as an invented user and judges,
capability by capability, what she can and cannot get done from her phone
([docs/capability-walkthrough.md](docs/capability-walkthrough.md)).

## What follows from it

1. **The collaboration lives in plain files, in a folder the assistant can reach.** Not in any one
   assistant's memory, and not in any one app. A conversation reads what the project knows, what
   needs deciding, and what happened recently, and it writes back what was worked out. The
   folder is the record, so the work outlives every conversation and every interface.
2. **Thinking happens in the conversation, between the person and the AI, and the person's thinking
   leads. The back end only does clerical work.** The AI's part in the conversation is to know the
   project, reflect ideas back, and pick through the pieces with the person: a collaboration, not an
   agent doing the work in their place. The back end files, indexes, sorts, and creates what it was
   asked to create, with scripts. It does not interpret, decide, or rewrite. Anything that needs
   judgment becomes an agenda item for a conversation. This makes the back end reliable and
   testable, and it means text arriving from outside has no AI to talk to.
3. **The back end is light, and its absence is not fatal.** An always-on machine is the
   recommended setup; a laptop works; a scheduled cloud run (GitHub Actions) needs no machine at
   all. The same scripts run in every one of them. Claude Code cloud sessions are not a back end:
   they would put an AI between incoming text and the credentials (DESIGN-0.5.md, section 9). When
   the back end is away, conversations keep working from the folder, and see what is still waiting.
4. **Everything has a place, at every level.** The top of Collab Kit holds what is about no
   single project (an inbox, an agenda across everything, knowledge about the person's whole
   world of work), and each project holds its own. Both look the same, so one set of rules covers
   all of it.
5. **New work starts by voice.** An idea grows on the top-level agenda until it is ready. The
   conversation checks it against everything that already exists (is this new, or part of
   something already there; is the name unique), and the back end creates the project.
6. **Not tied to one assistant, one storage service, or one kind of person.** Claude first, ChatGPT
   as soon as it can read and write the folder, others after. Google Drive first, other storage
   behind the same interface. Software projects in their own repositories, or any project at all
   (writing, music, data, planning) living entirely in the folder.
7. **Owned by the person.** Their files, their storage, their repositories. Nothing is sent
   anywhere they did not choose.
8. **Simple first, and the base is for everyone.** The kit leans toward the simplest thing that
   does the job. That is a direction, not a law, and it never costs a person something they could
   get done. A folder and a conversation give everyone the core: informed conversations, and a
   record that lasts. Everything heavier (a back end, a push to the phone, agents started from a
   phone, a repository created by voice) is a step a person turns on for the machines they have.
   The kit's owner needs every one of those steps, so every one gets built; nobody else has to run
   any of them.

## Out of scope for the base product

Several machines, teams with roles and permissions, and AI acting on its own between
conversations. Advanced configurations may add some of these; the base product never needs them.

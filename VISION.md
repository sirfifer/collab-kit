# Collab Kit: vision

This page says what Collab Kit is for and the ideals it is held to. It is an aim, not a report: what
is built so far is in the [README](README.md), under "Where it stands".

## The vision

**Real collaboration with an AI on serious work, from a phone, hands-free, by voice.**

A person should be able to do serious work (think a hard problem through, decide, write, plan, start
new projects, keep many projects moving) by talking with an AI that knows the work, without sitting
at a computer. Not "it works on a phone, but the real work happens at the desk": the full
capability, from the phone.

Collab Kit is not an app, and not a product with a voice of its own. The person talks to an AI
assistant in that assistant's own app, using the voice mode already built into it (today, Claude, in
the Claude app on a phone). Collab Kit is what stands behind that conversation: plain files, and a
few small programs that keep them in order.

Voice on a phone is the hardest case, so every decision should be measured against it. What works
hands-free works everywhere: typed chat, dictation, AI agents working in a project's code, other
assistants and, in time, other people should all be able to take part in the same collaboration.

## Collaboration is the point

Collab Kit exists for collaboration between a person and an AI, and that covers a wide range.

At one end the two bring different things, and what comes of it is more than the person would have
reached alone. At the other end the AI is closer to an executive assistant or a research assistant:
it may add little to the primary work, but it knows the whole project, so it can say whether
something was already decided, what is covered and what is missing, read a passage back, put it in
other words, or analyse it. The person is the primary author or scientist, and the AI makes the work
possible in a way nothing else could. Between those ends is everything else, including sessions
where most of the substance comes from the AI and the person's part is to steer.

Across that whole range one thing holds: **the person is the filter.** They guide the work, they
hear what comes back, and they respond to it. What an AI did or found is not settled until the
person has judged it. When an AI brings back ten things and the person says, and means, "yes, all
ten, that is exactly what I was after", that agreement is the person's work too: it rests on
everything they brought to the project up to that moment, and on being able to recognise the right
answer when they hear it. Saying yes to what the AI brought does not make it the AI's work, and
takes nothing from the person.

What Collab Kit is not for: an agent that goes off and does a person's work in their place, with the
person out of the loop.

## The conversation it is for

**A long, fully informed working session about an involved project, entirely by voice.**

Plenty of things need none of this: a note dictated, a list kept, a question asked. They can happen
alongside, and they are not the point. Collab Kit is for the conversation that today needs the desk:
an hour on a hard problem, in a project with real depth, where every answer depends on what the
project actually says.

Voice mode alone cannot hold that conversation, and the reason is where it runs. At a computer, the
assistant works where the work is: it can read the documents and the project's code. A voice session
is a conversation with a service in the cloud, which can see nothing on the phone or the computer.
It remembers some earlier chats, and it can be handed a document; then it knows only what it was
handed, as it stood at that moment, and handing it over took the person's hands. The one thing such
a session can reach is another cloud service connected to the assistant, so that is where what it
needs has to be put.

There is a second limit. Context is what an AI can hold in mind at once: everything it has been
given to read, plus the conversation itself. It is finite, and the more there is in it that has
nothing to do with the question, the worse the answers get. A deep conversation needs the right
pieces in context, and little else.

So the aim is to give the conversation a knowledge structure: a representation of the project made
for this one purpose. It is not the project, and not a copy of it. A project's own documents are
shaped for other uses, and may be large and all of a piece; that suits them, and it is no help to a
conversation. The knowledge structure is thought out, indexed, kept current, and loaded a piece at a
time, so the context holds the talk and the few pieces that matter to it. It is often a small
fraction of the project, and it should deepen wherever the work needs it to. And the aim is to do
this for every project a person has, so that moving from one to the next takes one sentence.

## Between conversations

The work does not stop when the talk does, and it does not all happen in the talk.

What a conversation works out should reach whatever else works on the project: AI agents (AI
programs that work in a project's files with nobody in the conversation), and any other systems the
person runs. Sometimes that is a plain record of a decision. Sometimes it is a request from the
person: here is a body of material, digest it, analyse it, see how it fits, make adjustments, and
tell me what you think. Or: the knowledge is thin on this topic, fill it in; and some minutes later
the agenda says it is there, with the depth the conversation needed. And some work starts with nobody asking: a system that watches a project
notices that strangers have found it, or an agent finishes something and has a question.

This is still collaboration, because of where it starts and where it ends. A request is the
person's own, made in their own conversation. What an agent did or found comes back to the person
for their judgment. And it comes back through two places only:

- **The agenda** holds what should come before the person: what needs a decision, and what they
  should hear about. An item can be a line, or it can carry a good deal: a tangent, a draft to
  review, something passing that still has depth.
- **The knowledge** holds what lasts: what permanently matures the project and moves it forward.
  When a finding is more than fits in an agenda item, the rest belongs here.

One rule follows: **what is not in the agenda or the knowledge does not exist for the next
conversation.** A document changed among the project's files, or a finding sitting in some other
system, should reach the person's next talk because it, a copy, or a summary of it was put there.
Then the conversation can summarise it, read all of it aloud, or work through it a paragraph at a
time.

The aim is that nothing waits: what a conversation worked out is filed within minutes, whatever
works on the project next starts from it, and what that work found or needs is on the agenda as soon
as it is known.

## The test

**Weeks or months of work without sitting down at a machine**, including starting new projects.
If something can only be done at the machine, the kit is not finished.

## The ideals that follow

1. **The collaboration lives in plain files, in a folder the assistant can reach.** Not in any one
   assistant's memory, and not in any one app. A conversation should read what the project knows,
   what needs deciding, and what happened recently, and write back what was worked out. The folder
   is the record, so the work outlives every conversation and every app.
2. **Thinking belongs to conversations and to agents. The filing never thinks.** Something has to
   keep the folder in order between conversations: file what was said, index, sort, create what was
   asked for. That part, the back end, should be small programs with no AI in them. It must not
   interpret, decide, or rewrite. Anything that needs judgment should become an agenda item for a
   conversation, or a task for an agent. That keeps the filing dependable and testable, and it means
   nothing written in a file can talk the filing into anything.
3. **The back end should be light, and doing without it should not be fatal.** It should run on
   whatever a person has: a machine that stays on, a laptop, or a scheduled run in the cloud with no
   machine at all. With no back end, or with it away, conversations should keep working from the
   folder.
4. **Everything has a place, at every level.** What belongs to no single project (an agenda across
   everything, knowledge about the person's whole world of work) should sit at the top, and each
   project should hold its own, laid out the same way, so one set of rules covers all of it.
5. **New work starts by voice.** An idea should be able to grow on the agenda until it is ready, and
   a conversation that began with no project in mind should become one when the person says so,
   checked against everything that already exists.
6. **Not tied to one assistant, one storage service, or one kind of work.** Claude first, other
   assistants as soon as they can read and write the folder. Google Drive first, other storage
   after. Software projects, or any project at all: a dissertation, a book, music, data, the
   planning of something large.
7. **Owned by the person.** Their files, their storage, their projects. Nothing should go anywhere
   they did not choose.
8. **Simple first, and the base is for everyone.** The kit should lean toward the simplest thing
   that does the job. That is a direction, not a law, and it should never be the reason a person
   cannot get something done. A folder and a conversation should give everyone the core: informed
   conversations, and a record that lasts. Everything heavier (a back end, a notification on the
   phone, agents started from a phone, a project's files created by voice) should be a step a person
   turns on for the machines they have. Every one of those steps is meant to be built, because the
   kit's owner needs them all. Nobody else should have to run any of them.

## What stays out

Out of the base, though a larger setup may add them: several people's machines working as one, and
teams with roles and permissions.

Out always: an AI inside the back end (ideal 2).

In scope, to be clear: agents and other systems acting between conversations, as the section above
says.

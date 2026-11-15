# Collab Kit: vision

## The vision

**Real, extensive work, from a phone, hands-free, in both directions, by voice.**

A person should be able to do serious work (brainstorm, decide, write, plan, start new projects,
keep many projects moving) by talking with an AI assistant, without sitting at a computer. Not
"it works on a phone, but the real work happens at the desk": the full capability, from the phone.

Typed chat, dictation, Claude Code, other assistants, and other people are all supported. Voice
on a phone is the hardest case, so it is the one every decision is measured against. What works
hands-free works everywhere.

## The test

**Weeks or months of work without touching the back end**, including starting new projects.
If something can only be done at the machine, the kit is not finished.

## What follows from it

1. **The collaboration lives in plain files, in a folder the assistant can reach.** Not in any one
   assistant's memory, and not in any one app. A conversation reads what the project knows, what
   needs deciding, and what happened recently, and it writes back what was worked out. The
   folder is the record, so the work outlives every conversation and every interface.
2. **Thinking happens in the conversation, between the person and the AI. The back end only
   does clerical work.** It files, indexes, sorts, and creates what it was asked to create, with
   scripts. It does not interpret, decide, or rewrite. Anything that needs judgment becomes an
   agenda item for a conversation. This makes the back end reliable and testable, and it means
   text arriving from outside has no AI to talk to.
3. **The back end is light, and its absence is not fatal.** An always-on machine is the
   recommended setup; a laptop works; a scheduled cloud run (GitHub Actions, Claude Code cloud
   sessions) needs no machine at all. The same scripts run in every one of them. When the back end
   is away, conversations keep working from the folder, and see what is still waiting.
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

## Out of scope for the base product

Several machines, teams with roles and permissions, and AI acting on its own between
conversations. Advanced configurations may add some of these; the base product never needs them.

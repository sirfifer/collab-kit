+++
# One question that took real digging = one answer file. Created with:
#   python3 tools/kb/kb.py new-kb "the question as it was asked"
# File name: KB-NNNN-short-slug.md. Ids are permanent and never reused.
id = "KB-0000"
question = "The question, phrased the way it was actually asked."
also_asked = [                   # other phrasings, so the next lookup finds it
  "another way to ask it",
]
short_answer = "Two or three sentences that stand on their own and could be spoken aloud."
concepts = ["concept-id"]        # concept files this answer is about
sources = ["OL#heading-key"]     # where the answer comes from, primary first (same syntax as concepts)
origin = "session"               # seed | session | conversation | nightly
status = "current"               # current | outdated (say what replaced it in the answer)
created = "YYYY-MM-DD"
updated = "YYYY-MM-DD"
+++

## Answer

The full answer. Cite as you go ("OL section 1.5 says...", "the idea first appears in...").
Keep it to what was asked; link concepts rather than re-explaining them.

## How this was found

Where the answer was NOT (what was searched first), and where it was. This is what tells the
next maintainer which index entry or alias was missing.

<!-- managed by Collab Kit 0.5.0: rendered from tools/kb/config.toml by kit/install.py apply. Edit the config or the kit, not this file. To make it the project's own, delete this line. -->

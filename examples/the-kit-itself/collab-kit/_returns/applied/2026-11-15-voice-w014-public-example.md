Project: collab-kit
Id: 2026-11-15-voice-w014-public-example
From: Claude voice session with Richard
Type: decision
Topic: W-014, the kit's own Collab Kit folder and the public repository

Changes v1:
settle W-014 "own collab-kit folder" outcome="Richard decided 2026-11-15: the kit's own live channels (agenda, returns, status, WIP) stay out of the public repository; their home is the Drive folder. Instead, the repository carries a static working example laid out exactly as it would sit in someone else's repository. It must be a sanitized snapshot of our real work, not a made-up example. It has to be maintained: any change to the kit that affects folder structure or how things work must be reflected in the example, so it is never stale or contradictory to how the kit actually works."
task "Public example snapshot" importance=3 "Build what W-014 settled. Proposed approach (Claude's suggestion, Richard said yes to writing it up): a script takes a fresh snapshot of the live Drive folder, sanitizes it (private decisions, account details, anything the private-to-public guard flags), and writes it into the repository's example location; a check fails any release where the example's structure does not match what the kit currently generates. Decide where the example lives in the repository and how sanitizing rules are kept."

End.

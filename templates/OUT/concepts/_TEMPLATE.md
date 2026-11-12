+++
# One concept = one file = one node in the knowledge graph. File name = id.
id = "example-concept"           # kebab-case, permanent; never rename (other files point to it)
title = "Example Concept"
kind = "mechanism"               # principle | mechanism | process | structure | property | analogy | problem | term | project
status = "active"                # active | proposed | superseded | deprecated
summary = "One sentence a listener could understand cold: what it is, not why it matters."
aliases = [                      # every other name it has gone by, including informal, older, and
  "older name",                  # misremembered ones ("that gearbox thing"). This is what makes
  "informal phrase",             # fuzzy recall work. Never give the same alias to two concepts.
]
sources = [                      # where it is discussed, PRIMARY FIRST. Reference syntax:
  "{{ex_heading_ref}}",           #   CODE (whole doc) | CODE#heading-key | CODE@first-last (source lines)
  "{{ex_line_ref}}",              # List heading keys with: python3 tools/kb/kb.py keys {{ex_doc}}
]
updated = "YYYY-MM-DD"

[relations]                      # typed edges to other concept ids (only list the meaningful ones)
part_of = []                     # this is a component of that
has_part = []
depends_on = []                  # this cannot work without that
enables = []
produces = []
refines = []                     # this is a sharper version of that
contrasts_with = []
analogy_for = []                 # (for analogies) the concept this analogy explains
example_of = []
supersedes = []
related = []                     # meaningful link that fits none of the above
+++

## Definition

Two to five sentences in the project's own terms. Accurate to the canon documents; where
documents disagree, say so and say which is newer.

## Analogy

The analogy the project uses for it, if there is one, in a sentence or two.

## Why it matters

What breaks or goes missing without it. One short paragraph.

## Open questions

Optional. What is unresolved about it, with a pointer to where that is discussed.

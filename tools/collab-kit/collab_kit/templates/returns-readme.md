# _returns: the inbox of {{name}}

Every change to this unit's agenda or knowledge arrives here first, as a return (format: the
top-level `00-START-HERE.md`, "Changing anything: write a return"). Returns here say
`Project: {{name}}`.

- `applied/`: returns that were applied, each with its ledger (`<id>.ledger.json`).
- `failed/`: returns that could not be applied as written; each has an agenda item saying why.
- `strays/`: files that do not belong here (another project's return, a Google Doc, anything else);
  each has an agenda item.

Nothing here is ever deleted by the back end.

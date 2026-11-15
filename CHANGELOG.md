# Changelog

## Unreleased

**New: the kit itself, as an example.** `examples/the-kit-itself/` is a sanitized snapshot of Collab
Kit's own project (its agenda, applied returns with ledgers, and knowledge), laid out as
`install.py project --home repo` lays out a repository. `tests/public_example.py refresh` takes a new
snapshot (generic rules for accounts, paths, and Drive ids; the owner's private never-publish words
from a file outside the repository); `check` fails, in the tests and before every release, when the
example is not what this kit generates or reads.

**Fixed: files another device wrote could not be read in a Claude Code session.** In a synced
folder, a file written elsewhere (by a phone conversation, say) is a cloud-only placeholder until read,
and processes started under Claude Code inherit a macOS policy that forbids that download: every read
failed at once with "Resource deadlock avoided". The folder store now allows the download for its
process and reads again.

**Returns: a kind word starts a new item.** `task "Order the drip line" importance=2 "What's needed"`
means `new-item kind=task`; so do `question`, `decision`, `work-out`, and `hole`. A second quoted text on
a new item is its What's needed. Voice conversations write these unprompted.

## 0.5.0 (2026-11-15)

The release that makes Collab Kit work from a phone for weeks without touching the back end
(VISION.md), and makes it a native part of every project an AI agent works in. The design record is
DESIGN-0.5.md.

**New: the layout.** One Collab Kit folder: a top level (`00-START-HERE.md`, `_returns/`, `agenda/`,
`knowledge/`, `WIP/`) and `projects/<name>/collab-kit/` shaped the same way. A project's home is
either that folder or its repository (`collab-kit/` in the repository).

**New: returns with a grammar.** Every change to an agenda or knowledge is a return with a
`Changes v1:` block (`new-item`, `set`, `log`, `settle`, `snooze`, `withdraw`, `reopen`, `status`,
`knowledge`, `project`, `new-project`, `push-request`, `undo`), applied whole or not at all, at most
once, with a ledger. Conversations apply their own returns when no back end runs (level 1);
otherwise the back end does.

**New: the back end is scripts only.** `ck backend run`: a lease (one runner at a time), every inbox
applied, repository-homed projects pulled, applied, committed (`collab-kit/` only), pushed under
guards (private repositories only unless allowed, a deny-list), and mirrored to the cloud folder
(copy, never sync; an edit to a mirror is saved as a return first). It writes the top-level start
file's health and due-soon blocks and `agenda/00-PRESSING.md` across every project. Scheduled by
launchd (through `collab-kit-runner` when the folder is a Drive for desktop folder), a systemd user
timer, or Task Scheduler: `install.py backend`.

**New: native in every project.** `install.py project <repo>` installs, into the repository:
`tools/collab-kit/` (the engine and the `ck` command), a Collab Kit section in `CLAUDE.md` and
`AGENTS.md`, hooks in `.claude/settings.json` (a session-start brief: the inbox, what is in progress
and due, recent status, other unmerged work, a kit-update notice; and a check that asks the agent to
record its work in Collab Kit when it changed files and recorded nothing), and the `collab-kit`,
`collab-kit-return`, and `collab-kit-upgrade` skills. `install.py machine --user-hooks` adds
user-level hooks so sessions started in a parent folder are briefed the first time they touch a
project. Verified with the real Claude Code (`tests/live-native-layer.sh`).

**New: starting a project by voice** (`new-project`, from an idea on the top-level agenda), moving
items between projects, approved pushes as agenda tasks, versioning by name with retention and
pinning (in the start file), WIP checkpoint notes, the seven-call reply cap.

**Changed.** The 0.4 AI curator leaves the base product. The 0.4 knowledge build (`kb.py`) stays for
projects that split their documents into sections; with `[knowledge].agenda = false` it leaves the
agenda to 0.5.

**Moving from 0.4.** `install.py migrate-04 <repo>` (channels to `collab-kit/`, agenda items
converted: importance runs the other way and `done` becomes `settled`), then
`install.py project <repo> --home repo`. Unload the 0.4 scheduled jobs first.

**Security and integrity.** Text from outside is fenced wherever an agent reads it; the back end
validates every path a return or a ledger names (a forged-ledger traversal was found and fixed in
review before release); every unpushed commit is checked against the deny-list and its paths before
a push; a failed push loses nothing. See SECURITY.md, "Text from outside", and DESIGN-0.5.md section
18.

## 0.4.0 (2026-11-11)

The parent folder, the fenced curator pass, captures in git as a forced choice, the launchd runner
for Google Drive access. See DESIGN.md.

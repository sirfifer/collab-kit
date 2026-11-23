# gh dependency intake

**Component:** [GitHub CLI](https://github.com/cli/cli), `gh`, external CLI. **Reviewed:** 2026-11-22,
against v2.105.0 (released 2026-11-18) and the project's published advisories on that day.
**Verdict:** accept as an optional tool the person provides, with the conditions in section 5.

Collab Kit never bundles, downloads, or installs `gh`. A back end runs it as a subprocess when it
is on the machine, for three things, and works without it:

| Use | Since | Commands | Without `gh` |
|---|---|---|---|
| Is a GitHub repository private, before pushing a project's `collab-kit/` to it | 0.5 | `repo view <owner>/<name> --json visibility -q .visibility` | every GitHub repository counts as public; nothing is pushed unless the project sets `allow_public` |
| The names a new project may not take | 0.5 | `repo list --limit 500 --json name,visibility` | `knowledge/repositories.md` lists local folders only |
| A new project's private repository, only with `[new_projects] github_owner` set (DESIGN-0.5.md section 25) | after 0.5.3 | `repo view <owner>/<name> --json visibility,isEmpty`, `repo create <owner>/<name> --private`, `config get git_protocol --host github.com`; `auth status --hostname github.com` from `ck doctor`; and, over https, git asks `gh auth git-credential` for the credential of that one push | the local repository is made, the remote is not, and a critical agenda item says why |

This intake was written when the third use was added, because that one creates something. The first
two only read.

## 1. License

MIT ([LICENSE](https://github.com/cli/cli/blob/trunk/LICENSE)), compatible with our MIT license.
Running a binary creates no derivative work, and nothing of it is redistributed.

## 2. Maintenance health

Maintained by GitHub. 100 stable releases between v2.36.0 (2023-10-03) and v2.105.0 (2026-11-18),
between two and three a month. Advisories are published in the repository and fixed in a named
release (section 3).

## 3. Known vulnerabilities

The [repository advisories](https://github.com/cli/cli/security/advisories) listed 17 entries on
2026-11-22, each patched in a release (the newest fixes are in v2.102.0). By what they touch:

- **Not commands we run:** codespaces (command execution from a malicious codespace, port
  forwarding), `attestation` and `release verify` (verification and a credential sent to a mirror),
  `run view` and artifact downloads, `skill search`, recursive cloning with submodules, writes
  through symbolic links during downloads and extraction, and a 2020 issue running a `git` binary
  from the current directory (patched in 1.2.1).
- **Partial token disclosure in `gh auth status` output** (patched in v2.97.0). `ck doctor` runs
  `gh auth status` and uses its exit code only. Its output is captured and discarded: never
  printed, logged, or written to the folder.
- **Unescaped parts in request URLs** (path traversal, patched in v2.97.0). The variable parts we
  pass are an owner and a repository name. For a new project each is checked first against a
  strict pattern (letters, digits, hyphens; for a name also lowercase and no leading digit), so
  neither can hold a slash, a dot, or a percent sign. For the privacy check they come from the
  address in the machine's own `backend.toml`, which only its owner writes.
- **Terminal escape sequences in output** (patched in v2.92.0 and v2.97.0). `gh`'s output never
  reaches a terminal from the back end: it is captured, parsed as JSON or reduced to one plain line
  (control characters removed) before any of it is written anywhere.

So no advisory published to that date affects the commands above as the kit runs them, on any
version. That is not a reason to run an old one: see the conditions.

## 4. What it is trusted with

- **The person's GitHub sign-in.** `gh` holds a token for the account it is signed in to, with
  that account's rights: for creating a repository under `github_owner`, the right to create
  repositories there. The kit never reads the token, never passes one, and never asks `gh` to
  print one. Over https, git obtains the credential for one push by calling `gh auth
  git-credential` itself; the setting that tells git to do so is given on that one command line
  and is not written to any git config.
- **Arguments.** Every `gh` command is an argument list with fixed words. The variable words are
  an owner and a repository name: from the machine's own `backend.toml`, or, for a new project,
  the configured owner and the project's name, both checked against a strict pattern before use.
  The back end starts no shell, and no text from a return (a title, a description, a body) is ever
  an argument. That is why a new repository gets no description. `gh` is also told its host
  (`GH_HOST=github.com`), so the repository whose visibility is checked is the one pushed to.
- **Creating, and nothing else.** One command creates: `repo create <owner>/<name> --private`.
  Nothing in the kit runs `repo edit`, `repo delete`, `repo rename`, `repo archive`, or any command
  that changes visibility or settings. After creating, the back end asks for the visibility and
  pushes only when the answer is `PRIVATE`.
- **Its answers.** What `gh` prints is parsed as JSON (two fields) or treated as a reason to show a
  person, cut to one plain line. Nothing it prints is executed or used as a path.

## 5. Verdict: accept, with conditions

1. **Optional, and the person's own.** The kit never installs or updates `gh`. A back end with no
   `[new_projects] github_owner` needs it only for the two reading uses, and degrades safely
   without it.
2. **Keep it current.** Install it from the person's package manager and let that update it. On
   2026-11-22 every published advisory is fixed in v2.102.0 or later. The kit does not check the
   version: no advisory affects the commands it runs (section 3), and a floor in the kit would
   have to be kept up by hand. Review this section when the commands change.
3. **Signed in as the account that should own the repositories,** on the back end's machine, as
   the user the back end runs as (`gh auth login`; `ck doctor` there checks it). A token limited to
   what is needed is better than a broad one, where the account allows it.
4. **A change to the list of commands repeats this intake,** and a test keeps the list honest:
   `tests/test_new_project.py` fails if any other word reaches `gh` on the way to a new
   repository, if a word of a return reaches `git` or `gh`, or if the back end's source names a
   flag for any visibility but private.
5. **Tests never reach GitHub.** `tests/fake_gh.py` stands in for `gh`, and git's addresses for
   github.com are rewritten to a temporary folder. What only a real account can show is listed in
   DESIGN-0.5.md, section 25.

## Watching for new advisories

`gh` is not in the SBOM as a package: it is not shipped. It is named in SECURITY.md under "Supply
chain" as an external tool. Subscribe to the
[repository's security advisories](https://github.com/cli/cli/security/advisories) (Watch, Custom,
Security alerts), as for rclone.

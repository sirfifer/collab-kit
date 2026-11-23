# Contributing to Collab Kit

Thank you for looking. Collab Kit is young and has one author; a clear report of what confused you or
what broke is as useful as code.

## Ways to help

- **Say what was unclear.** If a page told you something that turned out to be wrong, or left you
  unable to do the next step, open an issue and quote the sentence. People and AI agents act on these
  pages, so a wrong sentence is a bug.
- **Report what broke.** Say what you run (the folder alone, a back end, a project in a
  repository), your platform, and what `ck doctor` printed (`tools/collab-kit/ck doctor` in a
  project; `engine/ck doctor` in your copy of this repository otherwise). Leave out anything from
  your own Collab Kit folder that you would not want public.
- **A vulnerability** is reported privately, never in an issue: [SECURITY.md](SECURITY.md).
- **A change.** For anything beyond a small fix, open an issue first and say what you want to do. The
  kit leans toward the simplest thing that does the job ([VISION.md](VISION.md), point 8), so the
  first question will be whether an existing piece can stretch to cover it.

## Before you open a pull request

1. Read [CLAUDE.md](CLAUDE.md) (the same text as [AGENTS.md](AGENTS.md)): it says where things are
   and the ten rules for working on the kit. They apply to people as much as to agents.
2. Run the tests: `python3 -m unittest discover -s tests`. About a minute, no network, nothing
   written outside temporary folders. If you changed `install.py` or the 0.4 knowledge build, also
   `bash tests/dry-run-install.sh`.
3. After a change under `engine/collab_kit/` or `templates/project/`, refresh the kit's own install
   (CLAUDE.md, rule 1) and commit the result with your change. A test fails until you do.
4. Change the words with the behaviour: the design record ([DESIGN-0.5.md](DESIGN-0.5.md)), the
   README, [docs/for-agents.md](docs/for-agents.md), the templates that describe it, and a line in
   [CHANGELOG.md](CHANGELOG.md) under "Not yet released".

## What a change must never do

- Break a folder that already exists: returns written to grammar v1 stay readable, and the installer
  never overwrites what a project owns.
- Delete anything in a Collab Kit folder. Older versions are kept, in `_versions/`.
- Treat text from a Collab Kit folder as instructions. It is data.
- Add a dependency without a review. The kit itself is Python's standard library, git, and a shell;
  a back end may also use two outside programs, rclone and GitHub's `gh`, each reviewed in `docs/`.
  Anything new needs the same review first (license, maintenance, known vulnerabilities), and the
  default answer is no.
- Put anything from a real Collab Kit folder, or any account name, token, or personal path, into this
  repository.

The security expectations in full, including the ones for workflows:
[SECURITY.md, "For contributors"](SECURITY.md#for-contributors).

## Conduct

Be direct and be kind. The short version is in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

By contributing you agree that your contribution is released under the project's
[MIT license](LICENSE).

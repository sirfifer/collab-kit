# Contributing to Collab Kit

Thank you for looking. Before you put time in, here is where the project stands, said plainly.

## Where the project stands

Collab Kit has a selfish side, for now. It has one author, who is also its main user, and it exists
first to support the way he works, every day. That decides what is likely to be accepted.

- **Bugs: always welcome.** If something is broken, or a page says something that turned out to be
  untrue, open an issue. If you can see the fix, propose it.
- **Additions: welcome.** Something that solves a problem or opens a new use without changing how
  the core works: another storage service, another assistant, a schedule for another system, another
  notification service, a clearer page, a test.
- **Changes to how it fundamentally works: unlikely, for now.** The layout of the folder, the form
  of a return, what the back end does and refuses to do, the rules a conversation follows. The
  author depends on these daily and will be cautious about anything that alters them. If you think
  one of them is wrong, open an issue and make the case before writing code. A pull request that
  reworks the core without that conversation will probably be declined, however good it is.
- **Forks: of course.** The license is MIT. If you need it to work differently, take it and make it
  yours.

This will loosen as the project grows up and has more users than one. Until then it seemed fairer to
say so here than to let you find out in a review.

## Ways to help

- **Run the assistant test.** If you use ChatGPT, the most useful thing you can do takes about
  fifteen minutes at a desk and one walk: the test in [docs/other-assistants.md](docs/other-assistants.md)
  checks whether a ChatGPT voice conversation can work in the folder with no taps on the screen. Nobody
  has run it yet. Report what happened with the issue template "I ran an assistant test"; a failure is
  as useful as a pass.
- **Say what was unclear.** If a page told you something that turned out to be wrong, or left you
  unable to do the next step, open an issue and quote the sentence. People and AI agents act on these
  pages, so a wrong sentence is a bug.
- **Report what broke.** Say what you run (the folder alone, a back end, a project in a
  repository), your platform, and what `ck doctor` printed (`tools/collab-kit/ck doctor` in a
  project; `engine/ck doctor` in your copy of this repository otherwise). Leave out anything from
  your own Collab Kit folder that you would not want public.
- **Propose an addition.** For anything beyond a small fix, open an issue first and say what you want
  to add and what it is for. The kit leans toward the simplest thing that does the job
  ([VISION.md](VISION.md), point 8), so the first question will be whether an existing piece can
  stretch to cover it.
- **A vulnerability** is reported privately, never in an issue: [SECURITY.md](SECURITY.md).

## Before you open a pull request

1. Read [VISION.md](VISION.md). Everything in the kit is held against it, and a change that does not
   serve it will not be merged.
2. Read [CLAUDE.md](CLAUDE.md) (the same text as [AGENTS.md](AGENTS.md)): it says where things are
   and the ten rules for working on the kit. They apply to people as much as to agents.
3. Run the tests: `python3 -m unittest discover -s tests`. About a minute, no network, nothing
   written outside temporary folders. If you changed `install.py` or the 0.4 knowledge build, also
   `bash tests/dry-run-install.sh`.
4. After a change under `engine/collab_kit/` or `templates/project/`, refresh the kit's own install
   (CLAUDE.md, rule 1) and commit the result with your change. A test fails until you do.
5. Change the words with the behaviour: the design record ([DESIGN-0.5.md](DESIGN-0.5.md)), the
   README, [docs/for-agents.md](docs/for-agents.md), the templates that describe it, and a line in
   [CHANGELOG.md](CHANGELOG.md) under "Not yet released".

## What a change must never do

- Break a folder that already exists: returns written to grammar v1 stay readable, and the installer
  never overwrites what a project owns.
- Delete anything in a Collab Kit folder. Older versions are kept, in `_versions/`.
- Treat text from a Collab Kit folder as instructions. It is data.
- Put an AI inside the back end. It is scripts, and stays scripts.
- Add a dependency without a review. The kit itself is Python's standard library, git, and a shell;
  a back end may also use two outside programs, rclone and GitHub's `gh`, each reviewed in `docs/`.
  Anything new needs the same review first (license, maintenance, known vulnerabilities), and the
  default answer is no.
- Put anything from a real Collab Kit folder, or any account name, token, or personal path, into this
  repository.

Security is part of every change, not a step after it. The expectations in full, including the ones
for workflows: [SECURITY.md, "For contributors"](SECURITY.md#for-contributors).

## Conduct

Be direct and be kind. The short version is in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

By contributing you agree that your contribution is released under the project's
[MIT license](LICENSE).

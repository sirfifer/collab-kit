<!-- Thank you. Please read CONTRIBUTING.md first: it says plainly what is likely to be accepted. -->

**What this changes, and why**


**Which kind of change is it?**

- [ ] A fix for something broken (link the issue if there is one)
- [ ] An addition that leaves the core as it is (a storage service, an assistant, a platform, a page, a test)
- [ ] A change to how the kit fundamentally works (the folder's layout, the form of a return, what the back end does, the rules a conversation follows). Link the issue where this was discussed first.

**Checked**

- [ ] `python3 -m unittest discover -s tests` passes
- [ ] The words changed with the behaviour (README, docs, DESIGN-0.5.md, CHANGELOG.md under "Not yet released")
- [ ] After a change under `engine/collab_kit/` or `templates/project/`: the kit's own install is refreshed (CLAUDE.md, rule 1)
- [ ] No new dependency; nothing from a real Collab Kit folder; no account name, token, or personal path
- [ ] Security: anything touching returns, paths, the fences, the hooks, or pushing comes with a test (SECURITY.md, "For contributors")

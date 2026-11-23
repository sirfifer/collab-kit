"""`install.py setup`: the whole setup on one computer, in one guided command.

It finds the Google Drive folder Drive for desktop shows on this computer, asks the person's name,
creates the Collab Kit folder's top level (or keeps one that is there), records this computer's
settings, puts the kit into any repositories named, and ends with what to do in the Claude app. It
only calls the installer's own steps (`install_top`, `install_machine`, `install_project`), so it can
do nothing they cannot. Every question has a flag, so an agent can run it without prompts; with no
terminal to ask in, a missing answer is an error that names its flag.

Standard library only (Python 3.11+).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from . import config as C
from .installer import install_machine, install_project, install_top, kit_version

FOLDER_NAME = "Collab Kit"
KIT = Path(__file__).resolve().parent.parent.parent


def preference_line(folder_name: str = FOLDER_NAME) -> str:
    """The one line a person adds to the Claude app's preferences (the README quotes the same)."""
    return (f"When I talk about my work or a project, or say 'make this a project' or 'save this to Collab Kit', "
            f"first open 00-START-HERE.md in my Google Drive folder '{folder_name}' (list the folder; never search "
            f"all of Drive) and follow it.")


def drive_roots(home: Path | None = None) -> list[tuple[Path, str]]:
    """The 'My Drive' folders Google Drive for desktop shows on this computer, with the account each
    belongs to when the path says it ("" when it does not)."""
    home = home or Path.home()
    found: list[tuple[Path, str]] = []
    cloud = home / "Library" / "CloudStorage"                      # macOS, Drive for desktop
    if cloud.is_dir():
        for d in sorted(cloud.glob("GoogleDrive-*")):
            my = d / "My Drive"
            if my.is_dir():
                found.append((my, d.name[len("GoogleDrive-"):]))
    for legacy in (home / "Google Drive" / "My Drive", home / "My Drive"):  # older Drive for desktop
        if legacy.is_dir():
            found.append((legacy, ""))
    if os.name == "nt":                                            # Windows: a drive letter, G: by default
        for letter in "GHIJKLMNOPQRSTUVWXYZ":
            my = Path(f"{letter}:\\My Drive")
            try:
                if my.is_dir():
                    found.append((my, ""))
            except OSError:
                continue
    return found


class Asker:
    """Questions on a terminal; with none (an agent, a pipe) or --yes, a missing answer is an error."""

    def __init__(self, interactive: bool):
        self.interactive = interactive

    def text(self, question: str, flag: str, default: str = "") -> str:
        if not self.interactive:
            if default:
                return default
            raise SetupError(f"{question.rstrip('?: ')}: not given. Pass {flag}.")
        hint = f" [{default}]" if default else ""
        while True:
            ans = input(f"{question}{hint}: ").strip()
            if ans or default:
                return ans or default

    def choose(self, question: str, options: list[str], flag: str) -> int:
        if not self.interactive:
            raise SetupError(f"{question} There is more than one; pass {flag}.")
        print(question)
        for i, o in enumerate(options, 1):
            print(f"  {i}. {o}")
        while True:
            ans = input(f"Choose 1 to {len(options)}: ").strip()
            if ans.isdigit() and 1 <= int(ans) <= len(options):
                return int(ans) - 1

    def yes(self, question: str, default: bool = True) -> bool:
        if not self.interactive:
            return default
        ans = input(f"{question} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        return default if not ans else ans.startswith("y")


class SetupError(Exception):
    pass


def _account_of(folder: Path) -> str:
    m = re.search(r"GoogleDrive-([^/\\]+)", str(folder))
    return m.group(1) if m else ""


def find_folder(ask: Asker, given: str | None) -> Path:
    if given:
        return Path(given).expanduser()
    configured = C.machine().get("cloud", {}).get("root", "")
    if configured and not configured.startswith("rclone:") and Path(C.expand(configured)).is_dir():
        if ask.yes(f"This computer already uses the Collab Kit folder {configured}. Keep it?"):
            return Path(C.expand(configured))
    roots = drive_roots()
    if not roots:
        raise SetupError(
            "No Google Drive folder was found on this computer. Install Google Drive for desktop "
            "(https://www.google.com/drive/download/), sign in with the Google account you use in the Claude app, "
            "and run this again; or pass --folder \"<a folder inside your Google Drive>/Collab Kit\".")
    if len(roots) == 1:
        root, acct = roots[0]
    else:
        i = ask.choose("Which Google account's Drive should hold the Collab Kit folder? Use the one the Claude "
                       "app's Google Drive connector signs in with.",
                       [f"{acct or 'Google Drive'}  ({r})" for r, acct in roots], "--folder")
        root, acct = roots[i]
    folder = root / FOLDER_NAME
    if not ask.yes(f"Create (or use) the folder {folder}?"):
        folder = Path(ask.text("The Collab Kit folder to use (a path inside your Google Drive)", "--folder")).expanduser()
    return folder


def run(*, folder: str | None, human: str | None, repos: list[str], about: list[str], spoken: list[str],
        user_hooks: bool, dry: bool, interactive: bool, out=sys.stdout) -> int:
    ask = Asker(interactive)
    say = lambda *a: print(*a, file=out)                          # noqa: E731
    try:
        target = find_folder(ask, folder)
        name = human or ask.text("Your first name, as the agenda should say it (\"what needs Sam\")", "--human",
                                 C.machine().get("human", "") if C.machine_file().is_file() else "")
    except SetupError as e:
        say(f"setup: {e}")
        return 2
    except (EOFError, KeyboardInterrupt):
        say("\nsetup: stopped; nothing was written.")
        return 130
    if not target.parent.is_dir():
        say(f"setup: {target.parent} does not exist. Give a folder inside your Google Drive (--folder).")
        return 2
    mode = " (dry run: nothing is written)" if dry else ""
    say(f"\nCollab Kit {kit_version()} setup{mode}\n")

    say(f"1. The Collab Kit folder: {target}")
    if (target / "00-START-HERE.md").is_file():
        say("   it is already a Collab Kit folder: kept as it is")
        plan = install_top(target, human=name, dry=True)
        stale = [w for w, _ in plan.steps if "--replace-start" in w]
        if stale:
            say("   its start file is from another kit version: to bring it current, "
                f"python3 {KIT / 'install.py'} top \"{target}\" --human \"{name}\" --replace-start")
    else:
        plan = install_top(target, human=name, dry=dry)
        plan.show(out)

    say("\n2. This computer's settings")
    plan = install_machine(cloud_root=str(target), human=name, kit_source=None, user_hooks=user_hooks, dry=dry)
    plan.show(out)

    failed = 0
    for i, repo in enumerate(repos):
        say(f"\n{3 + i}. The kit in {repo}")
        r = Path(repo).expanduser()
        if not (r / ".git").exists():
            say("   not a git repository's top folder: skipped")
            failed += 1
            continue
        if dry:
            say("   (a dry run cannot add a project before this computer's settings exist: shown as it would be)")
        ab = about[i] if i < len(about) else ""
        sp = spoken[i] if i < len(spoken) else ""
        if interactive and not ab:
            ab = ask.text(f"   What is {r.name}, in one sentence", "--about", "")
        if interactive and not sp:
            sp = ask.text(f"   What do you call it aloud", "--spoken", r.name.replace("-", " "))
        if dry:
            continue
        p = install_project(r, about=ab, spoken=sp)
        p.show(out)
        if p.refused:
            failed += 1

    acct = _account_of(target)
    say("\nWhat you have now")
    say(f"  - The Collab Kit folder in your Google Drive{f' ({acct})' if acct else ''}: {target}")
    say(f"  - This computer knows where it is: {C.machine_file()}")
    if repos:
        say("  - The kit in each repository above that did not say 'nothing installed'. Commit each as its own "
            "commit (\"Install Collab Kit\"); the next Claude Code session there opens with a brief.")
    say("\nNext, in the Claude app (on your phone or computer, once):")
    say(f"  1. Turn on the Google Drive connector{f', signed in as {acct}' if acct else ''}.")
    say("  2. In its settings, add this to your personal preferences (the text Claude reads at the start of every conversation):")
    say(f"\n     {preference_line(target.name)}\n")
    say("  3. Wait a minute for Drive to sync the folder, then start a voice conversation and say "
        "\"what's pressing?\". A new folder has nothing on it yet: talk something through, then say "
        "\"make this a project\".")
    say("\nLater, if you want them: the kit in more repositories (python3 install.py project <repo>), and a back end "
        "that files what you said within minutes (docs/setup.md).")
    return 1 if failed else 0

"""A new project's repository (DESIGN-0.5 section 25). Part of the back end; off unless a machine's
backend.toml has a `[new_projects]` table (config.new_projects).

When `new-project` has made a project's folder, a back end that is set to also makes:

    local    a git repository at <repositories>/<name> (the folder's name is the project's name), with
             the kit installed by the kit's own installer, a short README.md, and a first commit. It
             is built in the back end's work folder and moved into place only once that commit exists,
             so a failure leaves nothing at the destination. A path that exists is never touched.
    remote   with github_owner: <owner>/<name> on GitHub, created private, checked private, and that
             first commit pushed. Nothing here can create a public repository or change visibility.

One journal per project, on this machine (<work>/new-projects/<name>.json), says how far it got:

    pending    nothing at the destination yet
    placing    built in the work folder, with its first commit recorded; about to be moved into place
    local      the local repository is in place
    done       everything the settings ask for is done and reported
    refused    it will not be done, and is not tried again (a denied word, an origin that is not ours)
    withdrawn  the project was undone
    stopped    the person dropped the agenda item that reported the failure

Every full pass takes each open journal (pending, placing, local) as far as it goes, so a failure is
retried until it works, the project is undone, or the person drops the item. Journals are the back
end's own record: they are never removed (a removed one is opened again from the ledger).

What may reach a command line: the project's name (checked against the name rule again here) and
the configured owner, each as one argument in an argument list, with addresses built from those two
and a commit id git itself printed. The back end starts no shell. Everything else a return carried
(what the project is about, what it is called) is written as file content only.
"""
from __future__ import annotations

import datetime as dt
import errno
import json
import os
import re
import shlex
import shutil
import socket
import tempfile
from pathlib import Path

from . import kit_version
from . import returns as R
from .apply import _cells, _col, _table_rows, apply_return, raise_item, read_ledger
from .store import run_quiet
from .text import check_project_name, one_line, sha, utcnow
from .unit import APPLIED, KNOWLEDGE, Unit

DIR = "new-projects"                                  # in the back end's work folder
SINCE = "since"                                       # when this back end began running with the setting on
LOOK_BACK_DAYS = 2                                    # ledgers older than this are not read again
OPEN = ("pending", "placing", "local")
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}
GH_ENV = {"GH_PROMPT_DISABLED": "1", "NO_COLOR": "1", "GH_HOST": "github.com"}   # the host the push goes to
IDENTITY = ("-c", "user.name=Collab Kit back end", "-c", "user.email=collab-kit@users.noreply.github.com",
            "-c", "commit.gpgsign=false")             # an unattended commit: no signing prompt can appear
SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")


class Stop(Exception):
    """This step cannot be done now. `kind` is a fixed word: the agenda hears of each kind once."""

    def __init__(self, kind: str, why: str, final: bool = False):
        super().__init__(why)
        self.kind, self.final = kind, final


# ---------------------------------------------------------------------------- journals --

def journal_dir(work: Path) -> Path:
    return work / DIR


def journal_path(work: Path, name: str) -> Path:
    return journal_dir(work) / f"{name}.json"


def read_journals(work: Path) -> list[dict]:
    out = []
    try:
        files = sorted(journal_dir(work).glob("*.json"))
    except OSError:
        return out
    for f in files:
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(j, dict) and j.get("name") == f.stem and not check_project_name(f.stem):
            out.append(j)
    return out


def save(work: Path, j: dict) -> None:
    d = journal_dir(work)
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f".{j['name']}.json.tmp"
    tmp.write_text(json.dumps(j, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, journal_path(work, j["name"]))


def _aware(t: dt.datetime) -> dt.datetime:
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def since(work: Path, now: dt.datetime) -> dt.datetime:
    """The moment this back end began running with the setting on. A project started before it never
    gets a repository from here: turning the setting on changes nothing about the past."""
    f = journal_dir(work) / SINCE
    try:
        return _aware(dt.datetime.fromisoformat(f.read_text(encoding="utf-8").strip()))
    except (OSError, ValueError):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(now.isoformat() + "\n", encoding="utf-8")
        return now


def forget_since(work: Path) -> None:
    """The setting is off: a project started now is not one to give a repository when it is turned
    on again."""
    try:
        (journal_dir(work) / SINCE).unlink(missing_ok=True)
    except OSError:
        pass


def started_projects(top: Unit, after: dt.datetime, now: dt.datetime) -> list[tuple[str, str]]:
    """(project name, return id) for each project a top-level return started since `after`, read from
    the ledgers of the last two days. The ledger is the record of what was applied, so a pass that
    stopped right after applying is caught by the next one. A ledger is a file in the shared folder:
    one that is not what a ledger looks like is skipped, and the name it gives is checked like any
    other text from outside."""
    floor = max(after, now - dt.timedelta(days=LOOK_BACK_DAYS)).timestamp() - 60
    out = []
    for e in top.store.files(APPLIED):
        if not e.name.endswith(".ledger.json") or (e.mtime and e.mtime < floor):
            continue
        try:
            led = json.loads(top.store.read(f"{APPLIED}/{e.name}") or "{}")
            if not isinstance(led, dict) or led.get("state") != "done" or led.get("undone_by"):
                continue
            if _aware(dt.datetime.fromisoformat(str(led.get("applied_at", "")))) < after:
                continue
            minted = led.get("minted")
            rid = str(led.get("id", ""))
            for m in minted if isinstance(minted, list) else []:
                name = m[len("project:"):] if isinstance(m, str) and m.startswith("project:") else ""
                if name and not check_project_name(name) and R.ID_RE.match(rid):
                    out.append((name, rid))
        except Exception:                             # noqa: BLE001 (one odd file never hides the others)
            continue
    return out


def project_row(top: Unit, name: str) -> dict:
    """What the catalog says of the project: {"what": ..., "say": ...} (empty when it has no row)."""
    lines, hi, cells, rows = _table_rows(top.store.read(f"{KNOWLEDGE}/projects.md") or "")
    fcol, wcol, scol = _col(cells, "folder"), _col(cells, "what"), _col(cells, "say")
    for j in rows if hi is not None and fcol is not None else []:
        row = _cells(lines[j])
        if fcol < len(row) and row[fcol].strip("`") == name:
            return {"what": row[wcol] if wcol is not None and wcol < len(row) else "",
                    "say": row[scol].replace('"', "") if scol is not None and scol < len(row) else ""}
    return {}


def undone(top: Unit, j: dict) -> bool:
    """Did an undo take back the return that started the project? The ledger says."""
    try:
        led = read_ledger(top, str(j.get("return", "")))
    except Exception:                                 # noqa: BLE001 (cannot be told now: carry on, ask again next pass)
        return False
    return bool(isinstance(led, dict) and led.get("undone_by"))


def own_items(top: Unit, j: dict) -> list:
    """The agenda items this back end raised about the project's repository, as they are now."""
    ids = [w for w in j.get("items", []) if isinstance(w, str)]
    return [i for i in top.items() if i.id in ids] if ids else []


# ------------------------------------------------------------------------ the two steps --

def _run(args: list[str], *, cwd: Path | None = None, env: dict | None = None, timeout: int = 120):
    return run_quiet(args, cwd=str(cwd) if cwd else None, capture_output=True, text=True, encoding="utf-8",
                     errors="replace", timeout=timeout, env={**os.environ, **(env or {})})


def _git(d: Path, *args: str, what: str, timeout: int = 120, check: bool = True) -> str | None:
    try:
        res = _run(["git", "-C", str(d), *args], env=GIT_ENV, timeout=timeout)
    except Exception as e:                            # noqa: BLE001 (git is not there, or it timed out)
        raise Stop("git", f"{what}: {type(e).__name__}") from None
    if res.returncode != 0:
        if not check:
            return None
        raise Stop("git", f"{what}: {one_line(res.stderr.strip(), 200)}")
    return res.stdout


def readme(name: str, about: str, spoken: str, human: str, day: str) -> str:
    """The new repository's README.md. `about` and `spoken` came from a return: they are written here
    as text and go nowhere else."""
    about = " ".join(str(about).split()).rstrip(".")
    said = ", ".join(f"\"{s.strip()}\"" for s in str(spoken).split(",") if s.strip())
    return (f"# {name}\n\n{about + '.' if about else 'A project started through Collab Kit.'}\n\n"
            f"Started {day} from a conversation, through Collab Kit."
            + (f" {human} calls it {said}." if said else "") + "\n\n"
            "## Working here\n\n"
            "This project is worked on in Collab Kit: its agenda, its inbox, and what it knows live in the\n"
            f"Collab Kit folder (`projects/{name}/collab-kit`), not in this repository. On a machine set up\n"
            "for Collab Kit, a session opened here starts from a brief of them; `CLAUDE.md` and `AGENTS.md`\n"
            "say how to work with it, and `tools/collab-kit/ck brief` shows the brief again.\n")


def shown(path: Path) -> str:
    try:
        return "~/" + path.relative_to(Path.home()).as_posix()
    except ValueError:
        return str(path)


def staging(work: Path, name: str) -> Path:
    return journal_dir(work) / "staging" / name


def has_commit(repo: Path, commit: str) -> bool:
    """Is `repo` a git repository that holds this commit? (How the back end knows a repository it
    made: by the first commit it recorded, never by the folder's name.)"""
    if not SHA_RE.match(str(commit)) or not (repo / ".git").exists():
        return False
    try:
        return _run(["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"], env=GIT_ENV, timeout=30).returncode == 0
    except Exception:                                 # noqa: BLE001
        return False


def build(work: Path, j: dict, human: str, now: dt.datetime) -> str:
    """Build the repository in the back end's work folder; return its first commit's id."""
    name = j["name"]
    stage = staging(work, name)
    try:
        if stage.exists():
            shutil.rmtree(stage)                      # what an attempt that stopped left: the back end's own scratch
        stage.mkdir(parents=True)
    except OSError as e:
        raise Stop("folder", f"the back end's work folder could not be written: {e.strerror or e}") from None
    _git(stage, "init", "-q", "-b", "main", what="git init")
    from .installer import install_project             # the kit's own installer, as for any project
    try:
        plan = install_project(stage, name=name, home="cloud", human=human, about=str(j.get("about", "")),
                               spoken=str(j.get("spoken", "")), cloud_side=False)
    except Exception as e:                            # noqa: BLE001 (reported; the staging folder is rebuilt next time)
        raise Stop("install", f"the kit's installer failed: {type(e).__name__}: {one_line(str(e), 200)}") from None
    if plan.refused:
        raise Stop("install", f"the kit's installer refused: {one_line(plan.refused, 200)}")
    try:
        (stage / "README.md").write_text(readme(name, j.get("about", ""), j.get("spoken", ""), human,
                                                now.strftime("%Y-%m-%d")), encoding="utf-8", newline="\n")
        (stage / ".gitignore").write_text("__pycache__/\n", encoding="utf-8", newline="\n")
    except OSError as e:
        raise Stop("folder", f"the back end's work folder could not be written: {e.strerror or e}") from None
    _git(stage, "add", "-A", what="git add")
    _git(stage, *IDENTITY, "commit", "-q", "-m", f"Start {name}: a README and Collab Kit {kit_version()}",
         what="the first commit")
    commit = (_git(stage, "rev-parse", "HEAD", what="git rev-parse") or "").strip()
    if not SHA_RE.match(commit):
        raise Stop("git", "git did not say which commit it made")
    return commit


def exists_stop(dest: Path) -> Stop:
    return Stop("exists", f"{dest} already exists, and nothing in it was touched: move it away, and the next "
                          "full pass makes the repository")


def place(stage: Path, dest: Path) -> None:
    """Move the finished repository into place in one step. Across file systems it is first copied
    into a new folder of this call's own making beside the destination, so the destination is never
    half there and nothing this call did not create is ever removed."""
    if os.path.lexists(dest):
        raise exists_stop(dest)
    try:
        os.rename(stage, dest)
        return
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise Stop("move", f"could not move the new repository to {dest}: {e.strerror or e}") from None
    tmp = None
    try:
        tmp = Path(tempfile.mkdtemp(prefix=f".{dest.name}.collab-kit-", dir=dest.parent))
        shutil.copytree(stage, tmp / dest.name, symlinks=True)
        if os.path.lexists(dest):
            raise exists_stop(dest)
        os.rename(tmp / dest.name, dest)
        shutil.rmtree(stage, ignore_errors=True)
    except OSError as e:
        raise Stop("move", f"could not copy the new repository to {dest}: {e.strerror or e}") from None
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)    # this call's own folder, whatever is left in it


def _gh(gh: str, *args: str, timeout: int = 90):
    try:
        return _run([gh, *args], env=GH_ENV, timeout=timeout)
    except Exception as e:                            # noqa: BLE001 (not there, or it timed out)
        raise Stop("gh", f"gh {' '.join(args[:2])}: {type(e).__name__}") from None


def _view(gh: str, slug: str) -> dict | None:
    """What GitHub says of <owner>/<name>, or None when gh cannot show it (it does not exist, gh is
    not signed in, or GitHub cannot be reached)."""
    res = _gh(gh, "repo", "view", slug, "--json", "visibility,isEmpty")
    if res.returncode != 0:
        return None
    try:
        out = json.loads(res.stdout)
    except ValueError:
        return None
    return out if isinstance(out, dict) else None


def remote_url(gh: str, owner: str, name: str) -> tuple[str, list[str]]:
    """(the remote's address, extra git settings for the push). It follows the protocol gh is set to
    for github.com. Over https git asks gh for the credential, which is what `gh auth setup-git`
    configures; here the setting is given for this one command, so the machine's git config is not
    changed. (git runs that one fixed line, gh's own path and three words, through sh itself.)"""
    res = _gh(gh, "config", "get", "git_protocol", "--host", "github.com", timeout=30)
    if res.returncode == 0 and res.stdout.strip() == "ssh":
        return f"git@github.com:{owner}/{name}.git", []
    helper = "credential.https://github.com.helper"
    return f"https://github.com/{owner}/{name}.git", ["-c", f"{helper}=", "-c",
                                                    f"{helper}=!{shlex.quote(gh)} auth git-credential"]


def make_remote(work: Path, settings: dict, j: dict) -> str:
    """Create <owner>/<name> private (or take up the one this back end created on an earlier attempt,
    or an empty private one of that name), check that it is private, and push the first commit: that
    commit, whatever the local branch has become since."""
    name, owner = j["name"], settings["github_owner"]
    slug = f"{owner}/{name}"
    local, commit = settings["repositories"] / name, str(j.get("commit", ""))
    if str(local) != j.get("local"):
        raise Stop("moved", f"the journal says the repository is at {one_line(str(j.get('local')), 120)}, and "
                            f"[new_projects] repositories now gives {local}: nothing is pushed", final=True)
    if not has_commit(local, commit):
        raise Stop("gone", f"{local} is no longer the repository the back end made (its first commit is not in "
                           "it), so nothing is pushed", final=True)
    gh = shutil.which("gh")
    if not gh:
        raise Stop("gh", "the GitHub CLI, gh, is not installed (or not on the back end's PATH): install it, then "
                         "sign in with `gh auth login`")
    seen = _view(gh, slug)
    if seen is None and not j.get("remote_made"):
        res = _gh(gh, "repo", "create", slug, "--private")
        if res.returncode != 0:
            raise Stop("gh", f"gh could not create {slug}: {one_line(res.stderr.strip(), 200) or 'no reason given'} "
                             "(`gh auth status` on that machine says whether it is signed in)")
        seen = _view(gh, slug)
    if seen is None or str(seen.get("visibility", "")).upper() != "PRIVATE":
        raise Stop("private", f"{slug} could not be confirmed private on GitHub, so nothing was pushed "
                              f"(it says: {one_line(str((seen or {}).get('visibility', 'nothing')), 40)})")
    empty = seen.get("isEmpty") is True
    if not empty and not j.get("remote_made"):
        raise Stop("taken", f"{slug} already exists on GitHub and is not empty; nothing was pushed to it")
    j["remote_made"] = True
    j["remote"] = slug
    save(work, j)
    url, extra = remote_url(gh, owner, name)
    have = (_git(local, "config", "--get", "remote.origin.url", what="git config", check=False) or "").strip()
    if have and have != url:
        raise Stop("origin", f"{local} already has an origin, {one_line(have, 120)}, which the back end did not "
                             "set: nothing is pushed", final=True)
    if not have:
        _git(local, "remote", "add", "origin", url, what="git remote add")
    if not empty:                                     # ours, and not empty: did the push arrive after all?
        there = (_git(local, *extra, "ls-remote", "origin", "refs/heads/main", what=f"asking {slug} for its main",
                      timeout=120) or "").split()
        if there[:1] == [commit]:
            return slug
        raise Stop("taken", f"{slug} is no longer empty, and its main is not this project's first commit; nothing "
                            "was pushed to it")
    _git(local, *extra, "push", "-q", "origin", f"{commit}:refs/heads/main", what=f"the first push to {slug}",
         timeout=300)
    _git(local, "branch", "-q", "--set-upstream-to=origin/main", "main", what="git branch", check=False)
    return slug


# ------------------------------------------------------------------------------ the pass --

def where_text(j: dict, host: str) -> str:
    local = shown(Path(j["local"]))
    if j.get("pushed"):
        return (f"repository {local} on {host}, and github.com/{j['remote']} (private at creation); "
                "its Collab Kit home is its folder here")
    return f"repository {local} on {host} (not on GitHub); its Collab Kit home is its folder here"


def place_text(j: dict, host: str) -> str:
    """Where it is, for a status line's heading (what the front page shows; cut at 100 characters, so
    the GitHub name comes first)."""
    return (f"github.com/{j['remote']} (private), " if j.get("pushed") else "") + f"{shown(Path(j['local']))} on {host}"


def _apply(top: Unit, rid: str, topic: str, changes: list, now) -> bool:
    """One return of the back end's own, applied at the top level. Its id is fixed per project and
    purpose, so a report that was already made is never made twice."""
    ret = R.Return(rid, top.name, {"from": "the back end", "topic": topic}, changes, True, True, "")
    return apply_return(top, ret, None, top=top, now=now).status in ("applied", "recorded", "already")


def report_id(j: dict) -> str:
    return f"backend-repository-{j['name']}-{sha(str(j.get('return', '')))[:8]}"


def close_items(p, j: dict, outcome: str, now) -> None:
    """Settle the items this back end raised about the repository that are still open."""
    for item in own_items(p.top, j):
        if item.is_open:                              # its own item, by its number: no title check to fail
            _apply(p.top, f"{report_id(j)}-closed-{item.id}", f"project {j['name']}: {item.id} is settled",
                   [R.Change("settle", 0, ref=item.id, args={"outcome": outcome})], now)


def report_done(p, j: dict, now) -> None:
    """Say where the project lives: its row in the catalog, and one status line at the top level
    whose heading names the place (the front page shows headings); then settle the items raised
    while it could not be made."""
    host = socket.gethostname()
    name, where = j["name"], where_text(j, host)
    status = R.Change("status", 0, text=f"Project {name} has its repository: {where}. Collab Kit is installed in it.")
    topic = f"project {name} has a repository: {place_text(j, host)}"
    if not _apply(p.top, report_id(j), topic, [R.Change("project", 0, ref=name, args={"where": where}), status], now):
        _apply(p.top, report_id(j) + "-status", topic, [status], now)      # no catalog row to set: say it at least
    close_items(p, j, f"made on a later pass: {where}", now)


def report_stop(p, j: dict, e: Stop, now) -> None:
    """A problem on the front page every pass it stands. On the agenda: one critical item for the
    project while it is open, and a line on its log each time the reason is of a new kind."""
    name = j["name"]
    have = f"its local repository is at {shown(Path(j['local']))}, and it is not on GitHub: " if j.get("state") == "local" \
        else "it has no repository yet: "
    why = one_line(str(e), 300)
    p.problem(f"project {name}: {have}{why}")
    kinds = [k for k in j.get("kinds", []) if isinstance(k, str)]
    if e.kind in kinds:
        return
    again = ("It is not tried again." if e.final else
             "It is tried again on every full pass (at least hourly), so correcting the cause is enough. To stop "
             "the attempts, drop this item: the project then stays as it is now.")
    said = f"{have[0].upper()}{have[1:]}{why}."
    standing = next((i for i in own_items(p.top, j) if i.is_open), None)
    if standing:
        _apply(p.top, f"{report_id(j)}-{e.kind}", f"project {name}: its repository, a new reason",
               [R.Change("log", 0, ref=standing.id, text=f"Now: {said} {again}")], now)
    else:
        title = f"Project {name}: its repository could not be " + ("put on GitHub" if j.get("state") == "local" else "made")
        out = raise_item(p.top, title, f"The project's Collab Kit folder is ready and can be used. {said}\n\n{again}",
                         top=p.top, now=now, importance=1)
        j["items"] = [*[w for w in j.get("items", []) if isinstance(w, str)], *out.minted[:1]]
    j["kinds"] = [*kinds, e.kind]


def run(p) -> None:
    """One pass's share of the work (called by backend.Pass after the top-level inbox): open a journal
    for each project started since the setting was turned on, then take every open journal as far as
    it goes."""
    settings, why = p.new_projects, p.new_projects_why
    if why:
        p.problem(f"backend.toml: {why}; no repository is made for a new project until it is corrected")
        return
    if not settings:
        if not p.dry:
            forget_since(p.work)
        return
    now = utcnow()
    if settings["github_owner"] and p.gh_listed is False:
        p.problem("new projects are set to get a GitHub repository, but gh could not list repositories just now "
                  "(not installed, not signed in, or GitHub cannot be reached): `gh auth status` on "
                  f"{socket.gethostname()} says which; `gh auth login` signs in")
    if p.dry:
        for j in read_journals(p.work):
            if j.get("state") in OPEN:
                p.note(f"project {j['name']}: its repository would be continued (state: {j['state']})")
        return
    try:
        after = since(p.work, p.started)              # before this pass applied anything
        have = {j["name"] for j in read_journals(p.work)}
        for name, rid in started_projects(p.top, after, now):
            if name in have:
                continue
            row = project_row(p.top, name)
            save(p.work, {"name": name, "return": rid, "requested": now.isoformat(), "state": "pending",
                          "about": row.get("what", ""), "spoken": row.get("say", "")})
            have.add(name)
    except Exception as ex:                           # noqa: BLE001 (said; the journals already open still go on)
        p.problem(f"new projects' repositories: looking for new projects: {type(ex).__name__}: {ex}")
    for j in read_journals(p.work):
        if j.get("state") in OPEN:
            try:
                advance(p, settings, j, now)
            except Exception as ex:                   # noqa: BLE001 (one project never stops the others)
                p.problem(f"project {j['name']}: its repository: {type(ex).__name__}: {ex}")


def advance(p, settings: dict, j: dict, now) -> None:
    name = j["name"]
    dest: Path = settings["repositories"] / name
    try:
        if undone(p.top, j):                          # at any point before it is done: nothing more is made
            if j["state"] == "local":
                _apply(p.top, report_id(j) + "-withdrawn", f"project {name} was undone; its repository stays",
                       [R.Change("status", 0, text=f"Project {name} was undone. Its repository {shown(dest)} on "
                                 f"{socket.gethostname()} stays as it is; nothing was put on GitHub.")], now)
            close_items(p, j, "the project was undone", now)
            j["state"] = "withdrawn"
            p.note(f"project {name}: undone; nothing more is made for it")
            return
        if any(i.status == "dropped" for i in own_items(p.top, j)):
            j["state"] = "stopped"                    # the person's word: leave it as it is
            p.note(f"project {name}: the item about its repository was dropped; the attempts stop")
            return
        if j["state"] == "placing" and not staging(p.work, name).exists() and not os.path.lexists(dest):
            j["state"] = "pending"                    # the built copy is gone: build it again
        if j["state"] == "pending":
            text = " ".join(str(x) for x in (name, j.get("about", ""), j.get("spoken", "")))
            hit = next((rx.pattern for rx in p.deny if rx.search(text)), None)
            if hit:
                raise Stop("deny", f"its name or description contains a denied word ({one_line(hit, 60)}), so no "
                                   "repository is made for it", final=True)
            today = now.strftime("%Y-%m-%d")
            if sum(1 for o in read_journals(p.work) if o.get("made_on") == today and o.get("name") != name) >= settings["per_day"]:
                p.problem(f"project {name}: its repository waits for tomorrow (UTC): at most "
                          f"{settings['per_day']} are made in one day ([new_projects] per_day)")
                return
            if not settings["repositories"].is_dir():
                raise Stop("folder", f"{settings['repositories']} is not a folder on this machine (correct "
                                     "[new_projects] repositories in backend.toml, or create the folder)")
            if os.path.lexists(dest):
                raise exists_stop(dest)
            commit = build(p.work, j, p.human, now)
            j.update(state="placing", local=str(dest), commit=commit, made_on=today)
            save(p.work, j)                           # what is about to be placed, said before it is placed
        if j["state"] == "placing":
            if not has_commit(dest, str(j.get("commit", ""))):     # else: placed by a pass that could not say so
                place(staging(p.work, name), dest)
            j.update(state="local", local=str(dest))
            save(p.work, j)
            p.note(f"project {name}: made its repository at {dest}")
        if j["state"] == "local":
            if settings["github_owner"] and not j.get("pushed"):
                slug = make_remote(p.work, settings, j)
                j["pushed"] = True
                save(p.work, j)
                p.note(f"project {name}: created {slug} (private) and pushed the first commit")
            report_done(p, j, now)
            j["state"] = "done"
    except Stop as e:
        j["error"] = one_line(str(e), 300)
        report_stop(p, j, e, now)
        if e.final:                                   # only once it has been said
            j["state"] = "refused"
    finally:
        save(p.work, j)

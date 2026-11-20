"""Where a unit's files live, behind one small interface.

Two stores:

- FolderStore: a folder on this machine. A synced folder (Google Drive for desktop, OneDrive,
  Dropbox, Syncthing), or any plain directory (tests, a folder-only setup).
- RcloneStore: a cloud folder reached through rclone, the way a back end must reach Google Drive
  (DESIGN-0.5 section 17: never trust Drive for desktop's local names). Only list, read, write,
  copy, move, and mkdir are used; never delete, never sync, never selfupdate.

Paths are relative and use forward slashes on every platform. A file's name is its identity.

Google Drive for desktop shows a file created in the cloud under a name that existed locally as
"name (1).md", while the cloud has one file with the right name. FolderStore reads such a local
name as the name it stands for, and writes back to the same local file, so the cloud file keeps
its name and id.
"""
from __future__ import annotations

import collections
import dataclasses
import errno
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

_DOWNLOADS = {"allowed": False}


def allow_downloads() -> bool:
    """Let this process download cloud-only placeholder files (macOS). A file another device wrote
    sits in a synced folder as a placeholder until something reads it; a process started under
    Claude Code inherits a policy that forbids that download, so every read fails at once with
    EDEADLK ("Resource deadlock avoided"). One call turns the download on for this process."""
    if _DOWNLOADS["allowed"] or os.uname().sysname != "Darwin":
        return False
    import ctypes
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        ok = libc.setiopolicy_np(3, 0, 2) == 0    # VFS_MATERIALIZE_DATALESS_FILES, PROCESS, ON
    except (OSError, AttributeError):
        return False
    _DOWNLOADS["allowed"] = ok
    return ok


def _placeholder_retry(fn):
    """Run a read; if it hit a placeholder this process may not download, allow it and run it again."""
    try:
        return fn()
    except OSError as e:
        if e.errno == errno.EDEADLK and allow_downloads():
            return fn()
        raise


_ALIAS = re.compile(r"^(?P<stem>.+?) \((?P<n>\d{1,3})\)(?P<ext>\.[^.]+)?$")
NATIVE_MIME = "application/vnd.google-apps."


@dataclasses.dataclass
class Entry:
    name: str            # the name a reader uses (its identity)
    real: str            # the name on this store (differs only for a Drive for desktop alias)
    is_dir: bool
    mtime: float = 0.0
    size: int = 0
    native: bool = False  # a Google Docs/Sheets/Slides file (never managed by Collab Kit)
    md5: str | None = None


class StoreError(RuntimeError):
    pass


def check_rel(rel: str) -> str:
    """A store path is relative, uses forward slashes, and never climbs out (.., ., a drive, a root)."""
    if (os.name == "nt" and "\\" in rel) or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel) or "\x00" in rel:
        raise StoreError(f"unsafe path {rel!r}")
    if any(p in ("..", ".") for p in rel.split("/")):
        raise StoreError(f"unsafe path {rel!r}")
    return rel


def _join(*parts: str) -> str:
    return "/".join(p.strip("/") for p in parts if p and p.strip("/"))


def _parent(rel: str) -> str:
    return rel.rsplit("/", 1)[0] if "/" in rel else ""


def _base(rel: str) -> str:
    return rel.rsplit("/", 1)[-1]


NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)     # Windows: a scheduled run opens no console window


def run_quiet(*args, **kwargs):
    """subprocess.run, without a console window for each program on Windows (the back end runs every
    minute under pythonw); the same as subprocess.run elsewhere."""
    return subprocess.run(*args, creationflags=NO_WINDOW, **kwargs)


def _inbox_name_ok(path: str) -> bool:
    base = path.rsplit("/", 1)[-1]
    return bool(base) and not base.startswith(("_", ".")) and base.lower() != "readme.md"


def _rclone_time(s: str) -> float:
    """rclone's ModTime (RFC 3339, up to nanoseconds) as epoch seconds; 0 when it cannot be read."""
    m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?(Z|[+-]\d\d:\d\d)?$", s or "")
    if not m:
        return 0.0
    frac = (m.group(2) or "")[:7]
    tz = m.group(3) or "+00:00"
    try:
        import datetime as _dt
        return _dt.datetime.fromisoformat(m.group(1) + frac + ("+00:00" if tz == "Z" else tz)).timestamp()
    except ValueError:
        return 0.0


class Store:
    """The interface. Subclasses implement the _primitives."""

    label = "store"

    def list(self, rel: str = "") -> list[Entry]:
        raise NotImplementedError

    def read(self, rel: str) -> str | None:
        raise NotImplementedError

    def write(self, rel: str, text: str) -> None:
        """Create the file, or replace its content in place."""
        raise NotImplementedError

    def copy(self, src: str, dst: str) -> None:
        raise NotImplementedError

    def move(self, src: str, dst: str) -> None:
        raise NotImplementedError

    def mkdir(self, rel: str) -> None:
        raise NotImplementedError

    def put_file(self, local: str | os.PathLike, rel: str) -> None:
        """Copy a local file (any bytes) to rel, replacing its content in place."""
        raise NotImplementedError

    def md5s(self, rel: str = "") -> dict[str, str | None]:
        """{name: md5 of its bytes} for the files in a folder (None when the store cannot say)."""
        return {e.name: None for e in self.files(rel)}

    def read_fresh(self, rel: str) -> str | None:
        """Read the file as it is now, never from a pass's snapshot (the lease)."""
        return self.read(rel)

    INBOXES = ("_returns", "projects/*/collab-kit/_returns")

    def inbox_entries(self) -> list[tuple[str, float, int]]:
        """Every file waiting in any inbox of a Collab Kit folder (the top level's and each project's), as
        (path, mtime, size), README and `_`/`.` names left out: what the back end's minute check asks."""
        out = []
        for e in self.files("_returns"):
            out.append((f"_returns/{e.name}", e.mtime, e.size))
        for d in self.dirs("projects"):
            for e in self.files(f"projects/{d.name}/collab-kit/_returns"):
                out.append((f"projects/{d.name}/collab-kit/_returns/{e.name}", e.mtime, e.size))
        return [x for x in out if _inbox_name_ok(x[0])]

    # ---- shared helpers
    def entry(self, rel: str) -> Entry | None:
        name = _base(rel)
        for e in self.list(_parent(rel)):
            if e.name == name:
                return e
        return None

    def exists(self, rel: str) -> bool:
        return self.entry(rel) is not None

    def files(self, rel: str = "") -> list[Entry]:
        return [e for e in self.list(rel) if not e.is_dir]

    def dirs(self, rel: str = "") -> list[Entry]:
        return [e for e in self.list(rel) if e.is_dir]


class FolderStore(Store):
    label = "folder"

    def __init__(self, root: str | os.PathLike):
        self.root = Path(root).expanduser()

    def __repr__(self):
        return f"FolderStore({self.root})"

    def _p(self, rel: str) -> Path:
        check_rel(rel)
        return self.root.joinpath(*[p for p in rel.split("/") if p]) if rel else self.root

    def _resolve(self, rel: str) -> Path:
        """The local path for a name: the exact file, else its Drive for desktop alias."""
        direct = self._p(rel)
        if direct.exists() or not rel:
            return direct
        e = self.entry(rel)
        return self._p(_join(_parent(rel), e.real)) if e else direct

    def list(self, rel: str = "") -> list[Entry]:
        d = self._resolve(rel)
        if not d.is_dir():
            return []
        raw = []
        for child in d.iterdir():
            try:
                st = child.stat()
            except OSError:
                continue
            raw.append(Entry(child.name, child.name, child.is_dir(), st.st_mtime, st.st_size,
                             native=child.suffix.lower() in (".gdoc", ".gsheet", ".gslides", ".gform", ".gsite")))
        names = {e.name for e in raw}
        out: dict[str, Entry] = {}
        for e in raw:
            m = _ALIAS.match(e.name)
            logical = e.name
            if m and not e.is_dir:
                plain = m.group("stem") + (m.group("ext") or "")
                if plain not in names:
                    logical = plain
            e.name = logical
            if logical in out:            # two local files for one name: the newer is current
                keep = max(out[logical], e, key=lambda x: x.mtime)
                out[logical] = keep
            else:
                out[logical] = e
        return sorted(out.values(), key=lambda e: e.name)

    def duplicates(self, rel: str = "") -> list[tuple[str, list[str]]]:
        """Names with more than one local file (the healing rule in DESIGN-0.5 section 16)."""
        d = self._resolve(rel)
        if not d.is_dir():
            return []
        groups: dict[str, list[str]] = {}
        for child in d.iterdir():
            if child.is_dir():
                continue
            m = _ALIAS.match(child.name)
            plain = (m.group("stem") + (m.group("ext") or "")) if m else child.name
            groups.setdefault(plain, []).append(child.name)
        return [(k, sorted(v)) for k, v in groups.items() if len(v) > 1]

    def read(self, rel: str) -> str | None:
        p = self._resolve(rel)
        if not p.is_file():
            return None
        return _placeholder_retry(lambda: p.read_text(encoding="utf-8", errors="replace"))

    def write(self, rel: str, text: str) -> None:
        p = self._resolve(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def copy(self, src: str, dst: str) -> None:
        d = self._p(dst)
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.exists():
            raise StoreError(f"copy would overwrite {dst}")
        _placeholder_retry(lambda: shutil.copy2(self._resolve(src), d))

    def move(self, src: str, dst: str) -> None:
        d = self._p(dst)
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.exists():
            raise StoreError(f"move would overwrite {dst}")
        os.replace(self._resolve(src), d)

    def mkdir(self, rel: str) -> None:
        self._p(rel).mkdir(parents=True, exist_ok=True)

    def put_file(self, local, rel: str) -> None:
        p = self._resolve(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(local, "rb") as src, open(p, "wb") as dst:
            shutil.copyfileobj(src, dst)

    def md5s(self, rel: str = "") -> dict[str, str | None]:
        import hashlib
        out = {}
        for e in self.files(rel):
            try:
                out[e.name] = hashlib.md5(self._p(_join(rel, e.real)).read_bytes()).hexdigest()
            except OSError:
                out[e.name] = None
        return out


_MD5 = re.compile(r"^[0-9a-f]{32}$")


class ContentCache:
    """File contents kept by their md5, the hash Drive lists for every file: a file whose listed md5
    is here is read from here instead of being downloaded again. In a folder of the back end's own (its
    work folder, never the Collab Kit folder), or in memory only (a dry run writes nothing). A cached
    copy whose bytes no longer match its md5 is dropped and downloaded again."""

    def __init__(self, folder: str | os.PathLike | None = None):
        self.folder = Path(folder).expanduser() if folder else None
        self.mem: dict[str, bytes] = {}
        if self.folder:
            self.folder.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(self.folder, 0o700)
            except OSError:
                pass

    def get(self, h: str | None) -> bytes | None:
        if not h or not _MD5.match(h):                # a listed hash is outside text: never a path otherwise
            return None
        if h in self.mem:
            return self.mem[h]
        if not self.folder:
            return None
        p = self.folder / h
        try:
            data = p.read_bytes()
        except OSError:
            return None
        if hashlib.md5(data).hexdigest() != h:
            p.unlink(missing_ok=True)
            return None
        return data

    def put(self, data: bytes) -> str:
        h = hashlib.md5(data).hexdigest()
        if not self.folder:
            self.mem[h] = data
            return h
        tmp = self.folder / f".{h}.{os.getpid()}.tmp"
        try:
            tmp.write_bytes(data)
            os.replace(tmp, self.folder / h)
        except OSError:
            tmp.unlink(missing_ok=True)              # a cache that cannot be written only costs a download
        return h

    def keep_only(self, wanted: set) -> None:
        """Drop every copy whose md5 no file in the folder has any more."""
        if not self.folder or not self.folder.is_dir():
            return
        for p in self.folder.iterdir():
            if p.name not in wanted:
                try:
                    p.unlink()
                except OSError:
                    pass


class RcloneStore(Store):
    """A cloud folder through rclone (e.g. remote 'gdrive:Collab Kit'), under the conditions of
    docs/rclone-intake.md: the pinned version only (rclone.lock), six commands only, argument lists
    (no shell), inherited RCLONE_* settings stripped, a dedicated config, fail closed on duplicate
    names, writes that keep the Drive file id (rcat, or copyto from a local file over 90 KiB).

    A back end's pass reads the folder through a snapshot (snapshot() to end_snapshot()): one
    recursive listing with every file's md5 answers every listing, and a read downloads a file
    (`cat`) only when the content cache does not hold its listed md5. Writes, copies and moves still go
    through rclone, and update the snapshot and the cache. Without a snapshot every call is its own
    rclone command, as before."""

    label = "rclone"
    SPOOL_OVER = 90 * 1024

    def __init__(self, remote: str, rclone: str | None = None, config: str | None = None, check_version: bool = True):
        self.remote = remote.rstrip("/")
        self.rclone = rclone or os.environ.get("COLLAB_KIT_RCLONE") or "rclone"
        self.config = config or os.environ.get("COLLAB_KIT_RCLONE_CONFIG", "")
        self.flags = ["--ask-password=false", "--drive-import-formats", "", "--drive-use-trash=true"]
        if self.config:
            self.flags = ["--config", self.config, *self.flags]
        self._checked = not check_version
        self.dupes: dict[str, set[str]] = {}     # folder -> names Drive holds more than once
        self.calls: collections.Counter = collections.Counter()   # rclone commands run, by command
        self.cache_hits = 0                       # reads a snapshot answered from the content cache
        self._snap: dict[str, dict[str, Entry]] | None = None    # folder -> {name: entry}, during a pass
        self._cache: ContentCache | None = None

    def __repr__(self):
        return f"RcloneStore({self.remote})"

    def _guard(self, rel: str) -> None:
        """Fail closed on a name Drive holds more than once: a single-file command would pick one."""
        if _base(rel) in self.dupes.get(_parent(rel), set()):
            raise StoreError(f"{rel}: Drive holds two files with this name; a conversation heals it (the newer is current)")

    def _r(self, rel: str) -> str:
        check_rel(rel)
        return f"{self.remote}/{rel}" if rel else self.remote

    def _env(self) -> dict:
        return {k: v for k, v in os.environ.items() if not k.startswith("RCLONE_")}

    def uses_shared_google_client(self) -> bool:
        """True when the remote is Google Drive signed in with rclone's shared client (no client_id of
        its own): Google retires that client during 2026, and it is rate-limited across every rclone
        user. Read from the config file itself, so no rclone command is added; False when unsure."""
        import configparser
        if self.config:
            candidates = [Path(self.config).expanduser()]
        else:                                         # rclone's own default places, in its order
            candidates = ([Path(os.environ["APPDATA"]) / "rclone" / "rclone.conf"] if os.name == "nt" and
                          os.environ.get("APPDATA") else [])
            if os.environ.get("XDG_CONFIG_HOME"):
                candidates.append(Path(os.environ["XDG_CONFIG_HOME"]) / "rclone" / "rclone.conf")
            candidates += [Path.home() / ".config" / "rclone" / "rclone.conf", Path.home() / ".rclone.conf"]
        path = next((c for c in candidates if c.is_file()), None)
        cp = configparser.ConfigParser(interpolation=None)
        try:
            cp.read_string(path.read_text(encoding="utf-8") if path else "")
        except (OSError, UnicodeDecodeError, configparser.Error):
            return False                              # missing, or encrypted: cannot tell
        name = self.remote.split(":", 1)[0]
        if not cp.has_section(name):
            return False
        sec = cp[name]
        return sec.get("type", "").strip() == "drive" and not sec.get("client_id", "").strip()

    def _check_version(self) -> None:
        if self._checked:
            return
        import tomllib
        want = tomllib.loads((Path(__file__).with_name("rclone.lock")).read_text(encoding="utf-8"))["version"]
        try:
            res = run_quiet([self.rclone, "version"], capture_output=True, text=True, timeout=60, env=self._env())
        except FileNotFoundError:
            raise StoreError("rclone is not installed (see docs/rclone-intake.md)") from None
        first = (res.stdout.splitlines() or [""])[0].strip()
        if first != f"rclone {want}":
            raise StoreError(f"rclone must be {want} (rclone.lock); this is '{first[:60]}'")
        self._checked = True

    def _run(self, args: list[str], data: str | None = None, raw: bool = False) -> str | bytes:
        if args[0] not in ("lsjson", "cat", "rcat", "copyto", "moveto", "mkdir"):
            raise StoreError(f"rclone {args[0]} is not one of the commands Collab Kit uses")
        self._check_version()
        self.calls[args[0]] += 1
        cmd = [self.rclone, *args, *self.flags]
        try:
            res = run_quiet(cmd, input=data.encode("utf-8") if data is not None else None,
                                 capture_output=True, timeout=300, env=self._env())
        except FileNotFoundError:
            raise StoreError("rclone is not installed (see docs/rclone-intake.md)") from None
        except subprocess.TimeoutExpired:
            raise StoreError(f"rclone timed out: {args[0]}") from None
        if res.returncode != 0:                       # the cause is at the end; notices are not it
            lines = [ln.strip() for ln in res.stderr.decode("utf-8", "replace").splitlines() if ln.strip()]
            msg = " / ".join([ln for ln in lines if " NOTICE: " not in ln] or lines)
            err = StoreError(f"rclone {args[0]} failed (exit {res.returncode}): {msg[-400:]}")
            err.code = res.returncode          # 3: directory not found, 4: file not found (rclone docs)
            raise err
        return res.stdout if raw else res.stdout.decode("utf-8", errors="replace")

    def inbox_entries(self) -> list[tuple[str, float, int]]:
        """One rclone call for every inbox (rather than one per folder): this runs every minute."""
        args = ["lsjson", "-R", "--files-only"]
        for pat in self.INBOXES:
            args += ["--include", f"/{pat}/*"]
        try:
            items = json.loads(self._run([*args, self._r("")]) or "[]")
        except StoreError as e:
            if getattr(e, "code", None) == 3:
                return []
            raise
        out = []
        for it in items:
            path = it.get("Path", "")
            if path and _inbox_name_ok(path):
                out.append((path, _rclone_time(it.get("ModTime", "")), int(it.get("Size") or 0)))
        return out

    @staticmethod
    def _entry(it: dict) -> Entry:
        """One item of `lsjson` output. Google Docs, Sheets, Slides appear under an export name with
        size -1 (rclone docs): native, never read."""
        size = int(it.get("Size") if it.get("Size") is not None else 0)
        name = str(it.get("Name") or _base(str(it.get("Path") or "")))
        return Entry(name, name, bool(it.get("IsDir")), _rclone_time(it.get("ModTime", "")), max(size, 0),
                     native=(not it.get("IsDir")) and size < 0, md5=(it.get("Hashes") or {}).get("md5"))

    def _add(self, folder: dict[str, Entry], parent: str, e: Entry) -> None:
        """Add a listed entry; a name listed twice is a duplicate (the newer is kept for listing)."""
        if e.name in folder:
            self.dupes.setdefault(parent, set()).add(e.name)
            if e.mtime <= folder[e.name].mtime:
                return
        folder[e.name] = e

    def list(self, rel: str = "") -> list[Entry]:
        if self._snap is not None:
            check_rel(rel)
            return sorted((dataclasses.replace(e) for e in self._snap.get(rel.strip("/"), {}).values()),
                          key=lambda e: e.name)
        try:
            out = self._run(["lsjson", "--hash", "--hash-type", "md5", self._r(rel)])
        except StoreError as e:
            if getattr(e, "code", None) == 3:
                return []
            raise
        res: dict[str, Entry] = {}
        for it in json.loads(out or "[]"):
            self._add(res, rel, self._entry(it))
        return sorted(res.values(), key=lambda e: e.name)

    # ---- a pass's snapshot
    def snapshot(self, cache: str | os.PathLike | None = None) -> int:
        """Read the whole folder in one listing (`lsjson -R` with md5s) and answer every listing and
        read from it until end_snapshot(); `cache` is the content cache's folder (None: memory only).
        Returns how many entries the listing held."""
        try:
            items = json.loads(self._run(["lsjson", "-R", "--hash", "--hash-type", "md5", self._r("")]) or "[]")
        except StoreError as e:
            if getattr(e, "code", None) != 3:
                raise
            items = []
        tree: dict[str, dict[str, Entry]] = {"": {}}
        self.dupes = {}
        for it in items:
            path = str(it.get("Path") or "").strip("/")
            if not path:
                continue
            e = self._entry(it)
            e.name = e.real = _base(path)
            if e.is_dir:
                tree.setdefault(path, {})
            self._add(tree.setdefault(_parent(path), {}), _parent(path), e)
        try:
            contents = ContentCache(cache)
        except OSError:
            contents = ContentCache(None)            # a cache that cannot be made only costs downloads
        self._snap, self._cache = tree, contents
        self.cache_hits = 0
        return len(items)

    def end_snapshot(self) -> None:
        """Back to one rclone call per operation; the cache keeps only what the folder still holds."""
        if self._snap is None:
            return
        if self._cache is not None:
            self._cache.keep_only({e.md5 for folder in self._snap.values() for e in folder.values() if e.md5})
        self._snap, self._cache = None, None

    def _snap_entry(self, rel: str) -> Entry | None:
        return self._snap.get(_parent(rel), {}).get(_base(rel)) if self._snap is not None else None

    def _snap_dirs(self, rel: str) -> None:
        """Every folder on the way to rel (a folder) is in the snapshot."""
        parts = [p for p in rel.split("/") if p]
        for i in range(len(parts)):
            path, parent = "/".join(parts[: i + 1]), "/".join(parts[:i])
            folder = self._snap.setdefault(parent, {})
            if parts[i] not in folder or not folder[parts[i]].is_dir:
                folder[parts[i]] = Entry(parts[i], parts[i], True, time.time())
            self._snap.setdefault(path, {})

    def _snap_file(self, rel: str, md5: str | None, size: int, native: bool = False, mtime: float | None = None) -> None:
        """The file as this pass left it (written, copied, moved; or read: then its time stays)."""
        if self._snap is None:
            return
        self._snap_dirs(_parent(rel))
        self._snap[_parent(rel)][_base(rel)] = Entry(_base(rel), _base(rel), False, time.time() if mtime is None else mtime,
                                                     size, native=native, md5=md5)

    def _snap_forget(self, rel: str) -> None:
        if self._snap is not None:
            self._snap.get(_parent(rel), {}).pop(_base(rel), None)

    def md5s(self, rel: str = "") -> dict[str, str | None]:
        return {e.name: getattr(e, "md5", None) for e in self.files(rel)}

    def account(self) -> str:
        """The Google account the folder belongs to: the owner of its start file, as Drive reports it
        (`lsjson --metadata`, read-only, the pinned rclone). "" when it cannot be told: no start file,
        no owner in the listing, or two files of that name with different owners. (rclone's
        `config userinfo` does not work for Google Drive, so the signed-in account cannot be asked.)"""
        try:
            items = json.loads(self._run(["lsjson", "--metadata", "--files-only", self._r("")]) or "[]")
        except (StoreError, ValueError):
            return ""
        owners = {str((it.get("Metadata") or {}).get("owner") or "") for it in items
                  if isinstance(it, dict) and it.get("Name") == "00-START-HERE.md"}
        return owners.pop() if len(owners) == 1 else ""

    def read(self, rel: str) -> str | None:
        self._guard(rel)
        if self._snap is not None:
            e = self._snap_entry(rel)
            if e is None or e.is_dir:
                return None                          # not in the folder when the pass listed it
            data = self._cache.get(e.md5) if not e.native else None
            if data is not None:
                self.cache_hits += 1
                return data.decode("utf-8", errors="replace")
        return self._cat(rel)

    def read_fresh(self, rel: str) -> str | None:
        self._guard(rel)
        return self._cat(rel)

    def _cat(self, rel: str) -> str | None:
        try:
            data = self._run(["cat", self._r(rel)], raw=True)
        except StoreError as e:
            if getattr(e, "code", None) in (3, 4):
                self._snap_forget(rel)
                return None
            raise
        if self._snap is not None:
            e = self._snap_entry(rel)
            if e is None or not e.native:             # what was read is what the folder holds now
                self._snap_file(rel, self._cache.put(data), len(data), mtime=e.mtime if e else None)
        return data.decode("utf-8", errors="replace")

    def put_file(self, local, rel: str) -> None:
        self._guard(rel)
        self._run(["copyto", str(local), self._r(rel)])
        if self._snap is not None:
            h, size = hashlib.md5(), 0
            with open(local, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
                    size += len(chunk)
            self._snap_file(rel, h.hexdigest(), size)

    def write(self, rel: str, text: str) -> None:
        self._guard(rel)
        data = text.encode("utf-8")
        if len(data) <= self.SPOOL_OVER:
            self._run(["rcat", self._r(rel)], data=text)
        else:
            import tempfile
            fd, tmp = tempfile.mkstemp(prefix="collab-kit-", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
                self._run(["copyto", tmp, self._r(rel)])
            finally:
                os.unlink(tmp)
        if self._snap is not None:
            self._snap_file(rel, self._cache.put(data), len(data))

    def copy(self, src: str, dst: str) -> None:
        self._guard(src)
        if self.exists(dst):
            raise StoreError(f"copy would overwrite {dst}")
        self._run(["copyto", self._r(src), self._r(dst)])
        e = self._snap_entry(src)
        if self._snap is not None:
            self._snap_file(dst, e.md5 if e else None, e.size if e else 0, e.native if e else False)

    def move(self, src: str, dst: str) -> None:
        self._guard(src)
        if self.exists(dst):
            raise StoreError(f"move would overwrite {dst}")
        self._run(["moveto", self._r(src), self._r(dst)])
        e = self._snap_entry(src)
        if self._snap is not None:
            self._snap_forget(src)
            self._snap_file(dst, e.md5 if e else None, e.size if e else 0, e.native if e else False)

    def mkdir(self, rel: str) -> None:
        if self._snap is not None and rel.strip("/") in self._snap:
            check_rel(rel)
            return                                   # listed: the folder is there (rclone also makes parents itself)
        self._run(["mkdir", self._r(rel)])
        if self._snap is not None:
            self._snap_dirs(rel.strip("/"))


class SubStore(Store):
    """A view of another store rooted at a subfolder (a unit inside the Collab Kit folder)."""

    def __init__(self, base: Store, prefix: str):
        self.base = base
        self.prefix = prefix.strip("/")
        self.label = base.label

    def __repr__(self):
        return f"{self.base!r}/{self.prefix}"

    def _j(self, rel: str) -> str:
        check_rel(rel)
        return _join(self.prefix, rel)

    def list(self, rel=""):
        return self.base.list(self._j(rel))

    def read(self, rel):
        return self.base.read(self._j(rel))

    def write(self, rel, text):
        return self.base.write(self._j(rel), text)

    def copy(self, src, dst):
        return self.base.copy(self._j(src), self._j(dst))

    def move(self, src, dst):
        return self.base.move(self._j(src), self._j(dst))

    def mkdir(self, rel):
        return self.base.mkdir(self._j(rel))

    def duplicates(self, rel=""):
        f = getattr(self.base, "duplicates", None)
        return f(self._j(rel)) if f else []

    def put_file(self, local, rel):
        return self.base.put_file(local, self._j(rel))

    def md5s(self, rel=""):
        return self.base.md5s(self._j(rel))


def open_store(spec: str) -> Store:
    """'rclone:<remote:path>' or a local folder path."""
    if spec.startswith("rclone:"):
        return RcloneStore(spec[len("rclone:"):])
    return FolderStore(spec)

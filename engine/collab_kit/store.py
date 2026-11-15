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

import dataclasses
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

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


class StoreError(RuntimeError):
    pass


def check_rel(rel: str) -> str:
    """A store path is relative, uses forward slashes, and never climbs out (.., ., a drive, a root)."""
    if "\\" in rel or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel) or "\x00" in rel:
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
        return p.read_text(encoding="utf-8", errors="replace")

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
        shutil.copy2(self._resolve(src), d)

    def move(self, src: str, dst: str) -> None:
        d = self._p(dst)
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.exists():
            raise StoreError(f"move would overwrite {dst}")
        os.replace(self._resolve(src), d)

    def mkdir(self, rel: str) -> None:
        self._p(rel).mkdir(parents=True, exist_ok=True)


class RcloneStore(Store):
    """A cloud folder through rclone (e.g. remote 'gdrive:Collab Kit'), under the conditions of
    docs/rclone-intake.md: the pinned version only (rclone.lock), six commands only, argument lists
    (no shell), inherited RCLONE_* settings stripped, a dedicated config, fail closed on duplicate
    names, writes that keep the Drive file id (rcat, or copyto from a local file over 90 KiB)."""

    label = "rclone"
    SPOOL_OVER = 90 * 1024

    def __init__(self, remote: str, rclone: str = "rclone", config: str | None = None, check_version: bool = True):
        self.remote = remote.rstrip("/")
        self.rclone = rclone
        self.config = config or os.environ.get("COLLAB_KIT_RCLONE_CONFIG", "")
        self.flags = ["--ask-password=false", "--drive-import-formats", "", "--drive-use-trash=true"]
        if self.config:
            self.flags = ["--config", self.config, *self.flags]
        self._checked = not check_version

    def __repr__(self):
        return f"RcloneStore({self.remote})"

    def _r(self, rel: str) -> str:
        check_rel(rel)
        return f"{self.remote}/{rel}" if rel else self.remote

    def _env(self) -> dict:
        return {k: v for k, v in os.environ.items() if not k.startswith("RCLONE_")}

    def _check_version(self) -> None:
        if self._checked:
            return
        import tomllib
        want = tomllib.loads((Path(__file__).with_name("rclone.lock")).read_text(encoding="utf-8"))["version"]
        try:
            res = subprocess.run([self.rclone, "version"], capture_output=True, text=True, timeout=60, env=self._env())
        except FileNotFoundError:
            raise StoreError("rclone is not installed (see docs/rclone-intake.md)") from None
        first = (res.stdout.splitlines() or [""])[0].strip()
        if first != f"rclone {want}":
            raise StoreError(f"rclone must be {want} (rclone.lock); this is '{first[:60]}'")
        self._checked = True

    def _run(self, args: list[str], data: str | None = None) -> str:
        if args[0] not in ("lsjson", "cat", "rcat", "copyto", "moveto", "mkdir"):
            raise StoreError(f"rclone {args[0]} is not one of the commands Collab Kit uses")
        self._check_version()
        cmd = [self.rclone, *args, *self.flags]
        try:
            res = subprocess.run(cmd, input=data, capture_output=True, text=True, encoding="utf-8",
                                 timeout=300, env=self._env())
        except FileNotFoundError:
            raise StoreError("rclone is not installed (see docs/rclone-intake.md)") from None
        except subprocess.TimeoutExpired:
            raise StoreError(f"rclone timed out: {args[0]}") from None
        if res.returncode != 0:
            raise StoreError(f"rclone {args[0]} failed: {res.stderr.strip()[:400]}")
        return res.stdout

    def list(self, rel: str = "") -> list[Entry]:
        try:
            out = self._run(["lsjson", self._r(rel)])
        except StoreError as e:
            if "directory not found" in str(e).lower():
                return []
            raise
        items = json.loads(out or "[]")
        res: dict[str, Entry] = {}
        for it in items:
            size = int(it.get("Size") if it.get("Size") is not None else 0)
            # Google Docs, Sheets, Slides appear under an export name with size -1 (rclone docs).
            e = Entry(it["Name"], it["Name"], bool(it.get("IsDir")), 0.0, max(size, 0),
                      native=(not it.get("IsDir")) and size < 0)
            mod = it.get("ModTime")
            if mod:
                try:
                    import datetime as _dt
                    e.mtime = _dt.datetime.fromisoformat(mod.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    pass
            if e.name in res:
                raise StoreError(f"two items are named {_join(rel, e.name)}; heal the duplicate first")
            res[e.name] = e
        return sorted(res.values(), key=lambda e: e.name)

    def read(self, rel: str) -> str | None:
        e = self.entry(rel)
        if e is None or e.is_dir:
            return None
        if e.native:
            raise StoreError(f"{rel} is a Google-native file; Collab Kit never reads those")
        return self._run(["cat", self._r(rel)])

    def write(self, rel: str, text: str) -> None:
        if len(text.encode("utf-8")) <= self.SPOOL_OVER:
            self._run(["rcat", self._r(rel)], data=text)
            return
        import tempfile
        fd, tmp = tempfile.mkstemp(prefix="collab-kit-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            self._run(["copyto", tmp, self._r(rel)])
        finally:
            os.unlink(tmp)

    def copy(self, src: str, dst: str) -> None:
        if self.exists(dst):
            raise StoreError(f"copy would overwrite {dst}")
        self._run(["copyto", self._r(src), self._r(dst)])

    def move(self, src: str, dst: str) -> None:
        if self.exists(dst):
            raise StoreError(f"move would overwrite {dst}")
        self._run(["moveto", self._r(src), self._r(dst)])

    def mkdir(self, rel: str) -> None:
        self._run(["mkdir", self._r(rel)])


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


def open_store(spec: str) -> Store:
    """'rclone:<remote:path>' or a local folder path."""
    if spec.startswith("rclone:"):
        return RcloneStore(spec[len("rclone:"):])
    return FolderStore(spec)

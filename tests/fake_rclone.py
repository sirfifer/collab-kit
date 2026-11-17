#!/usr/bin/env python3
"""A stand-in for rclone in tests: maps "<remote>:<path>" onto the folder $FAKE_RCLONE_ROOT/<remote>/
and implements the six commands Collab Kit uses with rclone's output shapes. A file named
"*.gdoc-native" lists with Size -1 (how rclone shows a Google Doc); FAKE_RCLONE_DUP=<name> makes
lsjson list that name twice."""
import datetime
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ["FAKE_RCLONE_ROOT"])
args = [a for a in sys.argv[1:]]
if os.environ.get("RCLONE_CONFIG_PASS"):
    print("inherited RCLONE_ variable reached rclone", file=sys.stderr)
    sys.exit(9)
if args[:1] == ["version"]:
    print("rclone " + os.environ.get("FAKE_RCLONE_VERSION", "v1.76.0"))
    sys.exit(0)
cmd = args[0]
# drop values of flags that take one
clean, skip = [], False
for a in args[1:]:
    if skip:
        skip = False
        continue
    if a in ("--config", "--drive-import-formats", "--hash-type", "--include"):
        skip = True
        continue
    if a.startswith("--"):
        continue
    clean.append(a)


def local(p):
    if ":" in p and not p.startswith("/"):
        remote, path = p.split(":", 1)
        return ROOT / remote / path.lstrip("/")
    return Path(p)


try:
    if cmd == "lsjson" and "-R" in args:
        import re as _re
        d = local(clean[-1])
        inc = [args[i + 1] for i, a in enumerate(args) if a == "--include"]
        rx = [_re.compile("^" + _re.escape(g.lstrip("/")).replace(r"\*", "[^/]*") + "$") for g in inc]
        out = []
        for c in sorted(d.rglob("*")) if d.is_dir() else []:
            rel = c.relative_to(d).as_posix()
            if ("--files-only" in args and c.is_dir()) or (rx and not any(r.match(rel) for r in rx)):
                continue
            st = c.stat()
            out.append({"Path": rel, "Name": c.name, "Size": st.st_size, "IsDir": c.is_dir(),
                        "ModTime": datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%S.123456789Z")})
        print(json.dumps(out))
    elif cmd == "lsjson":
        d = local(clean[0])
        if not d.is_dir():
            print("ERROR : error listing: directory not found", file=sys.stderr)
            sys.exit(3)
        out = []
        for c in sorted(d.iterdir()):
            st = c.stat()
            size = -1 if c.name.endswith(".gdoc-native") else (0 if c.is_dir() else st.st_size)
            import hashlib
            h = {} if c.is_dir() or size < 0 else {"md5": hashlib.md5(c.read_bytes()).hexdigest()}
            out.append({"Path": c.name, "Name": c.name, "Size": size, "IsDir": c.is_dir(), "Hashes": h,
                        "ModTime": datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).isoformat(),
                        "MimeType": "inode/directory" if c.is_dir() else "text/markdown"})
        dup = os.environ.get("FAKE_RCLONE_DUP")
        out += [dict(o) for o in out if o["Name"] == dup]
        print(json.dumps(out))
    elif cmd == "cat":
        p = local(clean[0])
        if not p.is_file():
            print("ERROR : object not found", file=sys.stderr)
            sys.exit(4)
        sys.stdout.buffer.write(p.read_bytes())
    elif cmd == "rcat":
        p = local(clean[0])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(sys.stdin.buffer.read())
    elif cmd in ("copyto", "moveto"):
        s, d = local(clean[0]), local(clean[1])
        d.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copy2 if cmd == "copyto" else shutil.move)(s, d)
    elif cmd == "mkdir":
        local(clean[0]).mkdir(parents=True, exist_ok=True)
    else:
        print(f"unexpected command {cmd}", file=sys.stderr)
        sys.exit(2)
except FileNotFoundError as e:
    print(f"ERROR : object not found: {e}", file=sys.stderr)
    sys.exit(3)

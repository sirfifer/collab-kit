"""Scheduling the back end on a machine: launchd (macOS), systemd user timers (Linux), Task Scheduler
(Windows). One runner at a time is enforced by the lease, not by the scheduler.

Returns are event driven (DESIGN-0.5.md section 20): the job runs every minute, and on macOS also the
moment a file lands in an inbox of a synced copy of the folder (`watch`, launchd WatchPaths: a doorbell,
nothing is read through it). Each run first asks whether any inbox holds a return (`--if-waiting`, one
listing) and does the full pass only then, or when the hourly sweep is due.

macOS and Google Drive for desktop: a launchd job may not read ~/Library/CloudStorage unless the
program it starts has been given access, and no prompt may appear. With an rclone remote the back end
never reads that folder and none of this applies. With a Drive for desktop folder, the job runs
through the kit's collab-kit-runner (engine/launchd/), the one program to grant access to.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

LABEL = "org.collab-kit.backend"


TICK_SECONDS = 60


def command(kit: Path, config: Path, python: list[str] | None = None) -> list[str]:
    return [*(python or [sys.executable]), str(kit / "engine" / "ck.py"), "backend", "run", "--if-waiting",
            "--config", str(config)]


def watch_paths(watch: str | os.PathLike | None) -> list[str]:
    """The inboxes of a synced copy of the Collab Kit folder, for launchd to watch: the top level's and
    every project's that exists now (a project added later is caught by the minute tick until the
    back end is installed again)."""
    if not watch:
        return []
    root = Path(watch).expanduser()
    out = [root / "_returns"]
    try:
        out += sorted(p / "collab-kit" / "_returns" for p in (root / "projects").iterdir()
                      if (p / "collab-kit" / "_returns").is_dir())
    except OSError:
        pass
    return [str(p) for p in out]


def launchd_plist(kit: Path, config: Path, log_dir: Path, minutes: int, runner: Path | None,
                  label: str = LABEL, watch: list[str] | None = None) -> str:
    if runner:
        args = [str(runner), str(kit / "engine" / "backend.sh"), str(config)]
    else:
        args = command(kit, config)
    argx = "\n".join(f"    <string>{escape(a)}</string>" for a in args)
    watchx = ("  <key>WatchPaths</key>\n  <array>\n"
              + "".join(f"    <string>{escape(w)}</string>\n" for w in watch) + "  </array>\n") if watch else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{escape(label)}</string>
  <key>ProgramArguments</key>
  <array>
{argx}
  </array>
  <key>StartInterval</key><integer>{TICK_SECONDS}</integer>
{watchx}  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>LowPriorityIO</key><true/>
  <key>StandardOutPath</key><string>{escape(str(log_dir / "backend.log"))}</string>
  <key>StandardErrorPath</key><string>{escape(str(log_dir / "backend.log"))}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>COLLAB_KIT_PYTHON</key><string>{escape(sys.executable)}</string>
    <key>GIT_TERMINAL_PROMPT</key><string>0</string>
  </dict>
</dict>
</plist>
"""


def systemd_units(kit: Path, config: Path, minutes: int) -> dict[str, str]:
    cmd = " ".join(f'"{a}"' if " " in a else a for a in command(kit, config, ["/usr/bin/env", "python3"]))
    return {
        "collab-kit-backend.service": (
            "[Unit]\nDescription=Collab Kit back end (one pass)\n\n[Service]\nType=oneshot\n"
            f"ExecStart={cmd}\nNice=10\n"),
        "collab-kit-backend.timer": (
            "[Unit]\nDescription=Collab Kit back end: every minute, a full pass when a return waits or every "
            f"{minutes} minutes\n\n[Timer]\nOnBootSec=2min\nOnUnitActiveSec={TICK_SECONDS}s\nAccuracySec=10s\n\n"
            "[Install]\nWantedBy=timers.target\n"),
    }


def windows_command(kit: Path, config: Path, minutes: int) -> str:
    tr = f'"py -3 \\"{kit / "engine" / "ck.py"}\\" backend run --if-waiting --config \\"{config}\\""'
    return f'schtasks /Create /SC MINUTE /MO 1 /TN "Collab Kit back end" /TR {tr} /F'


def plan(kit: Path, config: Path, minutes: int, *, runner: Path | None = None, watch: list[str] | None = None) -> dict:
    """{platform, files: {path: text}, then: [commands to run]}"""
    if sys.platform == "darwin":
        agents = Path.home() / "Library" / "LaunchAgents"
        logs = Path.home() / "Library" / "Logs" / "collab-kit"
        plist = agents / f"{LABEL}.plist"
        return {"platform": "macOS (launchd)",
                "files": {str(plist): launchd_plist(kit, config, logs, minutes, runner, watch=watch)},
                "mkdir": [str(logs)],
                "then": [f"launchctl bootout gui/{os.getuid()}/{LABEL} 2>/dev/null; "
                         f"launchctl bootstrap gui/{os.getuid()} '{plist}'",
                         f"launchctl print gui/{os.getuid()}/{LABEL} | grep -E 'state|last exit'"]}
    if os.name == "nt":
        return {"platform": "Windows (Task Scheduler)", "files": {}, "mkdir": [],
                "then": [windows_command(kit, config, minutes)]}
    units = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "systemd" / "user"
    return {"platform": "Linux (systemd user timer)",
            "files": {str(units / k): v for k, v in systemd_units(kit, config, minutes).items()},
            "mkdir": [],
            "then": ["systemctl --user daemon-reload",
                     "systemctl --user enable --now collab-kit-backend.timer",
                     "loginctl enable-linger $USER   # so it runs without a login session"]}

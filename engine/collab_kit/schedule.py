"""Scheduling the back end on a machine: launchd (macOS), systemd user timers (Linux), Task Scheduler
(Windows). One runner at a time is enforced by the lease, not by the scheduler.

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


def command(kit: Path, config: Path, python: list[str] | None = None) -> list[str]:
    return [*(python or [sys.executable]), str(kit / "engine" / "ck.py"), "backend", "run", "--config", str(config)]


def launchd_plist(kit: Path, config: Path, log_dir: Path, minutes: int, runner: Path | None,
                  label: str = LABEL) -> str:
    if runner:
        args = [str(runner), str(kit / "engine" / "backend.sh"), str(config)]
    else:
        args = command(kit, config)
    argx = "\n".join(f"    <string>{escape(a)}</string>" for a in args)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{escape(label)}</string>
  <key>ProgramArguments</key>
  <array>
{argx}
  </array>
  <key>StartInterval</key><integer>{minutes * 60}</integer>
  <key>RunAtLoad</key><true/>
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
            "[Unit]\nDescription=Collab Kit back end, every "
            f"{minutes} minutes\n\n[Timer]\nOnBootSec=5min\nOnUnitActiveSec={minutes}min\n\n"
            "[Install]\nWantedBy=timers.target\n"),
    }


def windows_command(kit: Path, config: Path, minutes: int) -> str:
    tr = f'"py -3 \\"{kit / "engine" / "ck.py"}\\" backend run --config \\"{config}\\""'
    return f'schtasks /Create /SC MINUTE /MO {minutes} /TN "Collab Kit back end" /TR {tr} /F'


def plan(kit: Path, config: Path, minutes: int, *, runner: Path | None = None) -> dict:
    """{platform, files: {path: text}, then: [commands to run]}"""
    if sys.platform == "darwin":
        agents = Path.home() / "Library" / "LaunchAgents"
        logs = Path.home() / "Library" / "Logs" / "collab-kit"
        plist = agents / f"{LABEL}.plist"
        return {"platform": "macOS (launchd)",
                "files": {str(plist): launchd_plist(kit, config, logs, minutes, runner)},
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

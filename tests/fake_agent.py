"""A stand-in for an agent command, for the dispatcher's tests: it reads the task on standard input
and does what its first argument says, in the folder it was started in. No test starts a real agent.

    commit    write a file and commit it
    nothing   end normally, leaving nothing
    fail      end with exit 3
    sleep     never end (the time limit stops it)
    break     commit a file the project's check refuses
"""
import subprocess
import sys
import time
from pathlib import Path

mode = sys.argv[1]
task = sys.stdin.read()
Path("task-seen.txt").write_text(task, encoding="utf-8") if mode == "commit" else None
ID = ["-c", "user.name=fake agent", "-c", "user.email=fake@example.invalid", "-c", "commit.gpgsign=false"]


def commit(name, text):
    Path(name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", *ID, "commit", "-q", "-m", f"add {name}"], check=True)


if mode == "commit":
    commit("drip.md", "two lines, one per bed\n")
elif mode == "break":
    commit("broken.flag", "x\n")
elif mode == "fail":
    sys.exit(3)
elif mode == "sleep":
    time.sleep(600)

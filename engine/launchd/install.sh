#!/bin/bash
# install.sh: schedule tools/kb/nightly.sh as two per-user launchd agents (no root needed). Part of
# Collab Kit: labels, times, and paths come from tools/kb/config.toml ([project].slug,
# [schedule]).
#
#   <label_prefix>.<slug>-kb-nightly   daily at [schedule].nightly: the full run (a missed run
#                                      happens at next wake)
#   <label_prefix>.<slug>-kb-returns   every [schedule].returns_every_minutes: nightly.sh
#                                      --returns-only, which exits silently unless a conversation's
#                                      returns are waiting and have settled
#
#   tools/kb/launchd/install.sh            show what would be installed (changes nothing)
#   tools/kb/launchd/install.sh --apply    install and load both, then --probe
#   tools/kb/launchd/install.sh --probe    run nightly.sh --probe once from inside launchd: can a
#                                          scheduled job read the mirror folder? (a transient job,
#                                          removed afterwards)
#   tools/kb/launchd/install.sh --remove   unload both and move the plists to the state folder
#
# It runs the copy of nightly.sh in the MAIN checkout, so merge the knowledge base first.
#
# The jobs run through collab-kit-runner (built here from collab-kit-runner.c into
# ~/.local/share/collab-kit/, once; rebuilt only when its source changes). On macOS a job launchd
# starts may not read Google Drive's folder until its program has Full Disk Access; the runner is the
# program to grant, so that /bin/bash never needs it. README: "Scheduled jobs and Google Drive".
set -euo pipefail
REPO="${KB_REPO:-$(cd "$(dirname "$0")/../../.." && pwd)}"
SCRIPT="$REPO/tools/kb/nightly.sh"
[ -f "$REPO/tools/kb/kb.py" ] || { echo "no tools/kb/kb.py under $REPO"; exit 1; }
eval "$(python3 "$REPO/tools/kb/kb.py" config --shell)"
STATE="${KB_STATE_DIR:-$KB_STATE_DEFAULT}"
NIGHTLY="$KB_LABEL_PREFIX.$KB_SLUG-kb-nightly"
RETURNS="$KB_LABEL_PREFIX.$KB_SLUG-kb-returns"
LABELS="$NIGHTLY $RETURNS"
DOMAIN="gui/$(id -u)"
PROBE_LABEL="$KB_LABEL_PREFIX.$KB_SLUG-kb-probe"
RUNNER="${KB_RUNNER:-$HOME/.local/share/collab-kit/collab-kit-runner}"
RUNNER_SRC="$REPO/tools/kb/launchd/collab-kit-runner.c"
plist_of() { echo "${KB_LAUNCH_AGENTS:-$HOME/Library/LaunchAgents}/$1.plist"; }

build_runner() {  # build the runner if it is missing or its source changed; never otherwise
  local want have tmp
  want="$(shasum -a 256 "$RUNNER_SRC" | cut -c1-64)"
  have="$(cat "$RUNNER.source-sha256" 2>/dev/null || true)"
  [ -x "$RUNNER" ] && [ "$want" = "$have" ] && return 0
  command -v cc >/dev/null || { echo "cannot build $RUNNER: no C compiler (xcode-select --install)"; return 1; }
  mkdir -p "$(dirname "$RUNNER")"; tmp="$RUNNER.new.$$"
  cc -O2 -Wall -o "$tmp" "$RUNNER_SRC" && codesign -s - -i org.collab-kit.runner -f "$tmp" 2>/dev/null \
    || { rm -f "$tmp"; echo "could not build $RUNNER"; return 1; }
  mv "$tmp" "$RUNNER"; echo "$want" > "$RUNNER.source-sha256"
  if [ -n "$have" ]; then
    echo "rebuilt $RUNNER (its source changed): a Full Disk Access grant given to the old one no longer applies; give it again"
  else
    echo "built $RUNNER"
  fi
}
xml() { local s="$1"; s="${s//&/&amp;}"; s="${s//</&lt;}"; s="${s//>/&gt;}"; printf '%s' "$s"; }

render() {  # render <label>
  local label="$1" extra="" schedule
  if [ "$label" = "$RETURNS" ]; then
    extra="<string>--returns-only</string>"
    schedule="<key>StartInterval</key><integer>$KB_RETURNS_SECONDS</integer>"
  else
    schedule="<key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>$KB_NIGHTLY_HOUR</integer><key>Minute</key><integer>$KB_NIGHTLY_MINUTE</integer></dict>"
  fi
  cat <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array><string>$(xml "$RUNNER")</string><string>$(xml "$SCRIPT")</string>$extra</array>
  $schedule
  <key>StandardOutPath</key><string>$(xml "$STATE")/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$(xml "$STATE")/launchd.err.log</string>
  <key>EnvironmentVariables</key>
  <dict><key>KB_REPO</key><string>$(xml "$REPO")</string><key>KB_TRIGGER</key><string>launchd</string></dict>
  <key>LowPriorityIO</key><true/>
  <key>Nice</key><integer>10</integer>
</dict>
</plist>
PL
}

render_probe() {
  cat <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$PROBE_LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$(xml "$RUNNER")</string><string>$(xml "$SCRIPT")</string><string>--probe</string></array>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$(xml "$STATE")/probe.out</string>
  <key>StandardErrorPath</key><string>$(xml "$STATE")/probe.out</string>
  <key>EnvironmentVariables</key>
  <dict><key>KB_REPO</key><string>$(xml "$REPO")</string><key>KB_PROBE_TIMEOUT</key><string>$PROBE_WAIT</string></dict>
</dict>
</plist>
PL
}

PROBE_WAIT="${KB_PROBE_WAIT:-120}"
probe() {  # run nightly.sh --probe once as a launchd job, report, and remove the job
  local plist="$STATE/$PROBE_LABEL.plist" code="" i
  mkdir -p "$STATE"; rm -f "$STATE/probe.out"
  render_probe > "$plist"; plutil -lint "$plist" >/dev/null
  launchctl bootout "$DOMAIN/$PROBE_LABEL" 2>/dev/null || true
  echo "probe: starting nightly.sh --probe as a launchd job (up to ${PROBE_WAIT}s)."
  echo "  If macOS asks whether collab-kit-runner may access files managed by Google Drive, click Allow."
  launchctl bootstrap "$DOMAIN" "$plist"
  for i in $(seq 1 $(( PROBE_WAIT * 2 + 20 ))); do
    code="$(launchctl print "$DOMAIN/$PROBE_LABEL" 2>/dev/null | sed -n 's/^[[:space:]]*last exit code = \([0-9][0-9]*\).*/\1/p' | head -1)"
    [ -n "$code" ] && break
    sleep 0.5
  done
  launchctl bootout "$DOMAIN/$PROBE_LABEL" 2>/dev/null || true
  rm -f "$plist"
  launchctl print "$DOMAIN/$PROBE_LABEL" >/dev/null 2>&1 && echo "warning: the probe job $PROBE_LABEL is still loaded"
  sed 's/^/  launchd: /' "$STATE/probe.out" 2>/dev/null || true
  if [ "$code" = "0" ]; then
    echo "probe: OK. A job launchd starts can read the mirror folder."
    return 0
  fi
  echo "probe: FAILED (exit ${code:-unknown}). The scheduled jobs cannot read the mirror folder yet."
  if grep -q 'no answer from macOS' "$STATE/probe.out" 2>/dev/null; then
    echo "  macOS was waiting for an answer. If it asked whether collab-kit-runner may access files managed"
    echo "  by Google Drive, run this again and click Allow (the narrowest grant: Drive's files, this program)."
    echo "  If nothing asked, use Full Disk Access instead (below)."
  fi
  echo "  Full Disk Access: System Settings > Privacy & Security > Full Disk Access, click +, press"
  echo "  Cmd+Shift+G, paste $RUNNER and add it (switched on). Give it to this runner only,"
  echo "  never to /bin/bash or Terminal (that would cover every script). Then run --probe again."
  echo "  (Google Drive for desktop not running, or the account signed out, fails the same way.)"
  return 3
}

case "${1:-}" in
  --probe)
    [ -f "$SCRIPT" ] || { echo "not found: $SCRIPT"; exit 1; }
    build_runner
    probe
    ;;
  --apply)
    [ -f "$SCRIPT" ] || { echo "not found: $SCRIPT (merge the knowledge base into $KB_MAIN first)"; exit 1; }
    build_runner
    mkdir -p "$STATE" "$(dirname "$(plist_of x)")"
    for LABEL in $LABELS; do
      PLIST="$(plist_of "$LABEL")"
      render "$LABEL" > "$PLIST"
      plutil -lint "$PLIST" >/dev/null
      launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
      launchctl bootstrap "$DOMAIN" "$PLIST"
      # verify from outside: launchd knows the job and has the right program
      launchctl print "$DOMAIN/$LABEL" | grep -q "$SCRIPT" || { echo "FAILED: launchd does not show $LABEL"; exit 1; }
      echo "installed and loaded: $LABEL"
    done
    echo "Verify any time: launchctl print $DOMAIN/<label>"
    if [ "$KB_MIRROR_KIND" != "none" ]; then
      probe || { echo "The jobs are installed but will fail until that is fixed; each failure is logged and shown by install.py check."; exit 3; }
    fi
    ;;
  --remove)
    for LABEL in $LABELS; do
      PLIST="$(plist_of "$LABEL")"
      launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
      if [ -f "$PLIST" ]; then mkdir -p "$STATE"; mv "$PLIST" "$STATE/$LABEL.plist.removed-$(date +%Y%m%d)"; fi
      launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 && { echo "FAILED: $LABEL still loaded"; exit 1; }
      echo "removed: $LABEL (plist kept in $STATE)"
    done
    ;;
  "")
    for LABEL in $LABELS; do echo "Would write $(plist_of "$LABEL") and load it into $DOMAIN:"; echo; render "$LABEL"; echo; done
    echo "Run again with --apply to install."
    ;;
  *) echo "usage: $0 [--apply|--probe|--remove]"; exit 2 ;;
esac

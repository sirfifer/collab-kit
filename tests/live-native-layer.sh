#!/bin/bash
# Opt-in, live: the real Claude Code against a throwaway Collab Kit project (a few cents of usage).
# Proves what the unit tests cannot: that the session-start brief reaches the model, and that an
# agent doing ordinary work records it in Collab Kit without being asked.
#   tests/live-native-layer.sh [--model sonnet]
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${2:-sonnet}"
command -v claude >/dev/null || { echo "claude (Claude Code) is not installed"; exit 2; }
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
export COLLAB_KIT_CONFIG="$T/machine.toml" COLLAB_KIT_STATE="$T/state"
CLOUD="$T/Collab Kit"
mkdir -p "$CLOUD/projects/garden/collab-kit/"{_returns,agenda,knowledge,WIP} "$CLOUD/_returns" "$CLOUD/agenda"
printf '# garden\n' > "$CLOUD/projects/garden/collab-kit/00-START-HERE.md"
cat > "$CLOUD/projects/garden/collab-kit/agenda/W-007-choose-the-tomato-beds.md" <<'EOF'
+++
id = "W-007"
title = "Choose which beds get the tomatoes"
kind = "decision"
importance = 1
status = "in-progress"
due = ""
project = ""
+++

## What's needed
Sam decides which beds get the tomatoes. Decided so far: never the north beds (too much shade).

## Log
- 2026-11-14: north beds ruled out.
EOF
printf 'human = "Sam"\n[cloud]\nroot = "%s"\n' "$CLOUD" > "$COLLAB_KIT_CONFIG"
R="$T/garden"
mkdir -p "$R" && cd "$R"
git init -q -b main && git config user.email t@example.com && git config user.name T
printf '# Garden\n\nPlans for the garden.\n' > CLAUDE.md
printf 'Beds: north-1, north-2, south-1, south-2.\nTomatoes: (not yet assigned)\n' > beds.md
python3 "$KIT/install.py" project . --human Sam >/dev/null
git add -A && git commit -qm start
pass=0; fail=0
check() { if eval "$2"; then echo "  ok   $1"; pass=$((pass+1)); else echo "  FAIL $1"; fail=$((fail+1)); fi; }

echo "1. the brief reaches the model (no tools allowed)"
out1="$(echo "Without using any tools: which agenda item is in progress in this project? One sentence." \
  | claude -p --model "$MODEL" --max-turns 1 --disallowedTools "Bash,Edit,Write,Read" 2>&1 || true)"
echo "     > ${out1:0:300}"
check "the answer names W-007 or the tomato beds" 'grep -qiE "W-007|tomato" <<<"$out1"'

echo "2. ordinary work gets recorded without being asked"
out2="$(echo "Assign the tomatoes to south-1 and south-2 in beds.md." \
  | claude -p --model "$MODEL" --max-turns 12 \
    --allowedTools "Read,Edit,Write,Bash(tools/collab-kit/ck:*),Bash(sh tools/collab-kit/ck:*),Bash(git:*)" 2>&1 || true)"
echo "     > ${out2:0:300}"
check "beds.md was changed" 'grep -q "south-1" beds.md && ! grep -q "not yet assigned" beds.md'
check "the agent recorded it in Collab Kit (a return was filed)" '[ -s "$COLLAB_KIT_STATE/filed.jsonl" ]'
check "W-007 or status in the cloud folder reflects it" \
  'grep -rqiE "south" "$CLOUD/projects/garden/collab-kit/agenda" "$CLOUD/projects/garden/collab-kit/knowledge" 2>/dev/null'
check "the agent did not try to contradict a settled decision (no north beds)" '! grep -qiE "tomato.*north|north.*tomato" beds.md'

echo "PASS: $pass, FAIL: $fail"
[ "$fail" = 0 ]

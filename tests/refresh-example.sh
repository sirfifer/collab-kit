#!/bin/bash
# refresh-example.sh: rebuild examples/the-lighthouse/knowledge/ with this kit.
#
# The sample project keeps only what a project writes itself (docs/, tools/kb/config.toml and
# manifest.toml, and the knowledge entries: concepts, answers, agenda items, the capture, the
# response, the proposal). Everything else in knowledge/ is what the kit renders and builds from
# those. This installs the kit into a copy, builds, checks, and copies knowledge/ back.
# tests/dry-run-install.sh fails when the committed copy is not what this would produce.
#
#   kit/tests/refresh-example.sh [--check]     --check: compare only, change nothing
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
EX="$KIT/examples/the-lighthouse"
T="$(mktemp -d "${TMPDIR:-/tmp}/kit-example.XXXXXX")"; trap 'rm -rf "$T"' EXIT
P="$T/the-lighthouse"
mkdir "$P" && cp -R "$EX/." "$P/" && rm -f "$P/README.md" "$P/tools/kb/collection-codes.json"
git -C "$P" init -q -b main
git -C "$P" add -A && git -C "$P" -c user.name=example -c user.email=example@example.invalid commit -qm "the lighthouse"
python3 "$KIT/install.py" apply "$P" >/dev/null
(cd "$P" && python3 tools/kb/kb.py build >/dev/null && python3 tools/kb/kb.py check >/dev/null) \
  || { (cd "$P" && python3 tools/kb/kb.py check); echo "refresh-example: the sample does not pass check"; exit 1; }
if [ "${1:-}" = "--check" ]; then
  diff -r "$P/knowledge" "$EX/knowledge" >/dev/null || { diff -r "$P/knowledge" "$EX/knowledge" | head -20; exit 1; }
  cmp -s "$P/tools/kb/collection-codes.json" "$EX/tools/kb/collection-codes.json" || { echo "collection-codes.json differs"; exit 1; }
  echo "refresh-example: examples/the-lighthouse is current"
else
  rm -rf "$EX/knowledge" && cp -R "$P/knowledge" "$EX/knowledge"
  cp "$P/tools/kb/collection-codes.json" "$EX/tools/kb/collection-codes.json"
  echo "refresh-example: rebuilt examples/the-lighthouse/knowledge"
fi

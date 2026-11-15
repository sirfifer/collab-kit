#!/bin/bash
# Collab Kit back end, one pass: what launchd starts through collab-kit-runner on macOS when the
# Collab Kit folder is a Google Drive for desktop folder (see engine/collab_kit/schedule.py).
#   backend.sh <backend.toml>
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
py="${COLLAB_KIT_PYTHON:-$(command -v python3 || true)}"   # the plist names the interpreter install.py used
[ -n "$py" ] || { echo "collab-kit: python3 not found" >&2; exit 127; }
exec "$py" "$here/ck.py" backend run --config "$1"

#!/usr/bin/env bash
# AIRT demo — safe, offline, no target needed.
set -e
cd "$(dirname "$0")"
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "[x] Python 3 not found. Install it (macOS: brew install python3 · Debian/Ubuntu: sudo apt install python3)"
  exit 1
fi
echo
echo "AIRT demo — attacking the built-in offline simulator (no network, no API key)"
echo "-------------------------------------------------------------------------"
echo
"$PY" -m airt demo --mutate-all
echo
echo "Reports (.html/.json) are in: $(pwd)"

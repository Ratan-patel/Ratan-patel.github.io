#!/usr/bin/env bash
# AIRT web console on http://localhost:8765
set -e
cd "$(dirname "$0")"
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "[x] Python 3 not found."
  exit 1
fi
echo "AIRT web console → http://localhost:8765"
echo "Remote targets ENABLED — scan only systems you have written permission for."
echo "Ctrl-C to stop."
( sleep 2; (command -v xdg-open >/dev/null && xdg-open http://localhost:8765 >/dev/null 2>&1) \
          || (command -v open >/dev/null && open http://localhost:8765 >/dev/null 2>&1) ) &
exec "$PY" -m airt serve --port 8765 --allow-remote

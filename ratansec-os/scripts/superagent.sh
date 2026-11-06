#!/usr/bin/env bash
# RatanSec Super Agent v2 launcher
#   bash scripts/superagent.sh                 # live console on 127.0.0.1:8000
#   bash scripts/superagent.sh --demo          # offline fixture demo (no key/live traffic)
#   bash scripts/superagent.sh --host 0.0.0.0  # LAN/VPS (auth required; use HTTPS externally)
#   bash scripts/superagent.sh --cli           # mission CLI client
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"
MODE="server"
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2;;
    --host) HOST="$2"; shift 2;;
    --demo) export SUPERAGENT_DEMO_MODE=1; shift;;
    --cli) MODE="cli"; shift;;
    -h|--help) sed -n '2,7p' "$0"; exit 0;;
    *) echo "unknown option: $1"; exit 1;;
  esac
done
PY=python3
if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; fi
"$PY" -c "import fastapi, uvicorn" 2>/dev/null || {
  echo "▶ Python dependencies install…"
  "$PY" -m pip install -q -r superagent/requirements.txt
}
if [ "$MODE" = "cli" ]; then
  exec "$PY" -m superagent.cli --url "${SUPERAGENT_URL:-http://127.0.0.1:$PORT}" --token "${SUPERAGENT_API_TOKEN:-}"
fi
if [ "${SUPERAGENT_DEMO_MODE:-0}" != "1" ] && [ ! -f .env ]; then
  cp superagent/.env.example .env
  chmod 600 .env
  echo "ℹ .env banayi. APP_PASSWORD / SUPERAGENT_API_TOKEN aur provider key locally bharo."
fi
export HOST PORT
echo "▶ RatanSec Super Agent v2: http://$HOST:$PORT  (demo=${SUPERAGENT_DEMO_MODE:-0})"
exec "$PY" -m uvicorn superagent.webui:app --host "$HOST" --port "$PORT"

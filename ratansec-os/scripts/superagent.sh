#!/usr/bin/env bash
# RatanSec Super Agent — one-command launcher
#
#   bash scripts/superagent.sh                 # install deps + start server (port 8000)
#   bash scripts/superagent.sh --port 8080
#   bash scripts/superagent.sh --cli           # terminal client (server chalu hona chahiye)
#   bash scripts/superagent.sh --local-cli     # server ke bina, isi machine par agent
#   bash scripts/superagent.sh --tools full    # tools install karke phir server
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8000}"
MODE="server"
TOOLS=""

while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2;;
    --cli) MODE="cli"; shift;;
    --local-cli) MODE="local"; shift;;
    --tools) TOOLS="$2"; shift 2;;
    -h|--help) sed -n '2,12p' "$0"; exit 0;;
    *) echo "unknown option: $1"; exit 1;;
  esac
done

PY=python3
if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; fi
export PORT

if [ -n "$TOOLS" ]; then
  echo "▶ tools install ($TOOLS)…"
  bash scripts/install-agent-tools.sh "$TOOLS" || echo "⚠ kuch tools install nahi hue — baad me Arsenal tab se dekho"
fi

if [ "$MODE" = "cli" ] || [ "$MODE" = "local" ]; then
  if [ "$MODE" = "local" ]; then
    exec "$PY" -m superagent.cli --local
  fi
  URL="${SUPERAGENT_URL:-http://127.0.0.1:$PORT}"
  exec "$PY" -m superagent.cli --url "$URL" --token "${SUPERAGENT_API_TOKEN:-}"
fi

if [ ! -f .env ] && [ -f superagent/.env.example ]; then
  cp superagent/.env.example .env
  echo "ℹ .env banayi (superagent/.env.example se) — APP_PASSWORD, SUPERAGENT_API_KEY bharo."
fi

"$PY" -c "import fastapi, uvicorn" 2>/dev/null || {
  echo "▶ python deps install…"
  "$PY" -m pip install -q -r superagent/requirements.txt
}

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "▶ Super Agent: http://localhost:$PORT  ·  phone: http://${IP:-<server-ip>}:$PORT/mobile"
exec "$PY" -m uvicorn superagent.webui:app --host 0.0.0.0 --port "$PORT"

#!/usr/bin/env bash
# RatanSec OS — server start karo
#   ./start.sh            → dashboard localhost par
#   Ctrl + C              → band
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  printf '\033[33mPehle setup chalao:\033[0m  ./setup.sh\n'
  exit 1
fi

# .env load karo (comment lines skip)
set -a
while IFS= read -r line; do
  case "$line" in ''|'#'*) continue ;; esac
  export "$(printf '%s' "$line" | sed 's/[[:space:]]*$//')" 2>/dev/null || true
done < .env
set +a

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then PY="python3"; fi
if ! "$PY" -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
  printf '\033[31mDependencies missing.\033[0m  ./setup.sh chalao (ek baar ka kaam hai).\n'
  exit 1
fi

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
DATA_DIR="${DATA_DIR:-./data}"
mkdir -p "$DATA_DIR/reports"

LAN_IP="$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -vE '^(169\.254\.|127\.|::)' | head -1)"
if [ -z "$LAN_IP" ] && command -v ipconfig >/dev/null 2>&1; then
  LAN_IP="$(ipconfig 2>/dev/null | grep -A2 'Wireless\|Ethernet' | grep -oE '192\.168\.[0-9]+\.[0-9]+' | head -1 || true)"
fi

C=$'\033[36m'; B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; D=$'\033[2m'; N=$'\033[0m'
printf '\n%s╔══════════════════════════════════════════════════════╗%s\n' "$C" "$N"
printf '%s║%s   %sRatanSec OS%s — server start ho raha hai…              %s║%s\n' "$C" "$N" "$B" "$N" "$C" "$N"
printf '%s╚══════════════════════════════════════════════════════╝%s\n\n' "$C" "$N"
printf '   %sDashboard (iss machine par):%s  http://localhost:%s\n' "$G" "$N" "$PORT"
if [ -n "$LAN_IP" ]; then
  printf '   %sPhone / dusre device se:%s      http://%s:%s  %s(same WiFi)%s\n' "$G" "$N" "$LAN_IP" "$PORT" "$D" "$N"
fi
if [ -n "${APP_PASSWORD:-}" ]; then
  printf '   %sPassword:%s                       %s\n' "$G" "$N" "$APP_PASSWORD"
else
  printf '   %s⚠ Password set nahi hai — koi bhi access kar sakta hai (lab/sirf localhost ke liye theek).%s\n' "$Y" "$N"
fi
printf '   %sBand karne ke liye:%s               Ctrl + C\n\n' "$D" "$N"

exec env HOST="$HOST" PORT="$PORT" DATA_DIR="$DATA_DIR" "$PY" -m app.webui

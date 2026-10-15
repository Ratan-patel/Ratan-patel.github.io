#!/usr/bin/env bash
# GitHub Codespaces ke liye auto-start (postStartCommand isko chalata hai).
# Kuch install nahi karna padta — browser me VS Code khulta hai aur dashboard ready hota hai.
set -uo pipefail
cd "$(dirname "$0")/.."   # → ratansec-os/

CY=$'\033[36m'; BOLD=$'\033[1m'; GRN=$'\033[32m'; DIM=$'\033[2m'; N=$'\033[0m'

# 1) .env nahi hai to banao (random password ke saath)
if [ ! -f .env ]; then
  bash setup.sh --no-tools --no-start >/tmp/ratansec-setup.log 2>&1 || true
fi
mkdir -p data/reports

# 2) purana server band karo (agar chal raha ho)
pkill -f "app.webui" >/dev/null 2>&1 || true
sleep 1

# 3) server background me start karo
nohup bash start.sh >/tmp/ratansec.log 2>&1 &
sleep 4

PASS="$(grep -E '^APP_PASSWORD=' .env 2>/dev/null | cut -d= -f2-)"
if grep -qE '^OPENROUTER_API_KEY=.+' .env 2>/dev/null; then
  AI="${GRN}ON${N}"
else
  AI="OFF — key add karne ke liye: nano .env  →  OPENROUTER_API_KEY=sk-or-v1-..."
fi

printf '\n'
printf '  %s╔══════════════════════════════════════════════════════════╗%s\n' "$CY" "$N"
printf '  %s║%s  %sRatanSec OS READY%s — dashboard chal raha hai             %s║%s\n' "$CY" "$N" "$BOLD" "$N" "$CY" "$N"
printf '  %s╚══════════════════════════════════════════════════════════╝%s\n' "$CY" "$N"
printf '   %sDashboard:%s  Ports tab → port 8000 ke aage globe icon par click karo\n' "$GRN" "$N"
printf '   %sPassword:%s   %s\n' "$GRN" "$N" "${PASS:-(khaali — auth off)}"
printf '   %sAI:%s         %s\n' "$GRN" "$N" "$AI"
printf '   %sLog:%s        /tmp/ratansec.log      %sBand karne ke liye:%s pkill -f app.webui\n\n' "$DIM" "$N" "$DIM" "$N"

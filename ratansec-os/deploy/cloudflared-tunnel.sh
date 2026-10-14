#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  RatanSec OS — Free public HTTPS URL (bina domain, bina port kholne)
#
#  Cloudflare Tunnel ("quick tunnel") — VM par port kholne ki zarurat nahi,
#  aur public internet par ek HTTPS URL mil jaata hai: https://xxxx.trycloudflare.com
#
#  ⚠️ Quick tunnel ka URL har restart par BADAL jata hai. Permanent URL chahiye
#     to apna domain Cloudflare se jodo (named tunnel) — docs: ratansec-os/VPS_DEPLOY.md
#
#  Chalao:  bash ratansec-os/deploy/cloudflared-tunnel.sh [PORT]
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

PORT="${1:-8000}"
B=$'\033[1m'; C=$'\033[36m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'
step() { printf '\n%s▶ %s%s\n' "$B" "$*" "$N"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
warn() { printf '  %s⚠%s %s\n' "$Y" "$N" "$*"; }
bad()  { printf '  %s✗%s %s\n' "$R" "$N" "$*"; }

SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo"

step "Cloudflared check"
if ! command -v cloudflared >/dev/null 2>&1; then
  ARCH="$(uname -m)"
  case "$ARCH" in
    x86_64|amd64) DEB="cloudflared-linux-amd64.deb" ;;
    aarch64|arm64) DEB="cloudflared-linux-arm64.deb" ;;
    *) bad "Is arch ($ARCH) ke liye auto-install nahi hai. Manual: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"; exit 1 ;;
  esac
  step "cloudflared install kar raha hoon ($DEB)"
  TMP_DEB="/tmp/$DEB"
  if curl -fsSL -o "$TMP_DEB" "https://github.com/cloudflare/cloudflared/releases/latest/download/$DEB"; then
    $SUDO dpkg -i "$TMP_DEB" >/dev/null 2>&1 || $SUDO apt-get install -y -f >/dev/null 2>&1 || true
    rm -f "$TMP_DEB"
    command -v cloudflared >/dev/null 2>&1 && ok "cloudflared install ho gaya" || { bad "install fail — manual try karo"; exit 1; }
  else
    bad "download fail (internet/GitHub access check karo)"; exit 1
  fi
else
  ok "cloudflared already installed: $(cloudflared --version 2>/dev/null | head -1)"
fi

step "Server check (localhost:$PORT)"
if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
  ok "RatanSec OS chal raha hai"
else
  warn "localhost:$PORT par server nahi mila — pehle chalu karo: ./start.sh  (ya: sudo systemctl start ratansecos)"
  warn "Phir bhi tunnel try kar raha hoon…"
fi

printf '\n%s▶ Public HTTPS URL banaya ja raha hai…%s\n' "$B" "$N"
printf '%s   Neeche "https://xxxxx-xxxx.trycloudflare.com" wali line aayegi — WAHI tumhara public URL hai.%s\n' "$Y" "$N"
printf '%s   Band karne ke liye: Ctrl + C   ·   Har restart par URL badalta hai.%s\n\n' "$Y" "$N"

exec cloudflared tunnel --url "http://127.0.0.1:$PORT" --no-autoupdate

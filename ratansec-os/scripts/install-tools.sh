#!/usr/bin/env bash
# RatanSec OS — security tools install karne ka helper (best-effort)
#   bash scripts/install-tools.sh
# Kali / Ubuntu / Debian / WSL → apt-get
# Termux (Android phone)       → pkg
set -uo pipefail

B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; D=$'\033[2m'; N=$'\033[0m'
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
warn() { printf '  %s⚠%s %s\n' "$Y" "$N" "$*"; }
bad()  { printf '  %s✗%s %s\n' "$R" "$N" "$*"; }

SUDO=""
if [ "$(id -u)" != "0" ] && command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi

printf '%s▶ Tools install kar raha hoon%s %s(root/sudo lagega)%s\n' "$B" "$N" "$D" "$N"

if command -v apt-get >/dev/null 2>&1 && [ "$(uname -o 2>/dev/null || echo Linux)" != "Android" ]; then
  # Kali / Ubuntu / Debian / WSL
  $SUDO apt-get update -qq || warn "apt-get update fail — purane index se try kar raha hoon"
  $SUDO apt-get install -y --no-install-recommends \
      nmap nikto whatweb sqlmap hydra whois dnsutils curl netcat-openbsd dirb \
    || warn "kuch packages install nahi hue (repos me naam alag ho sakta hai)"
  $SUDO apt-get install -y --no-install-recommends gobuster ffuf \
    || warn "gobuster/ffuf skip (Ubuntu purana ho sakta hai — baaki tools chalenge)"
  $SUDO apt-get install -y --no-install-recommends nuclei 2>/dev/null \
    || warn "nuclei apt me nahi mila (optional hai)"
elif command -v pkg >/dev/null 2>&1; then
  # Termux (phone)
  pkg update -y >/dev/null 2>&1 || true
  for package in nmap curl whois dnsutils git python; do
    pkg install -y "$package" >/dev/null 2>&1 && ok "$package" || warn "$package skip (Termux me nahi mila)"
  done
else
  bad "apt/pkg nahi mila — tools manually install karo (README → section 15 Troubleshooting)"
fi

printf '\n%s▶ Final check%s\n' "$B" "$N"
MISSING=""
for bin in nmap nikto whatweb gobuster ffuf nuclei sqlmap hydra whois dig curl; do
  if command -v "$bin" >/dev/null 2>&1; then
    ok "$bin"
  else
    MISSING="$MISSING $bin"
  fi
done
if [ -n "$MISSING" ]; then
  warn "Ye abhi bhi missing hain:${MISSING}"
  printf '  %sApp inke bina bhi chalta hai — un tools wale steps sirf "skipped" dikhenge.%s\n' "$D" "$N"
else
  printf '  %sSab tools ready! 🎉%s\n' "$G" "$N"
fi

#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  RatanSec OS — one-command setup (Hinglish)
#
#  Chalane ka tarika:      ./setup.sh
#  Options:
#     --with-tools         security tools bhi install karo (apt/pkg, sudo lagega)
#     --no-tools           tools skip karo (jaldi setup)
#     --no-start           sirf setup karo, server start mat karo
#     --port 8000          server port
#     --password "xyz"     dashboard password (na do to random generate hoga)
#     --key sk-or-v1-...   OpenRouter API key (AI chat ke liye)
# ═══════════════════════════════════════════════════════════════════
set -uo pipefail
cd "$(dirname "$0")"

PORT=8000
DO_TOOLS="ask"      # ask | yes | no
DO_START=1
PASSWORD=""
APIKEY=""
MODEL="openai/gpt-4o-mini"
BINS="nmap nikto whatweb gobuster ffuf nuclei sqlmap hydra whois dig curl"

B=$'\033[1m'; C=$'\033[36m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; D=$'\033[2m'; N=$'\033[0m'
say()  { printf '%s\n' "$*"; }
step() { printf '\n%s▶ %s%s\n' "$B" "$*" "$N"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
warn() { printf '  %s⚠%s %s\n' "$Y" "$N" "$*"; }
bad()  { printf '  %s✗%s %s\n' "$R" "$N" "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --with-tools) DO_TOOLS=yes ;;
    --no-tools)   DO_TOOLS=no ;;
    --no-start)   DO_START=0 ;;
    --port)       PORT="${2:-8000}"; shift ;;
    --password)   PASSWORD="${2:-}"; shift ;;
    --key)        APIKEY="${2:-}"; shift ;;
    --model)      MODEL="${2:-openai/gpt-4o-mini}"; shift ;;
    -h|--help)    sed -n '2,15p' "$0"; exit 0 ;;
    *) bad "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

say ""
say "${C}╔══════════════════════════════════════════════════════╗${N}"
say "${C}║${N}   ${B}RatanSec OS${N} — setup (Kali tools + AI copilot)      ${C}║${N}"
say "${C}╚══════════════════════════════════════════════════════╝${N}"
say "${D}   Sirf authorized security testing ke liye.${N}"

# ── 1) Python check ────────────────────────────────────────────────
step "Python check kar raha hoon"
if ! command -v python3 >/dev/null 2>&1; then
  bad "python3 nahi mila. Install karo:"
  say "     Kali/Ubuntu/Debian : sudo apt install -y python3 python3-venv python3-pip"
  say "     Termux (phone)     : pkg install -y python"
  exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'; then
  bad "Python 3.9+ chahiye. Aapka: $(python3 -V 2>&1)"
  exit 1
fi
ok "$(python3 -V 2>&1)"

# ── 2) Dependencies (venv) ─────────────────────────────────────────
step "Dependencies install kar raha hoon (ek baar ka kaam, ~30 sec)"
if [ ! -x .venv/bin/python ]; then
  if ! python3 -m venv .venv; then
    bad "venv nahi bana. Ye package install karo: sudo apt install -y python3-venv"
    exit 1
  fi
  ok "virtual environment banaya (.venv)"
else
  ok "purana .venv mila — reuse kar raha hoon"
fi
.venv/bin/pip install -q --upgrade pip >/dev/null 2>&1 || true
if .venv/bin/pip install -q -r requirements.txt; then
  ok "fastapi + uvicorn + pydantic ready"
else
  bad "pip install fail hua. Internet check karo, phir dobara: ./setup.sh"
  exit 1
fi

# ── 3) Security tools (optional) ───────────────────────────────────
step "Kali security tools check kar raha hoon"
MISSING=""
for bin in $BINS; do command -v "$bin" >/dev/null 2>&1 || MISSING="$MISSING $bin"; done
if [ -z "$MISSING" ]; then
  ok "saare tools already installed hain 🎉"
else
  warn "ye tools missing hain:${MISSING}"
  say "  ${D}(App inke bina bhi chalega — missing tools sirf 'skipped' dikhenge. Docker image me sab pre-installed hote hain.)${N}"

  INSTALL_TOOLS=0
  if [ "$DO_TOOLS" = "yes" ]; then
    INSTALL_TOOLS=1
  elif [ "$DO_TOOLS" = "ask" ] && [ -t 0 ]; then
    printf '  Tools install karun? (sudo password lagega) [y/N] '
    read -r answer </dev/tty || answer="n"
    case "$answer" in y|Y|yes|YES) INSTALL_TOOLS=1 ;; esac
  fi

  if [ "$INSTALL_TOOLS" = "1" ]; then
    bash scripts/install-tools.sh
  else
    say "  ${D}Skip kiya. Baad me kabhi bhi: bash scripts/install-tools.sh${N}"
  fi
fi

# ── 4) .env (password + AI key) ────────────────────────────────────
step "Configuration (.env) set kar raha hoon"
if [ -f .env ]; then
  ok ".env pehle se hai — usko waisa hi chhod diya"
  say "  ${D}Badalna ho to: nano .env  (phir ./start.sh)${N}"
else
  [ -n "$PASSWORD" ] || PASSWORD="$(python3 -c 'import secrets;print(secrets.token_urlsafe(9))')"
  if [ -z "$APIKEY" ]; then
    APIKEY=""
    warn "OpenRouter API key nahi di — AI chat abhi off rahega (scans/reports chalenge)"
    say "  ${D}Baad me key add karna: nano .env → OPENROUTER_API_KEY=sk-or-v1-...${N}"
  fi
  cat > .env <<EOF
# RatanSec OS config (setup.sh ne banayi)
APP_PASSWORD=${PASSWORD}
OPENROUTER_API_KEY=${APIKEY}
MODEL=${MODEL}
ALLOWED_TARGETS=
ALLOW_ANY_TARGET=1
ALLOW_LOCAL_TARGETS=1
ALLOW_SCOPE_OVERRIDE=0
APPROVAL_MODE=
MAX_SCAN_SECONDS=420
MAX_CONCURRENT_SCANS=2
ALLOW_INSTALL=0
HOST=0.0.0.0
PORT=${PORT}
DATA_DIR=./data
LOG_LEVEL=info
EOF
  chmod 600 .env
  ok ".env bana diya (password generate kiya)"
fi

# ── 5) Summary ─────────────────────────────────────────────────────
step "Ready!"
say "  Dashboard password : ${B}$(grep -E '^APP_PASSWORD=' .env | cut -d= -f2- | sed 's/^$/(khaali — auth off)/')${N}"
say "  AI status          : $(grep -qE '^OPENROUTER_API_KEY=.+' .env && echo 'ON' || echo 'OFF (key add karo)')"
say "  Scope (allowlist)  : $(grep -E '^ALLOWED_TARGETS=' .env | cut -d= -f2- | sed 's/^$/(khaali — har scan manual approval)/')"
say ""
say "  ${D}Normal use: ./start.sh   → browser me dashboard khulega${N}"

if [ "$DO_START" = "1" ]; then
  step "Server start kar raha hoon (band karne ke liye Ctrl+C)"
  exec ./start.sh
fi

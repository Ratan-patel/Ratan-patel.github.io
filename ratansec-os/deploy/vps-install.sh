#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  RatanSec OS — VPS / Cloud VM installer (Ubuntu · Debian · Kali · ARM64)
#
#  Kisi bhi cloud VM par ek command me poora setup:
#     tools + Python env + .env + systemd service (24x7, auto-restart)
#
#  Chalao (repo ke andar se):
#     sudo bash ratansec-os/deploy/vps-install.sh --key sk-or-v1-XXXX \
#          --scope "tera-domain.com" --port 8000
#
#  Common flags:
#     --key KEY        OpenRouter API key (AI chat ke liye)
#     --password PASS  Dashboard password (na do to random generate hoga)
#     --scope LIST     ALLOWED_TARGETS, comma separated: "site.com,*.lab.in"
#     --port N         port (default 8000)
#     --model M        AI model (default openai/gpt-4o-mini)
#     --lite           1 GB RAM wale free VMs ke liye (kam tools, kam workers)
#     --no-service     systemd install na karo (container/Codespaces ke liye)
#     --skip-tools     apt se tools install na karo
#     --no-apt         apt-get update/install bilkul na chalao
#     --url-only       sirf install, start nahi
#
#  Uske baad:
#     ratansec status        # systemd status + health
#     ratansec logs -f       # live logs
#     ratansec restart       # restart
#     ratansec update        # code update + restart
#     ratansec password      # dashboard password dikhao
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

# ─── defaults ─────────────────────────────────────────────────────────
APP_DIR="/opt/ratansec-os"
DATA_DIR="/opt/ratansec-os/data"
SERVICE_NAME="ratansecos"
SERVICE_USER="ratansec"
PORT=8000
API_KEY=""
APP_PASSWORD=""
SCOPE=""
MODEL="openai/gpt-4o-mini"
MODE_FULL=1
SKIP_TOOLS=0
NO_APT=0
NO_SERVICE=0
URL_ONLY=0

# ─── colors / helpers ─────────────────────────────────────────────────
B=$'\033[1m'; C=$'\033[36m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; D=$'\033[2m'; N=$'\033[0m'
step() { printf '\n%s▶ %s%s\n' "$B" "$*" "$N"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
info() { printf '  %s·%s %s\n' "$C" "$N" "$*"; }
warn() { printf '  %s⚠%s %s\n' "$Y" "$N" "$*"; }
bad()  { printf '  %s✗%s %s\n' "$R" "$N" "$*"; }
die()  { bad "$*"; exit 1; }

# ─── args ─────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    --key)        API_KEY="${2:-}"; shift ;;
    --password)   APP_PASSWORD="${2:-}"; shift ;;
    --scope)      SCOPE="${2:-}"; shift ;;
    --port)       PORT="${2:-8000}"; shift ;;
    --model)      MODEL="${2:-openai/gpt-4o-mini}"; shift ;;
    --dir)        APP_DIR="${2:-$APP_DIR}"; DATA_DIR="${2:-$APP_DIR}/data"; shift ;;
    --lite)       MODE_FULL=0 ;;
    --skip-tools) SKIP_TOOLS=1 ;;
    --no-apt)     NO_APT=1; SKIP_TOOLS=1 ;;
    --no-service) NO_SERVICE=1 ;;
    --url-only)   URL_ONLY=1 ;;
    -h|--help)    sed -n '2,30p' "$0"; exit 0 ;;
    *) die "Unknown option: $1  (--help dekho)" ;;
  esac
  shift
done

SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # → ratansec-os/

printf '\n%s╔══════════════════════════════════════════════════════════════╗%s\n' "$C" "$N"
printf '%s║%s   %sRatanSec OS — VPS / Cloud VM installer%s                  %s║%s\n' "$C" "$N" "$B" "$N" "$C" "$N"
printf '%s╚══════════════════════════════════════════════════════════════╝%s\n' "$C" "$N"
info "source: $SOURCE_DIR"
info "install: $APP_DIR   port: $PORT   mode: $([ "$MODE_FULL" = 1 ] && echo full || echo lite)"

# ─── 1) root / sudo ───────────────────────────────────────────────────
step "1/8 Permissions check"
SUDO=""
if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
  ok "root"
elif command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
  ok "sudo available (sudo use karunga)"
  $SUDO -n true 2>/dev/null || warn "sudo password maangega — terminal me daal dena"
else
  die "Na root ho, na sudo hai. VM me root/sudo user se chalao (ya: su -)"
fi

# ─── 2) OS detect ─────────────────────────────────────────────────────
step "2/8 OS detect"
ARCH="$(uname -m)"
OS_NAME="$(. /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-unknown}" || echo unknown)"
info "OS: $OS_NAME · arch: $ARCH"
HAVE_APT=0
command -v apt-get >/dev/null 2>&1 && HAVE_APT=1
[ "$HAVE_APT" = 1 ] && ok "apt-based distro (Ubuntu/Debian/Kali) → packages install kar sakta hoon" \
                    || warn "apt nahi mila — tools manually install karne padenge (app phir bhi chalega)"
case "$ARCH" in
  aarch64|arm64) info "ARM64 VM (Oracle Ampere free tier waghera) — nmap/nikto/sqlmap sab chalte hain" ;;
  x86_64|amd64)  ok "x86_64" ;;
  *) warn "unknown arch ($ARCH) — kuch tools skip ho sakte hain" ;;
esac

# ─── 3) base packages + tools ─────────────────────────────────────────
if [ "$HAVE_APT" = 1 ] && [ "$SKIP_TOOLS" = 0 ]; then
  step "3/8 Base packages + security tools (2-5 min, internet chahiye)"
  export DEBIAN_FRONTEND=noninteractive
  $SUDO apt-get update -qq || warn "apt update fail — purane index se chala raha hoon"
  $SUDO apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip ca-certificates curl git \
      dnsutils whois netcat-openbsd nmap sqlmap whatweb nikto dirb \
    || warn "kuch base packages install nahi hue — aage badh raha hoon"
  if [ "$MODE_FULL" = 1 ]; then
    $SUDO apt-get install -y --no-install-recommends gobuster ffuf hydra \
      || warn "gobuster/ffuf/hydra skip (repo me nahi / ARM par missing)"
    $SUDO apt-get install -y --no-install-recommends nuclei 2>/dev/null \
      || warn "nuclei apt me nahi mila — dashboard ke Tools tab me manual install command milega"
  else
    info "lite mode: gobuster/ffuf/nuclei/hydra skip (RAM bachane ke liye)"
  fi
  $SUDO apt-get clean >/dev/null 2>&1 || true
  MISSING=""
  for bin in nmap curl python3; do command -v "$bin" >/dev/null 2>&1 || MISSING="$MISSING $bin"; done
  [ -z "$MISSING" ] && ok "core tools ready: nmap, curl, python3" || warn "missing:$MISSING"
else
  step "3/8 Tools install skip kiya"
  [ "$NO_APT" = 1 ] && info "--no-apt diya tha" || true
fi

# ─── 4) app files copy ────────────────────────────────────────────────
step "4/8 App files $APP_DIR me install kar raha hoon"
$SUDO mkdir -p "$APP_DIR" "$DATA_DIR/reports"
$SUDO cp -r "$SOURCE_DIR/app" "$APP_DIR/"
$SUDO cp "$SOURCE_DIR/requirements.txt" "$SOURCE_DIR/cli.py" "$APP_DIR/"
$SUDO mkdir -p "$APP_DIR/scripts" && $SUDO cp "$SOURCE_DIR"/scripts/*.sh "$APP_DIR/scripts/" 2>/dev/null || true
$SUDO chmod +x "$APP_DIR"/scripts/*.sh 2>/dev/null || true

# dedicated user (root me chalane se bacha jaye; nmap ke liye CAP_NET_RAW ambient)
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  $SUDO useradd -r -s /usr/sbin/nologin -d "$APP_DIR" "$SERVICE_USER" 2>/dev/null \
    || $SUDO adduser -r -s /sbin/nologin -D -h "$APP_DIR" "$SERVICE_USER" 2>/dev/null \
    || warn "service user nahi bana — root par chalega"
fi
$SUDO chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR" 2>/dev/null || true
ok "files copied + ownership set ($SERVICE_USER)"

# ─── 5) Python venv ───────────────────────────────────────────────────
step "5/8 Python virtual environment"
if [ ! -x "$APP_DIR/.venv/bin/python" ] || [ "$SKIP_TOOLS" = 1 ]; then
  $SUDO python3 -m venv "$APP_DIR/.venv" || die "venv nahi bana (apt install python3-venv karo)"
fi
$SUDO "$APP_DIR/.venv/bin/pip" install -q --upgrade pip 2>/dev/null || true
$SUDO "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt" || die "pip install fail — internet check karo"
$SUDO chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR/.venv" 2>/dev/null || true
ok "fastapi + uvicorn ready"

# ─── 6) .env (idempotent: purana password preserve) ───────────────────
step "6/8 Config (.env)"
ENV_FILE="$APP_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  EXISTING_PASS="$($SUDO grep -E '^APP_PASSWORD=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)"
  [ -n "$EXISTING_PASS" ] && [ -z "$APP_PASSWORD" ] && APP_PASSWORD="$EXISTING_PASS"
  info "purani .env mili — password aur data preserve kar raha hoon"
fi
if [ -z "$APP_PASSWORD" ]; then
  APP_PASSWORD="$(python3 -c 'import secrets;print(secrets.token_urlsafe(9))' 2>/dev/null || echo "ratansec-$PORT")"
fi
if [ -z "$API_KEY" ] && [ -f "$ENV_FILE" ]; then
  API_KEY="$($SUDO grep -E '^OPENROUTER_API_KEY=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)"
fi

WORKERS=2; [ "$MODE_FULL" = 0 ] && WORKERS=1
$SUDO tee "$ENV_FILE" >/dev/null <<EOF
# RatanSec OS — VPS config (vps-install.sh ne banayi)
APP_PASSWORD=${APP_PASSWORD}
OPENROUTER_API_KEY=${API_KEY}
MODEL=${MODEL}
ALLOWED_TARGETS=${SCOPE}
ALLOW_ANY_TARGET=1
ALLOW_LOCAL_TARGETS=1
ALLOW_SCOPE_OVERRIDE=0
APPROVAL_MODE=
MAX_SCAN_SECONDS=420
MAX_CONCURRENT_SCANS=${WORKERS}
ALLOW_INSTALL=0
HOST=0.0.0.0
PORT=${PORT}
DATA_DIR=${DATA_DIR}
LOG_LEVEL=info
EOF
$SUDO chmod 600 "$ENV_FILE"
$SUDO chown "$SERVICE_USER:$SERVICE_USER" "$ENV_FILE" 2>/dev/null || true
ok "password: $APP_PASSWORD"
[ -n "$API_KEY" ] && ok "AI key set (AI chat ON)" || warn "AI key nahi di — baad me: sudo nano $ENV_FILE → OPENROUTER_API_KEY=…, phir: ratansec restart"
[ -n "$SCOPE" ] && ok "scope: $SCOPE (in targets par scan auto-approve)" || warn "scope khaali — har scan par dashboard me Approve/Deny card aayega (safety default)"

# ─── 7) systemd service (24x7) ────────────────────────────────────────
if [ "$NO_SERVICE" = 0 ] && command -v systemctl >/dev/null 2>&1 && [ -d /etc/systemd/system ]; then
  step "7/8 systemd service ($SERVICE_NAME) — 24x7 auto-start"
  $SUDO tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=RatanSec OS — AI pentest environment
Documentation=https://github.com/Ratan-patel/Ratan-patel.github.io
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
# nmap ke raw scans (SYN) ke liye — warna app khud -sT connect scan use karta hai
AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN
NoNewPrivileges=false
ExecStart=${APP_DIR}/.venv/bin/python -m app.webui
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ratansec

[Install]
WantedBy=multi-user.target
EOF
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable "$SERVICE_NAME" >/dev/null 2>&1 || true
  $SUDO systemctl restart "$SERVICE_NAME"
  ok "service install + start ho gayi (VM reboot par bhi khud chalu hogi)"
else
  step "7/8 systemd skip (--no-service ya systemd nahi hai)"
  info "manual start: cd $APP_DIR && sudo DATA_DIR=$DATA_DIR PORT=$PORT .venv/bin/python -m app.webui"
fi

# ─── helper CLI: ratansec + update script ─────────────────────────────
$SUDO tee "$APP_DIR/.source" >/dev/null <<EOF
${SOURCE_DIR}
EOF
$SUDO tee "$APP_DIR/deploy-update.sh" >/dev/null <<EOF
#!/usr/bin/env bash
# Naya code laao (git pull) + restart. ratansec update se chalta hai.
set -euo pipefail
APP_DIR="${APP_DIR}"; SERVICE="${SERVICE_NAME}"; SRC="\$(cat ${APP_DIR}/.source 2>/dev/null || echo '')"
SUDO=""; [ "\$(id -u)" -eq 0 ] && SUDO="" || SUDO="sudo"
if [ -n "\$SRC" ] && [ -d "\$SRC/.git" ]; then
  echo "[update] git pull: \$SRC"
  git -C "\$SRC" pull --ff-only || echo "[update] git pull skip (local changes?)"
  echo "[update] files copy"
  \$SUDO cp -r "\$SRC/app" "\$APP_DIR/"
  \$SUDO cp "\$SRC/requirements.txt" "\$SRC/cli.py" "\$APP_DIR/"
  \$SUDO cp -r "\$SRC/scripts/." "\$APP_DIR/scripts/" 2>/dev/null || true
  \$SUDO "\$APP_DIR/.venv/bin/pip" install -q -r "\$APP_DIR/requirements.txt"
else
  echo "[update] source repo nahi mila — sirf restart kar raha hoon"
fi
\$SUDO systemctl restart "\$SERVICE" 2>/dev/null || echo "[update] systemd nahi hai — manual restart karo"
echo "[update] done ✓"
EOF
$SUDO chmod +x "$APP_DIR/deploy-update.sh"

if [ -n "$SUDO" ] || [ -w /usr/local/bin ]; then
  $SUDO tee /usr/local/bin/ratansec >/dev/null <<EOF
#!/usr/bin/env bash
# RatanSec OS helper
SVC=${SERVICE_NAME}; DIR=${APP_DIR}; PORT=${PORT}
case "\${1:-status}" in
  status)   systemctl status \$SVC --no-pager 2>/dev/null | head -12; echo; curl -s "http://127.0.0.1:\$PORT/api/health" && echo ;;
  logs)     shift; journalctl -u \$SVC -f --no-pager "\$@" ;;
  restart)  sudo systemctl restart \$SVC && echo "restarted" ;;
  stop)     sudo systemctl stop \$SVC && echo "stopped" ;;
  start)    sudo systemctl start \$SVC && echo "started" ;;
  password) grep -E '^APP_PASSWORD=' \$DIR/.env | cut -d= -f2- ;;
  url)      echo "http://\$(curl -s -m 5 ifconfig.me || echo SERVER_IP):\$PORT" ;;
  tools)    cd \$DIR && .venv/bin/python cli.py --url http://127.0.0.1:\$PORT --token "\$(grep -E '^APP_PASSWORD=' \$DIR/.env | cut -d= -f2-)" tools ;;
  update)   sudo bash \$DIR/deploy-update.sh ;;
  *) echo "Use: ratansec [status|logs|restart|stop|start|password|url|tools|update]" ;;
esac
EOF
  $SUDO chmod +x /usr/local/bin/ratansec 2>/dev/null || warn "helper CLI skip (permission)"
fi

# ─── 8) firewall + health check ───────────────────────────────────────
step "8/8 Firewall + health check"
if command -v ufw >/dev/null 2>&1 && $SUDO ufw status 2>/dev/null | grep -qi active; then
  $SUDO ufw allow "$PORT"/tcp >/dev/null 2>&1 && ok "ufw: port $PORT allow kar diya"
else
  info "ufw active nahi hai — cloud console ki 'Security List / Firewall rules' me port $PORT (TCP) allow karna zaroori hai"
fi

if [ "$URL_ONLY" = 0 ]; then
  printf '  '
  for i in $(seq 1 15); do
    sleep 2
    if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
      printf '\r'
      ok "server live hai (health OK)"
      break
    fi
    printf '%s' "."
    [ "$i" = 15 ] && { printf '\r'; warn "health check timeout — logs dekho: ratansec logs"; }
  done
fi

PUBLIC_IP="$(curl -s -m 5 ifconfig.me 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')"

printf '\n%s╔══════════════════════════════════════════════════════════════╗%s\n' "$G" "$N"
printf '%s║%s   %s✅ RatanSec OS INSTALL HO GAYA%s                             %s║%s\n' "$G" "$N" "$B" "$N" "$G" "$N"
printf '%s╚══════════════════════════════════════════════════════════════╝%s\n' "$G" "$N"
printf '   %sDashboard:%s  http://%s:%s\n' "$G" "$N" "${PUBLIC_IP:-<VM-IP>}" "$PORT"
printf '   %sPassword:%s   %s\n' "$G" "$N" "$APP_PASSWORD"
printf '   %sAI:%s         %s\n' "$G" "$N" "$([ -n "$API_KEY" ] && echo "ON ($MODEL)" || echo 'OFF — .env me key daalo')"
printf '   %sScope:%s      %s\n' "$G" "$N" "${SCOPE:-(khaali — manual approval mode)}"
printf '\n   %sCommands:%s\n' "$B" "$N"
printf '     ratansec status      # chal raha hai ya nahi + health\n'
printf '     ratansec logs -f     # live logs\n'
printf '     ratansec restart     # restart\n'
printf '     ratansec password    # password dikhao\n'
printf '     ratansec update      # naya code + restart\n'
printf '\n   %s⚠️  Dashboard khulne par: cloud console me port %s (TCP) inbound allow hona chahiye.%s\n' "$Y" "$PORT" "$N"
printf '   %s⚠️  Sirf authorized targets par scan karo.%s\n\n' "$Y" "$N"

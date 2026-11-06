#!/usr/bin/env bash
# RatanSec Super Agent — tool install script (Kali / Debian / Ubuntu / Termux)
#
#   bash scripts/install-agent-tools.sh            # core tools
#   bash scripts/install-agent-tools.sh full       # core + web/api + exploitation + cracking
#   bash scripts/install-agent-tools.sh catalog    # catalog ke saare apt packages (best effort)
#
# Phone (Termux): core profile chalta hai (nmap, sqlmap, hydra). Wireless/exploit
# frameworks phone par generally kaam nahi karte — unhe laptop/VPS par chalao.
set -uo pipefail

PROFILE="${1:-core}"
SUDO=""
if [ "$(id -u)" != "0" ] && command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi

log() { printf '\n\033[36m[superagent]\033[0m %s\n' "$*"; }

TERMUX=0
if [ -n "${PREFIX:-}" ] && [ -d "/data/data/com.termux" ]; then TERMUX=1; fi

if [ "$TERMUX" = "1" ]; then
  log "Termux detected — pkg se install kar raha hoon"
  pkg update -y || true
  pkg install -y python git nmap openssl curl ncurses-utils dnsutils whois 2>/dev/null || pkg install -y python git nmap openssl curl
  pip install --upgrade pip
  APT_INSTALL="pkg install -y"
else
  export DEBIAN_FRONTEND=noninteractive
  APT_INSTALL="$SUDO apt-get install -y --no-install-recommends"
  $SUDO apt-get update -y || true
fi

CORE=(whois dnsutils traceroute iputils-ping netcat-openbsd nmap nikto whatweb gobuster ffuf
      sqlmap hydra seclists ldap-utils socat jq openssl hashcat john cewl crunch exploitdb)

FULL=(masscan medusa ncrack smbclient smbmap enum4linux-ng snmp snmpcheck nbtscan nfs-common
      nfs-utils proxychains4 sslscan testssl.sh wafw00f dnsrecon fierce dmitry
      zaproxy wapiti commix feroxbuster dirsearch wpscan joomscan crunch cewl
      aircrack-ng wifite responder bettercap nuclei trivy semgrep gitleaks)

case "$PROFILE" in
  core)
    log "Core tools install: ${CORE[*]}"
    $APT_INSTALL "${CORE[@]}" || log "kuch packages fail hue — baaki chalte rahenge"
    ;;
  full)
    log "Full tools install (core + web/api + exploitation + cracking)"
    $APT_INSTALL "${CORE[@]}" || true
    $APT_INSTALL "${FULL[@]}" || true
    ;;
  catalog)
    log "Catalog ke saare apt packages (best effort)"
    $APT_INSTALL "${CORE[@]}" "${FULL[@]}" metasploit-framework beef-xss set routersploit impacket-scripts \
      ldapdomaindump 2>/dev/null || true
    ;;
  *)
    echo "usage: $0 [core|full|catalog]"; exit 1;;
esac

# Go / Python based tools (best effort, apt me na milne wale)
if [ "$TERMUX" = "0" ]; then
  log "Optional ekstra (best effort): go tools + python tools"
  command -v go >/dev/null 2>&1 && {
    go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest 2>/dev/null || true
    go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest 2>/dev/null || true
    go install -v github.com/projectdiscovery/katana/cmd/katana@latest 2>/dev/null || true
    go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest 2>/dev/null || true
    go install -v github.com/tomnomnom/waybackurls@latest 2>/dev/null || true
    go install -v github.com/tomnomnom/assetfinder@latest 2>/dev/null || true
  }
  $SUDO pip3 install --break-system-packages -q arjun hashid ldapdomaindump 2>/dev/null || \
    pip3 install -q arjun hashid 2>/dev/null || true
fi

log "Nuclei templates update (agar nuclei hai)"
command -v nuclei >/dev/null 2>&1 && nuclei -update-templates -silent 2>/dev/null || true

log "Python deps"
pip install -q -r "$(dirname "$0")/../superagent/requirements.txt" 2>/dev/null || \
  pip install -q fastapi 'uvicorn[standard]' pydantic

log "Kaunse tools ready hain:"
python3 - <<'PY' 2>/dev/null || true
import shutil, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else ".", ".."))
try:
    from superagent import catalog
except Exception:
    sys.exit(0)
ok = [t.name for t in catalog.TOOLS.values() if shutil.which(t.binary)]
missing = [t.name for t in catalog.TOOLS.values() if not shutil.which(t.binary)]
print(f"  installed : {len(ok)}/{catalog.TOTAL_TOOLS}")
print("  ready     : " + ", ".join(ok[:40]) + (" …" if len(ok) > 40 else ""))
print(f"  missing   : {len(missing)} (dashboard ke Arsenal tab me install hints dekho)")
PY

log "Ho gaya. Ab chalao:  uvicorn superagent.webui:app --host 0.0.0.0 --port 8000"

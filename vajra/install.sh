#!/usr/bin/env bash
# ============================================================
#  VAJRA ⚡ — All-in-one installer (Termux / Android)
#  Usage:   bash install.sh          → core tools (~15 min)
#           bash install.sh --full   → + Metasploit jaise heavy tools
#  Note:    Koi bhi tool fail ho toh script aage badhta rahega.
# ============================================================
set -u

FULL=0
[ "${1:-}" = "--full" ] && FULL=1

# ---------- detect termux ----------
IS_TERMUX=0
if [ -d "/data/data/com.termux" ] || [ -n "${TERMUX_VERSION:-}" ]; then
  IS_TERMUX=1
  PREFIX="/data/data/com.termux/files/usr"
else
  echo "⚠️  Termux detect nahi hua (testing/Linux mode) — kuch tools skip honge."
  PREFIX="$HOME/.local"
fi
export PATH="$PREFIX/bin:$PATH"
mkdir -p "$PREFIX/bin" "$HOME/vajra-tools" "$HOME/.vajra"

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS_DIR="$HOME/vajra-tools"
OK_LIST=""; FAIL_LIST=""

G()  { printf "\033[1;32m%s\033[0m\n" "$*"; }
Y()  { printf "\033[1;33m%s\033[0m\n" "$*"; }
R()  { printf "\033[1;31m%s\033[0m\n" "$*"; }
H()  { printf "\n\033[1;35m==> %s\033[0m\n" "$*"; }

mark_ok()   { OK_LIST="$OK_LIST $1";   G "  [✓] $1"; }
mark_fail() { FAIL_LIST="$FAIL_LIST $1"; R "  [✗] $1"; }

pkgi()  { command -v "$1" >/dev/null 2>&1 && return 0
          pkg install -y "$1" >/dev/null 2>&1 || apt install -y "$1" >/dev/null 2>&1
          command -v "$1" >/dev/null 2>&1; }

pipi()  { "$2" >/dev/null 2>&1 && return 0
          pip install -q --upgrade "$1" >/dev/null 2>&1
          "$2" >/dev/null 2>&1; }

wrap()  { # wrap <name> <dir> <file> <interpreter>
  cat > "$PREFIX/bin/$1" <<EOF
#!/data/data/com.termux/files/usr/bin/env bash
cd "$2" || exit 1
exec $3 "\$@"
EOF
  [ "$IS_TERMUX" = "0" ] && sed -i '1s|.*|#!/usr/bin/env bash|' "$PREFIX/bin/$1"
  chmod +x "$PREFIX/bin/$1"; }

gh_latest() { # gh_latest <repo> <pattern> → echo url
  curl -sL "https://api.github.com/repos/$1/releases/latest" \
    | grep browser_download_url | grep -i "$2" | head -1 | cut -d'"' -f4
}

get_binary() { # get_binary <name> <repo> <pattern> <archive-ext>
  local name="$1" url
  url="$(gh_latest "$2" "$3")"
  [ -z "$url" ] && return 1
  local tmp="/tmp/vj_$name"; mkdir -p "$tmp"
  curl -sL "$url" -o "$tmp/a" || return 1
  case "$4" in
    zip) unzip -o -q "$tmp/a" -d "$tmp" || return 1 ;;
    tgz) tar -xzf "$tmp/a" -C "$tmp" || return 1 ;;
  esac
  local bin
  bin="$(find "$tmp" -type f -name "$name*" | head -1)"
  [ -z "$bin" ] && return 1
  cp "$bin" "$PREFIX/bin/" && chmod +x "$PREFIX/bin/$name"*
}

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   ⚡  V A J R A  —  Installer  v1.0       ║"
echo "║   AI Ethical Hacking Agent (Termux)      ║"
echo "╚══════════════════════════════════════════╝"
echo ""
[ "$FULL" = "1" ] && Y "FULL MODE: heavy tools (Metasploit, winPEAS) bhi install honge."
Y "Internet + ~600MB storage chahiye. Shuru karte hain…"

# ============================================================
H "1/7 Base packages (python, git, network basics)"
for p in "python:python" "python-pip:pip" "git:git" "curl:curl" "wget:wget" \
         "openssh:ssh" "whois:whois" "dnsutils:dig" "jq:jq" "socat:socat" \
         "unzip:unzip" "tar:tar" "termux-api:termux-api" "ncurses:clear"; do
  pkg="${p%%:*}"; bin="${p##*:}"
  if pkgi "$pkg"; then mark_ok "$pkg"; else mark_fail "$pkg"; fi
done
pip install -q --upgrade pip setuptools wheel >/dev/null 2>&1

# ============================================================
H "2/7 Scanning & Enumeration — nmap, dirsearch, gobuster, enum4linux"
pkgi nmap           && mark_ok "nmap"         || mark_fail "nmap"
pipi dirsearch dirsearch && mark_ok "dirsearch"  || mark_fail "dirsearch"
if get_binary gobuster "OJ/gobuster" "linux_arm64" tgz; then mark_ok "gobuster"
elif get_binary gobuster "OJ/gobuster" "linux_armv7" tgz; then mark_ok "gobuster"
else mark_fail "gobuster"; fi
if [ ! -d "$TOOLS_DIR/enum4linux" ]; then
  git clone -q --depth 1 https://github.com/CiscoCXSecurity/enum4linux "$TOOLS_DIR/enum4linux" 2>/dev/null
fi
if [ -d "$TOOLS_DIR/enum4linux" ]; then
  wrap enum4linux "$TOOLS_DIR/enum4linux" "perl enum4linux.pl" && mark_ok "enum4linux" || mark_fail "enum4linux"
else mark_fail "enum4linux"; fi

# ============================================================
H "3/7 Recon & OSINT — theHarvester, sherlock, holehe, phoneinfoga, dnsenum"
# --- theHarvester
if [ ! -d "$TOOLS_DIR/theHarvester" ]; then
  git clone -q --depth 1 https://github.com/laramies/theHarvester "$TOOLS_DIR/theHarvester" 2>/dev/null
fi
if [ -d "$TOOLS_DIR/theHarvester" ]; then
  (cd "$TOOLS_DIR/theHarvester" && pip install -q -r requirements.txt >/dev/null 2>&1)
  wrap theHarvester "$TOOLS_DIR/theHarvester" "python3 theHarvester.py" \
    && mark_ok "theHarvester" || mark_fail "theHarvester"
else mark_fail "theHarvester"; fi
# --- pip tools
pipi sherlock-project sherlock && mark_ok "sherlock"   || mark_fail "sherlock"
pipi holehe holehe             && mark_ok "holehe"     || mark_fail "holehe"
pipi fierce fierce             && mark_ok "fierce"     || mark_fail "fierce"
# --- phoneinfoga (go binary)
if get_binary phoneinfoga "sundowndev/phoneinfoga" "linux_arm64" tgz; then mark_ok "phoneinfoga"
else mark_fail "phoneinfoga"; fi
# --- dnsenum
if [ ! -d "$TOOLS_DIR/dnsenum" ]; then
  git clone -q --depth 1 https://github.com/fwaeytens/dnsenum "$TOOLS_DIR/dnsenum" 2>/dev/null
fi
if [ -d "$TOOLS_DIR/dnsenum" ]; then
  wrap dnsenum "$TOOLS_DIR/dnsenum" "perl dnsenum.pl" && mark_ok "dnsenum" || mark_fail "dnsenum"
else mark_fail "dnsenum"; fi
# --- RED_HAWK (php)
if pkgi php; then
  if [ ! -d "$TOOLS_DIR/RED_HAWK" ]; then
    git clone -q --depth 1 https://github.com/Tuhinshubhra/RED_HAWK "$TOOLS_DIR/RED_HAWK" 2>/dev/null
  fi
  if [ -d "$TOOLS_DIR/RED_HAWK" ]; then
    wrap RED_HAWK "$TOOLS_DIR/RED_HAWK" "php RED_HAWK.php" && mark_ok "RED_HAWK" || mark_fail "RED_HAWK"
  else mark_fail "RED_HAWK"; fi
else mark_fail "RED_HAWK(php)"; fi

# ============================================================
H "4/7 Vulnerability Analysis — nikto, nuclei, searchsploit, testssl"
if [ ! -d "$TOOLS_DIR/nikto" ]; then
  git clone -q --depth 1 https://github.com/sullo/nikto "$TOOLS_DIR/nikto" 2>/dev/null
fi
if [ -d "$TOOLS_DIR/nikto" ]; then
  wrap nikto "$TOOLS_DIR/nikto/program" "perl nikto.pl" && mark_ok "nikto" || mark_fail "nikto"
else mark_fail "nikto"; fi
if get_binary nuclei "projectdiscovery/nuclei" "linux_arm64" zip; then mark_ok "nuclei"
else mark_fail "nuclei"; fi
# searchsploit + exploitdb
if [ ! -d "$TOOLS_DIR/exploitdb" ]; then
  git clone -q --depth 1 https://gitlab.com/exploit-database/exploitdb.git "$TOOLS_DIR/exploitdb" 2>/dev/null \
  || git clone -q --depth 1 https://github.com/offensive-security/exploitdb.git "$TOOLS_DIR/exploitdb" 2>/dev/null
fi
if [ -d "$TOOLS_DIR/exploitdb" ]; then
  ln -sf "$TOOLS_DIR/exploitdb/searchsploit" "$PREFIX/bin/searchsploit" 2>/dev/null
  command -v searchsploit >/dev/null 2>&1 && mark_ok "searchsploit" || mark_fail "searchsploit"
else mark_fail "searchsploit"; fi
# testssl.sh
if [ ! -d "$TOOLS_DIR/testssl.sh" ]; then
  git clone -q --depth 1 --branch v3.0.9 https://github.com/drwetter/testssl.sh "$TOOLS_DIR/testssl.sh" 2>/dev/null
fi
if [ -d "$TOOLS_DIR/testssl.sh" ]; then
  wrap testssl.sh "$TOOLS_DIR/testssl.sh" "bash testssl.sh" && mark_ok "testssl.sh" || mark_fail "testssl.sh"
else mark_fail "testssl.sh"; fi

# ============================================================
H "5/7 Gaining Access + Passwords — sqlmap, hydra, commix, john, cupp, crunch"
pipi sqlmap sqlmap   && mark_ok "sqlmap"  || mark_fail "sqlmap"
pkgi hydra           && mark_ok "hydra"   || mark_fail "hydra"
pkgi john            && mark_ok "john"    || mark_fail "john"
pkgi crunch          && mark_ok "crunch"  || mark_fail "crunch"
if [ ! -d "$TOOLS_DIR/commix" ]; then
  git clone -q --depth 1 https://github.com/commixproject/commix "$TOOLS_DIR/commix" 2>/dev/null
fi
if [ -d "$TOOLS_DIR/commix" ]; then
  wrap commix "$TOOLS_DIR/commix" "python3 commix.py" && mark_ok "commix" || mark_fail "commix"
else mark_fail "commix"; fi
if [ ! -d "$TOOLS_DIR/cupp" ]; then
  git clone -q --depth 1 https://github.com/Mebus/cupp "$TOOLS_DIR/cupp" 2>/dev/null
fi
if [ -d "$TOOLS_DIR/cupp" ]; then
  wrap cupp "$TOOLS_DIR/cupp" "python3 cupp.py" && mark_ok "cupp" || mark_fail "cupp"
else mark_fail "cupp"; fi

# ============================================================
H "6/7 Wireless + Post-Exploitation — aircrack, wifite, linpeas, les"
pkgi aircrack-ng && mark_ok "aircrack-ng" || mark_fail "aircrack-ng"
if [ ! -d "$TOOLS_DIR/wifite2" ]; then
  git clone -q --depth 1 https://github.com/derv82/wifite2 "$TOOLS_DIR/wifite2" 2>/dev/null
fi
if [ -d "$TOOLS_DIR/wifite2" ]; then
  wrap wifite "$TOOLS_DIR/wifite2" "python3 wifite.py" && mark_ok "wifite" || mark_fail "wifite"
else mark_fail "wifite"; fi
curl -sL "https://github.com/peass-ng/PEASS-ng/raw/master/linPEAS/linpeas.sh" \
  -o "$PREFIX/bin/linpeas" 2>/dev/null && chmod +x "$PREFIX/bin/linpeas" \
  && mark_ok "linpeas" || mark_fail "linpeas"
curl -sL "https://github.com/mzet-/linux-exploit-suggester/raw/master/linux-exploit-suggester.sh" \
  -o "$PREFIX/bin/les" 2>/dev/null && chmod +x "$PREFIX/bin/les" \
  && mark_ok "les" || mark_fail "les"

# ============================================================
H "7/7 VAJRA setup — launcher"
cat > "$PREFIX/bin/vajra" <<EOF
#!/data/data/com.termux/files/usr/bin/env bash
cd "$SRC_DIR" || { echo "vajra folder missing: $SRC_DIR"; exit 1; }
exec python3 vajra.py "\$@"
EOF
[ "$IS_TERMUX" = "0" ] && sed -i '1s|.*|#!/usr/bin/env bash|' "$PREFIX/bin/vajra"
chmod +x "$PREFIX/bin/vajra"
mark_ok "vajra command"

# wordlist (common.txt) for dir busting
if [ ! -f "$TOOLS_DIR/wordlist.txt" ]; then
  curl -sL "https://raw.githubusercontent.com/v0re/dirb/master/wordlists/common.txt" \
    -o "$TOOLS_DIR/wordlist.txt" 2>/dev/null \
  && G "  [✓] wordlist.txt (dirb common)" || touch "$TOOLS_DIR/wordlist.txt"
fi

# ============================================================
# FULL MODE — heavy tools
# ============================================================
if [ "$FULL" = "1" ]; then
  H "FULL: winPEAS (Windows privesc)"
  curl -sL "https://github.com/peass-ng/PEASS-ng/releases/latest/download/winPEASx64.exe" \
    -o "$TOOLS_DIR/winPEASx64.exe" 2>/dev/null \
    && mark_ok "winPEAS" || mark_fail "winPEAS"

  H "FULL: Metasploit Framework (~1GB, 20-40 min, best-effort)"
  Y "Yeh Android par heavy hai — fail ho sakta hai, ghabrao mat."
  if [ ! -d "$TOOLS_DIR/metasploit-framework" ]; then
    pkg install -y ruby libffi make clang pkg-config libpcap >/dev/null 2>&1
    git clone -q --depth 1 https://github.com/rapid7/metasploit-framework.git \
      "$TOOLS_DIR/metasploit-framework" 2>/dev/null
  fi
  if [ -d "$TOOLS_DIR/metasploit-framework" ]; then
    ( cd "$TOOLS_DIR/metasploit-framework"
      export NOKOGIRI="--use-system-libraries"
      gem install bundler >/dev/null 2>&1
      bundle install -j 2 >/dev/null 2>&1
      if [ -f "msfconsole" ]; then
        wrap msfconsole "$TOOLS_DIR/metasploit-framework" "ruby msfconsole"
        wrap msfvenom "$TOOLS_DIR/metasploit-framework" "ruby msfvenom"
        mark_ok "metasploit"
      else mark_fail "metasploit (bundle install fail — dobara try karo)"
      fi
    ) || mark_fail "metasploit"
  else mark_fail "metasploit (clone fail)"; fi
fi

# ============================================================
# SUMMARY
# ============================================================
echo ""
echo "╔════════════════════════════════════════════╗"
echo "║  📋  INSTALL SUMMARY                       ║"
echo "╚════════════════════════════════════════════╝"
G "OK:$OK_LIST"
[ -n "$FAIL_LIST" ] && R "FAIL:$FAIL_LIST"
echo ""
echo "   ▶ Chalane ke liye:   vajra"
echo "   ▶ Tools status:      vajra --tools"
echo "   ▶ Web UI (app jaisa): vajra --server  → http://localhost:8080"
echo ""
[ -n "$FAIL_LIST" ] && Y "Fail hue tools dobara try karo: bash install.sh"
Y "⚠️  Sirf authorized targets par use karo — scope: /scope add <target>"
echo ""

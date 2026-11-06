#!/data/data/com.termux/files/usr/bin/bash
# RatanSec Super Agent — apne Android phone ko hi server bana do (no root, no laptop).
#
# Termux (F-Droid build) me chalao:
#   bash phone-server.sh            # live server (console password maangega)
#   bash phone-server.sh --demo     # offline demo, bina password/key
#   bash phone-server.sh --port=8080
#
# Phir Super Agent APK me Server URL daalo:  http://127.0.0.1:8000
#
# Kya karta hai:
#   1. Termux me proot-distro + Debian install karta hai
#   2. Debian ke prebuilt python3-fastapi/uvicorn packages lagata hai
#      (Termux ke native python me pydantic-core ke liye Rust compile karna padta hai — isliye Debian)
#   3. Super Agent source download karke 127.0.0.1 par chalata hai
#
# Safety: server sirf 127.0.0.1 par bind hota hai — bahar se koi nahi pahunch sakta.
#         API key phone par hi rehti hai (.env), kisi cloud par nahi jaati.
#
# Source update karna ho:  SA_UPDATE=1 bash phone-server.sh
# Merge ke baad main se:   SA_REF=main bash phone-server.sh

set -euo pipefail

REPO="${SA_REPO:-Ratan-patel/Ratan-patel.github.io}"
REF="${SA_REF:-arena/77c68fc8-ratan-patel-github-io}"
PORT="${SA_PORT:-8000}"
UPDATE="${SA_UPDATE:-0}"
DEMO=0
PASSWORD=""

for arg in "$@"; do
  case "$arg" in
    --demo) DEMO=1 ;;
    --port=*) PORT="${arg#*=}" ;;
    -h|--help) sed -n '2,21p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

say()  { printf '\n\033[1;32m==>\033[0m %s\n' "$*"; }
die()  { printf '\n\033[1;31mx\033[0m %s\n' "$*" >&2; exit 1; }

# --- 0. Termux check -------------------------------------------------------
if [ -z "${TERMUX_VERSION:-}" ] && [ ! -d /data/data/com.termux/files/usr ]; then
  die "Ye script Termux (Android) ke andar chalni chahiye. Laptop par: bash scripts/superagent.sh"
fi

case "$PORT" in
  ''|*[!0-9]*) die "Port number galat hai: $PORT" ;;
esac
[ "$PORT" -ge 1024 ] && [ "$PORT" -le 65535 ] || die "Port 1024-65535 ke beech hona chahiye."

# --- 1. Console password (live mode) --------------------------------------
if [ "$DEMO" = "0" ]; then
  say "Console password set karo (app me login ke liye)"
  printf 'Password (min 8 chars): '
  stty -echo 2>/dev/null || true
  IFS= read -r PASSWORD || true
  stty echo 2>/dev/null || true
  printf '\n'
  [ "${#PASSWORD}" -ge 8 ] || die "Password kam se kam 8 characters ka hona chahiye."
  # .env parser value ke kinare ke quotes/space hata deta hai — aisa password
  # chupchaap badal jayega, isliye pehle hi mana kar dete hain.
  case "$PASSWORD" in
    [[:space:]]*|*[[:space:]]|\"*|*\"|\'*|*\')
      die "Password space ya quote se shuru/khatam nahi ho sakta. Beech me kuch bhi chalega." ;;
  esac
fi

# --- 2. proot-distro + Debian ---------------------------------------------
if ! command -v proot-distro >/dev/null 2>&1; then
  say "proot-distro install ho raha hai"
  pkg update -y
  pkg install -y proot-distro
fi

if ! proot-distro list 2>/dev/null | grep -qiE 'debian.*installed'; then
  say "Debian rootfs download ho raha hai (~150 MB, sirf pehli baar)"
  proot-distro install debian
fi

command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock || true

# --- 3. Inner script ------------------------------------------------------
# Values env vars ke through jaati hain (shell-quoted) — Python source me
# interpolate nahi karte, warna password ke quotes/\$ code tod dete hain.
HEADER=$(printf 'SA_REPO=%q\nSA_REF=%q\nSA_PORT=%q\nSA_DEMO=%q\nSA_UPDATE=%q\nSA_PASSWORD=%q\nexport SA_REPO SA_REF SA_PORT SA_DEMO SA_UPDATE SA_PASSWORD\n' \
  "$REPO" "$REF" "$PORT" "$DEMO" "$UPDATE" "$PASSWORD")

BODY=$(cat <<'BODY_EOF'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "==> Debian packages (prebuilt — koi Rust compile nahi)"
grep -qs 'nameserver' /etc/resolv.conf || echo 'nameserver 1.1.1.1' > /etc/resolv.conf
apt-get update
apt-get install -y --no-install-recommends python3 python3-fastapi python3-uvicorn curl ca-certificates

python3 - <<'PYCHK'
import sys
try:
    import fastapi, pydantic, uvicorn
except ImportError as exc:
    sys.exit("Python deps missing: %s" % exc)

def ver(text):
    parts = []
    for chunk in text.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits or 0))
    return tuple(parts)

if ver(fastapi.__version__) < (0, 110):
    sys.exit("FastAPI %s purana hai (>=0.110 chahiye) — Debian trixie chahiye." % fastapi.__version__)
if ver(pydantic.__version__) < (2, 6):
    sys.exit("Pydantic %s purana hai (>=2.6 chahiye)." % pydantic.__version__)
print("==> deps OK: fastapi", fastapi.__version__, "| pydantic", pydantic.__version__)
PYCHK

SRC=/opt/ratansec
if [ "$SA_UPDATE" = "1" ] || [ ! -f "$SRC/ratansec-os/superagent/webui.py" ]; then
  echo "==> Super Agent source download ho raha hai ($SA_REF)"
  mkdir -p "$SRC"
  curl -fsSL --retry 3 -o /tmp/sa.tar.gz \
    "https://codeload.github.com/$SA_REPO/tar.gz/refs/heads/$SA_REF"
  tar xzf /tmp/sa.tar.gz -C "$SRC" --strip-components=1
  rm -f /tmp/sa.tar.gz
fi

cd "$SRC/ratansec-os"
[ -f .env ] || { cp superagent/.env.example .env; chmod 600 .env; }

python3 - <<'PYENV'
import os
from pathlib import Path

path = Path(".env")
want = {
    "HOST": "127.0.0.1",
    "PORT": os.environ["SA_PORT"],
    "SUPERAGENT_DEMO_MODE": os.environ["SA_DEMO"],
}
password = os.environ.get("SA_PASSWORD", "")
if password:
    want["APP_PASSWORD"] = password

lines = path.read_text(encoding="utf-8").splitlines()
out, seen = [], set()
for line in lines:
    key = None
    if "=" in line and not line.lstrip().startswith("#"):
        key = line.split("=", 1)[0].strip()
    if key in want:
        out.append("%s=%s" % (key, want[key]))
        seen.add(key)
    else:
        out.append(line)
for key, value in want.items():
    if key not in seen:
        out.append("%s=%s" % (key, value))
path.write_text("\n".join(out) + "\n", encoding="utf-8")
path.chmod(0o600)
print("==> .env ready (key/password phone par hi rehti hai)")
PYENV

echo ""
echo "================================================"
echo "  Super Agent server:  http://127.0.0.1:$SA_PORT"
echo "  APK me yahi URL daalo."
echo "  Band karne ke liye: Ctrl + C"
echo "================================================"
echo ""
exec python3 -m uvicorn superagent.webui:app --host 127.0.0.1 --port "$SA_PORT"
BODY_EOF
)

say "Server start ho raha hai (pehli baar 5-10 min lag sakte hain)"
printf '%s\n%s\n' "$HEADER" "$BODY" | proot-distro login debian -- /bin/bash -s

cat <<TAIL

Server band ho gaya.
Dobara chalane ke liye:  bash phone-server.sh
API key daalni ho to:    proot-distro login debian
                         nano /opt/ratansec/ratansec-os/.env
                         (SUPERAGENT_API_KEY=... bharo, phir script dobara chalao)

TAIL
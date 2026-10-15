#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  RatanSec OS — cloud-init SEED ISO banao (real bootable config ISO)
#
#  Chalao:
#     bash deploy/build-seed-iso.sh --key sk-or-v1-XXXX --scope "site.com"
#     bash deploy/build-seed-iso.sh --branch main            # PR merge ke baad
#     bash deploy/build-seed-iso.sh --out /tmp/my-seed.iso
#
#  Kya banata hai: ek chhoti (~40 KB) ISO jiske andar user-data + meta-data hoti hai.
#  Isko VM me second CD-ROM me attach karo → first boot par poora RatanSec OS
#  apne aap install ho jayega (4-6 min).
#
#  pycdlib (pure python) use karta hai — koi root/xorriso/qemu ki zarurat nahi.
#  Install (agar na ho):  pip install pycdlib
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"        # → deploy/
ROOT="$(cd "$HERE/.." && pwd)"              # → ratansec-os/

BRANCH="arena/f71ea5d9-ratan-patel-github-io"
API_KEY=""
SCOPE=""
MODEL="openai/gpt-4o-mini"
PORT="8000"
EXTRA_FLAGS=""
OUT="$ROOT/artifacts/ratansec-seed.iso"

B=$'\033[1m'; C=$'\033[36m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
warn() { printf '  %s⚠%s %s\n' "$Y" "$N" "$*"; }
die()  { printf '  %s✗%s %s\n' "$R" "$N" "$*"; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --branch) BRANCH="${2:-}"; shift ;;
    --key)    API_KEY="${2:-}"; shift ;;
    --scope)  SCOPE="${2:-}"; shift ;;
    --model)  MODEL="${2:-}"; shift ;;
    --port)   PORT="${2:-}"; shift ;;
    --out)    OUT="${2:-}"; shift ;;
    --lite)   EXTRA_FLAGS="${EXTRA_FLAGS} --lite" ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
  shift
done

printf '\n%s▶ RatanSec OS seed ISO bana raha hoon%s\n' "$B" "$N"
printf '   branch: %s · port: %s · AI key: %s\n' "$BRANCH" "$PORT" "$([ -n "$API_KEY" ] && echo 'set ✓' || echo 'khaali (baad me .env me daal sakte ho)')"

# ── python + pycdlib ─────────────────────────────────────────────────
PY="python3"
command -v "$PY" >/dev/null 2>&1 || die "python3 nahi mila"
if ! "$PY" -c 'import pycdlib' >/dev/null 2>&1; then
  printf '   pycdlib install kar raha hoon (pip)…\n'
  "$PY" -m pip install -q --user pycdlib >/dev/null 2>&1 \
    || "$PY" -m pip install -q --break-system-packages pycdlib >/dev/null 2>&1 \
    || die "pycdlib install nahi hua — 'pip install pycdlib' manually chalao"
fi

# ── template me placeholders replace karo ────────────────────────────
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

"$PY" - "$HERE/cloud-init/user-data" "$TMP/user-data" \
        "$BRANCH" "$API_KEY" "$SCOPE" "$MODEL" "$PORT" "$EXTRA_FLAGS" <<'PYEOF'
import sys, pathlib
src, dst, branch, key, scope, model, port, extra = sys.argv[1:9]
text = pathlib.Path(src).read_text(encoding="utf-8")
text = (text.replace("__RATANSEC_BRANCH__", branch)
            .replace("__RATANSEC_API_KEY__", key)
            .replace("__RATANSEC_SCOPE__", scope)
            .replace("__RATANSEC_MODEL__", model)
            .replace("__RATANSEC_PORT__", port)
            .replace("__RATANSEC_EXTRA_FLAGS__", extra.strip()))
pathlib.Path(dst).write_text(text, encoding="utf-8")
print(f"   user-data ready ({len(text)} bytes)")
PYEOF

cp "$HERE/cloud-init/meta-data" "$TMP/meta-data"

# ── ISO build (volume label CIDATA — cloud-init NoCloud isi ko dhundhta hai) ──
mkdir -p "$(dirname "$OUT")"
"$PY" - "$TMP" "$OUT" <<'PYEOF'
import sys, pathlib, pycdlib

tmp, out = pathlib.Path(sys.argv[1]), sys.argv[2]
iso = pycdlib.PyCdlib()
iso.new(interchange_level=1, joliet=3, rock_ridge="1.09",
        vol_ident="CIDATA", sys_ident="LINUX", vol_set_ident="CIDATA")
# ISO9660 level-1 names 8.3 hone chahiye → short uppercase naam rakho,
# aur asli naam (user-data / meta-data) Rock Ridge + Joliet me do.
files = (("user-data", "/USERDATA.;1"), ("meta-data", "/METADATA.;1"))
for name, iso_path in files:
    iso.add_file(str(tmp / name), iso_path=iso_path, rr_name=name, joliet_path=f"/{name}")
iso.write(out)
iso.close()
print(f"   ISO written: {out}")
PYEOF

# ── verify (wahi names jo cloud-init dhundhta hai) ───────────────────
"$PY" - "$OUT" <<'PYEOF'
import io, sys, pycdlib

iso = pycdlib.PyCdlib()
iso.open(sys.argv[1])
ident = iso.pvd.volume_identifier.decode().strip()
contents = {}
for name in ("user-data", "meta-data"):
    buf = io.BytesIO()
    try:
        iso.get_file_from_iso_fp(buf, rr_path=f"/{name}")   # Rock Ridge naam se padho
        contents[name] = buf.getvalue().decode("utf-8", "replace")
    except Exception as exc:                                 # Joliet fallback
        try:
            buf = io.BytesIO()
            iso.get_file_from_iso_fp(buf, joliet_path=f"/{name}")
            contents[name] = buf.getvalue().decode("utf-8", "replace")
        except Exception:
            contents[name] = ""
            print(f"   ✗ '{name}' ISO me nahi mila ({exc})")
iso.close()

print(f"   volume label: {ident}")
for name, text in contents.items():
    print(f"   {name:10} → {len(text)} bytes read ✓" if text else f"   {name:10} → MISSING ✗")

problems = []
if ident != "CIDATA":
    problems.append("volume label CIDATA nahi hai (cloud-init isko nahi dhundh payega)")
if not contents.get("user-data"):
    problems.append("user-data nahi mila")
if not contents.get("meta-data"):
    problems.append("meta-data nahi mila")
if contents.get("user-data") and not contents["user-data"].lstrip().startswith("#cloud-config"):
    problems.append("user-data '#cloud-config' se start nahi hoti")

if problems:
    print("   ✗ verification fail:")
    for p in problems:
        print(f"      - {p}")
    raise SystemExit(1)
print("   ✓ cloud-init isko padh lega (label=CIDATA + Rock Ridge names sahi)")
PYEOF

SIZE="$(du -h "$OUT" | cut -f1)"
printf '\n  %s✓ Ban gayi:%s %s (%s)\n' "$G" "$N" "$OUT" "$SIZE"
printf '\n  %sIsko kaise use karo (VM me):%s\n' "$B" "$N"
printf '   1. Kisi bhi Ubuntu/Debian cloud image se VM banao (Oracle/GCP/AWS/Proxmox/Multipass)\n'
printf '   2. Is ISO ko us VM me %ssecond CD-ROM / additional drive%s me attach karo\n' "$B" "$N"
printf '   3. VM boot karo → 4-6 min me RatanSec OS ready\n'
printf '   4. Dashboard: %shttp://<VM-IP>:%s%s  ·  password: %s/root/ratansec-credentials.txt%s\n\n' \
        "$C" "$PORT" "$N" "$C" "$N"

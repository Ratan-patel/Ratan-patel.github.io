#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  RatanSec OS — VM disk image builder (qcow2 · vmdk · vdi) + seed ISO
#
#  Kahan chalta hai: kisi bhi Linux box / CI runner par jisme root ya sudo ho.
#                    (GitHub Actions par .github/workflows/build-ratansec-image.yml
#                     yahi script chalata hai — wahan se seedha release me file aati hai.)
#
#  Zaroori tools: qemu-utils, libguestfs-tools, curl, python3 (+ pycdlib)
#     Ubuntu/Debian:  sudo apt-get install -y qemu-utils libguestfs-tools curl python3-pip
#
#  Chalao:
#     sudo bash deploy/build-image.sh                         # qcow2 + vmdk + vdi + seed ISO
#     sudo bash deploy/build-image.sh --arch arm64            # Oracle ARM free tier ke liye
#     sudo bash deploy/build-image.sh --distro jammy          # Ubuntu 22.04
#     sudo bash deploy/build-image.sh --stock-only            # sirf stock image + seed ISO (koi bake nahi)
#     bash deploy/build-image.sh --key sk-or-... --scope "site.com"   # config bake karo
#
#  Ban jaane ke baad (deploy/artifacts/ me):
#     ratansec-os-1.0.0-amd64.qcow2   → KVM/Proxmox/Oracle custom image import
#     ratansec-os-1.0.0-amd64.vmdk    → VMware / VirtualBox (convert) / ESXi
#     ratansec-os-1.0.0-amd64.vdi     → VirtualBox (direct)
#     ratansec-seed.iso               → cloud-init config (VM me 2nd drive)
#     SHA256SUMS.txt                  → checksums
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"        # → ratansec-os/
VERSION="$(grep -E '^VERSION' "$ROOT/app/config.py" | head -1 | sed 's/.*"\(.*\)".*/\1/')"
OUT_DIR="$ROOT/artifacts"
WORK_DIR="${WORK_DIR:-/tmp/ratansec-image-build}"

DISTRO="noble"          # noble = 24.04 LTS · jammy = 22.04 LTS
ARCH="amd64"
TYPES="qcow2,vmdk,vdi"
BRANCH="arena/f71ea5d9-ratan-patel-github-io"
API_KEY=""
SCOPE=""
MODEL="openai/gpt-4o-mini"
PORT="8000"
PASSWORD=""
STOCK_ONLY=0
KEEP_WORK=0

B=$'\033[1m'; C=$'\033[36m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; D=$'\033[2m'; N=$'\033[0m'
step() { printf '\n%s▶ %s%s\n' "$B" "$*" "$N"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
info() { printf '  %s·%s %s\n' "$C" "$N" "$*"; }
warn() { printf '  %s⚠%s %s\n' "$Y" "$N" "$*"; }
die()  { printf '  %s✗%s %s\n' "$R" "$N" "$*"; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --distro)     DISTRO="${2:-noble}"; shift ;;
    --arch)       ARCH="${2:-amd64}"; shift ;;
    --types)      TYPES="${2:-qcow2}"; shift ;;
    --branch)     BRANCH="${2:-}"; shift ;;
    --key)        API_KEY="${2:-}"; shift ;;
    --scope)      SCOPE="${2:-}"; shift ;;
    --model)      MODEL="${2:-$MODEL}"; shift ;;
    --port)       PORT="${2:-8000}"; shift ;;
    --password)   PASSWORD="${2:-}"; shift ;;
    --out)        OUT_DIR="${2:-$OUT_DIR}"; shift ;;
    --stock-only) STOCK_ONLY=1 ;;
    --keep-work)  KEEP_WORK=1 ;;
    -h|--help)    sed -n '2,28p' "$0"; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
  shift
done

mkdir -p "$OUT_DIR" "$WORK_DIR"
BASE_NAME="ratansec-os-${VERSION}-${ARCH}"
IMG="$WORK_DIR/${BASE_NAME}.img"
SOURCE_URL="https://cloud-images.ubuntu.com/${DISTRO}/current/${DISTRO}-server-cloudimg-${ARCH}.img"

printf '\n%s╔══════════════════════════════════════════════════════════════╗%s\n' "$C" "$N"
printf '%s║%s   %sRatanSec OS — VM image builder%s v%s                     %s║%s\n' "$C" "$N" "$B" "$N" "$VERSION" "$C" "$N"
printf '%s╚══════════════════════════════════════════════════════════════╝%s\n' "$C" "$N"
info "distro=$DISTRO arch=$ARCH types=$TYPES"
info "output: $OUT_DIR"
[ "$STOCK_ONLY" = 1 ] && warn "stock-only mode: bake skip (sirf Ubuntu image + seed ISO)"

# ─── 0) tools check ───────────────────────────────────────────────────
step "Tools check"
for t in qemu-img curl python3; do command -v "$t" >/dev/null 2>&1 || die "$t nahi mila (apt-get install -y qemu-utils curl python3-pip)"; done
ok "qemu-img, curl, python3 present"
if [ "$STOCK_ONLY" = 0 ]; then
  command -v virt-customize >/dev/null 2>&1 || die "virt-customize nahi mila → sudo apt-get install -y libguestfs-tools"
  export LIBGUESTFS_BACKEND="${LIBGUESTFS_BACKEND:-direct}"
  ok "virt-customize present (backend=$LIBGUESTFS_BACKEND)"
fi

# ─── 1) Ubuntu cloud image download ───────────────────────────────────
step "Ubuntu $DISTRO ($ARCH) cloud image download"
if [ -f "$IMG" ]; then
  ok "cache me mila: $IMG"
else
  info "source: $SOURCE_URL"
  curl -fL --retry 3 --retry-delay 5 -o "$IMG" "$SOURCE_URL" || die "download fail"
  ok "download complete ($(du -h "$IMG" | cut -f1))"
fi
# working copy (original cache rehne do)
BUILD_IMG="$WORK_DIR/${BASE_NAME}-build.img"
cp --reflink=auto "$IMG" "$BUILD_IMG"

# ─── 2) bake: app + first-boot installer ──────────────────────────────
if [ "$STOCK_ONLY" = 0 ]; then
  step "App bake kar raha hoon (image me /opt/ratansec-src daal raha hoon)"
  STAGE="$WORK_DIR/stage"; rm -rf "$STAGE"; mkdir -p "$STAGE"
  rsync -a --exclude 'artifacts' --exclude '.venv' --exclude 'data' --exclude '__pycache__' \
        "$ROOT" "$STAGE/ratansec-os" 2>/dev/null \
    || { cp -r "$ROOT" "$STAGE/ratansec-os"; rm -rf "$STAGE/ratansec-os"/{artifacts,.venv,data}; }
  ok "staged: $(du -sh "$STAGE/ratansec-os" | cut -f1)"

  # first-boot script: ek baar chalta hai, phir khud delete ho jata hai (virt-customize --firstboot)
  FIRSTBOOT="$WORK_DIR/firstboot.sh"
  cat > "$FIRSTBOOT" <<FIRSTBOOT_EOF
#!/usr/bin/env bash
# RatanSec OS — pehla boot: poora install (tools + service)
set -uo pipefail
exec > >(tee -a /var/log/ratansec-firstboot.log) 2>&1
echo "═══ RatanSec OS first boot \$(date -Is) ═══"

# cloud-init ke write_files se aayi config (agar user ne di ho) — warna defaults
CONF=/etc/ratansec-boot.conf
KEY="__KEY__"; SCOPE="__SCOPE__"; MODEL="__MODEL__"; PORT="__PORT__"; PASS="__PASSWORD__"
if [ -f "\$CONF" ]; then
  # shellcheck disable=SC1090
  . "\$CONF"
  KEY="\${RATANSEC_API_KEY:-\$KEY}"; SCOPE="\${RATANSEC_SCOPE:-\$SCOPE}"
  MODEL="\${RATANSEC_MODEL:-\$MODEL}"; PORT="\${RATANSEC_PORT:-\$PORT}"; PASS="\${RATANSEC_PASSWORD:-\$PASS}"
fi

bash /opt/ratansec-src/deploy/vps-install.sh \\
  --key "\$KEY" --scope "\$SCOPE" --model "\$MODEL" --port "\$PORT" --password "\$PASS" || true

IP="\$(curl -s -m 5 ifconfig.me || hostname -I | awk '{print \$1}')"
REAL_PASS="\$(grep -E '^APP_PASSWORD=' /opt/ratansec-os/.env 2>/dev/null | cut -d= -f2-)"
{
  echo "RatanSec OS — dashboard credentials"
  echo "URL:      http://\${IP}:\${PORT}"
  echo "Password: \${REAL_PASS}"
} > /root/ratansec-credentials.txt
chmod 600 /root/ratansec-credentials.txt 2>/dev/null || true
{
  echo ""
  echo "════════════════════════════════════════════"
  echo "  ✅ RatanSec OS READY   →  http://\${IP}:\${PORT}"
  echo "  Password: \${REAL_PASS}   (/root/ratansec-credentials.txt)"
  echo "════════════════════════════════════════════"
} > /dev/console 2>/dev/null || true

rm -rf /opt/ratansec-src
echo "═══ first boot done \$(date -Is) ═══"
FIRSTBOOT_EOF
  sed -i "s|__KEY__|${API_KEY}|; s|__SCOPE__|${SCOPE}|; s|__MODEL__|${MODEL}|; s|__PORT__|${PORT}|; s|__PASSWORD__|${PASSWORD}|" "$FIRSTBOOT"
  chmod +x "$FIRSTBOOT"

  info "virt-customize chal raha hai (files inject + firstboot unit)…"
  virt-customize -a "$BUILD_IMG" --no-network \
    --hostname ratansec-os \
    --copy-in "$STAGE/ratansec-os:/opt" \
    --copy-in "$FIRSTBOOT:/usr/local/bin" \
    --run-command 'mv /usr/local/bin/firstboot.sh /usr/local/bin/ratansec-firstboot.sh 2>/dev/null || true; chmod 755 /usr/local/bin/ratansec-firstboot.sh; mkdir -p /etc/motd.d' \
    --write '/etc/motd.d/ratansec: RatnSec OS image — pehle boot par apne aap install hoga (4-6 min) | dashboard: http://<IP>:8000' \
    --firstboot /usr/local/bin/ratansec-firstboot.sh \
    || die "virt-customize fail — logs dekho (LIBGUESTFS_BACKEND=direct already set hai)"
  ok "image bake ho gayi"
else
  info "stock-only: bake skip kiya"
fi

# ─── 3) formats convert ───────────────────────────────────────────────
IFS=',' read -r -a WANT <<< "$TYPES"
for fmt in "${WANT[@]}"; do
  case "$fmt" in
    qcow2)
      step "qcow2 bana raha hoon (compressed)"
      qemu-img convert -p -c -O qcow2 "$BUILD_IMG" "$OUT_DIR/${BASE_NAME}.qcow2"
      ok "$(du -h "$OUT_DIR/${BASE_NAME}.qcow2" | cut -f1) · $(qemu-img info --output=json "$OUT_DIR/${BASE_NAME}.qcow2" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f"virtual {d[\"virtual-size\"]/10**9:.1f} GB")')"
      ;;
    vmdk)
      step "vmdk (streamOptimized — VMware/ESXi/VirtualBox) bana raha hoon"
      qemu-img convert -p -O vmdk -o subformat=streamOptimized,adapter_type=lsilogic "$BUILD_IMG" "$OUT_DIR/${BASE_NAME}.vmdk"
      ok "$(du -h "$OUT_DIR/${BASE_NAME}.vmdk" | cut -f1)"
      ;;
    vdi)
      step "vdi (VirtualBox direct) bana raha hoon"
      qemu-img convert -p -O vdi "$BUILD_IMG" "$OUT_DIR/${BASE_NAME}.vdi"
      ok "$(du -h "$OUT_DIR/${BASE_NAME}.vdi" | cut -f1)"
      ;;
    raw|img)
      step "raw img copy"
      qemu-img convert -p -O raw "$BUILD_IMG" "$OUT_DIR/${BASE_NAME}.img"
      ok "$(du -h "$OUT_DIR/${BASE_NAME}.img" | cut -f1)"
      ;;
    *) warn "unknown format: $fmt (skip)" ;;
  esac
done

# ─── 4) seed ISO (cloud-init) ─────────────────────────────────────────
step "cloud-init seed ISO bana raha hoon"
bash "$ROOT/deploy/build-seed-iso.sh" --branch "$BRANCH" --key "$API_KEY" --scope "$SCOPE" \
     --model "$MODEL" --port "$PORT" --out "$OUT_DIR/ratansec-seed.iso" >/dev/null \
  && ok "ratansec-seed.iso ($(du -h "$OUT_DIR/ratansec-seed.iso" | cut -f1))" \
  || warn "seed ISO fail (app images to ban gayi hain)"

# ─── 5) checksums ─────────────────────────────────────────────────────
step "SHA256 checksums"
( cd "$OUT_DIR" && sha256sum *.qcow2 *.vmdk *.vdi *.iso *.img 2>/dev/null > SHA256SUMS.txt || true )
ok "SHA256SUMS.txt ($(wc -l < "$OUT_DIR/SHA256SUMS.txt" 2>/dev/null || echo 0) files)"

# ─── 6) cleanup + summary ─────────────────────────────────────────────
IMMUTABLE_FLAG=""
[ "$KEEP_WORK" = 1 ] || rm -rf "$WORK_DIR"

printf '\n%s╔══════════════════════════════════════════════════════════════╗%s\n' "$G" "$N"
printf '%s║%s   %s✅ RatanSec OS images ready%s                              %s║%s\n' "$G" "$N" "$B" "$N" "$G" "$N"
printf '%s╚══════════════════════════════════════════════════════════════╝%s\n' "$G" "$N"
ls -lh "$OUT_DIR" | tail -n +2 | awk '{printf "   %-42s %s\n", $9, $5}'
printf '\n   %sVM me kaise daalein:%s deploy/IMAGE_GUIDE.md dekho (Oracle/Proxmox/VirtualBox/VMware/GCP)\n\n' "$B" "$N"

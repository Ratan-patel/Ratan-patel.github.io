#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  RatanSec OS — VM disk image builder (qcow2 · vmdk · vdi) + seed ISO
#
#  Kahan chalta hai: kisi bhi Linux box / CI runner par jisme root ya sudo ho.
#  (GitHub Actions par .github/workflows/build-ratansec-image.yml ise stage-wise chalata hai.)
#
#  Zaroori tools: qemu-utils, libguestfs-tools, curl, python3 (+ pycdlib)
#     Ubuntu/Debian:  sudo apt-get install -y qemu-utils libguestfs-tools curl python3-pip
#
#  Chalao:
#     sudo bash deploy/build-image.sh                       # sab kuch
#     sudo bash deploy/build-image.sh --arch arm64          # Oracle ARM free tier
#     sudo bash deploy/build-image.sh --distro jammy        # Ubuntu 22.04
#     sudo bash deploy/build-image.sh --stock-only          # sirf stock image + seed ISO
#     sudo bash deploy/build-image.sh --only bake           # ek stage (debug/CI ke liye)
#           stages: download, bake, convert, seed, sums
#     bash deploy/build-image.sh --help
#
#  Output (deploy/artifacts/ me):
#     ratansec-os-<ver>-<arch>.qcow2  → KVM/Proxmox/Oracle custom image import
#     ratansec-os-<ver>-<arch>.vmdk   → VMware/ESXi/VirtualBox
#     ratansec-os-<ver>-<arch>.vdi    → VirtualBox (direct)
#     ratansec-seed.iso               → cloud-init config (VM me 2nd CD-ROM)
#     SHA256SUMS.txt
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"        # → ratansec-os/
WORK_DIR="${WORK_DIR:-/tmp/ratansec-image-build}"
OUT_DIR="$ROOT/artifacts"

DISTRO="noble"          # noble = 24.04 LTS · jammy = 22.04 LTS
ARCH="amd64"
TYPES="qcow2,vmdk,vdi,img"
ONLY="download,bake,convert,seed,sums"
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
gh_annotate() { [ "${GITHUB_ACTIONS:-}" = "true" ] && printf '::error::%s\n' "$*" || true; }
die()  { printf '  %s✗%s %s\n' "$R" "$N" "$*"; gh_annotate "$*"; exit 1; }
want() { case ",$ONLY," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }

while [ $# -gt 0 ]; do
  case "$1" in
    --distro)     DISTRO="${2:-noble}"; shift ;;
    --arch)       ARCH="${2:-amd64}"; shift ;;
    --types)      TYPES="${2:-qcow2}"; shift ;;
    --only)       ONLY="${2:-}"; shift ;;
    --branch)     BRANCH="${2:-}"; shift ;;
    --key)        API_KEY="${2:-}"; shift ;;
    --scope)      SCOPE="${2:-}"; shift ;;
    --model)      MODEL="${2:-$MODEL}"; shift ;;
    --port)       PORT="${2:-8000}"; shift ;;
    --password)   PASSWORD="${2:-}"; shift ;;
    --out)        OUT_DIR="${2:-$OUT_DIR}"; shift ;;
    --work)       WORK_DIR="${2:-$WORK_DIR}"; shift ;;
    --stock-only) STOCK_ONLY=1 ;;
    --keep-work)  KEEP_WORK=1 ;;
    -h|--help)    sed -n '2,30p' "$0"; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
  shift
done

mkdir -p "$OUT_DIR" "$WORK_DIR"

# version nikaalo (pipefail-safe)
VERSION="$(sed -n 's/^VERSION = "\(.*\)"/\1/p' "$ROOT/app/config.py" | sed -n '1p')"
VERSION="${VERSION:-1.0.0}"
BASE_NAME="ratansec-os-${VERSION}-${ARCH}"
IMG="$WORK_DIR/${BASE_NAME}-base.img"          # downloaded cloud image (cache)
BUILD_IMG="$WORK_DIR/${BASE_NAME}-build.img"   # baked working image
SOURCE_URL="https://cloud-images.ubuntu.com/${DISTRO}/current/${DISTRO}-server-cloudimg-${ARCH}.img"

printf '\n%s╔══════════════════════════════════════════════════════════════╗%s\n' "$C" "$N"
printf '%s║%s   %sRatanSec OS — VM image builder%s v%s                     %s║%s\n' "$C" "$N" "$B" "$N" "$VERSION" "$C" "$N"
printf '%s╚══════════════════════════════════════════════════════════════╝%s\n' "$C" "$N"
info "distro=$DISTRO arch=$ARCH types=$TYPES"
info "stages: $ONLY"
info "work=$WORK_DIR out=$OUT_DIR"
[ "$STOCK_ONLY" = 1 ] && warn "stock-only: bake skip (stock Ubuntu + seed ISO)"

# ─── stage: download ──────────────────────────────────────────────────
if want download; then
  step "Stage: download — Ubuntu $DISTRO ($ARCH) cloud image"
  for t in qemu-img curl python3; do
    command -v "$t" >/dev/null 2>&1 || die "$t nahi mila → apt-get install -y qemu-utils curl python3-pip"
  done
  ok "qemu-img $(qemu-img --version | sed -n 's/.*version \([0-9.]*\).*/\1/p' | sed -n '1p') · curl · python3 present"

  if [ -s "$IMG" ]; then
    ok "cache me mila: $IMG ($(du -h "$IMG" | cut -f1))"
  else
    info "download: $SOURCE_URL"
    curl -fL --retry 3 --retry-delay 5 --connect-timeout 20 -o "$IMG.part" "$SOURCE_URL" \
      || die "Ubuntu cloud image download fail ($SOURCE_URL)"
    mv "$IMG.part" "$IMG"
    ok "download complete ($(du -h "$IMG" | cut -f1))"
  fi
  qemu-img info "$IMG" >/dev/null 2>&1 || die "downloaded image qemu-img se readable nahi hai"
  ok "image valid (qemu-img info OK)"
fi

# ─── stage: bake ──────────────────────────────────────────────────────
if want bake; then
  step "Stage: bake — app + first-boot installer image me daal raha hoon"
  [ -s "$IMG" ] || die "base image nahi mili ($IMG) — pehle 'download' stage chalao"
  if [ "$STOCK_ONLY" = 1 ]; then
    info "stock-only: seed ISO hi kaafi hai, bake skip"
  else
    command -v virt-customize >/dev/null 2>&1 || die "virt-customize nahi mila → apt-get install -y libguestfs-tools"
    export LIBGUESTFS_BACKEND="${LIBGUESTFS_BACKEND:-direct}"
    ok "virt-customize present (LIBGUESTFS_BACKEND=$LIBGUESTFS_BACKEND)"

    # working copy (cache image untouched rehne do)
    rm -f "$BUILD_IMG"
    cp --reflink=auto "$IMG" "$BUILD_IMG"
    ok "working copy banayi ($(du -h "$BUILD_IMG" | cut -f1))"

    # app source staging (artifacts/venv/data hata ke)
    STAGE="$WORK_DIR/stage"; rm -rf "$STAGE"; mkdir -p "$STAGE/ratansec-os"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --exclude 'artifacts' --exclude '.venv' --exclude 'data' --exclude '__pycache__' \
            --exclude '*.pyc' "$ROOT/" "$STAGE/ratansec-os/" || die "rsync fail"
    else
      cp -r "$ROOT/." "$STAGE/ratansec-os/" && rm -rf "$STAGE/ratansec-os"/{artifacts,.venv,data}
    fi
    [ -f "$STAGE/ratansec-os/deploy/vps-install.sh" ] || die "staged copy me installer nahi mila"
    ok "staged: $(du -sh "$STAGE/ratansec-os" | cut -f1)"

    # first-boot script (ek baar chalta hai, phir virt-customize khud hata deta hai)
    FIRSTBOOT="$WORK_DIR/firstboot.sh"
    cat > "$FIRSTBOOT" <<FIRSTBOOT_EOF
#!/usr/bin/env bash
set -uo pipefail
exec > >(tee -a /var/log/ratansec-firstboot.log) 2>&1
echo "═══ RatanSec OS first boot \$(date -Is) ═══"

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
  echo "  Password: \${REAL_PASS}  (/root/ratansec-credentials.txt)"
  echo "════════════════════════════════════════════"
} > /dev/console 2>/dev/null || true

rm -rf /opt/ratansec-src
echo "═══ first boot done \$(date -Is) ═══"
FIRSTBOOT_EOF
    sed -i "s|__KEY__|${API_KEY}|; s|__SCOPE__|${SCOPE}|; s|__MODEL__|${MODEL}|; s|__PORT__|${PORT}|; s|__PASSWORD__|${PASSWORD}|" "$FIRSTBOOT"
    bash -n "$FIRSTBOOT" || die "firstboot script syntax galat"
    chmod +x "$FIRSTBOOT"
    ok "firstboot script ready"

    info "virt-customize #1: app source inject (/opt/ratansec-os)…"
    virt-customize -a "$BUILD_IMG" --no-network \
      --hostname ratansec-os \
      --mkdir /opt \
      --copy-in "$STAGE/ratansec-os:/opt" \
      --run-command 'mkdir -p /etc/motd.d /opt/ratansec-os' \
      --write '/etc/motd.d/ratansec:RatanSec OS image — pehle boot par apne aap install hoga (4-6 min). Dashboard: http://<VM-IP>:8000' \
      || die "virt-customize copy-in fail (libguestfs)"

    info "virt-customize #2: first-boot unit install (--firstboot = HOST file path)…"
    virt-customize -a "$BUILD_IMG" --no-network \
      --firstboot "$FIRSTBOOT" \
      || die "virt-customize --firstboot fail (libguestfs)"

    ok "image bake ho gayi: $BUILD_IMG"
    # sanity: guest ke andar sab cheezein pahunchi?
    # NOTE: verify best-effort hai — iske fail hone se build nahi rukna chahiye
    if command -v virt-ls >/dev/null 2>&1; then
      MOUNT=""
      MOUNT="$( { virt-filesystems -a "$BUILD_IMG" --mountpoints --filesystems 2>/dev/null || true; } \
                | sed -n 's|^\(/dev/[^ ]*\).*|\1|p' | sed -n '1p' )" || MOUNT=""
      if [ -n "$MOUNT" ]; then
        if virt-ls -a "$BUILD_IMG" -m "$MOUNT" /opt 2>/dev/null | grep -q ratansec-os; then
          ok "guest verify ✓ /opt/ratansec-os maujood hai"
        else
          warn "guest verify: /opt/ratansec-os list nahi hua (bake log dekho)"
        fi
        virt-ls -a "$BUILD_IMG" -m "$MOUNT" /opt/ratansec-os/deploy 2>/dev/null | grep -q vps-install.sh \
          && ok "guest verify ✓ installer maujood hai" \
          || warn "guest verify: vps-install.sh list nahi hua"
      else
        warn "virt-filesystems se mountpoint nahi mila — verify skip (build aage badh raha hai)"
      fi
    fi
  fi
fi

# ─── stage: convert ───────────────────────────────────────────────────
if want convert; then
  step "Stage: convert — disk formats"
  SRC_IMG="$BUILD_IMG"
  [ -s "$SRC_IMG" ] || SRC_IMG="$IMG"
  [ -s "$SRC_IMG" ] || die "convert ke liye koi image nahi mili (download/bake stage chalao)"
  info "source: $SRC_IMG ($(du -h "$SRC_IMG" | cut -f1))"

  IFS=',' read -r -a WANT <<< "$TYPES"
  for fmt in "${WANT[@]}"; do
    case "$fmt" in
      qcow2)
        info "qcow2 (compressed) convert…"
        qemu-img convert -p -c -O qcow2 "$SRC_IMG" "$OUT_DIR/${BASE_NAME}.qcow2" || die "qcow2 convert fail"
        ok "qcow2: $(du -h "$OUT_DIR/${BASE_NAME}.qcow2" | cut -f1)"
        ;;
      vmdk)
        info "vmdk (streamOptimized) convert…"
        qemu-img convert -p -O vmdk -o subformat=streamOptimized,adapter_type=lsilogic "$SRC_IMG" "$OUT_DIR/${BASE_NAME}.vmdk" || die "vmdk convert fail"
        ok "vmdk: $(du -h "$OUT_DIR/${BASE_NAME}.vmdk" | cut -f1)"
        ;;
      vdi)
        info "vdi convert…"
        qemu-img convert -p -O vdi "$SRC_IMG" "$OUT_DIR/${BASE_NAME}.vdi" || die "vdi convert fail"
        ok "vdi: $(du -h "$OUT_DIR/${BASE_NAME}.vdi" | cut -f1)"
        ;;
      img|raw|img.gz)
        info "raw .img convert (uncompressed disk)…"
        RAW_OUT="$OUT_DIR/${BASE_NAME}.img"
        qemu-img convert -p -O raw "$SRC_IMG" "$RAW_OUT" || die "raw convert fail"
        ok "raw img: $(du -h "$RAW_OUT" | cut -f1)"
        # GitHub release asset limit 2 GiB hai → gzip karke rakhna zaroori hai
        if [ "$fmt" != "raw" ]; then
          info "gzip kar raha hoon (.img.gz)…"
          if command -v pigz >/dev/null 2>&1; then
            pigz -6 -f "$RAW_OUT" || die "pigz fail"
          else
            gzip -6 -f "$RAW_OUT" || die "gzip fail"
          fi
          ok "img.gz: $(du -h "$RAW_OUT.gz" | cut -f1)  (unzip: gzip -d ${BASE_NAME}.img.gz)"
        fi
        ;;
      vhd|vhdx)
        info "vhd/vhdx (Hyper-V) convert…"
        SUBFMT="dynamic"; [ "$fmt" = "vhdx" ] && SUBFMT="fixed"
        qemu-img convert -p -O vpc -o subformat="$SUBFMT" "$SRC_IMG" "$OUT_DIR/${BASE_NAME}.vhd" || die "vhd convert fail"
        ok "vhd: $(du -h "$OUT_DIR/${BASE_NAME}.vhd" | cut -f1)"
        ;;
      *) warn "unknown format skip: $fmt" ;;
    esac
  done
fi

# ─── stage: seed ──────────────────────────────────────────────────────
if want seed; then
  step "Stage: seed — cloud-init ISO"
  if bash "$ROOT/deploy/build-seed-iso.sh" --branch "$BRANCH" --key "$API_KEY" --scope "$SCOPE" \
        --model "$MODEL" --port "$PORT" --out "$OUT_DIR/ratansec-seed.iso" >"$WORK_DIR/seed.log" 2>&1; then
    ok "ratansec-seed.iso ($(du -h "$OUT_DIR/ratansec-seed.iso" | cut -f1))"
  else
    warn "seed ISO fail — log: $WORK_DIR/seed.log"
    tail -15 "$WORK_DIR/seed.log" || true
    gh_annotate "seed ISO build fail (dekho $WORK_DIR/seed.log)"
  fi
fi

# ─── stage: sums ──────────────────────────────────────────────────────
if want sums; then
  step "Stage: sums — SHA256 checksums"
  ( cd "$OUT_DIR" && sha256sum ./*.qcow2 ./*.vmdk ./*.vdi ./*.img.gz ./*.img ./*.iso ./*.vhd 2>/dev/null | sed 's|\./||' > SHA256SUMS.txt ) || true
  if [ -s "$OUT_DIR/SHA256SUMS.txt" ]; then
    ok "SHA256SUMS.txt ($(wc -l < "$OUT_DIR/SHA256SUMS.txt") files)"
  else
    warn "SHA256SUMS.txt khaali (koi image nahi bani?)"
  fi
fi

# ─── cleanup + summary ────────────────────────────────────────────────
if [ "$KEEP_WORK" = 0 ] && [ "$ONLY" = "download,bake,convert,seed,sums" ]; then
  rm -rf "$WORK_DIR"
fi

printf '\n%s╔══════════════════════════════════════════════════════════════╗%s\n' "$G" "$N"
printf '%s║%s   %s✅ RatanSec OS build stage(s) complete%s                   %s║%s\n' "$G" "$N" "$B" "$N" "$G" "$N"
printf '%s╚══════════════════════════════════════════════════════════════╝%s\n' "$G" "$N"
if ls "$OUT_DIR"/* >/dev/null 2>&1; then
  ls -lh "$OUT_DIR" | tail -n +2 | awk '{printf "   %-44s %s\n", $9, $5}'
fi
printf '\n   %sVM me kaise daalein:%s deploy/IMAGE_GUIDE.md\n\n' "$B" "$N"

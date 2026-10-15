#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${PARROT_VERSION:-7.4}"
SUITE="${PARROT_SUITE:-echo}"
ARCH="${PARROT_ARCH:-amd64}"
BUILDER_URL="https://github.com/ParrotSec/parrot-iso-build.git"
BUILDER_REF="${PARROT_BUILDER_REF:-50cb6c7fbf8ac7b5933d93cd127b5bbbd2b914ba}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/artifacts}"
WORK_BASE="${WORK_DIR:-${TMPDIR:-/tmp}}"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this builder as root (for example: sudo bash $0)." >&2
    exit 1
fi
if [[ "$VERSION" != "7.4" || "$SUITE" != "echo" || "$ARCH" != "amd64" ]]; then
    echo "This ISO recipe is pinned to Parrot 7.4 Echo AMD64." >&2
    exit 1
fi
for tool in git python3 lb debootstrap rsync; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "Missing ISO build dependency: $tool" >&2
        exit 1
    }
done

mkdir -p "$OUTPUT_DIR" "$WORK_BASE"
[[ "$WORK_BASE" != "/" ]] || { echo "WORK_DIR must not be /" >&2; exit 1; }
WORK_DIR="$(mktemp -d "${WORK_BASE%/}/parrot-${VERSION}-${ARCH}-iso-XXXXXX")"
BUILDER_DIR="$WORK_DIR/parrot-iso-build"
BUILT_ISO="$BUILDER_DIR/images/Parrot-lite-xfce-${VERSION}_${ARCH}.iso"
OUTPUT_FILE="$OUTPUT_DIR/Parrot-${VERSION}-Minimal-XFCE-${ARCH}.iso"

cleanup() {
    if [[ "${KEEP_WORK:-0}" != "1" ]]; then
        rm -rf "$WORK_DIR"
    else
        echo "Keeping build work directory: $WORK_DIR"
    fi
}
trap cleanup EXIT

rm -rf "$BUILDER_DIR"
printf 'Fetching pinned Parrot ISO build configuration (%s)...\n' "$BUILDER_REF"
git init -q "$BUILDER_DIR"
git -C "$BUILDER_DIR" remote add origin "$BUILDER_URL"
git -C "$BUILDER_DIR" fetch --depth 1 origin "$BUILDER_REF"
git -C "$BUILDER_DIR" checkout --quiet --detach FETCH_HEAD

mkdir -p "$BUILDER_DIR/templates/variant-lite-xfce"
cp -a "$ROOT/iso/variant-lite-xfce/." "$BUILDER_DIR/templates/variant-lite-xfce/"
chmod 0755 "$BUILDER_DIR/templates/variant-lite-xfce/hooks/live/zzzz-parrot-lite-prune.chroot"

# The pinned upstream template still contains an old lory-backports upgrade.
# Skip that release-specific block for the Parrot 7.4 Echo build.
python3 - "$BUILDER_DIR/templates/common/hooks/live/parrot-hooks.chroot" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text()
pattern = re.compile(
    r"(?ms)^# Install any available update from lory-backports\.\n.*?"
    r"^# Add additional filesystem modules to initramfs"
)
replacement = (
    "# Backports upgrade intentionally skipped for the Parrot 7.4 Echo custom build.\n"
    "# Add additional filesystem modules to initramfs"
)
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    if "lory-backports" in text:
        raise SystemExit("Could not safely remove the stale lory-backports hook block")
path.write_text(text)
PY

# Parrot 7.4's parrot-core bootstrap requires dnsutils. On the Echo suite,
# bind9-dnsutils provides it; the old dnsutils package name is no longer shipped.
python3 - "$BUILDER_DIR/auto/config" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
needle = "--include=gnupg2,base-files,parrot-core,ca-certificates"
if text.count(needle) != 1:
    raise SystemExit("Could not safely add bind9-dnsutils to the Parrot bootstrap include list")
path.write_text(text.replace(needle, needle + ",bind9-dnsutils", 1))
PY

mkdir -p /usr/share/live/build/data/debian-cd
ln -sfn sid "/usr/share/live/build/data/debian-cd/$SUITE"
rm -f "$OUTPUT_FILE"
printf 'Building custom live ISO; this can take a while...\n'
if ! (
    cd "$BUILDER_DIR"
    ./build.sh --distribution "$SUITE" --version "$VERSION" \
        --variant lite-xfce --arch "$ARCH"
); then
    if [[ -f "$BUILDER_DIR/build.log" ]]; then
        echo 'Last 120 lines of the upstream build log:' >&2
        tail -120 "$BUILDER_DIR/build.log" >&2
    fi
    if [[ -f "$BUILDER_DIR/chroot/debootstrap/debootstrap.log" ]]; then
        echo 'Last 120 lines of the debootstrap log:' >&2
        tail -120 "$BUILDER_DIR/chroot/debootstrap/debootstrap.log" >&2
    fi
    exit 1
fi

[[ -s "$BUILT_ISO" ]] || {
    echo "Expected ISO was not created: $BUILT_ISO" >&2
    exit 1
}
mv -- "$BUILT_ISO" "$OUTPUT_FILE"
xorriso -indev "$OUTPUT_FILE" -report_el_torito plain >/dev/null
chmod 0644 "$OUTPUT_FILE"
(
    cd "$OUTPUT_DIR"
    sha256sum "$(basename "$OUTPUT_FILE")" > SHA256SUMS.txt
)
printf '\nCreated: %s\n' "$OUTPUT_FILE"
ls -lh "$OUTPUT_FILE" "$OUTPUT_DIR/SHA256SUMS.txt"

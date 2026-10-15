#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${PARROT_VERSION:-7.4}"
ARCH="${PARROT_ARCH:-amd64}"
EDITION="${PARROT_SOURCE_EDITION:-security}"
MIRROR="${PARROT_MIRROR:-https://deb.parrot.sh/parrot}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/artifacts}"
WORK_BASE="${WORK_DIR:-${TMPDIR:-/tmp}}"
EXPECTED_FINGERPRINT="B711822346552E4D92DA02DF7A8286AF0E81EE4A"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this builder as root (for example: sudo bash $0)." >&2
    exit 1
fi
if [[ "$VERSION" != "7.4" || "$ARCH" != "amd64" ]]; then
    echo "This verified image recipe is pinned to Parrot 7.4 AMD64." >&2
    exit 1
fi
if [[ "$EDITION" != "security" && "$EDITION" != "home" ]]; then
    echo "PARROT_SOURCE_EDITION must be 'security' or 'home'." >&2
    exit 1
fi

for tool in curl xz gpg awk sha512sum qemu-img virt-customize virt-sparsify; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "Missing build dependency: $tool" >&2
        exit 1
    }
done

SOURCE_NAME="Parrot-${EDITION}-${VERSION}_${ARCH}.qcow2.xz"
SOURCE_URL="$MIRROR/iso/$VERSION/$SOURCE_NAME"
mkdir -p "$OUTPUT_DIR" "$WORK_BASE"
[[ "$WORK_BASE" != "/" ]] || { echo "WORK_DIR must not be /" >&2; exit 1; }
WORK_DIR="$(mktemp -d "${WORK_BASE%/}/parrot-${VERSION}-${ARCH}-qcow2-XXXXXX")"
chmod 700 "$WORK_DIR"
GNUPGHOME="$WORK_DIR/gnupg"
mkdir -p "$GNUPGHOME"
chmod 700 "$GNUPGHOME"

SIGNED_HASHES="$WORK_DIR/signed-hashes.txt"
PARROT_KEY="$WORK_DIR/parrotsec.gpg"
COMPRESSED_SOURCE="$WORK_DIR/$SOURCE_NAME"
BASE_QCOW2="$WORK_DIR/${SOURCE_NAME%.xz}"
OUTPUT_FILE="$OUTPUT_DIR/Parrot-${VERSION}-Minimal-XFCE-${ARCH}.qcow2"

cleanup() {
    if [[ "${KEEP_WORK:-0}" != "1" ]]; then
        rm -rf "$WORK_DIR"
    else
        echo "Keeping build work directory: $WORK_DIR"
    fi
}
trap cleanup EXIT

printf 'Fetching Parrot signing key and %s hash list...\n' "$VERSION"
curl --fail --location --retry 5 --retry-all-errors --retry-delay 2 --silent --show-error \
    "$MIRROR/misc/parrotsec.gpg" -o "$PARROT_KEY"
curl --fail --location --retry 5 --retry-all-errors --retry-delay 2 --silent --show-error \
    "$MIRROR/iso/$VERSION/signed-hashes.txt" -o "$SIGNED_HASHES"
gpg --homedir "$GNUPGHOME" --batch --import "$PARROT_KEY"
if ! gpg --homedir "$GNUPGHOME" --batch --with-colons --list-keys \
    | awk -F: -v expected="$EXPECTED_FINGERPRINT" \
        '$1 == "fpr" && toupper($10) == expected { found = 1 } END { exit found ? 0 : 1 }'; then
    echo "The downloaded Parrot key did not match the documented fingerprint." >&2
    exit 1
fi
if ! gpg --homedir "$GNUPGHOME" --batch --verify "$SIGNED_HASHES" \
    >"$WORK_DIR/signature-check.log" 2>&1; then
    cat "$WORK_DIR/signature-check.log" >&2
    echo "Parrot's signed hash list did not verify." >&2
    exit 1
fi
cat "$WORK_DIR/signature-check.log"
EXPECTED_SHA512="$(awk -v filename="$SOURCE_NAME" '
    $0 == "sha512" { in_sha512 = 1; next }
    /^-----BEGIN PGP SIGNATURE-----/ { exit }
    in_sha512 && $2 == filename { print $1; exit }
' "$SIGNED_HASHES" | tr -d '[:space:]')"
if (( ${#EXPECTED_SHA512} != 128 )) || [[ ! "$EXPECTED_SHA512" =~ ^[[:xdigit:]]{128}$ ]]; then
    printf 'No valid SHA-512 entry found for %s (length=%d, value=%q).\n' \
        "$SOURCE_NAME" "${#EXPECTED_SHA512}" "$EXPECTED_SHA512" >&2
    exit 1
fi

printf 'Downloading official Parrot %s QCOW2 source...\n' "$EDITION"
curl --fail --location --retry 5 --retry-all-errors --retry-delay 2 --silent --show-error \
    --output "$COMPRESSED_SOURCE" "$SOURCE_URL"
printf '%s  %s\n' "$EXPECTED_SHA512" "$COMPRESSED_SOURCE" | sha512sum --check --status \
    || { echo "Official source image checksum mismatch." >&2; exit 1; }

rm -f "$BASE_QCOW2" "$OUTPUT_FILE"
printf 'Decompressing verified source image...\n'
xz --threads=0 --decompress --keep -- "$COMPRESSED_SOURCE"
rm -f "$COMPRESSED_SOURCE"
if ! qemu-img check "$BASE_QCOW2"; then
    echo "Official source QCOW2 integrity check failed; image metadata follows:" >&2
    qemu-img info "$BASE_QCOW2" >&2 || true
    exit 1
fi

export LIBGUESTFS_BACKEND="${LIBGUESTFS_BACKEND:-direct}"
export LIBGUESTFS_MEMSIZE="${LIBGUESTFS_MEMSIZE:-2048}"
MIRROR_HOST="${MIRROR#*://}"
MIRROR_HOST="${MIRROR_HOST%%/*}"
MIRROR_HOST="${MIRROR_HOST%%:*}"
MIRROR_IP="$(getent ahostsv4 "$MIRROR_HOST" | awk 'NR == 1 { print $1; exit }')"
if [[ -z "$MIRROR_IP" ]]; then
    echo "Could not resolve the Parrot mirror on the host: $MIRROR_HOST" >&2
    exit 1
fi
printf 'Removing security/office apps and installing XFCE (mirror %s -> %s)...\n' \
    "$MIRROR_HOST" "$MIRROR_IP"
GUEST_CUSTOMIZER=/tmp/parrot-lite-customize-guest.sh
virt-customize --add "$BASE_QCOW2" --network \
    --upload "$ROOT/scripts/customize-guest.sh:$GUEST_CUSTOMIZER" \
    --run-command "PARROT_MIRROR_HOST=$MIRROR_HOST PARROT_MIRROR_IP=$MIRROR_IP bash $GUEST_CUSTOMIZER" \
    --delete "$GUEST_CUSTOMIZER"

printf 'Sparsifying and compressing virtual disk...\n'
# The source image is disposable, so sparsify it in place and then write a
# compressed QCOW2 copy; this avoids virt-sparsify's larger temporary copy.
virt-sparsify --in-place "$BASE_QCOW2"
qemu-img convert -p -c -O qcow2 "$BASE_QCOW2" "$OUTPUT_FILE"
if ! qemu-img check "$OUTPUT_FILE"; then
    echo "Customized QCOW2 integrity check failed; image metadata follows:" >&2
    qemu-img info "$OUTPUT_FILE" >&2 || true
    exit 1
fi
qemu-img info "$OUTPUT_FILE"
chmod 0644 "$OUTPUT_FILE"
(
    cd "$OUTPUT_DIR"
    sha256sum "$(basename "$OUTPUT_FILE")" > SHA256SUMS.txt
)
printf '\nCreated: %s\n' "$OUTPUT_FILE"
ls -lh "$OUTPUT_FILE" "$OUTPUT_DIR/SHA256SUMS.txt"

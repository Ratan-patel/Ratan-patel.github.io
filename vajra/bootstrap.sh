#!/usr/bin/env bash
# ============================================================
#  VAJRA ⚡ one-line installer (Termux)
#  Install:  curl -fsSL <RAW_URL>/vajra/bootstrap.sh | bash
#  ya:       bash bootstrap.sh [--full]
# ============================================================
set -u
REPO="Ratan-patel/Ratan-patel.github.io"
BRANCH="${VAJRA_BRANCH:-main}"

echo "⚡ VAJRA download ho raha hai (repo: $REPO @ $BRANCH)…"

TMP="$(mktemp -d)"
URL="https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz"
if ! curl -fsSL "$URL" -o "$TMP/v.tar.gz"; then
  echo "✗ Download fail ($URL)"
  echo "  Branch merge nahi hua ho toh: VAJRA_BRANCH=<branch> bash bootstrap.sh"
  exit 1
fi
tar -xzf "$TMP/v.tar.gz" -C "$TMP" || { echo "✗ Extract fail"; exit 1; }
DIR="$(find "$TMP" -maxdepth 2 -type d -name vajra | head -1)"
[ -z "$DIR" ] && { echo "✗ vajra folder nahi mila"; exit 1; }
rm -rf "$HOME/vajra"
cp -r "$DIR" "$HOME/vajra"
cd "$HOME/vajra" || exit 1
echo "✓ Code mil gaya: ~/vajra"
bash install.sh "$@"

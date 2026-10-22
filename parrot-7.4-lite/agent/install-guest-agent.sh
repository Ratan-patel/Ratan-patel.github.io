#!/bin/sh
set -eu

SOURCE_BIN="${1:-/usr/share/parrot-ai/parrot-ai}"
SOURCE_DESKTOP="${2:-/usr/share/parrot-ai/parrot-ai.desktop}"

[ -f "$SOURCE_BIN" ] || { echo "Missing Parrot AI program: $SOURCE_BIN" >&2; exit 1; }
[ -f "$SOURCE_DESKTOP" ] || { echo "Missing Parrot AI desktop entry: $SOURCE_DESKTOP" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required for Parrot AI" >&2; exit 1; }
command -v sudo >/dev/null 2>&1 || { echo "sudo is required for Parrot AI" >&2; exit 1; }
python3 -c 'import pexpect' || { echo "python3-pexpect could not be imported" >&2; exit 1; }

install -D -o root -g root -m 0755 "$SOURCE_BIN" /usr/local/bin/parrot-ai
install -D -o root -g root -m 0644 "$SOURCE_DESKTOP" /usr/share/applications/parrot-ai.desktop

# Keep execution unrestricted within the guest, as selected for this agent.
# No per-command approval dialog is added; the model uses the existing guest
# sudo policy (the app invokes sudo non-interactively so it never hangs on a
# password prompt). This does not grant new sudo rights to the user.

if ! dpkg-query -W -f='${db:Status-Abbrev}\n' python3-pexpect 2>/dev/null | grep -q '^ii'; then
    echo "python3-pexpect must be installed before enabling Parrot AI" >&2
    exit 1
fi

printf 'Parrot AI terminal agent %s installed.\n' "$(/usr/local/bin/parrot-ai --version 2>&1 | sed 's/^parrot-ai //')"

#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
#  Ratan agent - Termux installer (run this ON YOUR PHONE, inside Termux)
#
#  What it does:
#    1. installs proot-distro + python in Termux
#    2. installs Ubuntu 26.04 LTS (Resolute Raccoon) userspace in a proot container
#    3. sets up the `ratan` AI agent inside that Ubuntu (Hugging Face powered)
#
#  Usage (in Termux):
#     curl -fsSL https://ratan-patel.github.io/ratan-agent/install-termux.sh | bash
#
#  Optional overrides:
#     UBUNTU_TAG=26.04        which Ubuntu to install
#     RATAN_BASE_URL=...      where to fetch ratan.py / install-ubuntu.sh
#     SKIP_HF_LOGIN=1         do not prompt for a Hugging Face token
# =============================================================================
set -euo pipefail

UBUNTU_TAG="${UBUNTU_TAG:-26.04}"
RATAN_BASE_URL="${RATAN_BASE_URL:-https://ratan-patel.github.io/ratan-agent}"
CONTAINER="${CONTAINER:-ubuntu}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo .)"

say()  { printf '\033[1;36m[ratan]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[ratan]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[ratan]\033[0m %s\n' "$*" >&2; exit 1; }

# --- 0. sanity checks -------------------------------------------------------
if [ -z "${PREFIX:-}" ] || ! command -v pkg >/dev/null 2>&1; then
  warn "This does not look like Termux (no \$PREFIX / pkg)."
  warn "On a normal Linux box use install-ubuntu.sh instead."
  read -r -p "Continue anyway? [y/N] " ans
  [ "${ans:-n}" = "y" ] || exit 1
fi

say "Termux found: ${PREFIX:-unknown}"
say "Phone kernel: $(uname -r)  (proot containers share this Android kernel)"

# --- 1. Termux packages -----------------------------------------------------
say "Updating Termux packages..."
pkg update -y || warn "pkg update reported an error; continuing"
pkg install -y python curl git proot-distro || die "could not install Termux packages"

if ! command -v proot-distro >/dev/null 2>&1; then
  die "proot-distro did not install. Try: pkg install proot-distro"
fi
say "proot-distro: $(proot-distro --version 2>/dev/null | head -1 || echo installed)"

# --- 2. Ubuntu 26.04 in proot ----------------------------------------------
if proot-distro list 2>/dev/null | grep -q "^ *${CONTAINER} "; then
  say "Ubuntu container '${CONTAINER}' already installed - skipping download"
else
  say "Installing Ubuntu ${UBUNTU_TAG} userspace (this downloads a few hundred MB)..."
  if ! proot-distro install "${CONTAINER}:${UBUNTU_TAG}"; then
    warn "ubuntu:${UBUNTU_TAG} not available - trying ubuntu:latest"
    proot-distro install "${CONTAINER}:latest" || proot-distro install "${CONTAINER}" \
      || die "could not install Ubuntu"
  fi
fi

say "Ubuntu userspace inside the container:"
proot-distro login "${CONTAINER}" -- bash -lc 'cat /etc/os-release | grep PRETTY_NAME; uname -r' || true

# --- 3. get the agent files into the container ------------------------------
fetch_into_container() {  # $1 = remote file name
  local name="$1"
  # (a) download straight from GitHub Pages inside Ubuntu
  if proot-distro login "${CONTAINER}" -- bash -lc \
       "curl -fsSL '${RATAN_BASE_URL}/${name}' -o /root/${name}"; then
    say "fetched ${name} from ${RATAN_BASE_URL}"
    return 0
  fi
  # (b) copy the local copy (running from a git clone / downloaded folder)
  if [ -f "${SCRIPT_DIR}/${name}" ]; then
    if proot-distro copy "${SCRIPT_DIR}/${name}" "${CONTAINER}:/root/${name}" 2>/dev/null; then
      say "copied local ${name} into the container"
      return 0
    fi
    # (c) pipe it through stdin (older proot-distro without `copy`)
    if proot-distro login "${CONTAINER}" -- bash -lc "cat > /root/${name}" < "${SCRIPT_DIR}/${name}"; then
      say "streamed local ${name} into the container"
      return 0
    fi
  fi
  return 1
}

fetch_into_container "ratan.py"          || die "could not place ratan.py in the container"
fetch_into_container "install-ubuntu.sh" || die "could not place install-ubuntu.sh in the container"

# --- 4. install inside Ubuntu ----------------------------------------------
say "Installing the ratan agent inside Ubuntu (python venv + huggingface_hub)..."
proot-distro login "${CONTAINER}" -- bash -lc 'bash /root/install-ubuntu.sh' \
  || die "install-ubuntu.sh failed inside the container"

# --- 5. Hugging Face token --------------------------------------------------
if [ "${SKIP_HF_LOGIN:-0}" != "1" ]; then
  say "Hugging Face token time."
  say "Free token: https://huggingface.co/settings/tokens  (permission: 'Make calls to Inference Providers')"
  read -r -p "Paste your HF token now (empty to skip): " HF_TOKEN_VALUE
  if [ -n "${HF_TOKEN_VALUE}" ]; then
    proot-distro login "${CONTAINER}" -- bash -lc "ratan login '${HF_TOKEN_VALUE}'" \
      && say "token saved inside Ubuntu"
  else
    warn "skipped - run 'ratan login' inside Ubuntu later"
  fi
fi

# --- 6. done ----------------------------------------------------------------
cat <<'EOF'

  ==============================================
   Ratan agent installed inside Ubuntu 26.04
  ==============================================

  Start it:
      proot-distro login ubuntu
      ratan doctor        # check token + connectivity
      ratan               # interactive terminal agent

  One-shot from Termux without entering Ubuntu:
      proot-distro login ubuntu -- ratan ask "disk kitna free hai?"

  Handy:
      ratan models qwen   # list models on the Hugging Face router
      ratan --model openai/gpt-oss-120b:fastest

  Note on "latest kernel": proot-distro runs Ubuntu *userspace* on your
  phone's Android kernel. Ubuntu 26.04 ships Linux 7.0, but that kernel
  cannot boot inside proot - `uname -r` in the container is a string
  proot reports. For a real 7.0 kernel use a VM (QEMU/qcow2), not Termux.

EOF

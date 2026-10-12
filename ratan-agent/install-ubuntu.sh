#!/usr/bin/env bash
# =============================================================================
#  Ratan agent - installer for the Ubuntu side
#  (runs INSIDE Ubuntu 26.04 in proot-distro, or on any Ubuntu/Debian box)
#
#  Usage:
#     bash install-ubuntu.sh
#
#  Result: `ratan` on PATH, backed by /opt/ratan/venv (python + huggingface_hub)
# =============================================================================
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/ratan}"
BIN_DIR="${BIN_DIR:-/usr/local/bin}"
SRC_PY="${SRC_PY:-/root/ratan.py}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

say()  { printf '\033[1;36m[ratan]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[ratan]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[ratan]\033[0m %s\n' "$*" >&2; exit 1; }

if [ "$(id -u)" != "0" ]; then
  warn "not root - will try without sudo; use sudo if this fails"
  SUDO="sudo"
else
  SUDO=""
fi

say "Ubuntu: $(. /etc/os-release && echo "$PRETTY_NAME")"
say "Kernel string reported here: $(uname -r)"

# --- 1. system packages -----------------------------------------------------
say "Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
$SUDO apt-get update -y
$SUDO apt-get install -y --no-install-recommends \
  python3 python3-venv python3-dev ca-certificates curl git less nano \
  || die "apt-get install failed"

$PYTHON_BIN --version || die "python3 missing"

# --- 2. virtualenv + Hugging Face SDK --------------------------------------
say "Creating virtualenv at ${INSTALL_DIR}/venv ..."
$SUDO mkdir -p "${INSTALL_DIR}"
$SUDO $PYTHON_BIN -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/python" -m pip install --upgrade pip >/dev/null
# huggingface_hub 2.x pulls its HTTP stack (httpx2) in as a core dependency.
# Older 1.x/0.x builds needed the [inference] extra, so that form is the fallback.
say "Installing huggingface_hub..."
"${INSTALL_DIR}/venv/bin/pip" install --upgrade "huggingface_hub>=1.0" \
  || "${INSTALL_DIR}/venv/bin/pip" install --upgrade "huggingface_hub[inference]" \
  || die "pip install failed"
"${INSTALL_DIR}/venv/bin/python" -c "from huggingface_hub import InferenceClient; import huggingface_hub; print('  huggingface_hub', huggingface_hub.__version__, 'InferenceClient OK')" \
  || die "huggingface_hub did not import correctly"

# --- 3. the agent itself ----------------------------------------------------
if [ -f "${SRC_PY}" ]; then
  $SUDO cp "${SRC_PY}" "${INSTALL_DIR}/ratan.py"
  say "installed ${SRC_PY} -> ${INSTALL_DIR}/ratan.py"
else
  say "fetching ratan.py from GitHub Pages..."
  curl -fsSL "https://ratan-patel.github.io/ratan-agent/ratan.py" -o "${INSTALL_DIR}/ratan.py" \
    || die "could not fetch ratan.py (set SRC_PY=/path/to/ratan.py)"
fi
$SUDO chmod 0755 "${INSTALL_DIR}/ratan.py"

$SUDO tee "${BIN_DIR}/ratan" >/dev/null <<EOF
#!/bin/sh
exec "${INSTALL_DIR}/venv/bin/python" "${INSTALL_DIR}/ratan.py" "\$@"
EOF
$SUDO chmod 0755 "${BIN_DIR}/ratan"

# --- 4. verify -------------------------------------------------------------
say "Verifying installation..."
"${BIN_DIR}/ratan" version || die "ratan did not run"
"${BIN_DIR}/ratan" doctor || warn "doctor reported a problem (probably no token yet)"

cat <<EOF

  ==============================================
   Ratan agent ready on Ubuntu
  ==============================================
  ratan login          # save your free Hugging Face token
  ratan doctor         # re-check token + network
  ratan                # start the terminal agent
  ratan ask "..."      # one-shot question

  Binary: ${BIN_DIR}/ratan
  Files : ${INSTALL_DIR}/ratan.py, ${INSTALL_DIR}/venv
EOF

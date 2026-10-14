#!/usr/bin/env bash
# RatanSec OS entrypoint — optional bootstrap + app start
set -euo pipefail

echo "[ratansec] starting…"

# Nuclei templates (agar missing hain aur user chahta hai)
if [ "${UPDATE_NUCLEI_TEMPLATES:-0}" = "1" ] && command -v nuclei >/dev/null 2>&1; then
  echo "[ratansec] nuclei templates update ho rahe hain…"
  nuclei -update-templates -duc -no-color -silent || echo "[ratansec] nuclei templates update fail — chalne me koi rukavat nahi."
fi

if [ -z "${APP_PASSWORD:-}" ]; then
  echo "[ratansec] ⚠️  APP_PASSWORD set nahi hai — dashboard bina auth ke khulega (public deploy ke liye password zaroor lagao)."
fi
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "[ratansec] ⚠️  OPENROUTER_API_KEY set nahi hai — AI chat off rahega (scans/tools chalte rahenge)."
fi
if [ -n "${ALLOWED_TARGETS:-}" ]; then
  echo "[ratansec] scope: ${ALLOWED_TARGETS}"
else
  echo "[ratansec] scope: khaali — har action ke liye manual approval lagegi."
fi

exec "$@"

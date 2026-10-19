#!/usr/bin/env sh
set -eu

exec /usr/local/libexec/parrot-passt --ipv4-only "$@"

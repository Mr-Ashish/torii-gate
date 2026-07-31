#!/usr/bin/env bash
# Torii Gate product entrypoint — security pack forced.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export TORII_ROOT="$ROOT"
export TORII_LENS_PACK="${TORII_LENS_PACK:-security}"
export TORII_PR_LABELS="${TORII_PR_LABELS:-1}"
export TORII_LABEL_PREFIX="${TORII_LABEL_PREFIX:-torii}"
export TORII_MEMORY_PATH="${TORII_MEMORY_PATH:-.torii}"
exec "$ROOT/scripts/run-torii-review.sh" "$@"

#!/usr/bin/env bash
# F8: Build (and optionally push) the prebaked Torii+Hermes runner image.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=hermes-pin.sh
PIN="$("$ROOT/scripts/hermes-pin.sh" default | tr -d '\n')"
PIN="${HERMES_COMMIT:-$PIN}"
SHORT="${PIN:0:12}"

IMAGE_BASE="${TORII_RUNNER_IMAGE_BASE:-ghcr.io/mr-ashish/torii-hermes-runner}"
TAG_PIN="${IMAGE_BASE}:${SHORT}"
TAG_LATEST="${IMAGE_BASE}:latest"

log() { echo "$*" >&2; }

command -v docker >/dev/null 2>&1 || {
  log "ERROR: docker not found"
  exit 1
}

log "Building $TAG_PIN (HERMES_COMMIT=$PIN)"
docker build \
  --build-arg "HERMES_COMMIT=$PIN" \
  -t "$TAG_PIN" \
  -t "$TAG_LATEST" \
  -f "$ROOT/docker/torii-runner/Dockerfile" \
  "$ROOT"

log "Smoke: hermes --version in image"
docker run --rm "$TAG_PIN" hermes --version

if [[ "${PUSH:-0}" == "1" ]]; then
  log "Pushing $TAG_PIN and $TAG_LATEST"
  docker push "$TAG_PIN"
  docker push "$TAG_LATEST"
fi

log "OK image=$TAG_PIN"
printf '%s\n' "$TAG_PIN"

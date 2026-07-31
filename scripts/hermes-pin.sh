#!/usr/bin/env bash
# F7: resolve Hermes install pin + install.sh args (no network).
#
# Env:
#   TORII_HERMES_COMMIT  full/short SHA, or empty/"latest"/"main" for floating tip
#
# Usage:
#   scripts/hermes-pin.sh resolve     → print effective pin (empty if floating)
#   scripts/hermes-pin.sh install-args → print args for: bash -s -- <args>
#   scripts/hermes-pin.sh matches <head> → exit 0 if installed HEAD matches pin
#   scripts/hermes-pin.sh cache-suffix → pin or "latest" (safe for cache keys)
#
# Default pin: known-good NousResearch/hermes-agent commit (update intentionally).
set -euo pipefail

# Upstream tip pinned for reproducible CI (2026-07-31; NousResearch/hermes-agent main).
# F25 single source of truth: bump ONLY here (workflows resolve via `default` when var unset).
# Set repo var TORII_HERMES_COMMIT=latest|main|floating to float on install.sh tip.
DEFAULT_HERMES_COMMIT="53559aaf86b84dadae83cd9bb605ca476f9a0606"

resolve_pin() {
  local raw="${TORII_HERMES_COMMIT-${DEFAULT_HERMES_COMMIT}}"
  # Explicit empty / latest / main → floating (install tracks install.sh default branch)
  if [[ -z "$raw" || "$raw" == "latest" || "$raw" == "main" || "$raw" == "floating" ]]; then
    printf ''
    return
  fi
  printf '%s' "$raw"
}

install_args() {
  local pin
  pin="$(resolve_pin)"
  # Non-interactive CI-friendly install
  printf '%s' "--skip-setup"
  if [[ -n "$pin" ]]; then
    # --force-commit: re-pin even if cached tree is newer than pin
    printf ' --commit %s --force-commit' "$pin"
  fi
  printf '\n'
}

# Exit 0 if installed git HEAD matches pin (prefix or full). No pin → always match.
matches() {
  local head="${1:-}"
  local pin
  pin="$(resolve_pin)"
  if [[ -z "$pin" ]]; then
    return 0
  fi
  if [[ -z "$head" ]]; then
    return 1
  fi
  # Normalize: match if either is a prefix of the other (short vs full SHA)
  if [[ "$head" == "$pin"* || "$pin" == "$head"* ]]; then
    return 0
  fi
  return 1
}

cache_suffix() {
  local pin
  pin="$(resolve_pin)"
  if [[ -z "$pin" ]]; then
    printf 'latest\n'
  else
    # Short form keeps GH cache key readable
    printf '%s\n' "${pin:0:12}"
  fi
}

cmd="${1:-resolve}"
case "$cmd" in
  resolve) resolve_pin; printf '\n' ;;
  install-args) install_args ;;
  matches) matches "${2:-}" ;;
  cache-suffix) cache_suffix ;;
  default) printf '%s\n' "$DEFAULT_HERMES_COMMIT" ;;
  *)
    echo "usage: $0 resolve|install-args|matches <head>|cache-suffix|default" >&2
    exit 2
    ;;
esac

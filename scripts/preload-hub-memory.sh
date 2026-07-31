#!/usr/bin/env bash
# Preload MEMORY.md into HERMES_HOME before review.
#
# Order (F28 repo-local memory):
#   1) Target repo .torii/MEMORY.md (or TORII_MEMORY_PATH) from default branch via API
#   2) Hub memory/repos/{slug}/MEMORY.md if hub opted in
#   3) Leave seed/local only
#
# Env:
#   REPO / GITHUB_REPOSITORY
#   HERMES_HOME
#   TORII_MEMORY_MODE   local|hub|both  (default local)
#   TORII_MEMORY_PATH   default .torii
#   TORII_HUB_REPO      default Mr-Ashish/torii-gate
#   TORII_MEMORY_TENANT F65 optional multi-tenant hub namespace
#   TORII_HUB_PUBLISH / TORII_HUB_TOKEN / GITHUB_TOKEN
set -euo pipefail

log() { echo "$*" >&2; }
notice() { echo "::notice::$*" >&2; log "$*"; }

REPO="${REPO:-${GITHUB_REPOSITORY:-}}"
HERMES_HOME="${HERMES_HOME:-}"
HUB_REPO="${TORII_HUB_REPO:-Mr-Ashish/torii-gate}"
TOKEN="${TORII_HUB_TOKEN:-${GH_TOKEN:-${GITHUB_TOKEN:-}}}"
MEM_PATH="${TORII_MEMORY_PATH:-.torii}"
MODE="${TORII_MEMORY_MODE:-local}"
MODE="$(printf '%s' "$MODE" | tr '[:upper:]' '[:lower:]')"
# F65: sanitize tenant (alnum/._- only)
TENANT="${TORII_MEMORY_TENANT:-}"
TENANT="$(printf '%s' "$TENANT" | tr -c 'A-Za-z0-9._-' '-' | sed 's/^-*//;s/-*$//' | cut -c1-64)"

if [[ -z "$REPO" || -z "$HERMES_HOME" ]]; then
  log "REPO/HERMES_HOME missing; skip memory preload"
  if [[ -n "${OUT_DIR:-}" && -f "$(dirname "${BASH_SOURCE[0]}")/memory-health.sh" ]]; then
    OUT_DIR="${OUT_DIR}" bash "$(dirname "${BASH_SOURCE[0]}")/memory-health.sh" record "MEMORY_SOURCE=skipped_no_repo" || true
  fi
  exit 0
fi

_MH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/memory-health.sh"
record_mh() {
  if [[ -n "${OUT_DIR:-}" && -f "$_MH" ]]; then
    OUT_DIR="$OUT_DIR" bash "$_MH" record "$1" >/dev/null || true
  fi
  echo "$1"
}

mkdir -p "$HERMES_HOME/memories"
LOCAL_DEST="$HERMES_HOME/memories/MEMORY.md"
record_mh "MEMORY_MODE=${MODE}"
record_mh "MEMORY_PATH=${MEM_PATH}"
if [[ -n "$TENANT" ]]; then
  record_mh "MEMORY_TENANT=${TENANT}"
fi

# Hub fallback allowed?
HUB_OK=0
if [[ "${TORII_HUB_PUBLISH:-}" == "1" ]]; then
  HUB_OK=1
fi
case "$MODE" in
  hub|both) HUB_OK=1 ;;
esac
# Explicit off wins
if [[ "${TORII_HUB_PUBLISH:-}" == "0" && "$MODE" != "hub" && "$MODE" != "both" ]]; then
  HUB_OK=0
fi

fetch_raw() {
  # $1 = owner/repo  $2 = path  → writes to $TMP, sets HTTP
  local api_repo="$1" path="$2"
  local API="https://api.github.com/repos/${api_repo}/contents/${path}"
  local HDR=(-H "Accept: application/vnd.github.raw+json")
  if [[ -n "$TOKEN" ]]; then
    HDR+=(-H "Authorization: Bearer ${TOKEN}")
  fi
  set +e
  HTTP=$(curl -sS -L -o "$TMP" -w "%{http_code}" "${HDR[@]}" "$API")
  set -e
}

merge_into_hermes() {
  # merge $TMP into LOCAL_DEST
  if [[ -f "$LOCAL_DEST" && -s "$LOCAL_DEST" ]]; then
    {
      cat "$TMP"
      echo ""
      echo "---"
      echo "## Local session notes"
      cat "$LOCAL_DEST"
    } >"${LOCAL_DEST}.merged"
    mv "${LOCAL_DEST}.merged" "$LOCAL_DEST"
  else
    cp -f "$TMP" "$LOCAL_DEST"
  fi
}

TMP="$(mktemp)"
HTTP=""

# F64: durable structured FP rules (optional companion to MEMORY.md)
preload_fp_rules() {
  local rules_api="${MEM_PATH}/fp-rules.json"
  rules_api="${rules_api#./}"
  local rules_tmp
  rules_tmp="$(mktemp)"
  local rules_http=""
  set +e
  local API="https://api.github.com/repos/${REPO}/contents/${rules_api}"
  local HDR=(-H "Accept: application/vnd.github.raw+json")
  if [[ -n "$TOKEN" ]]; then
    HDR+=(-H "Authorization: Bearer ${TOKEN}")
  fi
  rules_http=$(curl -sS -L -o "$rules_tmp" -w "%{http_code}" "${HDR[@]}" "$API" 2>/dev/null || echo "000")
  set -e
  if [[ "$rules_http" == "200" && -s "$rules_tmp" ]]; then
    mkdir -p "$HERMES_HOME/memories"
    cp -f "$rules_tmp" "$HERMES_HOME/memories/fp-rules.json"
    if [[ -n "${OUT_DIR:-}" ]]; then
      mkdir -p "$OUT_DIR"
      cp -f "$rules_tmp" "$OUT_DIR/fp-rules.json"
    fi
    notice "Preloaded F64 fp-rules: ${REPO}/${rules_api} ($(wc -c <"$rules_tmp" | tr -d ' ') bytes)"
    record_mh "FP_RULES=local"
  else
    record_mh "FP_RULES=missing"
  fi
  rm -f "$rules_tmp"
}

# 1) Repo-local .torii/MEMORY.md (default branch contents API — do not rely on sparse PR workspace)
LOCAL_MEM="${MEM_PATH}/MEMORY.md"
# strip leading ./
LOCAL_MEM="${LOCAL_MEM#./}"
fetch_raw "$REPO" "$LOCAL_MEM"
if [[ "$HTTP" == "200" && -s "$TMP" ]]; then
  merge_into_hermes
  notice "Preloaded local memory: ${REPO}/${LOCAL_MEM} ($(wc -c <"$LOCAL_DEST" | tr -d ' ') bytes)"
  record_mh "MEMORY_SOURCE=local"
  preload_fp_rules || true
  echo "HUB_MEMORY=local"
  rm -f "$TMP"
  exit 0
fi
log "No local memory yet at ${REPO}/${LOCAL_MEM} (HTTP ${HTTP:-?})"
# Still try F64 rules even when MEMORY.md is missing
preload_fp_rules || true

# 2) Hub fallback when opted in (F65: optional tenants/{tenant}/repos/{slug})
if [[ "$HUB_OK" == "1" ]]; then
  SLUG="$(printf '%s' "$REPO" | sed 's|/|--|g')"
  if [[ -n "$TENANT" ]]; then
    HUB_BASE="memory/tenants/${TENANT}/repos/${SLUG}"
  else
    HUB_BASE="memory/repos/${SLUG}"
  fi
  HUB_MEM="${HUB_BASE}/MEMORY.md"
  fetch_raw "$HUB_REPO" "$HUB_MEM"
  if [[ "$HTTP" == "200" && -s "$TMP" ]]; then
    merge_into_hermes
    notice "Preloaded hub memory: ${HUB_REPO}/${HUB_MEM} ($(wc -c <"$LOCAL_DEST" | tr -d ' ') bytes)"
    record_mh "MEMORY_SOURCE=hub"
    # F64/F65: also pull structured fp-rules from the same hub tree
    HUB_FP="${HUB_BASE}/fp-rules.json"
    fetch_raw "$HUB_REPO" "$HUB_FP"
    if [[ "$HTTP" == "200" && -s "$TMP" ]]; then
      mkdir -p "$HERMES_HOME/memories"
      cp -f "$TMP" "$HERMES_HOME/memories/fp-rules.json"
      if [[ -n "${OUT_DIR:-}" ]]; then
        mkdir -p "$OUT_DIR"
        cp -f "$TMP" "$OUT_DIR/fp-rules.json"
      fi
      notice "Preloaded hub F64 fp-rules: ${HUB_REPO}/${HUB_FP}"
      record_mh "FP_RULES=hub"
    fi
    echo "HUB_MEMORY=preloaded"
    rm -f "$TMP"
    exit 0
  fi
  log "No hub memory for ${HUB_BASE} (HTTP ${HTTP:-?}); using seed/local only"
  record_mh "MEMORY_SOURCE=missing"
  echo "HUB_MEMORY=missing"
else
  log "Hub preload skipped (mode=${MODE}, TORII_HUB_PUBLISH=${TORII_HUB_PUBLISH:-unset})"
  record_mh "MEMORY_SOURCE=seed"
  echo "HUB_MEMORY=skipped"
fi
rm -f "$TMP"

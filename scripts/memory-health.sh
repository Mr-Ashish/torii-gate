#!/usr/bin/env bash
# F30: write/read memory health for operators (preload + publish visibility).
#
# Subcommands:
#   record KEY=VALUE   append to $OUT_DIR/memory-health.env
#   summary            print Markdown section for $GITHUB_STEP_SUMMARY
#
# Does not fail the review pipeline — ops signal only.
set -euo pipefail

log() { echo "$*" >&2; }

OUT_DIR="${OUT_DIR:-.torii-out}"
HEALTH="${OUT_DIR}/memory-health.env"

cmd="${1:-summary}"
shift || true

record() {
  mkdir -p "$OUT_DIR"
  local kv="$1"
  # replace existing key if present
  local key="${kv%%=*}"
  if [[ -f "$HEALTH" ]] && grep -q "^${key}=" "$HEALTH" 2>/dev/null; then
    # portable rewrite without sed -i differences
    local tmp
    tmp="$(mktemp)"
    grep -v "^${key}=" "$HEALTH" >"$tmp" || true
    echo "$kv" >>"$tmp"
    mv "$tmp" "$HEALTH"
  else
    echo "$kv" >>"$HEALTH"
  fi
  # also echo for logs / capture
  echo "$kv"
}

get() {
  local key="$1" default="${2:-}"
  if [[ -f "$HEALTH" ]]; then
    local line
    line="$(grep "^${key}=" "$HEALTH" 2>/dev/null | tail -1 || true)"
    if [[ -n "$line" ]]; then
      echo "${line#*=}"
      return 0
    fi
  fi
  echo "$default"
}

case "$cmd" in
  record)
    [[ $# -ge 1 ]] || { log "usage: memory-health.sh record KEY=VALUE"; exit 1; }
    record "$1"
    ;;
  summary)
    mkdir -p "$OUT_DIR"
    src="$(get MEMORY_SOURCE unknown)"
    local_pub="$(get LOCAL_PUBLISH unknown)"
    hub_pub="$(get HUB_PUBLISH unknown)"
    mode="$(get MEMORY_MODE "${TORII_MEMORY_MODE:-local}")"
    path="$(get MEMORY_PATH "${TORII_MEMORY_PATH:-.torii}")"
    echo "### Torii memory health (F30)"
    echo ""
    echo "| Field | Value |"
    echo "|-------|-------|"
    echo "| **Mode** | \`${mode}\` |"
    echo "| **Path** | \`${path}\` |"
    echo "| **Preload source** | \`${src}\` |"
    echo "| **Local publish** | \`${local_pub}\` |"
    echo "| **Hub publish** | \`${hub_pub}\` |"
    echo ""
    case "$local_pub" in
      failed|no_token|error|missing_repo)
        echo "> ⚠️ **Local \`.torii/\` memory did not land.** Next review may not see this run's notes."
        echo "> Check branch protection (bot push to default branch), \`contents: write\`, and job logs for \`LOCAL_PUBLISH=\`."
        echo ""
        ;;
      ok|noop|skipped)
        echo "> Local memory stage: **${local_pub}** (slim pack under \`.torii/\`; fat traces remain artifacts)."
        echo ""
        ;;
      *)
        echo "> Local memory stage: **${local_pub}**."
        echo ""
        ;;
    esac
    ;;
  warn-if-bad)
    local_pub="$(get LOCAL_PUBLISH unknown)"
    case "$local_pub" in
      failed|no_token|error|missing_repo)
        echo "::warning::F30 local .torii memory publish=${local_pub} — durable memory may be stale (branch protection / token / push). See job summary Memory health."
        ;;
    esac
    ;;
  *)
    log "usage: memory-health.sh record|summary|warn-if-bad"
    exit 1
    ;;
esac

#!/usr/bin/env bash
# Publish a Torii run into the central hub memory.
#
# Modes (auto):
#   1) direct  — clone hub, run hub-ingest-run.py, commit+push (needs write token)
#   2) dispatch — repository_dispatch torii-run (needs classic PAT; GITHUB_TOKEN cannot)
#
# Env:
#   TORII_HUB_REPO     default Mr-Ashish/torii-gate
#   TORII_HUB_TOKEN    write token (or GH_TOKEN/GITHUB_TOKEN)
#   TORII_HUB_MODE     auto|direct|dispatch  (default auto)
#   TORII_MEMORY_MODE  local|hub|both  (default local — hub off unless hub|both or TORII_HUB_PUBLISH=1)
#   TORII_MEMORY_TENANT F65 optional multi-tenant hub namespace (memory/tenants/{t}/repos/…)
#   TORII_HUB_PUBLISH  1 to force hub publish; 0 to force skip
#   OUT_DIR, REPO, PR_NUMBER, ...
set -euo pipefail

log() { echo "$*" >&2; }
notice() { echo "::notice::$*" >&2; log "$*"; }

MODE_MEM="${TORII_MEMORY_MODE:-local}"
MODE_MEM="$(printf '%s' "$MODE_MEM" | tr '[:upper:]' '[:lower:]')"

# Default hub publish: off for local (F28); on for hub|both; explicit TORII_HUB_PUBLISH wins
if [[ -z "${TORII_HUB_PUBLISH:-}" ]]; then
  case "$MODE_MEM" in
    hub|both) TORII_HUB_PUBLISH=1 ;;
    *) TORII_HUB_PUBLISH=0 ;;
  esac
fi

TORII_ROOT="${TORII_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_DIR="${OUT_DIR:-$TORII_ROOT/.torii-out}"
_MH="$TORII_ROOT/scripts/memory-health.sh"
record_mh() {
  if [[ -f "$_MH" ]]; then
    OUT_DIR="$OUT_DIR" bash "$_MH" record "$1" >/dev/null || true
  fi
  echo "$1"
}

if [[ "${TORII_HUB_PUBLISH}" == "0" ]]; then
  log "TORII_HUB_PUBLISH=0 (mode=${MODE_MEM}); skip hub publish"
  record_mh "HUB_PUBLISH=skipped"
  exit 0
fi

HUB_REPO="${TORII_HUB_REPO:-Mr-Ashish/torii-gate}"
TOKEN="${TORII_HUB_TOKEN:-${GH_TOKEN:-${GITHUB_TOKEN:-}}}"
MODE="${TORII_HUB_MODE:-auto}"
SOURCE_REPO="${REPO:-${GITHUB_REPOSITORY:-}}"

if [[ -z "$TOKEN" ]]; then
  log "No TORII_HUB_TOKEN/GITHUB_TOKEN; skip hub publish"
  record_mh "HUB_PUBLISH=no_token"
  exit 0
fi

command -v gh >/dev/null 2>&1 || { log "gh not found; skip"; exit 0; }
command -v python3 >/dev/null 2>&1 || { log "python3 not found; skip"; exit 0; }
command -v git >/dev/null 2>&1 || { log "git not found; skip"; exit 0; }

export OUT_DIR
python3 "$TORII_ROOT/scripts/build-hub-payload.py"
PAYLOAD="$OUT_DIR/hub-payload.json"
[[ -f "$PAYLOAD" ]] || { log "missing hub-payload.json"; exit 1; }

python3 - <<'PY' "$PAYLOAD" "$OUT_DIR/client_payload.json"
import json, sys
payload = json.loads(open(sys.argv[1]).read())
open(sys.argv[2], "w").write(json.dumps({"run": payload}, indent=2) + "\n")
print(sys.argv[2])
PY

export GH_TOKEN="$TOKEN"

# Decide mode
if [[ "$MODE" == "auto" ]]; then
  # Prefer direct write — works with GITHUB_TOKEN (contents:write) and PATs.
  # repository_dispatch is NOT allowed for GITHUB_TOKEN (403 integration).
  MODE="direct"
fi

publish_direct() {
  notice "Hub publish mode=direct → $HUB_REPO"
  WORK="$(mktemp -d)"
  cleanup() { rm -rf "$WORK"; }
  trap cleanup EXIT

  git clone --depth 1 \
    "https://x-access-token:${TOKEN}@github.com/${HUB_REPO}.git" \
    "$WORK/hub"

  # Prefer hub's own ingest script (from cloned main); fall back to local copy
  INGEST="$WORK/hub/scripts/hub-ingest-run.py"
  if [[ ! -f "$INGEST" ]]; then
    mkdir -p "$WORK/hub/scripts"
    cp -f "$TORII_ROOT/scripts/hub-ingest-run.py" "$INGEST"
  fi

  (
    cd "$WORK/hub"
    git config user.name "torii-hub-bot"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    export CLIENT_PAYLOAD_FILE="$OUT_DIR/client_payload.json"
    export HUB_ROOT="$WORK/hub"
    export TORII_INGEST_LAYOUT=hub
    # F65: pass tenant into ingest (also embedded in hub-payload.tenant)
    if [[ -n "${TORII_MEMORY_TENANT:-}" ]]; then
      export TORII_MEMORY_TENANT
    fi
    python3 "$INGEST"
    git add memory/
    if git diff --cached --quiet; then
      log "No memory changes to commit"
      return 0
    fi
    MSG="chore(memory): ingest ${SOURCE_REPO} PR #${PR_NUMBER:-?} $(date -u +%Y-%m-%dT%H%MZ)"
    git commit -m "$MSG"
    for i in 1 2 3 4 5; do
      if git pull --rebase origin main && git push origin HEAD:main; then
        notice "Pushed hub memory update to $HUB_REPO"
        echo "HUB_PUBLISH=direct_ok"
        echo "direct_ok" >"$OUT_DIR/.hub-publish-rc"
        return 0
      fi
      log "push retry $i"
      sleep $((i * 2))
    done
    log "direct push failed after retries"
    echo "failed" >"$OUT_DIR/.hub-publish-rc"
    return 1
  )
}

publish_dispatch() {
  notice "Hub publish mode=dispatch → $HUB_REPO (repository_dispatch torii-run)"
  python3 - <<'PY' "$OUT_DIR/client_payload.json" "$OUT_DIR/dispatch-body.json"
import json, sys
client = json.loads(open(sys.argv[1]).read())
body = {"event_type": "torii-run", "client_payload": client}
open(sys.argv[2], "w").write(json.dumps(body))
print(sys.argv[2])
PY
  set +e
  gh api --method POST \
    -H "Accept: application/vnd.github+json" \
    "/repos/${HUB_REPO}/dispatches" \
    --input "$OUT_DIR/dispatch-body.json"
  RC=$?
  set -e
  if [[ $RC -ne 0 ]]; then
    log "repository_dispatch failed (rc=$RC)"
    return "$RC"
  fi
  notice "Hub dispatch accepted (Ingest Torii Run should start)"
  echo "HUB_PUBLISH=dispatch_ok"
}

rm -f "$OUT_DIR/.hub-publish-rc" 2>/dev/null || true
set +e
case "$MODE" in
  direct)
    publish_direct
    HRC=$?
    ;;
  dispatch)
    publish_dispatch
    HRC=$?
    [[ $HRC -eq 0 ]] && echo "dispatch_ok" >"$OUT_DIR/.hub-publish-rc"
    ;;
  both)
    publish_direct || true
    publish_dispatch || true
    HRC=0
    ;;
  *)
    log "Unknown TORII_HUB_MODE=$MODE"
    set -e
    exit 1
    ;;
esac
set -e
if [[ -f "$OUT_DIR/.hub-publish-rc" ]]; then
  record_mh "HUB_PUBLISH=$(tr -d '[:space:]' <"$OUT_DIR/.hub-publish-rc")"
  rm -f "$OUT_DIR/.hub-publish-rc"
elif [[ "${HRC:-1}" -eq 0 ]]; then
  record_mh "HUB_PUBLISH=ok"
else
  record_mh "HUB_PUBLISH=failed"
  echo "::warning::F30 hub memory publish failed (mode=${MODE})"
fi

#!/usr/bin/env bash
# Publish a Torii run into the *target* repo under .torii/ (repo-local memory).
#
# Writes slim pack only: MEMORY.md + runs/{trace_id}/{meta.json,review.md,summary.md}
# Fat traces stay as Actions artifacts (save-trace.sh) — never committed here.
#
# Env:
#   TORII_MEMORY_MODE   local|hub|both  (default local)
#   TORII_LOCAL_PUBLISH 0 to skip (default: on when mode is local|both)
#   TORII_MEMORY_PATH   default .torii
#   REPO / GITHUB_REPOSITORY  target repo owner/name
#   GITHUB_TOKEN / GH_TOKEN    contents:write on target
#   OUT_DIR, PR_NUMBER, TORII_ROOT, ...
set -euo pipefail

log() { echo "$*" >&2; }
notice() { echo "::notice::$*" >&2; log "$*"; }

MODE="${TORII_MEMORY_MODE:-local}"
MODE="$(printf '%s' "$MODE" | tr '[:upper:]' '[:lower:]')"
# Local publish default: on for local|both
if [[ -z "${TORII_LOCAL_PUBLISH:-}" ]]; then
  case "$MODE" in
    hub) TORII_LOCAL_PUBLISH=0 ;;
    *) TORII_LOCAL_PUBLISH=1 ;;
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

if [[ "${TORII_LOCAL_PUBLISH}" == "0" ]]; then
  log "TORII_LOCAL_PUBLISH=0; skip local .torii publish"
  record_mh "LOCAL_PUBLISH=skipped"
  exit 0
fi

TOKEN="${TORII_LOCAL_TOKEN:-${GH_TOKEN:-${GITHUB_TOKEN:-}}}"
SOURCE_REPO="${REPO:-${GITHUB_REPOSITORY:-}}"
MEM_PATH="${TORII_MEMORY_PATH:-.torii}"
# Branch to commit memory onto (default branch of target)
BRANCH="${TORII_MEMORY_BRANCH:-}"
record_mh "MEMORY_MODE=${MODE}"
record_mh "MEMORY_PATH=${MEM_PATH}"

if [[ -z "$SOURCE_REPO" ]]; then
  log "REPO/GITHUB_REPOSITORY missing; skip local publish"
  echo "::warning::F30 local .torii publish skipped — REPO missing"
  record_mh "LOCAL_PUBLISH=missing_repo"
  exit 1
fi
if [[ -z "$TOKEN" ]]; then
  log "No GITHUB_TOKEN; cannot publish local .torii memory"
  echo "::warning::F30 local .torii publish failed — no GITHUB_TOKEN (need contents: write)"
  record_mh "LOCAL_PUBLISH=no_token"
  exit 1
fi

command -v python3 >/dev/null 2>&1 || {
  log "python3 not found; skip"
  record_mh "LOCAL_PUBLISH=error"
  echo "::warning::F30 local .torii publish failed — python3 missing"
  exit 1
}
command -v git >/dev/null 2>&1 || {
  log "git not found; skip"
  record_mh "LOCAL_PUBLISH=error"
  echo "::warning::F30 local .torii publish failed — git missing"
  exit 1
}

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

# Resolve default branch if not set
if [[ -z "$BRANCH" ]]; then
  if command -v gh >/dev/null 2>&1; then
    BRANCH="$(gh api "repos/${SOURCE_REPO}" --jq .default_branch 2>/dev/null || true)"
  fi
  BRANCH="${BRANCH:-main}"
fi

notice "Local memory publish → ${SOURCE_REPO}@${BRANCH} path=${MEM_PATH}"
WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT
mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR/.local-publish-rc"

set +e
git clone --depth 1 --branch "$BRANCH" \
  "https://x-access-token:${TOKEN}@github.com/${SOURCE_REPO}.git" \
  "$WORK/target" 2>/dev/null \
  || git clone --depth 1 \
    "https://x-access-token:${TOKEN}@github.com/${SOURCE_REPO}.git" \
    "$WORK/target"
CLONE_RC=$?
set -e
if [[ $CLONE_RC -ne 0 || ! -d "$WORK/target/.git" ]]; then
  record_mh "LOCAL_PUBLISH=error"
  echo "::warning::F30 local .torii publish failed — could not clone ${SOURCE_REPO}@${BRANCH}"
  exit 1
fi

INGEST="$TORII_ROOT/scripts/hub-ingest-run.py"
set +e
(
  cd "$WORK/target"
  git config user.name "torii-memory-bot"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  export CLIENT_PAYLOAD_FILE="$OUT_DIR/client_payload.json"
  export TORII_INGEST_LAYOUT=local
  export TORII_MEMORY_ROOT="$WORK/target"
  export TORII_MEMORY_PATH="$MEM_PATH"
  python3 "$INGEST" || exit 2
  git add -- "$MEM_PATH"
  if git diff --cached --quiet; then
    log "No local memory changes to commit"
    echo "noop" >"$OUT_DIR/.local-publish-rc"
    exit 0
  fi
  MSG="chore(memory): torii local ingest PR #${PR_NUMBER:-?} $(date -u +%Y-%m-%dT%H%MZ)"
  git commit -m "$MSG"
  PUSH_REF="$(git rev-parse --abbrev-ref HEAD)"
  for i in 1 2 3 4 5; do
    if git pull --rebase origin "$PUSH_REF" 2>/dev/null || git pull --rebase origin "$BRANCH" 2>/dev/null; then
      :
    fi
    if git push origin "HEAD:${BRANCH}"; then
      notice "Pushed local .torii memory to ${SOURCE_REPO}@${BRANCH}"
      echo "ok" >"$OUT_DIR/.local-publish-rc"
      exit 0
    fi
    log "local push retry $i"
    sleep $((i * 2))
  done
  log "local push failed after retries (branch protection may require a PAT)"
  echo "failed" >"$OUT_DIR/.local-publish-rc"
  exit 1
)
SUB_RC=$?
set -e

_status="error"
if [[ -f "$OUT_DIR/.local-publish-rc" ]]; then
  _status="$(tr -d '[:space:]' <"$OUT_DIR/.local-publish-rc")"
  rm -f "$OUT_DIR/.local-publish-rc"
elif [[ $SUB_RC -ne 0 ]]; then
  _status="error"
fi
case "$_status" in
  ok)
    record_mh "LOCAL_PUBLISH=ok"
    ;;
  noop)
    record_mh "LOCAL_PUBLISH=noop"
    ;;
  failed)
    record_mh "LOCAL_PUBLISH=failed"
    echo "::warning::F30 local .torii push failed after retries — branch protection may block GITHUB_TOKEN; use a PAT with contents:write or allow bot pushes to default branch"
    exit 1
    ;;
  *)
    record_mh "LOCAL_PUBLISH=error"
    echo "::warning::F30 local .torii publish error (clone/ingest/push rc=${SUB_RC})"
    exit 1
    ;;
esac

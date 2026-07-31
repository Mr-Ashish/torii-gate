#!/usr/bin/env bash
# F24: Dismiss prior Torii formal PR reviews on the same PR (Reviews-panel hygiene).
#
# Finds reviews whose body contains `<!-- torii-pr-review pr=N` and dismisses
# those still in APPROVED or CHANGES_REQUESTED state. COMMENTED reviews cannot
# be dismissed via the GitHub API and are left alone (logged).
#
# Soft-fail always (exit 0) — never block posting a new review.
#
# Usage:
#   ./scripts/dismiss-prior-pr-reviews.sh [pr_number]
#
# Env:
#   REPO / GITHUB_REPOSITORY
#   PR_NUMBER
#   GH_TOKEN / GITHUB_TOKEN
#   TORII_REPLACE_PREVIOUS — 1 (default) to dismiss; 0/off to skip
#   TORII_PR_REVIEWS_FIXTURE — optional JSON array of {id,state,body} (no network)
#
# Stdout: key=value lines dismissed_count= N skipped_commented= N
set -euo pipefail

log() { echo "$*" >&2; }

REPO="${REPO:-${GITHUB_REPOSITORY:-}}"
PR_NUMBER="${1:-${PR_NUMBER:-}}"
TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
REPLACE="${TORII_REPLACE_PREVIOUS:-1}"

case "${REPLACE}" in
  0|false|FALSE|off|OFF|no|NO)
    log "F24 skip dismiss (TORII_REPLACE_PREVIOUS=$REPLACE)"
    echo "dismissed_count=0"
    echo "skipped_commented=0"
    echo "reason=replace_off"
    exit 0
    ;;
esac

if [[ -z "$REPO" || -z "$PR_NUMBER" ]]; then
  log "F24 skip dismiss (missing REPO/PR_NUMBER)"
  echo "dismissed_count=0"
  echo "skipped_commented=0"
  echo "reason=missing_args"
  exit 0
fi

marker="<!-- torii-pr-review pr=${PR_NUMBER}"
export MARKER="$marker"
export REPO PR_NUMBER TOKEN

# Collect review JSON array → select dismissable / commented-only ids
# shellcheck disable=SC2016
select_py='
import json, os, sys

marker = os.environ["MARKER"]
raw = sys.stdin.read()
reviews = []
if raw.strip():
    # gh --paginate may emit concatenated JSON arrays
    dec = json.JSONDecoder()
    idx = 0
    s = raw.lstrip()
    while idx < len(s):
        while idx < len(s) and s[idx].isspace():
            idx += 1
        if idx >= len(s):
            break
        try:
            obj, end = dec.raw_decode(s, idx)
        except json.JSONDecodeError:
            break
        idx = end
        if isinstance(obj, list):
            reviews.extend(obj)
        elif isinstance(obj, dict):
            reviews.append(obj)

dismissable = []
commented = []
for r in reviews:
    if not isinstance(r, dict):
        continue
    body = r.get("body") or ""
    if marker not in body:
        continue
    rid = r.get("id")
    state = (r.get("state") or "").upper()
    if rid is None:
        continue
    if state in ("APPROVED", "CHANGES_REQUESTED"):
        dismissable.append(str(rid))
    elif state in ("COMMENTED", "PENDING"):
        commented.append(str(rid))
    # DISMISSED: ignore

print("DISMISSABLE=" + " ".join(dismissable))
print("COMMENTED=" + " ".join(commented))
'

if [[ -n "${TORII_PR_REVIEWS_FIXTURE:-}" && -f "${TORII_PR_REVIEWS_FIXTURE}" ]]; then
  log "F24 using fixture $TORII_PR_REVIEWS_FIXTURE"
  SEL="$(python3 -c "$select_py" <"$TORII_PR_REVIEWS_FIXTURE" 2>/dev/null || true)"
else
  if [[ -z "$TOKEN" ]] || ! command -v gh >/dev/null 2>&1; then
    log "F24 skip dismiss (no gh/token)"
    echo "dismissed_count=0"
    echo "skipped_commented=0"
    echo "reason=no_gh"
    exit 0
  fi
  export GH_TOKEN="$TOKEN"
  RAW="$(
    gh api --paginate "repos/${REPO}/pulls/${PR_NUMBER}/reviews" 2>/dev/null || true
  )"
  SEL="$(printf '%s' "$RAW" | python3 -c "$select_py" 2>/dev/null || true)"
fi

DISMISSABLE=""
COMMENTED=""
while IFS= read -r line || [[ -n "$line" ]]; do
  case "$line" in
    DISMISSABLE=*) DISMISSABLE="${line#DISMISSABLE=}" ;;
    COMMENTED=*) COMMENTED="${line#COMMENTED=}" ;;
  esac
done <<<"${SEL:-}"

skipped=0
for _ in $COMMENTED; do
  skipped=$((skipped + 1))
done
if [[ "$skipped" -gt 0 ]]; then
  log "F24 $skipped prior Torii COMMENTED review(s) cannot be dismissed (API limit)"
fi

dismissed=0
if [[ -n "${TORII_PR_REVIEWS_FIXTURE:-}" ]]; then
  # Dry path for tests: count only, do not call API
  for _ in $DISMISSABLE; do
    dismissed=$((dismissed + 1))
  done
  log "F24 fixture would dismiss $dismissed review(s)"
else
  for rid in $DISMISSABLE; do
    [[ -z "$rid" ]] && continue
    if gh api --method PUT \
      -H "Accept: application/vnd.github+json" \
      "/repos/${REPO}/pulls/${PR_NUMBER}/reviews/${rid}/dismissals" \
      -f message="Superseded by newer Torii Gate review" \
      -f event="DISMISS" >/dev/null 2>&1; then
      log "F24 dismissed prior Torii Gate review id=$rid"
      dismissed=$((dismissed + 1))
    else
      log "warn: F24 could not dismiss review id=$rid"
    fi
  done
fi

echo "dismissed_count=${dismissed}"
echo "skipped_commented=${skipped}"
echo "reason=ok"
exit 0

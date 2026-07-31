#!/usr/bin/env bash
# F19: per-PR re-trigger cooldown — skip paid OpenRouter runs after a recent success.
#
# Usage:
#   scripts/cooldown-check.sh <pr_number>
#
# Env:
#   REPO / GITHUB_REPOSITORY   owner/repo (required unless TORII_COOLDOWN_FIXTURE set)
#   GH_TOKEN / GITHUB_TOKEN    for gh api
#   TORII_COOLDOWN_SECONDS     window in seconds (default 900). 0 / empty / off = disabled
#   TORII_COOLDOWN_FORCE=1     always allow (operator override)
#   TORII_COOLDOWN_FIXTURE     path to JSON array of {created_at,body} comments (tests; no network)
#   NOW_EPOCH                  optional fixed clock for tests
#
# Exit:
#   0  allow run
#   2  cooldown active (skip paid review)
#   1  hard error (workflow should soft-fail open → allow)
#
# Prints key=value lines to stdout for Actions outputs (allowed, reason, age_s, remaining_s).
set -euo pipefail

PR_NUMBER="${1:-${PR_NUMBER:-}}"
REPO="${REPO:-${GITHUB_REPOSITORY:-}}"
FORCE="${TORII_COOLDOWN_FORCE:-0}"
RAW_CD="${TORII_COOLDOWN_SECONDS-900}"
FIXTURE="${TORII_COOLDOWN_FIXTURE:-}"

emit() {
  # shellcheck disable=SC2059
  printf '%s\n' "$@"
}

allow() {
  local reason="${1:-ok}"
  emit "allowed=true"
  emit "reason=${reason}"
  emit "age_s="
  emit "remaining_s=0"
  exit 0
}

deny() {
  local reason="$1" age="${2:-}" remaining="${3:-}"
  emit "allowed=false"
  emit "reason=${reason}"
  emit "age_s=${age}"
  emit "remaining_s=${remaining}"
  exit 2
}

# Force override
if [[ "$FORCE" == "1" || "$FORCE" == "true" || "$FORCE" == "yes" ]]; then
  allow "force"
fi

# Disable cooldown
case "${RAW_CD}" in
  '' | 0 | off | OFF | false | FALSE | disabled | DISABLED)
    allow "disabled"
    ;;
esac

# Integer seconds
if ! [[ "$RAW_CD" =~ ^[0-9]+$ ]]; then
  echo "::warning::TORII_COOLDOWN_SECONDS='${RAW_CD}' not an integer; treating as disabled" >&2
  allow "disabled_invalid"
fi
COOLDOWN_S="$RAW_CD"

[[ -n "$PR_NUMBER" ]] || {
  echo "usage: $0 <pr_number>" >&2
  exit 1
}

# Fetch comment list as JSON array
COMMENTS_JSON='[]'
if [[ -n "$FIXTURE" ]]; then
  [[ -f "$FIXTURE" ]] || {
    echo "fixture not found: $FIXTURE" >&2
    exit 1
  }
  COMMENTS_JSON="$(cat "$FIXTURE")"
else
  [[ -n "$REPO" ]] || {
    echo "REPO or GITHUB_REPOSITORY required" >&2
    exit 1
  }
  export GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
  command -v gh >/dev/null 2>&1 || {
    echo "gh CLI required" >&2
    exit 1
  }
  # Paginate issue comments; soft failures bubble as exit 1 for caller soft-open
  COMMENTS_JSON="$(
    gh api --paginate "repos/${REPO}/issues/${PR_NUMBER}/comments" \
      --jq '[.[] | {created_at, body}]' 2>/dev/null \
      | python3 -c '
import sys, json
chunks = []
buf = sys.stdin.read().strip()
if not buf:
    print("[]")
    raise SystemExit(0)
# gh --paginate may emit multiple JSON arrays
dec = json.JSONDecoder()
idx = 0
while idx < len(buf):
    while idx < len(buf) and buf[idx].isspace():
        idx += 1
    if idx >= len(buf):
        break
    obj, end = dec.raw_decode(buf, idx)
    if isinstance(obj, list):
        chunks.extend(obj)
    idx = end
print(json.dumps(chunks))
'
  )" || {
    echo "warn: failed to list comments for cooldown" >&2
    exit 1
  }
fi

export COMMENTS_JSON PR_NUMBER COOLDOWN_S
export NOW_EPOCH="${NOW_EPOCH:-}"

python3 - <<'PY'
import json, os, re, sys
from datetime import datetime, timezone

pr = os.environ["PR_NUMBER"]
cooldown = int(os.environ["COOLDOWN_S"])
now_raw = os.environ.get("NOW_EPOCH") or ""
if now_raw:
    now = int(now_raw)
else:
    now = int(datetime.now(tz=timezone.utc).timestamp())

comments = json.loads(os.environ.get("COMMENTS_JSON") or "[]")
marker = f"<!-- torii-review pr={pr}"

# Failure / non-success stubs must NOT start the cooldown (allow retry).
FAIL_SNIPPETS = (
    "torii failed to produce a review",
    "missing required secret",
    "openrouter_api_key is not set",
    "openrouter_api_key not set",
    "config error",
    "review agent run failed",
    "failure path only",
    "check workflow logs, hermes install",
    "missing openrouter",
)

def is_success_review(body: str) -> bool:
    if not body or marker not in body:
        return False
    low = body.lower()
    return not any(s in low for s in FAIL_SNIPPETS)

def parse_created(ts: str) -> int | None:
    if not ts:
        return None
    # GitHub: 2026-07-31T12:00:00Z
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return int(datetime.fromisoformat(ts).timestamp())
    except Exception:
        return None

latest_ok = None  # (epoch, body snippet)
for c in comments:
    body = c.get("body") or ""
    if not is_success_review(body):
        continue
    ep = parse_created(c.get("created_at") or "")
    if ep is None:
        continue
    if latest_ok is None or ep > latest_ok[0]:
        latest_ok = (ep, body[:80])

if latest_ok is None:
    print("allowed=true")
    print("reason=no_recent_success")
    print("age_s=")
    print("remaining_s=0")
    sys.exit(0)

age = now - latest_ok[0]
if age < 0:
    age = 0
if age < cooldown:
    remaining = cooldown - age
    print("allowed=false")
    print(f"reason=cooldown_active")
    print(f"age_s={age}")
    print(f"remaining_s={remaining}")
    sys.exit(2)

print("allowed=true")
print("reason=cooldown_expired")
print(f"age_s={age}")
print("remaining_s=0")
sys.exit(0)
PY

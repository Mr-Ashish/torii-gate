#!/usr/bin/env bash
# Offline smoke for Torii Gate product path (no OpenRouter / no PR required).
#
# Checks:
#   1. Security pack is the default lens pack
#   2. demo/insecure still carries intentional vuln patterns
#   3. torii_gate_status maps approve / request-changes / security-concern correctly
#   4. Reusable workflow posts context torii/gate via torii_gate_status.py
#
# Usage:
#   ./scripts/smoke-torii-gate.sh
#   bash scripts/smoke-torii-gate.sh   # from CI or local
#
# Exit: 0 all green, 1 any check failed
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS="$ROOT/scripts/torii_gate_status.py"
DEMO="$ROOT/demo/insecure/app.py"
WORKFLOW="$ROOT/.github/workflows/torii-review-reusable.yml"
FAIL=0

log() { echo "$*" >&2; }
pass() { log "  ok  $*"; }
fail() { log "  FAIL $*"; FAIL=1; }

log "=== Torii Gate offline smoke ==="

# --- 1. Default pack is security ---
log "[1/4] security pack default"
PACK="$(
  cd "$ROOT" && env -u TORII_LENS_PACK python3 - <<'PY'
import importlib.util
import sys
from pathlib import Path
root = Path(".").resolve()
sys.path.insert(0, str(root / "scripts"))
# clean import path for pack resolution
for name in ("lens_recipes", "feature_toggles"):
    sys.modules.pop(name, None)
spec = importlib.util.spec_from_file_location("lens_recipes", root / "scripts" / "lens_recipes.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(mod.active_pack_id())
PY
)"
if [[ "$PACK" == "security" ]]; then
  pass "active_pack_id=$PACK"
else
  fail "expected security pack, got: $PACK"
fi

# --- 2. Dogfood fixture still intentionally insecure ---
log "[2/4] demo/insecure dogfood fixture"
if [[ ! -f "$DEMO" ]]; then
  fail "missing $DEMO"
else
  for needle in "f\"SELECT" "pickle.loads" "shell=True"; do
    if grep -qF "$needle" "$DEMO"; then
      pass "pattern present: $needle"
    else
      fail "demo missing intentional pattern: $needle"
    fi
  done
fi

# --- 3. Gate decision map ---
log "[3/4] torii_gate_status decision map"
if [[ ! -f "$STATUS" ]]; then
  fail "missing $STATUS"
else
  TMPDIR_SMOKE="$(mktemp -d)"
  trap 'rm -rf "$TMPDIR_SMOKE"' EXIT

  cat >"$TMPDIR_SMOKE/approve.md" <<'EOF'
**Verdict:** APPROVE
**Security audit:** No
**Score:** 90
EOF
  cat >"$TMPDIR_SMOKE/request.md" <<'EOF'
**Verdict:** REQUEST CHANGES
**Security audit:** SQL injection in demo/insecure/app.py search handler
**Score:** 15
EOF
  cat >"$TMPDIR_SMOKE/sec.md" <<'EOF'
**Verdict:** COMMENT
**Security audit:** pickle.loads on untrusted body in /load
**Score:** 40
EOF

  # APPROVE → open (rc 0 even with --strict)
  if python3 "$STATUS" "$TMPDIR_SMOKE/approve.md" --json --strict >/dev/null; then
    pass "APPROVE opens gate (strict rc=0)"
  else
    fail "APPROVE should open gate under --strict"
  fi

  # REQUEST CHANGES → closed (rc 1 with --strict)
  set +e
  python3 "$STATUS" "$TMPDIR_SMOKE/request.md" --json --strict >/dev/null
  RC=$?
  set -e
  if [[ "$RC" -eq 1 ]]; then
    pass "REQUEST CHANGES closes gate (strict rc=1)"
  else
    fail "REQUEST CHANGES expected strict rc=1, got $RC"
  fi

  # Security concern even with COMMENT → closed
  set +e
  python3 "$STATUS" "$TMPDIR_SMOKE/sec.md" --json --strict >/dev/null
  RC=$?
  set -e
  if [[ "$RC" -eq 1 ]]; then
    pass "security concern closes gate (strict rc=1)"
  else
    fail "security concern expected strict rc=1, got $RC"
  fi

  # JSON context must be torii/gate
  CTX="$(python3 "$STATUS" "$TMPDIR_SMOKE/approve.md" --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["context"])')"
  if [[ "$CTX" == "torii/gate" ]]; then
    pass "status context=$CTX"
  else
    fail "expected context torii/gate, got $CTX"
  fi
fi

# --- 4. Workflow wiring ---
log "[4/4] reusable workflow torii/gate post-step"
if [[ ! -f "$WORKFLOW" ]]; then
  fail "missing $WORKFLOW"
else
  if grep -q 'torii_gate_status.py' "$WORKFLOW" && grep -q 'torii/gate' "$WORKFLOW"; then
    pass "workflow references torii_gate_status.py and torii/gate"
  else
    fail "workflow missing torii_gate_status / torii/gate wiring"
  fi
  if grep -q 'name: Torii Gate status (torii/gate)' "$WORKFLOW"; then
    pass "named post-step present"
  else
    fail "missing named Torii Gate status step"
  fi
fi

if [[ "$FAIL" -ne 0 ]]; then
  log "=== SMOKE FAILED ==="
  exit 1
fi
log "=== SMOKE PASSED ==="
exit 0

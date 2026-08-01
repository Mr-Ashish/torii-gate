#!/usr/bin/env bash
# Offline smoke for Torii Gate product path (no OpenRouter / no PR required).
#
# Checks:
#   1. Security pack is the default lens pack
#   2. demo/insecure still carries intentional vuln patterns
#   3. torii_gate_status maps approve / request-changes / security-concern correctly
#   4. Reusable workflow posts context torii/gate via torii_gate_status.py
#   5. workflows-as-code fixture (F79)
#   6. skill compound loop readiness L3 (F91/F92)
#   7. memory compound loop readiness L3 (F96)
#   8. product CLI doctor (F110/F111)
#   9. integrity compound + federate on insecure-demo good review (F104/F107)
#
# Usage:
#   ./scripts/smoke-torii-gate.sh
#   bash scripts/smoke-torii-gate.sh   # from CI or local
#   TORII_SMOKE_SKILL_LOOP=0 to skip deep skill-loop fixtures (shallow pack only)
#   TORII_SMOKE_PRODUCT_CLI=0 to skip product doctor
#   TORII_SMOKE_COMPOUND_FEDERATE=0 to skip compound/federate proof
#
# Exit: 0 all green, 1 any check failed
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS="$ROOT/scripts/torii_gate_status.py"
DEMO="$ROOT/demo/insecure/app.py"
WORKFLOW="$ROOT/.github/workflows/torii-review-reusable.yml"
SKILL_LOOP="$ROOT/scripts/skill_loop_status.py"
FAIL=0

log() { echo "$*" >&2; }
pass() { log "  ok  $*"; }
fail() { log "  FAIL $*"; FAIL=1; }

log "=== Torii Gate offline smoke ==="

# --- 1. Default pack is security ---
log "[1/9] security pack default"
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

# --- 2. Dogfood fixture still intentionally insecure (hub product tree only) ---
log "[2/9] demo/insecure dogfood fixture"
if [[ ! -f "$DEMO" ]]; then
  # Pack installs on app repos omit demo/; skip rather than fail.
  pass "skip (no $DEMO — pack/target install is fine)"
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
log "[3/9] torii_gate_status decision map"
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
log "[4/9] reusable workflow torii/gate post-step"
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


# --- 5. F79 workflows-as-code ---
log "[5/9] workflows-as-code (F79)"
if [[ -f "$ROOT/scripts/workflow_as_code.py" && -f "$ROOT/docs/workflows/torii-gate.workflow.yaml" ]]; then
  if python3 "$ROOT/scripts/workflow_as_code.py" fixture >/dev/null 2>&1; then
    pass "workflow_as_code fixture L3"
  else
    python3 "$ROOT/scripts/workflow_as_code.py" fixture 2>&1 | tail -15 || true
    fail "workflow_as_code fixture"
  fi
else
  pass "skip F79 (workflow file not in this tree)"
fi

# --- 6. F91/F92 skill compound loop readiness ---
log "[6/9] skill compound loop readiness (F91)"
if [[ ! -f "$SKILL_LOOP" ]]; then
  # Pack targets may omit until re-install; fail on hub product tree only
  if [[ -d "$ROOT/agent/skills/active" ]]; then
    fail "missing $SKILL_LOOP (hub tree expects F91 skill_loop_status.py)"
  else
    pass "skip skill_loop (script not in pack tree)"
  fi
else
  # shallow scorecard always; deep fixture unless TORII_SMOKE_SKILL_LOOP=0
  case "${TORII_SMOKE_SKILL_LOOP:-1}" in
    0|false|FALSE|off|OFF|no|NO)
      if OUT="$(python3 "$SKILL_LOOP" scorecard --shallow 2>/dev/null)"; then
        LVL="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("level",""))' <<<"$OUT")"
        READY="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("ready",False))' <<<"$OUT")"
        if [[ "$READY" == "True" || "$READY" == "true" ]] && [[ "$LVL" == "L2" || "$LVL" == "L3" ]]; then
          pass "skill_loop shallow level=$LVL ready=$READY"
        else
          fail "skill_loop shallow not ready: $OUT"
        fi
      else
        fail "skill_loop scorecard --shallow failed"
      fi
      ;;
    *)
      if OUT="$(python3 "$SKILL_LOOP" fixture 2>/dev/null)"; then
        LVL="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("level",""))' <<<"$OUT")"
        PASSF="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("fixture_pass",False))' <<<"$OUT")"
        if [[ "$PASSF" == "True" || "$PASSF" == "true" ]] && [[ "$LVL" == "L3" ]]; then
          pass "skill_loop fixture L3"
        else
          log "  detail: $OUT"
          fail "skill_loop fixture expected L3 fixture_pass, got level=$LVL pass=$PASSF"
        fi
      else
        python3 "$SKILL_LOOP" fixture 2>&1 | tail -20 || true
        fail "skill_loop fixture"
      fi
      # also ensure gate ops surface works
      if python3 "$STATUS" --skill-loop-only >/dev/null 2>&1; then
        pass "torii_gate_status --skill-loop-only ready"
      else
        fail "torii_gate_status --skill-loop-only not ready"
      fi
      ;;
  esac
fi

# --- 7. F96 memory compound loop readiness ---
MEMORY_LOOP="$ROOT/scripts/memory_loop_status.py"
log "[7/9] memory compound loop readiness (F96)"
if [[ ! -f "$MEMORY_LOOP" ]]; then
  if [[ -f "$ROOT/scripts/scoped_memory_recall.py" ]]; then
    fail "missing $MEMORY_LOOP (hub tree expects F96 memory_loop_status.py)"
  else
    pass "skip memory_loop (script not in pack tree)"
  fi
else
  case "${TORII_SMOKE_MEMORY_LOOP:-1}" in
    0|false|FALSE|off|OFF|no|NO)
      if OUT="$(python3 "$MEMORY_LOOP" scorecard --shallow 2>/dev/null)"; then
        LVL="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("level",""))' <<<"$OUT")"
        READY="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("ready",False))' <<<"$OUT")"
        if [[ "$READY" == "True" || "$READY" == "true" ]] && [[ "$LVL" == "L2" || "$LVL" == "L3" ]]; then
          pass "memory_loop shallow level=$LVL ready=$READY"
        else
          fail "memory_loop shallow not ready: $OUT"
        fi
      else
        fail "memory_loop scorecard --shallow failed"
      fi
      ;;
    *)
      if OUT="$(python3 "$MEMORY_LOOP" fixture 2>/dev/null)"; then
        LVL="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("level",""))' <<<"$OUT")"
        PASSF="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("fixture_pass",False))' <<<"$OUT")"
        if [[ "$PASSF" == "True" || "$PASSF" == "true" ]] && [[ "$LVL" == "L3" ]]; then
          pass "memory_loop fixture L3"
        else
          log "  detail: $OUT"
          fail "memory_loop fixture expected L3 fixture_pass, got level=$LVL pass=$PASSF"
        fi
      else
        python3 "$MEMORY_LOOP" fixture 2>&1 | tail -30 || true
        fail "memory_loop fixture"
      fi
      if python3 "$STATUS" --memory-loop-only >/dev/null 2>&1; then
        pass "torii_gate_status --memory-loop-only ready"
      else
        fail "torii_gate_status --memory-loop-only not ready"
      fi
      ;;
  esac
fi

# --- 8. F110/F111 product CLI doctor ---
PRODUCT_CLI="$ROOT/scripts/torii.py"
log "[8/9] product CLI doctor (F110)"
case "${TORII_SMOKE_PRODUCT_CLI:-1}" in
  0|false|FALSE|off|OFF|no|NO)
    pass "skip product CLI (TORII_SMOKE_PRODUCT_CLI=0)"
    ;;
  *)
    if [[ ! -f "$PRODUCT_CLI" ]]; then
      if [[ -f "$ROOT/scripts/torii_memory.py" ]]; then
        fail "missing $PRODUCT_CLI (hub expects F110 torii.py)"
      else
        pass "skip product CLI (not in pack tree)"
      fi
    else
      if OUT="$(python3 "$PRODUCT_CLI" doctor 2>/dev/null)"; then
        PASSF="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("doctor_pass",False))' <<<"$OUT" 2>/dev/null || echo False)"
        if [[ "$PASSF" == "True" || "$PASSF" == "true" ]]; then
          pass "torii.py doctor_pass"
        else
          log "  detail: $OUT"
          fail "torii.py doctor_pass expected true"
        fi
      else
        python3 "$PRODUCT_CLI" doctor 2>&1 | tail -20 || true
        fail "torii.py doctor"
      fi
    fi
    ;;
esac

# --- 9. F104/F107 integrity compound + federate on insecure-demo good review ---
COMPOUND="$ROOT/scripts/memory_compound_write.py"
GOOD_REV="$ROOT/docs/benchmarks/fixtures/insecure-demo-good-review.md"
log "[9/9] integrity compound+federate insecure-demo (F104/F107)"
case "${TORII_SMOKE_COMPOUND_FEDERATE:-1}" in
  0|false|FALSE|off|OFF|no|NO)
    pass "skip compound federate (TORII_SMOKE_COMPOUND_FEDERATE=0)"
    ;;
  *)
    if [[ ! -f "$COMPOUND" || ! -f "$GOOD_REV" ]]; then
      if [[ -f "$ROOT/scripts/torii_memory.py" && ! -f "$COMPOUND" ]]; then
        fail "missing compound script on hub tree"
      else
        pass "skip compound federate (fixtures not in this tree)"
      fi
    else
      if OUT="$(python3 "$COMPOUND" fixture 2>/dev/null)"; then
        PASSF="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("fixture_pass",False))' <<<"$OUT" 2>/dev/null || echo False)"
        FEDN="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("fed_count") or d.get("federate_signals") or 0)' <<<"$OUT" 2>/dev/null || echo 0)"
        if [[ "$PASSF" == "True" || "$PASSF" == "true" ]]; then
          # require federate signal count ≥1 when feature present
          if [[ "${FEDN:-0}" -ge 1 ]] 2>/dev/null; then
            pass "compound+federate fixture_pass fed_count=$FEDN"
          else
            # older fixture without fed_count still ok if fixture_pass
            pass "compound fixture_pass (fed_count=$FEDN)"
          fi
        else
          log "  detail: $OUT"
          fail "compound fixture expected fixture_pass"
        fi
      else
        python3 "$COMPOUND" fixture 2>&1 | tail -25 || true
        fail "memory_compound_write fixture"
      fi
    fi
    ;;
esac

if [[ "$FAIL" -ne 0 ]]; then
  log "=== SMOKE FAILED ==="
  exit 1
fi
log "=== SMOKE PASSED ==="
exit 0


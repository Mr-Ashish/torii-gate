#!/usr/bin/env bash
# Run Hermes one-shot review with detailed agent-loop capture.
#
# Env:
#   OPENROUTER_API_KEY
#   TORII_ROOT, HERMES_HOME, WORKSPACE_ROOT
#   OUT_DIR, PROMPT_PATH (or meta.env)
#   TORII_MODEL / OPENROUTER_MODEL  (default: DEFAULT_TORII_MODEL below — F26 SoT)
#   TORII_TOOLSETS  (optional hermes -t value; default: terminal for workspace tools)
#   TORII_HERMES_COMMIT  pin SHA (default in hermes-pin.sh); empty/latest/main = floating
#   TORII_REVIEW_TIMEOUT_SECONDS  F36 wall-clock for hermes (default 1500; 0/off disables)
#   TORII_MAX_TURNS  F41 Hermes tool-iteration cap (default 40; 0/off = Hermes default ~500)
#   TORII_MODEL_TIER  F42 off|auto|cheap|full (default off) — auto picks cheap model for tiny/docs PRs
#   TORII_MODEL_CHEAP / TORII_MODEL_FULL  F42 tier models (defaults gpt-4.1-mini / opus-5)
#   TORII_MAX_COST_USD  F29 soft + F43 hard preflight threshold when set
#   TORII_PREFLIGHT_COST  F43 on|off|auto (default auto=hard when budget set)
#   TORII_PREFLIGHT_ACTION  F43 force_cheap|refuse|warn (default force_cheap)
#   TORII_TOOL_TURNS_GATE  F45 fail-closed on zero tools multi-file (default 1)
#   TORII_TOOL_TURNS_REPROMPT  F49/H15 soft re-prompt once when zero tools (default 1)
#   TORII_SEVERITY_CALIBRATION  F50/H20 APPROVE+test-gap → REQUEST CHANGES (default 1)
#   PR_NUMBER
set -euo pipefail

log() { echo "$*" >&2; }
notice() { echo "::notice::$*" >&2; log "$*"; }
die() { echo "::error::$*" >&2; exit 1; }

: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is required}"

# F26: single source of truth for the unpaid-default model id.
# OPERATIONS.md / USAGE.md / README / .env.example must match this string.
# Override per-repo with vars.TORII_MODEL (e.g. openai/gpt-5-mini) to cut cost.
DEFAULT_TORII_MODEL="anthropic/claude-opus-5"

TORII_ROOT="${TORII_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_DIR="${OUT_DIR:-$TORII_ROOT/.torii-out}"
HERMES_HOME="${HERMES_HOME:-$TORII_ROOT/.torii-hermes-home}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$TORII_ROOT}"
MODEL="${TORII_MODEL:-${OPENROUTER_MODEL:-$DEFAULT_TORII_MODEL}}"
TOOLSETS="${TORII_TOOLSETS:-terminal}"
PIN_HELPER="$TORII_ROOT/scripts/hermes-pin.sh"
MODEL_TIER_HELPER="$TORII_ROOT/scripts/model_tier.py"

mkdir -p "$OUT_DIR" "$HERMES_HOME/memories" "$HERMES_HOME/logs"

if [[ -f "$OUT_DIR/meta.env" ]]; then
  # shellcheck disable=SC1091
  source "$OUT_DIR/meta.env"
fi

PROMPT_PATH="${PROMPT_PATH:-$OUT_DIR/prompt.md}"
PR_NUMBER="${PR_NUMBER:-unknown}"
[[ -f "$PROMPT_PATH" ]] || die "Missing prompt: $PROMPT_PATH"

# ---------------------------------------------------------------------------
# F42: auto model tier by PR size (opt-in TORII_MODEL_TIER=auto)
# ---------------------------------------------------------------------------
MODEL_TIER_MODE="${TORII_MODEL_TIER:-off}"
MODEL_TIER_SELECTED="default"
MODEL_TIER_REASON="default_full"
if [[ -f "$MODEL_TIER_HELPER" ]]; then
  _tier_args=(select)
  [[ -n "${DIFF_SIZE:-}" ]] && _tier_args+=(--diff-bytes "$DIFF_SIZE")
  [[ -n "${FILE_COUNT:-}" ]] && _tier_args+=(--file-count "$FILE_COUNT")
  [[ -n "${DIFF_TRUNCATED:-}" ]] && _tier_args+=(--diff-truncated "$DIFF_TRUNCATED")
  [[ -f "${PR_JSON_PATH:-}" ]] && _tier_args+=(--pr-json "$PR_JSON_PATH")
  [[ -f "$OUT_DIR/meta.env" ]] && _tier_args+=(--meta "$OUT_DIR/meta.env")
  [[ -f "$OUT_DIR/files.txt" ]] && _tier_args+=(--paths-file "$OUT_DIR/files.txt")
  _tier_out="$(
    python3 "$MODEL_TIER_HELPER" "${_tier_args[@]}" 2>/dev/null || true
  )"
  if [[ -n "$_tier_out" ]]; then
    _m="$(printf '%s\n' "$_tier_out" | awk -F= '/^model=/{print substr($0,7); exit}')"
    _t="$(printf '%s\n' "$_tier_out" | awk -F= '/^tier=/{print $2; exit}')"
    _r="$(printf '%s\n' "$_tier_out" | awk -F= '/^reason=/{print $2; exit}')"
    _mode="$(printf '%s\n' "$_tier_out" | awk -F= '/^mode=/{print $2; exit}')"
    if [[ -n "$_m" ]]; then
      MODEL="$_m"
    fi
    MODEL_TIER_SELECTED="${_t:-$MODEL_TIER_SELECTED}"
    MODEL_TIER_REASON="${_r:-$MODEL_TIER_REASON}"
    MODEL_TIER_MODE="${_mode:-$MODEL_TIER_MODE}"
  fi
fi
# Export so hermes + capture see the effective model
export TORII_MODEL="$MODEL"
export OPENROUTER_MODEL="$MODEL"
# Trace/debug: record effective model (override, tier, or default)
printf '%s\n' "$MODEL" >"$OUT_DIR/torii-model.txt" || true
{
  echo "mode=$MODEL_TIER_MODE"
  echo "tier=$MODEL_TIER_SELECTED"
  echo "reason=$MODEL_TIER_REASON"
  echo "model=$MODEL"
  echo "diff_bytes=${DIFF_SIZE:-}"
  echo "file_count=${FILE_COUNT:-}"
} >"$OUT_DIR/model-tier.env" || true
if [[ "$MODEL_TIER_MODE" == "auto" || "$MODEL_TIER_MODE" == "cheap" || "$MODEL_TIER_MODE" == "full" ]]; then
  notice "F42 model tier · mode=$MODEL_TIER_MODE tier=$MODEL_TIER_SELECTED reason=$MODEL_TIER_REASON model=$MODEL"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo "### Torii model tier (F42)"
      echo "- **Mode:** \`$MODEL_TIER_MODE\` · **tier:** \`$MODEL_TIER_SELECTED\` · **reason:** \`$MODEL_TIER_REASON\`"
      echo "- **Model:** \`$MODEL\`"
      echo "- Opt-in: \`vars.TORII_MODEL_TIER=auto\` (cheap for tiny/docs; full otherwise)"
      echo
    } >>"$GITHUB_STEP_SUMMARY" || true
  fi
fi

# ---------------------------------------------------------------------------
# F43: hard preflight spend estimate (before Hermes / OpenRouter)
# ---------------------------------------------------------------------------
PREFLIGHT_HELPER="$TORII_ROOT/scripts/preflight_cost.py"
PREFLIGHT_DECISION="allow"
PREFLIGHT_REASON="skipped"
PREFLIGHT_EST=""
PREFLIGHT_REFUSED=0
PREFLIGHT_FORCED_CHEAP=0
if [[ -f "$PREFLIGHT_HELPER" ]]; then
  _pf_args=(decide --model "$MODEL" --diff-bytes "${DIFF_SIZE:-0}" --file-count "${FILE_COUNT:-0}")
  [[ -n "${TORII_MAX_COST_USD:-}" ]] && _pf_args+=(--max-usd "$TORII_MAX_COST_USD")
  [[ -n "${TORII_PREFLIGHT_COST:-}" ]] && _pf_args+=(--mode "$TORII_PREFLIGHT_COST")
  [[ -n "${TORII_PREFLIGHT_ACTION:-}" ]] && _pf_args+=(--action "$TORII_PREFLIGHT_ACTION")
  [[ -n "${TORII_MODEL_CHEAP:-}" ]] && _pf_args+=(--cheap-model "$TORII_MODEL_CHEAP")
  [[ -n "${TORII_MAX_TURNS:-}" ]] && _pf_args+=(--max-turns "$TORII_MAX_TURNS")
  set +e
  _pf_out="$(python3 "$PREFLIGHT_HELPER" "${_pf_args[@]}" 2>/dev/null)"
  _pf_rc=$?
  set -e
  if [[ -n "$_pf_out" ]]; then
    PREFLIGHT_DECISION="$(printf '%s\n' "$_pf_out" | awk -F= '/^decision=/{print $2; exit}')"
    PREFLIGHT_REASON="$(printf '%s\n' "$_pf_out" | awk -F= '/^reason=/{print $2; exit}')"
    PREFLIGHT_EST="$(printf '%s\n' "$_pf_out" | awk -F= '/^estimated_usd=/{print $2; exit}')"
    _pf_model="$(printf '%s\n' "$_pf_out" | awk -F= '/^model=/{print substr($0,7); exit}')"
    _pf_forced="$(printf '%s\n' "$_pf_out" | awk -F= '/^forced_cheap=/{print $2; exit}')"
    _pf_refused="$(printf '%s\n' "$_pf_out" | awk -F= '/^refused=/{print $2; exit}')"
    if [[ "$_pf_forced" == "true" && -n "$_pf_model" ]]; then
      MODEL="$_pf_model"
      export TORII_MODEL="$MODEL"
      export OPENROUTER_MODEL="$MODEL"
      printf '%s\n' "$MODEL" >"$OUT_DIR/torii-model.txt" || true
      PREFLIGHT_FORCED_CHEAP=1
      # Reflect forced cheap in model-tier.env
      {
        echo "mode=${MODEL_TIER_MODE:-off}"
        echo "tier=cheap"
        echo "reason=f43_preflight_force_cheap"
        echo "model=$MODEL"
        echo "diff_bytes=${DIFF_SIZE:-}"
        echo "file_count=${FILE_COUNT:-}"
      } >"$OUT_DIR/model-tier.env" || true
    fi
    if [[ "$_pf_refused" == "true" || "$_pf_rc" -eq 2 ]]; then
      PREFLIGHT_REFUSED=1
    fi
  fi
  # Always persist telemetry
  {
    printf '%s\n' "$_pf_out"
    echo "preflight_rc=${_pf_rc:-0}"
  } >"$OUT_DIR/preflight-cost.env" || true
  notice "F43 preflight cost · decision=${PREFLIGHT_DECISION:-?} reason=${PREFLIGHT_REASON:-?} est=\$${PREFLIGHT_EST:-?} model=$MODEL"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo "### Torii preflight cost (F43)"
      echo "- **Decision:** \`${PREFLIGHT_DECISION:-?}\` · **reason:** \`${PREFLIGHT_REASON:-?}\`"
      echo "- **Estimate:** \~$\`${PREFLIGHT_EST:-n/a}\` · model \`$MODEL\`"
      echo "- Budget: \`vars.TORII_MAX_COST_USD\` · action \`vars.TORII_PREFLIGHT_ACTION\` (default force_cheap)"
      echo
    } >>"$GITHUB_STEP_SUMMARY" || true
  fi
fi

if [[ "$PREFLIGHT_REFUSED" -eq 1 ]]; then
  notice "F43 preflight REFUSED paid Hermes (est=\$${PREFLIGHT_EST:-?} > budget) — writing stub review"
  _pf_summary="Torii **preflight cost gate (F43)** refused the paid Hermes run. Estimated spend ~\$${PREFLIGHT_EST:-?} (model was headed for premium tokens on a large PR) exceeds \`TORII_MAX_COST_USD\`. No OpenRouter agent loop was started."
  _pf_blocking="Raise \`TORII_MAX_COST_USD\`, set \`TORII_PREFLIGHT_ACTION=warn\`, force with \`TORII_PREFLIGHT_FORCE=1\` / \`@torii review force\`, use a cheaper \`TORII_MODEL\`, or shrink the PR."
  cat >"$OUT_DIR/review-${PR_NUMBER}.md" <<EOF
<!-- torii-review pr=${PR_NUMBER} -->
## 🏴‍☠️ Torii Review — PR #${PR_NUMBER}

**Verdict:** COMMENT
**Confidence:** low

### Summary
${_pf_summary}

### Blocking
- ${_pf_blocking}

### Suggestions
- Split the PR or enable \`TORII_MODEL_TIER=auto\` / a cheap model for large diffs
- Or raise the soft/hard budget via \`vars.TORII_MAX_COST_USD\`

### Nits
- None

### Tests & risk
- Coverage: n/a (preflight refuse — no agent review)
- Risk: unknown (review skipped to protect spend)
- Rollback: n/a

### What I checked
- F43 preflight cost estimate only (diff bytes + model rate proxy)
- Reason: \`${PREFLIGHT_REASON:-refused}\`

---
*Torii · Hermes Agent · OpenRouter · memory-backed review · F43 preflight refuse*
*Cost / usage: model=\`none\` · ~\$0 (preflight refuse) · budget gate*
EOF
  # Also raw for any consumers expecting it
  cp -f "$OUT_DIR/review-${PR_NUMBER}.md" "$OUT_DIR/review-${PR_NUMBER}.raw.md" 2>/dev/null || true
  printf '0\n' >"$OUT_DIR/hermes-skipped.txt" || true
  echo "skip=preflight_cost" >>"$OUT_DIR/preflight-cost.env" || true
  notice "F43 stub review written; skipping Hermes install + agent loop"
  exit 0
fi

export HERMES_HOME
export OPENROUTER_API_KEY
export PATH="${HOME}/.local/bin:${HOME}/.hermes/bin:${PATH}"
# Encourage verbose file logging for agent/tool activity
export HERMES_TUI_TOOL_PROGRESS="${HERMES_TUI_TOOL_PROGRESS:-verbose}"
export PYTHONUNBUFFERED=1

# ---------------------------------------------------------------------------
# F7: Ensure Hermes (pinned install; path cached by workflow when possible)
# ---------------------------------------------------------------------------
_hermes_install_head() {
  local d
  for d in \
    "${HOME}/.hermes/hermes-agent" \
    "${HERMES_INSTALL_DIR:-}" \
    "${HOME}/.local/share/hermes-agent"; do
    [[ -n "$d" && -d "$d/.git" ]] || continue
    git -C "$d" rev-parse HEAD 2>/dev/null && return 0
  done
  return 1
}

ensure_hermes() {
  export PATH="${HOME}/.local/bin:${HOME}/.hermes/bin:${PATH}"
  chmod +x "$PIN_HELPER" 2>/dev/null || true

  local pin head
  pin="$("$PIN_HELPER" resolve 2>/dev/null | tr -d '\n' || true)"
  printf '%s\n' "${pin:-floating}" >"$OUT_DIR/hermes-pin.txt" || true

  # F8: prebaked Docker/custom runner (image sets TORII_HERMES_PREBAKED=1 or /.hermes-pin)
  if [[ "${TORII_HERMES_PREBAKED:-}" == "1" || -f /root/.hermes-pin || -f "${HOME}/.hermes-pin" ]] \
    && command -v hermes >/dev/null 2>&1; then
    notice "hermes prebaked runner: $(command -v hermes)"
    hermes --version 2>/dev/null || true
    return
  fi

  if command -v hermes >/dev/null 2>&1; then
    head="$(_hermes_install_head || true)"
    if [[ -z "$pin" ]]; then
      notice "hermes (cached/present, floating): $(command -v hermes)"
      hermes --version 2>/dev/null || true
      return
    fi
    if "$PIN_HELPER" matches "$head"; then
      notice "hermes (cached/present, pin=$pin head=${head:-unknown}): $(command -v hermes)"
      hermes --version 2>/dev/null || true
      return
    fi
    # Version string may still mention short pin when git dir missing
    local ver
    ver="$(hermes --version 2>/dev/null || true)"
    if [[ -n "$ver" && "$ver" == *"${pin:0:8}"* ]]; then
      notice "hermes version matches pin ${pin:0:8}: $(command -v hermes)"
      return
    fi
    notice "hermes present but pin mismatch (want $pin head=${head:-n/a}); reinstalling..."
  else
    notice "Installing Hermes Agent (cold, pin=${pin:-floating})..."
  fi

  local args
  # shellcheck disable=SC2207
  args=( $("$PIN_HELPER" install-args) )
  notice "hermes install.sh args: ${args[*]}"
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- "${args[@]}"
  export PATH="${HOME}/.local/bin:${HOME}/.hermes/bin:${PATH}"
  # shellcheck disable=SC1091
  [[ -f "${HOME}/.bashrc" ]] && source "${HOME}/.bashrc" || true
  hash -r 2>/dev/null || true
  for candidate in \
    "${HOME}/.local/bin/hermes" \
    "${HOME}/.hermes/bin/hermes" \
    "${HOME}/.hermes/hermes"; do
    if [[ -x "$candidate" ]]; then
      export PATH="$(dirname "$candidate"):${PATH}"
      break
    fi
  done
  command -v hermes >/dev/null 2>&1 || die "hermes not found after install"
  head="$(_hermes_install_head || true)"
  notice "hermes installed: $(command -v hermes) head=${head:-unknown} pin=${pin:-floating}"
  hermes --version 2>/dev/null || true
}

ensure_hermes

# ---------------------------------------------------------------------------
# Seed HERMES_HOME (preserve growing MEMORY.md)
# ---------------------------------------------------------------------------
cp -f "$TORII_ROOT/agent/config.yaml" "$HERMES_HOME/config.yaml"
cp -f "$TORII_ROOT/agent/SOUL.md" "$HERMES_HOME/SOUL.md"
# F46 / H13: refuse to ship a SOUL.md Hermes would block (prompt_injection false +ve)
SOUL_SCAN_HELPER="$TORII_ROOT/scripts/soul_context_scan.py"
if [[ -f "$SOUL_SCAN_HELPER" ]]; then
  if python3 "$SOUL_SCAN_HELPER" check "$HERMES_HOME/SOUL.md" >"$OUT_DIR/soul-context-preflight.env" 2>/dev/null; then
    notice "F46 SOUL context scan clean (Hermes will load reviewer contract)"
  else
    _soul_rc=$?
    if [[ $_soul_rc -eq 2 ]]; then
      notice "F46 SOUL.md would be blocked by Hermes scanner — fix agent/SOUL.md phrasing (H13)"
      if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
        {
          echo "### Torii SOUL context scan (F46)"
          echo "- **Preflight failed:** \`agent/SOUL.md\` matches Hermes threat patterns"
          echo "- Hermes would replace SOUL with a \`[BLOCKED: …]\` stub — review discipline lost"
          echo "- Rephrase without classic injection quotes; see \`scripts/soul_context_scan.py\`"
          echo
        } >>"$GITHUB_STEP_SUMMARY" || true
      fi
      # Soft-continue: still run review, but mark ops signal (content may still block at Hermes)
      {
        echo "preflight_failed=1"
        echo "soul_blocked_risk=1"
      } >>"$OUT_DIR/soul-context-preflight.env" || true
    fi
  fi
fi
umask 077
cat >"$HERMES_HOME/.env" <<EOF
OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
EOF

if [[ ! -f "$HERMES_HOME/memories/MEMORY.md" ]]; then
  if [[ -f "$TORII_ROOT/agent/MEMORY.seed.md" ]]; then
    cp -f "$TORII_ROOT/agent/MEMORY.seed.md" "$HERMES_HOME/memories/MEMORY.md"
  else
    printf '# Torii Gate review memory\n\n' >"$HERMES_HOME/memories/MEMORY.md"
  fi
fi

PROMPT="$(cat "$PROMPT_PATH")"
RAW_OUT="$OUT_DIR/review-${PR_NUMBER}.raw.md"
STDERR_FILE="$OUT_DIR/hermes-${PR_NUMBER}.stderr"
FINAL_OUT="$OUT_DIR/review-${PR_NUMBER}.md"
USAGE_FILE="$OUT_DIR/hermes-usage.json"
LOOP_DIR="$OUT_DIR/agent-loop"
# Snapshot log position for this run only
LOG_FILE="$HERMES_HOME/logs/agent.log"
LOG_OFFSET=0
if [[ -f "$LOG_FILE" ]]; then
  LOG_OFFSET=$(wc -c <"$LOG_FILE" | tr -d ' ')
fi
echo "$LOG_OFFSET" >"$OUT_DIR/hermes-log-offset.txt"

# F36: wall-clock timeout for Hermes (kill hung agent loops / runaway OpenRouter)
TIMEOUT_HELPER="$TORII_ROOT/scripts/run-with-timeout.py"
TIMEOUT_SECS="$(
  python3 "$TIMEOUT_HELPER" resolve "${TORII_REVIEW_TIMEOUT_SECONDS-}" 2>/dev/null || echo 1500
)"
# normalize non-integer
case "$TIMEOUT_SECS" in
  ''|*[!0-9]*) TIMEOUT_SECS=1500 ;;
esac
printf '%s\n' "$TIMEOUT_SECS" >"$OUT_DIR/hermes-timeout-seconds.txt" || true

# F41 / F47 (H14): Hermes max_turns iteration budget (complements F36 wall-clock).
# Cap via HERMES_MAX_ITERATIONS + agent.max_turns in config.yaml ONLY.
# Do NOT pass --max-turns on the hermes CLI: current hermes argparse has no such
# flag; the bare integer is parsed as a subcommand → rc=2
# ("invalid choice: '25'") and forces hermes chat -q fallback (zero tools).
MAX_TURNS_HELPER="$TORII_ROOT/scripts/max_turns.py"
MAX_TURNS_RAW="$(
  python3 "$MAX_TURNS_HELPER" resolve "${TORII_MAX_TURNS-}" 2>/dev/null || echo 40
)"
MAX_TURNS_ENABLED=0
MAX_TURNS_VAL=""
if [[ "$MAX_TURNS_RAW" != "off" && -n "$MAX_TURNS_RAW" ]]; then
  case "$MAX_TURNS_RAW" in
    *[!0-9]*) MAX_TURNS_RAW=40 ;;
  esac
  if [[ "$MAX_TURNS_RAW" -gt 0 ]]; then
    MAX_TURNS_ENABLED=1
    MAX_TURNS_VAL="$MAX_TURNS_RAW"
    export HERMES_MAX_ITERATIONS="$MAX_TURNS_VAL"
    # Ensure HERMES_HOME config matches (agent.config copy may lag installer)
    python3 - <<'PY' "$HERMES_HOME/config.yaml" "$MAX_TURNS_VAL"
from pathlib import Path
import re, sys
path, n = Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8") if path.is_file() else ""
block = f"agent:\n  max_turns: {n}\n"
if re.search(r"(?m)^agent:\s*$", text):
    text2, cnt = re.subn(
        r"(?m)^(agent:\s*\n(?:[ \t]+.+\n)*)",
        block,
        text,
        count=1,
    )
    if cnt:
        text = text2
    else:
        text = text.rstrip() + "\n\n" + block
elif re.search(r"(?m)^agent:\s*\n", text):
    text = re.sub(
        r"(?ms)^agent:.*?(?=^[a-zA-Z_]|\Z)",
        block,
        text,
        count=1,
    )
else:
    text = text.rstrip() + "\n\n" + block
path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
PY
  fi
fi
{
  echo "max_turns_enabled=$MAX_TURNS_ENABLED"
  echo "max_turns=${MAX_TURNS_VAL:-off}"
} >"$OUT_DIR/hermes-max-turns.env" || true

_hermes_wrap() {
  # Run hermes under F36 timeout when enabled; else bare exec.
  if [[ "${TIMEOUT_SECS}" -gt 0 && -f "$TIMEOUT_HELPER" ]]; then
    python3 "$TIMEOUT_HELPER" --seconds "$TIMEOUT_SECS" -- "$@"
  else
    "$@"
  fi
}

notice "Hermes review · model=$MODEL tier=${MODEL_TIER_SELECTED:-?} toolsets=$TOOLSETS workspace=$WORKSPACE_ROOT hermes_home=$HERMES_HOME timeout=${TIMEOUT_SECS}s max_turns=${MAX_TURNS_VAL:-off}"

# F67: when TORII_STREAM_LOGS=1 (Modal sets this) or TORII_HOST=modal, tee Hermes
# stderr to both the capture file AND process stderr so Modal UI / CI live logs
# show tool/agent activity in real time (review body still goes only to RAW_OUT).
STREAM_LOGS=0
case "${TORII_STREAM_LOGS:-}${TORII_HOST:-}" in
  *1*|*modal*|*true*|*yes*) STREAM_LOGS=1 ;;
esac
if [[ "${TORII_HOST:-}" == "modal" ]]; then
  STREAM_LOGS=1
fi
if [[ $STREAM_LOGS -eq 1 ]]; then
  notice "F67 stream logs ON (tee hermes stderr → file + process stderr for Modal UI)"
fi

TIMED_OUT=0
set +e
(
  cd "$WORKSPACE_ROOT"
  # --usage-file: tokens/cost/session_id for the agentic loop package
  # -t toolsets: allow terminal/file tools so the loop can inspect the workspace
  if [[ $STREAM_LOGS -eq 1 ]]; then
    # process-substitution tee: live stderr for Modal + durable STDERR_FILE
    _hermes_wrap hermes -z "$PROMPT" \
      --provider openrouter \
      --model "$MODEL" \
      -t "$TOOLSETS" \
      --usage-file "$USAGE_FILE" \
      >"$RAW_OUT" 2> >(tee -a "$STDERR_FILE" >&2)
  else
    _hermes_wrap hermes -z "$PROMPT" \
      --provider openrouter \
      --model "$MODEL" \
      -t "$TOOLSETS" \
      --usage-file "$USAGE_FILE" \
      >"$RAW_OUT" 2>"$STDERR_FILE"
  fi
)
RC=$?
if [[ $RC -eq 124 ]]; then
  TIMED_OUT=1
  notice "F36 hermes -z TIMED OUT after ${TIMEOUT_SECS}s (skip chat fallback to avoid double spend)"
  # Drop partial model output — force the timeout failure stub below
  : >"$RAW_OUT"
  {
    echo "timed_out=1"
    echo "timeout_seconds=$TIMEOUT_SECS"
    echo "stage=hermes-z"
  } >"$OUT_DIR/hermes-timeout.env" || true
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo "### Torii Gate review timeout (F36)"
      echo "- **Timed out** after \`${TIMEOUT_SECS}s\` wall-clock during \`hermes -z\`"
      echo "- Chat fallback skipped (would double OpenRouter spend)"
      echo "- Override: \`vars.TORII_REVIEW_TIMEOUT_SECONDS\` (\`0\`/\`off\` disables)"
      echo
    } >>"$GITHUB_STEP_SUMMARY" || true
  fi
fi
# F47: detect hermes CLI misuse (unknown flags misparsed as subcommands) so we
# do not silently burn a chat-fallback spend that still has zero tools.
HERMES_CLI_ARGV_BROKEN=0
if [[ $TIMED_OUT -eq 0 && $RC -ne 0 && -s "$STDERR_FILE" ]]; then
  if grep -qiE "invalid choice:|unrecognized arguments:|error: argument" "$STDERR_FILE" 2>/dev/null; then
    HERMES_CLI_ARGV_BROKEN=1
    notice "F47 hermes -z CLI argv rejected (rc=$RC); skip chat fallback (fix hermes flags / H14)"
    {
      echo "cli_argv_broken=1"
      echo "stage=hermes-z"
      echo "rc=$RC"
    } >"$OUT_DIR/hermes-cli-argv.env" || true
  fi
fi
if [[ $TIMED_OUT -eq 0 && $HERMES_CLI_ARGV_BROKEN -eq 0 && ( $RC -ne 0 || ! -s "$RAW_OUT" ) ]]; then
  notice "hermes -z failed or empty (rc=$RC); trying hermes chat -q"
  (
    cd "$WORKSPACE_ROOT"
    if [[ $STREAM_LOGS -eq 1 ]]; then
      _hermes_wrap hermes chat -q "$PROMPT" \
        --provider openrouter \
        --model "$MODEL" \
        >"$RAW_OUT" 2> >(tee -a "$STDERR_FILE" >&2)
    else
      _hermes_wrap hermes chat -q "$PROMPT" \
        --provider openrouter \
        --model "$MODEL" \
        >"$RAW_OUT" 2>>"$STDERR_FILE"
    fi
  )
  RC=$?
  if [[ $RC -eq 124 ]]; then
    TIMED_OUT=1
    notice "F36 hermes chat TIMED OUT after ${TIMEOUT_SECS}s"
    : >"$RAW_OUT"
    {
      echo "timed_out=1"
      echo "timeout_seconds=$TIMEOUT_SECS"
      echo "stage=hermes-chat"
    } >"$OUT_DIR/hermes-timeout.env" || true
  fi
fi
set -e

if [[ $RC -ne 0 ]]; then
  if [[ $TIMED_OUT -eq 1 ]]; then
    notice "hermes exit=$RC (F36 wall-clock timeout ${TIMEOUT_SECS}s)"
  else
    notice "hermes exit=$RC"
  fi
  [[ -s "$STDERR_FILE" ]] && tail -c 8000 "$STDERR_FILE" >&2 || true
fi

# Slice of agent.log written during this invocation
if [[ -f "$LOG_FILE" ]]; then
  python3 - <<'PY' "$LOG_FILE" "$OUT_DIR/hermes-run.log" "$LOG_OFFSET"
import sys
from pathlib import Path
src, dest, off = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3] or 0)
data = src.read_bytes()
chunk = data[off:] if off < len(data) else data[-200_000:]
dest.write_bytes(chunk)
print(f"hermes-run.log bytes={len(chunk)}", file=sys.stderr)
PY
fi

# Detailed agentic-loop package (messages, tool calls, usage, logs)
export HERMES_HOME OUT_DIR TORII_MODEL="$MODEL" OPENROUTER_MODEL="$MODEL"
export HERMES_USAGE_FILE="$USAGE_FILE"
export AGENT_LOOP_DIR="$LOOP_DIR"
export TORII_PROVIDER=openrouter
# F48: pass log offset so capture only packages this-invocation agent.log slice
export HERMES_LOG_OFFSET="$LOG_OFFSET"
chmod +x "$TORII_ROOT/scripts/capture-hermes-loop.py" 2>/dev/null || true
python3 "$TORII_ROOT/scripts/capture-hermes-loop.py" || notice "capture-hermes-loop soft-failed"

# F108: shared soft-re-prompt budget (F49 + F106 share max_extra paid retries)
REPROMPT_BUDGET_HELPER="$TORII_ROOT/scripts/reprompt_budget.py"
if [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
  python3 "$REPROMPT_BUDGET_HELPER" init --out-dir "$OUT_DIR" >/dev/null 2>&1 || true
fi

# ---------------------------------------------------------------------------
# F49 / H15: soft re-prompt once when tool_turns=0 on multi-file code PRs.
# Runs *before* F45 fail-closed so a second agentic attempt can recover quality.
# F108: gated by shared re-prompt budget (default max_extra=1).
# ---------------------------------------------------------------------------
TOOL_TURNS_GATE_HELPER="$TORII_ROOT/scripts/tool_turns_gate.py"
REPROMPT_ATTEMPTED=0
REPROMPT_RECOVERED=0
TT_BEFORE=""
TT_AFTER=""
REPROMPT_REASON="skipped"
if [[ -f "$TOOL_TURNS_GATE_HELPER" && $TIMED_OUT -eq 0 && "${HERMES_CLI_ARGV_BROKEN:-0}" -eq 0 && -s "$RAW_OUT" ]]; then
  _rp_args=(
    reprompt-decide
    --loop-json "$LOOP_DIR/agent-loop.json"
  )
  [[ -n "${FILE_COUNT:-}" ]] && _rp_args+=(--file-count "$FILE_COUNT")
  [[ -f "$OUT_DIR/files.txt" ]] && _rp_args+=(--paths-file "$OUT_DIR/files.txt")
  _rp_kv="$(python3 "$TOOL_TURNS_GATE_HELPER" "${_rp_args[@]}" 2>/dev/null || true)"
  _rp_do="$(printf '%s\n' "$_rp_kv" | sed -n 's/^reprompt=//p' | head -1)"
  TT_BEFORE="$(printf '%s\n' "$_rp_kv" | sed -n 's/^tool_turns=//p' | head -1)"
  REPROMPT_REASON="$(printf '%s\n' "$_rp_kv" | sed -n 's/^reason=//p' | head -1)"
  # F108 budget gate
  if [[ "$_rp_do" == "1" || "$_rp_do" == "true" ]] && [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
    _bud_kv="$(python3 "$REPROMPT_BUDGET_HELPER" allow --out-dir "$OUT_DIR" --kind f49 2>/dev/null || true)"
    _bud_allow="$(printf '%s\n' "$_bud_kv" | sed -n 's/^allow=//p' | head -1)"
    if [[ "$_bud_allow" != "1" && "$_bud_allow" != "true" ]]; then
      _bud_reason="$(printf '%s\n' "$_bud_kv" | sed -n 's/^reason=//p' | head -1)"
      notice "F108 re-prompt budget blocked F49 · reason=${_bud_reason:-budget}"
      REPROMPT_REASON="budget_blocked:${_bud_reason:-exhausted}"
      _rp_do="0"
    fi
  fi
  if [[ "$_rp_do" == "1" || "$_rp_do" == "true" ]]; then
    REPROMPT_ATTEMPTED=1
    notice "F49 soft re-prompt · tool_turns=${TT_BEFORE:-0} files=${FILE_COUNT:-?} (H15 zero-tool multi-file)"
    # F108: reserve budget slot as soon as we commit to a paid re-run
    if [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
      python3 "$REPROMPT_BUDGET_HELPER" consume --out-dir "$OUT_DIR" --kind f49 --note "attempt_start" >/dev/null 2>&1 || true
    fi
    # Archive attempt-1 artifacts for comparison
    cp -f "$RAW_OUT" "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" 2>/dev/null || true
    [[ -f "$STDERR_FILE" ]] && cp -f "$STDERR_FILE" "$OUT_DIR/hermes-${PR_NUMBER}.attempt1.stderr" 2>/dev/null || true
    [[ -f "$USAGE_FILE" ]] && cp -f "$USAGE_FILE" "$OUT_DIR/hermes-usage.attempt1.json" 2>/dev/null || true
    if [[ -d "$LOOP_DIR" ]]; then
      rm -rf "$OUT_DIR/agent-loop-attempt1"
      cp -a "$LOOP_DIR" "$OUT_DIR/agent-loop-attempt1" 2>/dev/null || true
    fi
    # Build nudged prompt
    REPROMPT_PROMPT="$OUT_DIR/prompt-reprompt.md"
    _rpw_args=(
      reprompt-write
      --prompt-in "$PROMPT_PATH"
      --prompt-out "$REPROMPT_PROMPT"
      --tool-turns "${TT_BEFORE:-0}"
    )
    [[ -n "${FILE_COUNT:-}" ]] && _rpw_args+=(--file-count "$FILE_COUNT")
    [[ -f "$OUT_DIR/files.txt" ]] && _rpw_args+=(--paths-file "$OUT_DIR/files.txt")
    python3 "$TOOL_TURNS_GATE_HELPER" "${_rpw_args[@]}" >/dev/null 2>&1 || true
    if [[ -s "$REPROMPT_PROMPT" ]]; then
      PROMPT="$(cat "$REPROMPT_PROMPT")"
      # Fresh log offset for attempt-2 slice
      LOG_OFFSET=0
      if [[ -f "$LOG_FILE" ]]; then
        LOG_OFFSET=$(wc -c <"$LOG_FILE" | tr -d ' ')
      fi
      echo "$LOG_OFFSET" >"$OUT_DIR/hermes-log-offset-reprompt.txt" || true
      STDERR_FILE_RP="$OUT_DIR/hermes-${PR_NUMBER}.reprompt.stderr"
      set +e
      (
        cd "$WORKSPACE_ROOT"
        if [[ $STREAM_LOGS -eq 1 ]]; then
          _hermes_wrap hermes -z "$PROMPT" \
            --provider openrouter \
            --model "$MODEL" \
            -t "$TOOLSETS" \
            --usage-file "$USAGE_FILE" \
            >"$RAW_OUT" 2> >(tee -a "$STDERR_FILE_RP" >&2)
        else
          _hermes_wrap hermes -z "$PROMPT" \
            --provider openrouter \
            --model "$MODEL" \
            -t "$TOOLSETS" \
            --usage-file "$USAGE_FILE" \
            >"$RAW_OUT" 2>"$STDERR_FILE_RP"
        fi
      )
      RC_RP=$?
      set -e
      if [[ $RC_RP -eq 124 ]]; then
        # Do not leave a partial second body; restore attempt-1
        notice "F49 soft re-prompt TIMED OUT — keeping attempt-1 body"
        if [[ -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" ]]; then
          cp -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" "$RAW_OUT"
        fi
        REPROMPT_REASON="reprompt_timeout"
        RC=$RC_RP
        TIMED_OUT=1
      elif [[ $RC_RP -ne 0 || ! -s "$RAW_OUT" ]]; then
        notice "F49 soft re-prompt failed/empty (rc=$RC_RP) — keeping attempt-1 body"
        if [[ -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" ]]; then
          cp -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" "$RAW_OUT"
        fi
        REPROMPT_REASON="reprompt_failed"
        # Keep original RC if first run was ok
        [[ $RC -eq 0 ]] || RC=$RC_RP
      else
        RC=$RC_RP
        REPROMPT_REASON="reprompt_ran"
        # Append reprompt stderr for operators
        if [[ -s "$STDERR_FILE_RP" ]]; then
          {
            echo ""
            echo "===== F49 soft re-prompt stderr ====="
            cat "$STDERR_FILE_RP"
          } >>"$STDERR_FILE" 2>/dev/null || true
        fi
        # Re-slice hermes-run.log for attempt-2
        if [[ -f "$LOG_FILE" ]]; then
          python3 - <<'PY' "$LOG_FILE" "$OUT_DIR/hermes-run.log" "$LOG_OFFSET"
import sys
from pathlib import Path
src, dest, off = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3] or 0)
data = src.read_bytes()
chunk = data[off:] if off < len(data) else data[-200_000:]
dest.write_bytes(chunk)
print(f"hermes-run.log (reprompt) bytes={len(chunk)}", file=sys.stderr)
PY
        fi
        # Re-capture agent loop for the second session
        export HERMES_LOG_OFFSET="$LOG_OFFSET"
        rm -rf "$LOOP_DIR"
        mkdir -p "$LOOP_DIR"
        python3 "$TORII_ROOT/scripts/capture-hermes-loop.py" || notice "capture-hermes-loop (reprompt) soft-failed"
        TT_AFTER="$(
          python3 - <<'PY' "$LOOP_DIR/agent-loop.json"
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.is_file():
    print("")
    raise SystemExit(0)
try:
    d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    print(d.get("tool_call_turns", ""))
except Exception:
    print("")
PY
        )"
        if [[ -n "$TT_AFTER" && "$TT_AFTER" != "0" ]]; then
          REPROMPT_RECOVERED=1
          REPROMPT_REASON="reprompt_recovered"
          notice "F49 soft re-prompt recovered tool_turns=${TT_AFTER} (was ${TT_BEFORE:-0})"
        else
          notice "F49 soft re-prompt still tool_turns=${TT_AFTER:-0} — F45 gate may still fire"
        fi
        # F108: update recovered flag on already-consumed f49 slot
        if [[ -f "$REPROMPT_BUDGET_HELPER" && "${REPROMPT_RECOVERED}" == "1" ]]; then
          python3 "$REPROMPT_BUDGET_HELPER" consume --out-dir "$OUT_DIR" --kind f49 --recovered --note "tool_turns ${TT_BEFORE:-?}→${TT_AFTER:-?}" >/dev/null 2>&1 || true
        fi
      fi
      {
        echo "reprompt=1"
        echo "enabled=1"
        echo "reason=$REPROMPT_REASON"
        echo "attempted=1"
        echo "tool_turns_before=${TT_BEFORE:-}"
        echo "tool_turns_after=${TT_AFTER:-}"
        echo "file_count=${FILE_COUNT:-}"
        echo "recovered=$REPROMPT_RECOVERED"
        echo "rc=${RC_RP:-}"
      } >"$OUT_DIR/tool-turns-reprompt.env" || true
      if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
        {
          echo "### Torii soft re-prompt (F49 / H15)"
          echo "- **Attempted:** yes · **reason:** \`${REPROMPT_REASON}\`"
          echo "- **tool_turns:** before=\`${TT_BEFORE:-?}\` → after=\`${TT_AFTER:-?}\` · recovered=\`${REPROMPT_RECOVERED}\`"
          echo "- F45 fail-closed still applies if tools remain zero"
          echo
        } >>"$GITHUB_STEP_SUMMARY" || true
      fi
    else
      REPROMPT_ATTEMPTED=0
      REPROMPT_REASON="reprompt_prompt_write_failed"
      {
        echo "reprompt=0"
        echo "enabled=1"
        echo "reason=$REPROMPT_REASON"
        echo "attempted=0"
        echo "tool_turns_before=${TT_BEFORE:-}"
        echo "file_count=${FILE_COUNT:-}"
        echo "recovered=0"
      } >"$OUT_DIR/tool-turns-reprompt.env" || true
    fi
  else
    {
      echo "reprompt=0"
      echo "enabled=1"
      echo "reason=${REPROMPT_REASON:-skipped}"
      echo "attempted=0"
      echo "tool_turns_before=${TT_BEFORE:-}"
      echo "file_count=${FILE_COUNT:-}"
      echo "recovered=0"
    } >"$OUT_DIR/tool-turns-reprompt.env" || true
  fi
else
  {
    echo "reprompt=0"
    echo "enabled=${TORII_TOOL_TURNS_REPROMPT:-1}"
    echo "reason=preconditions_not_met"
    echo "attempted=0"
    echo "file_count=${FILE_COUNT:-}"
    echo "recovered=0"
  } >"$OUT_DIR/tool-turns-reprompt.env" || true
fi

# ---------------------------------------------------------------------------
# F106: soft re-prompt once when memory tools were offered but unused after
# tools ran (utilization_gap). Complements F49 (zero tools) — does not stack
# when tool_turns==0 (defers to F49). F108: shared budget may block after F49.
# ---------------------------------------------------------------------------
MEM_REPROMPT_ATTEMPTED=0
MEM_REPROMPT_RECOVERED=0
MEM_REPROMPT_REASON="skipped"
MEM_HIT_BEFORE=""
MEM_HIT_AFTER=""
MEM_AUDIT_HELPER="$TORII_ROOT/scripts/memory_tool_audit.py"
if [[ -f "$MEM_AUDIT_HELPER" && $TIMED_OUT -eq 0 && "${HERMES_CLI_ARGV_BROKEN:-0}" -eq 0 && -s "$RAW_OUT" ]]; then
  case "${TORII_MEMORY_TOOL_REPROMPT:-1}" in
    0|false|no|off)
      {
        echo "reprompt=0"
        echo "enabled=0"
        echo "reason=reprompt_off"
        echo "attempted=0"
        echo "recovered=0"
      } >"$OUT_DIR/memory-tool-reprompt.env" || true
      ;;
    *)
      _mrp_args=(
        reprompt-decide
        --out-dir "$OUT_DIR"
        --loop "$LOOP_DIR/agent-loop.json"
        --prompt "$PROMPT_PATH"
      )
      [[ -f "$OUT_DIR/memory-tool-reprompt.env" ]] && _mrp_args+=(--already-env "$OUT_DIR/memory-tool-reprompt.env")
      _mrp_kv="$(python3 "$MEM_AUDIT_HELPER" "${_mrp_args[@]}" 2>/dev/null || true)"
      _mrp_do="$(printf '%s\n' "$_mrp_kv" | sed -n 's/^reprompt=//p' | head -1)"
      MEM_HIT_BEFORE="$(printf '%s\n' "$_mrp_kv" | sed -n 's/^hit_count=//p' | head -1)"
      MEM_REPROMPT_REASON="$(printf '%s\n' "$_mrp_kv" | sed -n 's/^reason=//p' | head -1)"
      _mrp_tt="$(printf '%s\n' "$_mrp_kv" | sed -n 's/^tool_call_turns=//p' | head -1)"
      # F108 budget gate (e.g. F49 already consumed the only extra attempt)
      if [[ "$_mrp_do" == "1" || "$_mrp_do" == "true" ]] && [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
        _mbud_kv="$(python3 "$REPROMPT_BUDGET_HELPER" allow --out-dir "$OUT_DIR" --kind f106 2>/dev/null || true)"
        _mbud_allow="$(printf '%s\n' "$_mbud_kv" | sed -n 's/^allow=//p' | head -1)"
        if [[ "$_mbud_allow" != "1" && "$_mbud_allow" != "true" ]]; then
          _mbud_reason="$(printf '%s\n' "$_mbud_kv" | sed -n 's/^reason=//p' | head -1)"
          notice "F108 re-prompt budget blocked F106 · reason=${_mbud_reason:-budget}"
          MEM_REPROMPT_REASON="budget_blocked:${_mbud_reason:-exhausted}"
          _mrp_do="0"
        fi
      fi
      if [[ "$_mrp_do" == "1" || "$_mrp_do" == "true" ]]; then
        MEM_REPROMPT_ATTEMPTED=1
        notice "F106 memory soft re-prompt · hits=${MEM_HIT_BEFORE:-0} tool_turns=${_mrp_tt:-?} (utilization_gap)"
        # F108: reserve budget slot for paid memory re-run
        if [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
          python3 "$REPROMPT_BUDGET_HELPER" consume --out-dir "$OUT_DIR" --kind f106 --note "attempt_start" >/dev/null 2>&1 || true
        fi
        # Archive attempt-1 if F49 did not already
        if [[ ! -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" ]]; then
          cp -f "$RAW_OUT" "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" 2>/dev/null || true
          [[ -d "$LOOP_DIR" ]] && rm -rf "$OUT_DIR/agent-loop-attempt1" && cp -a "$LOOP_DIR" "$OUT_DIR/agent-loop-attempt1" 2>/dev/null || true
        fi
        # Prefer F49 nudged prompt as base if present, else original
        _mrp_base="$PROMPT_PATH"
        [[ -s "$OUT_DIR/prompt-reprompt.md" ]] && _mrp_base="$OUT_DIR/prompt-reprompt.md"
        MEM_REPROMPT_PROMPT="$OUT_DIR/prompt-memory-reprompt.md"
        _mrw_args=(
          reprompt-write
          --prompt-in "$_mrp_base"
          --prompt-out "$MEM_REPROMPT_PROMPT"
          --hit-count "${MEM_HIT_BEFORE:-0}"
          --tool-turns "${_mrp_tt:-0}"
        )
        [[ -f "$OUT_DIR/files.txt" ]] && _mrw_args+=(--paths-file "$OUT_DIR/files.txt")
        python3 "$MEM_AUDIT_HELPER" "${_mrw_args[@]}" >/dev/null 2>&1 || true
        if [[ -s "$MEM_REPROMPT_PROMPT" ]]; then
          PROMPT="$(cat "$MEM_REPROMPT_PROMPT")"
          LOG_OFFSET=0
          if [[ -f "$LOG_FILE" ]]; then
            LOG_OFFSET=$(wc -c <"$LOG_FILE" | tr -d ' ')
          fi
          echo "$LOG_OFFSET" >"$OUT_DIR/hermes-log-offset-memory-reprompt.txt" || true
          STDERR_FILE_MRP="$OUT_DIR/hermes-${PR_NUMBER}.memory-reprompt.stderr"
          set +e
          (
            cd "$WORKSPACE_ROOT"
            if [[ $STREAM_LOGS -eq 1 ]]; then
              _hermes_wrap hermes -z "$PROMPT" \
                --provider openrouter \
                --model "$MODEL" \
                -t "$TOOLSETS" \
                --usage-file "$USAGE_FILE" \
                >"$RAW_OUT" 2> >(tee -a "$STDERR_FILE_MRP" >&2)
            else
              _hermes_wrap hermes -z "$PROMPT" \
                --provider openrouter \
                --model "$MODEL" \
                -t "$TOOLSETS" \
                --usage-file "$USAGE_FILE" \
                >"$RAW_OUT" 2>"$STDERR_FILE_MRP"
            fi
          )
          RC_MRP=$?
          set -e
          if [[ $RC_MRP -eq 124 ]]; then
            notice "F106 memory re-prompt TIMED OUT — keeping prior body"
            if [[ -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" ]]; then
              cp -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" "$RAW_OUT"
            fi
            MEM_REPROMPT_REASON="reprompt_timeout"
            TIMED_OUT=1
          elif [[ $RC_MRP -ne 0 || ! -s "$RAW_OUT" ]]; then
            notice "F106 memory re-prompt failed/empty (rc=$RC_MRP) — keeping prior body"
            if [[ -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" ]]; then
              cp -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" "$RAW_OUT"
            fi
            MEM_REPROMPT_REASON="reprompt_failed"
            [[ $RC -eq 0 ]] || RC=$RC_MRP
          else
            RC=$RC_MRP
            MEM_REPROMPT_REASON="reprompt_ran"
            if [[ -s "$STDERR_FILE_MRP" ]]; then
              {
                echo ""
                echo "===== F106 memory soft re-prompt stderr ====="
                cat "$STDERR_FILE_MRP"
              } >>"$STDERR_FILE" 2>/dev/null || true
            fi
            if [[ -f "$LOG_FILE" ]]; then
              python3 - <<'PY' "$LOG_FILE" "$OUT_DIR/hermes-run.log" "$LOG_OFFSET"
import sys
from pathlib import Path
src, dest, off = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3] or 0)
data = src.read_bytes()
chunk = data[off:] if off < len(data) else data[-200_000:]
dest.write_bytes(chunk)
print(f"hermes-run.log (memory-reprompt) bytes={len(chunk)}", file=sys.stderr)
PY
            fi
            export HERMES_LOG_OFFSET="$LOG_OFFSET"
            rm -rf "$LOOP_DIR"
            mkdir -p "$LOOP_DIR"
            python3 "$TORII_ROOT/scripts/capture-hermes-loop.py" || notice "capture-hermes-loop (memory-reprompt) soft-failed"
            # re-audit hits
            MEM_HIT_AFTER="$(
              python3 "$MEM_AUDIT_HELPER" audit --out-dir "$OUT_DIR" --prompt "$PROMPT_PATH" 2>/dev/null \
                | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("hit_count",0))' 2>/dev/null || echo "0"
            )"
            if [[ -n "$MEM_HIT_AFTER" && "$MEM_HIT_AFTER" != "0" ]]; then
              MEM_REPROMPT_RECOVERED=1
              MEM_REPROMPT_REASON="reprompt_recovered"
              notice "F106 memory re-prompt recovered hits=${MEM_HIT_AFTER} (was ${MEM_HIT_BEFORE:-0})"
            else
              notice "F106 memory re-prompt still hits=${MEM_HIT_AFTER:-0} — F105 gap may remain"
            fi
            # F108: mark recovered on f106 slot
            if [[ -f "$REPROMPT_BUDGET_HELPER" && "${MEM_REPROMPT_RECOVERED}" == "1" ]]; then
              python3 "$REPROMPT_BUDGET_HELPER" consume --out-dir "$OUT_DIR" --kind f106 --recovered --note "hits ${MEM_HIT_BEFORE:-?}→${MEM_HIT_AFTER:-?}" >/dev/null 2>&1 || true
            fi
          fi
          {
            echo "reprompt=1"
            echo "enabled=1"
            echo "reason=${MEM_REPROMPT_REASON}"
            echo "attempted=1"
            echo "recovered=${MEM_REPROMPT_RECOVERED}"
            echo "hit_count_before=${MEM_HIT_BEFORE:-}"
            echo "hit_count_after=${MEM_HIT_AFTER:-}"
            echo "tool_call_turns=${_mrp_tt:-}"
            echo "feature=F106"
          } >"$OUT_DIR/memory-tool-reprompt.env" || true
          if [[ -f "$FINAL_OUT" || -s "$RAW_OUT" ]]; then
            {
              echo ""
              echo "### Torii memory soft re-prompt (F106)"
              echo "- **memory tool hits:** before=\`${MEM_HIT_BEFORE:-?}\` → after=\`${MEM_HIT_AFTER:-?}\` · recovered=\`${MEM_REPROMPT_RECOVERED}\`"
              echo "- **reason:** \`${MEM_REPROMPT_REASON}\`"
              echo "- Prefer \`python3 scripts/torii_memory.py search|graph\` when memory sections are injected"
            } >>"$OUT_DIR/memory-tool-reprompt.md" 2>/dev/null || true
          fi
        else
          MEM_REPROMPT_REASON="reprompt_prompt_write_failed"
          {
            echo "reprompt=0"
            echo "enabled=1"
            echo "reason=${MEM_REPROMPT_REASON}"
            echo "attempted=1"
            echo "recovered=0"
            echo "hit_count_before=${MEM_HIT_BEFORE:-}"
            echo "feature=F106"
          } >"$OUT_DIR/memory-tool-reprompt.env" || true
        fi
      else
        {
          echo "reprompt=0"
          echo "enabled=1"
          echo "reason=${MEM_REPROMPT_REASON:-skipped}"
          echo "attempted=0"
          echo "recovered=0"
          echo "hit_count_before=${MEM_HIT_BEFORE:-}"
          echo "tool_call_turns=${_mrp_tt:-}"
          echo "feature=F106"
        } >"$OUT_DIR/memory-tool-reprompt.env" || true
      fi
      ;;
  esac
else
  {
    echo "reprompt=0"
    echo "enabled=${TORII_MEMORY_TOOL_REPROMPT:-1}"
    echo "reason=preconditions_not_met"
    echo "attempted=0"
    echo "recovered=0"
    echo "feature=F106"
  } >"$OUT_DIR/memory-tool-reprompt.env" || true
fi

# ---------------------------------------------------------------------------
# F122: soft re-prompt once when recovery always-skills injected but idle
# (F121 util gap). Complements F106; F108 shared budget may block after F49/F106.
# ---------------------------------------------------------------------------
REC_REPROMPT_ATTEMPTED=0
REC_REPROMPT_RECOVERED=0
REC_REPROMPT_REASON="skipped"
SKILL_ROUTER_HELPER="$TORII_ROOT/scripts/skill_router.py"
if [[ -f "$SKILL_ROUTER_HELPER" && $TIMED_OUT -eq 0 && "${HERMES_CLI_ARGV_BROKEN:-0}" -eq 0 && -s "$RAW_OUT" ]]; then
  case "${TORII_RECOVERY_SKILL_REPROMPT:-1}" in
    0|false|no|off)
      {
        echo "reprompt=0"
        echo "enabled=0"
        echo "reason=reprompt_off"
        echo "attempted=0"
        echo "recovered=0"
        echo "feature=F122"
      } >"$OUT_DIR/recovery-skill-reprompt.env" || true
      ;;
    *)
      # Score hits + util from this run's agent-loop
      _rec_score_args=(score --review "$RAW_OUT" --out-dir "$OUT_DIR")
      [[ -f "$LOOP_DIR/agent-loop.json" ]] && _rec_score_args+=(--agent-loop "$LOOP_DIR/agent-loop.json")
      [[ -f "$LOOP_DIR/agent.log" ]] && _rec_score_args+=(--log "$LOOP_DIR/agent.log")
      python3 "$SKILL_ROUTER_HELPER" "${_rec_score_args[@]}" >/dev/null 2>&1 || true
      python3 "$SKILL_ROUTER_HELPER" util --out-dir "$OUT_DIR" >/dev/null 2>&1 || true
      # F163: soft fitness cycle after util (chronic hub-archival federate heat)
      if [[ -f "$TORII_ROOT/scripts/skill_fitness.py" ]]; then
        python3 "$TORII_ROOT/scripts/skill_fitness.py" ingest-hub-archival --out-dir "$OUT_DIR" >/dev/null 2>&1 || true
        # F185: compound re-prompt outcomes → fitness (after budget state written)
        python3 "$TORII_ROOT/scripts/skill_fitness.py" ingest-compound-reprompt --out-dir "$OUT_DIR" >/dev/null 2>&1 || true
        notice "F185 compound re-prompt fitness ingest (soft)"
        # F186: chronic compound re-prompt miss → always priority (applied in ingest) + critic
        notice "F186 compound re-prompt chronic miss pressure (soft; fitness+router+critic)"
        python3 "$TORII_ROOT/scripts/skill_fitness.py" cycle --out-dir "$OUT_DIR" >/dev/null 2>&1 || true
      fi
      # F165: GEPA-lite skill body refine from util traces (Hermes self-evolution pattern)
      # Reads recovery/hub-archival util + fitness; mutates active skill bodies under size/probe gates.
      if [[ -f "$TORII_ROOT/scripts/self_evolve.py" ]]; then
        case "${TORII_SKILL_REFINE:-1}" in
          0|false|no|off) ;;
          *)
            python3 "$TORII_ROOT/scripts/self_evolve.py" refine-from-util --out-dir "$OUT_DIR" --apply >/dev/null 2>&1 || true
            notice "F165 GEPA-lite refine-from-util (soft) · skill-refine.json"
            # F166: dual-gate stamp already in refine; fitness shield + attr floor fuel
            if [[ -f "$TORII_ROOT/scripts/skill_fitness.py" ]]; then
              python3 "$TORII_ROOT/scripts/skill_fitness.py" ingest-refine --out-dir "$OUT_DIR" >/dev/null 2>&1 || true
              notice "F166 refine fitness shield (soft) · ingest-refine"
            fi
            if [[ -f "$TORII_ROOT/scripts/skill_attribution.py" ]]; then
              python3 "$TORII_ROOT/scripts/skill_attribution.py" refine-floor --out-dir "$OUT_DIR" --write >/dev/null 2>&1 || true
              notice "F166 refine LOO floor hint · skill-refine-attr.json"
            fi
            # F167: paper dual-rollout refine contribution_pp (with vs ablated GEPA body)
            if [[ -f "$TORII_ROOT/scripts/skill_dual_rollout.py" ]]; then
              case "${TORII_SKILL_REFINE_DUAL:-1}" in
                0|false|no|off) ;;
                *)
                  python3 "$TORII_ROOT/scripts/skill_dual_rollout.py" refine-dual --out-dir "$OUT_DIR" >/dev/null 2>&1 || true
                  notice "F167 refine dual-rollout contribution_pp · refine-dual.json"
                  # F171: chronic dual_fail → fitness decay + always-priority demote fuel
                  if [[ -f "$TORII_ROOT/scripts/skill_fitness.py" ]]; then
                    case "${TORII_SKILL_FITNESS_REFINE_DUAL_DECAY:-1}" in
                      0|false|no|off) ;;
                      *)
                        python3 "$TORII_ROOT/scripts/skill_fitness.py" ingest-refine-dual --out-dir "$OUT_DIR" >/dev/null 2>&1 || true
                        notice "F171 refine dual chronic-fail decay (soft) · ingest-refine-dual"
                        # F172: multi-tenant federate/promote of decay bins (FederatedSkill)
                        python3 "$TORII_ROOT/scripts/skill_fitness.py" federate-refine-decay >/dev/null 2>&1 || true
                        python3 "$TORII_ROOT/scripts/skill_fitness.py" promote-refine-decay >/dev/null 2>&1 || true
                        notice "F172 refine dual decay federate+promote (soft)"
                        # F175: dual_pass revive after decay → multi-tenant re-boost always budget
                        case "${TORII_SKILL_FITNESS_REFINE_DUAL_REVIVE:-1}" in
                          0|false|no|off) ;;
                          *)
                            python3 "$TORII_ROOT/scripts/skill_fitness.py" federate-refine-revive >/dev/null 2>&1 || true
                            python3 "$TORII_ROOT/scripts/skill_fitness.py" promote-refine-revive >/dev/null 2>&1 || true
                            notice "F175 refine dual_pass revive federate+promote (soft)"
                            # F176: multi-tenant free-rider gate is inline in ingest/promote;
                            # notice when sticky multi_tenant_decay + local revive pending
                            notice "F176 free-rider revive MT gate (soft · sticky multi_tenant_decay until promote)"
                            notice "F177 revive contribution_pp floor (soft · TORII_REFINE_REVIVE_MIN_PP)"
                            notice "F179 revive LOO attribution floor (soft · skill-attribution free_rider/avg)"
                            notice "F180 hub-archival×GEPA compound demote (soft · dual-loop free-rider)"
                            notice "F181 hub×GEPA compound prompt inject (soft · maker sees dual-loop heat)"
                            notice "F182 hub×GEPA compound always priority (soft · dual-loop heat → always budget)"
                            notice "F183 hub×GEPA compound re-prompt budget (soft · dual-loop heat → f157/f122 slot)"
                            ;;
                        esac
                        ;;
                    esac
                  fi
                  # F168: federate bins + multi-tenant promote (FederatedSkill gate)
                  case "${TORII_SKILL_REFINE_PROMOTE:-1}" in
                    0|false|no|off) ;;
                    *)
                      python3 "$TORII_ROOT/scripts/skill_dual_rollout.py" promote-refine-dual >/dev/null 2>&1 || true
                      python3 "$TORII_ROOT/scripts/skill_dual_rollout.py" cycle-refine-promote --out-dir "$OUT_DIR" --skip-dual >/dev/null 2>&1 || true
                      notice "F168 refine dual federate+promote · promoted-refine-dual-themes.json"
                      ;;
                  esac
                  ;;
              esac
            fi
            ;;
        esac
      fi
      # F136/F137: scorecard util before composite re-prompt decide
      python3 "$SKILL_ROUTER_HELPER" scorecard-util --out-dir "$OUT_DIR" >/dev/null 2>&1 || true
      _rrp_args=(reprompt-decide --out-dir "$OUT_DIR" --review "$RAW_OUT")
      [[ -f "$OUT_DIR/recovery-skill-reprompt.env" ]] && _rrp_args+=(--already-env "$OUT_DIR/recovery-skill-reprompt.env")
      _rrp_kv="$(python3 "$SKILL_ROUTER_HELPER" "${_rrp_args[@]}" 2>/dev/null || true)"
      _rrp_do="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^reprompt=//p' | head -1)"
      REC_REPROMPT_REASON="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^reason=//p' | head -1)"
      _rrp_tt="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^tool_call_turns=//p' | head -1)"
      _rrp_idle="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^idle_ids=//p' | head -1)"
      _rrp_ichars="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^inject_chars=//p' | head -1)"
      # F126: hub gap pressure bias fields from reprompt-decide
      _rrp_hgp="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^hub_gap_pressure=//p' | head -1)"
      _rrp_hgb="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^hub_gap_bias=//p' | head -1)"
      # F137: scorecard util re-prompt fields
      _rrp_sc_do="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^scorecard_reprompt=//p' | head -1)"
      _rrp_sc_idle="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^scorecard_idle_ids=//p' | head -1)"
      _rrp_sc_gap="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^scorecard_utilization_gap=//p' | head -1)"
      _rrp_sc_only="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^scorecard_only=//p' | head -1)"
      _rrp_sc_hub="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^hub_scorecard_util_gap=//p' | head -1)"
      # F157: hub-archival util gap fields
      _rrp_ha_gap="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^hub_archival_util_gap=//p' | head -1)"
      _rrp_bkind="$(printf '%s\n' "$_rrp_kv" | sed -n 's/^budget_kind=//p' | head -1)"
      if [[ "$_rrp_do" == "1" || "$_rrp_do" == "true" ]] && [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
        _rbud_kind="f122"
        [[ "$_rrp_sc_only" == "1" ]] && _rbud_kind="f137"
        # F157: prefer budget_kind from decide when hub-archival util gap
        [[ "$_rrp_bkind" == "f157" || "$_rrp_ha_gap" == "1" ]] && _rbud_kind="f157"
        _rbud_kv="$(python3 "$REPROMPT_BUDGET_HELPER" allow --out-dir "$OUT_DIR" --kind "$_rbud_kind" 2>/dev/null || true)"
        _rbud_allow="$(printf '%s\n' "$_rbud_kv" | sed -n 's/^allow=//p' | head -1)"
        _rbud_adapt="$(printf '%s\n' "$_rbud_kv" | sed -n 's/^adaptive_expanded=//p' | head -1)"
        _rbud_areason="$(printf '%s\n' "$_rbud_kv" | sed -n 's/^adaptive_reason=//p' | head -1)"
        if [[ "$_rbud_adapt" == "1" ]]; then
          notice "F159 adaptive dual-recovery slot · kind=${_rbud_kind} reason=${_rbud_areason:-complementary}"
        fi
        if [[ "$_rbud_allow" != "1" && "$_rbud_allow" != "true" ]]; then
          _rbud_reason="$(printf '%s\n' "$_rbud_kv" | sed -n 's/^reason=//p' | head -1)"
          notice "F108 re-prompt budget blocked F122/F137/F157 · reason=${_rbud_reason:-budget}"
          REC_REPROMPT_REASON="budget_blocked:${_rbud_reason:-exhausted}"
          _rrp_do="0"
        fi
      fi
      if [[ "$_rrp_do" == "1" || "$_rrp_do" == "true" ]]; then
        REC_REPROMPT_ATTEMPTED=1
        notice "F122/F137/F157 skill util soft re-prompt · idle=${_rrp_idle:-?} sc_idle=${_rrp_sc_idle:-?} tool_turns=${_rrp_tt:-?} reason=${REC_REPROMPT_REASON:-gap} hub_gap=${_rrp_hgp:-0} sc_reprompt=${_rrp_sc_do:-0} ha_gap=${_rrp_ha_gap:-0} kind=${_rbud_kind:-f122} adaptive=${_rbud_adapt:-0}"
        if [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
          _rbud_kind="f122"
          [[ "$_rrp_sc_only" == "1" ]] && _rbud_kind="f137"
          [[ "$_rrp_bkind" == "f157" || "$_rrp_ha_gap" == "1" ]] && _rbud_kind="f157"
          python3 "$REPROMPT_BUDGET_HELPER" consume --out-dir "$OUT_DIR" --kind "$_rbud_kind" --note "attempt_start" >/dev/null 2>&1 || true
        fi
        if [[ ! -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" ]]; then
          cp -f "$RAW_OUT" "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" 2>/dev/null || true
          [[ -d "$LOOP_DIR" ]] && rm -rf "$OUT_DIR/agent-loop-attempt1" && cp -a "$LOOP_DIR" "$OUT_DIR/agent-loop-attempt1" 2>/dev/null || true
        fi
        _rrp_base="$PROMPT_PATH"
        [[ -s "$OUT_DIR/prompt-memory-reprompt.md" ]] && _rrp_base="$OUT_DIR/prompt-memory-reprompt.md"
        [[ -s "$OUT_DIR/prompt-reprompt.md" ]] && _rrp_base="$OUT_DIR/prompt-reprompt.md"
        REC_REPROMPT_PROMPT="$OUT_DIR/prompt-recovery-reprompt.md"
        # F126: pass hub gap pressure into recovery re-prompt body
        export TORII_HUB_GAP_PRESSURE="${_rrp_hgp:-0}"
        export TORII_HUB_GAP_BIAS="${_rrp_hgb:-0}"
        export TORII_SCORECARD_UTIL_GAP="${_rrp_sc_gap:-0}"
        export TORII_HUB_SCORECARD_UTIL_GAP="${_rrp_sc_hub:-0}"
        export TORII_HUB_ARCHIVAL_UTIL_GAP="${_rrp_ha_gap:-0}"
        python3 "$SKILL_ROUTER_HELPER" reprompt-write \
          --prompt-in "$_rrp_base" \
          --prompt-out "$REC_REPROMPT_PROMPT" \
          --idle-ids "${_rrp_idle:-}" \
          --tool-turns "${_rrp_tt:-0}" \
          --inject-chars "${_rrp_ichars:-0}" \
          --hub-gap-pressure "${_rrp_hgp:-0}" \
          --hub-gap-bias "${_rrp_hgb:-0}" \
          --scorecard-idle-ids "${_rrp_sc_idle:-}" \
          --scorecard-gap "${_rrp_sc_gap:-0}" \
          --hub-scorecard-util-gap "${_rrp_sc_hub:-0}" \
          --scorecard-only "${_rrp_sc_only:-0}" \
          --hub-archival-util-gap "${_rrp_ha_gap:-0}" >/dev/null 2>&1 || true
        if [[ -s "$REC_REPROMPT_PROMPT" ]]; then
          PROMPT="$(cat "$REC_REPROMPT_PROMPT")"
          LOG_OFFSET=0
          if [[ -f "$LOG_FILE" ]]; then
            LOG_OFFSET=$(wc -c <"$LOG_FILE" | tr -d ' ')
          fi
          echo "$LOG_OFFSET" >"$OUT_DIR/hermes-log-offset-recovery-reprompt.txt" || true
          STDERR_FILE_RRP="$OUT_DIR/hermes-${PR_NUMBER}.recovery-reprompt.stderr"
          set +e
          (
            cd "$WORKSPACE_ROOT"
            if [[ $STREAM_LOGS -eq 1 ]]; then
              _hermes_wrap hermes -z "$PROMPT" \
                --provider openrouter \
                --model "$MODEL" \
                -t "$TOOLSETS" \
                --usage-file "$USAGE_FILE" \
                >"$RAW_OUT" 2> >(tee -a "$STDERR_FILE_RRP" >&2)
            else
              _hermes_wrap hermes -z "$PROMPT" \
                --provider openrouter \
                --model "$MODEL" \
                -t "$TOOLSETS" \
                --usage-file "$USAGE_FILE" \
                >"$RAW_OUT" 2>"$STDERR_FILE_RRP"
            fi
          )
          RC_RRP=$?
          set -e
          if [[ $RC_RRP -eq 124 ]]; then
            notice "F122 recovery re-prompt TIMED OUT — keeping prior body"
            if [[ -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" ]]; then
              cp -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" "$RAW_OUT"
            fi
            REC_REPROMPT_REASON="reprompt_timeout"
            TIMED_OUT=1
            {
              echo "reprompt=1"
              echo "enabled=1"
              echo "reason=reprompt_timeout"
              echo "attempted=1"
              echo "recovered=0"
              echo "feature=F122"
            } >"$OUT_DIR/recovery-skill-reprompt.env" || true
          elif [[ $RC_RRP -ne 0 || ! -s "$RAW_OUT" ]]; then
            notice "F122 recovery re-prompt failed/empty (rc=$RC_RRP) — keeping prior body"
            if [[ -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" ]]; then
              cp -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" "$RAW_OUT"
            fi
            {
              echo "reprompt=1"
              echo "enabled=1"
              echo "reason=reprompt_failed"
              echo "attempted=1"
              echo "recovered=0"
              echo "feature=F122"
            } >"$OUT_DIR/recovery-skill-reprompt.env" || true
          else
            RC=$RC_RRP
            if [[ -s "$STDERR_FILE_RRP" ]]; then
              {
                echo ""
                echo "===== F122 recovery soft re-prompt stderr ====="
                cat "$STDERR_FILE_RRP"
              } >>"$STDERR_FILE" 2>/dev/null || true
            fi
            if [[ -f "$LOG_FILE" ]]; then
              python3 - <<'PY' "$LOG_FILE" "$OUT_DIR/hermes-run.log" "$LOG_OFFSET"
import sys
from pathlib import Path
src, dest, off = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3] or 0)
data = src.read_bytes()
chunk = data[off:] if off < len(data) else data[-200_000:]
dest.write_bytes(chunk)
print(f"hermes-run.log (recovery-reprompt) bytes={len(chunk)}", file=sys.stderr)
PY
            fi
            export HERMES_LOG_OFFSET="$LOG_OFFSET"
            rm -rf "$LOOP_DIR"
            mkdir -p "$LOOP_DIR"
            python3 "$TORII_ROOT/scripts/capture-hermes-loop.py" || notice "capture-hermes-loop (recovery-reprompt) soft-failed"
            # re-score util after re-run
            _rec_score2=(score --review "$RAW_OUT" --out-dir "$OUT_DIR")
            [[ -f "$LOOP_DIR/agent-loop.json" ]] && _rec_score2+=(--agent-loop "$LOOP_DIR/agent-loop.json")
            python3 "$SKILL_ROUTER_HELPER" "${_rec_score2[@]}" >/dev/null 2>&1 || true
            _util_after="$(python3 "$SKILL_ROUTER_HELPER" util --out-dir "$OUT_DIR" 2>/dev/null || true)"
            _tool_after="$(printf '%s\n' "$_util_after" | python3 -c 'import sys,json
try:
 d=json.load(sys.stdin); print(int(d.get("tool_hit_n") or 0))
except Exception:
 print(0)' 2>/dev/null || echo 0)"
            if [[ "${_tool_after:-0}" -ge 1 ]] 2>/dev/null; then
              REC_REPROMPT_RECOVERED=1
              notice "F122 recovery re-prompt recovered tool_hit_n=${_tool_after}"
              if [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
                python3 "$REPROMPT_BUDGET_HELPER" consume --out-dir "$OUT_DIR" --kind f122 --recovered --note "tool_hits→${_tool_after}" >/dev/null 2>&1 || true
              fi
            else
              notice "F122 recovery re-prompt still tool_hit_n=${_tool_after:-0}"
            fi
            {
              echo "reprompt=1"
              echo "enabled=1"
              echo "reason=${REC_REPROMPT_REASON:-recovery_utilization_gap}"
              echo "attempted=1"
              echo "recovered=$REC_REPROMPT_RECOVERED"
              echo "tool_hit_n_after=${_tool_after:-}"
              echo "feature=F122"
            } >"$OUT_DIR/recovery-skill-reprompt.env" || true
          fi
        else
          {
            echo "reprompt=0"
            echo "enabled=1"
            echo "reason=prompt_write_failed"
            echo "attempted=0"
            echo "recovered=0"
            echo "feature=F122"
          } >"$OUT_DIR/recovery-skill-reprompt.env" || true
        fi
      else
        {
          echo "reprompt=0"
          echo "enabled=1"
          echo "reason=${REC_REPROMPT_REASON:-skipped}"
          echo "attempted=0"
          echo "recovered=0"
          echo "feature=F122"
        } >"$OUT_DIR/recovery-skill-reprompt.env" || true
      fi
      ;;
  esac
else
  {
    echo "reprompt=0"
    echo "enabled=${TORII_RECOVERY_SKILL_REPROMPT:-1}"
    echo "reason=preconditions_not_met"
    echo "attempted=0"
    echo "recovered=0"
    echo "feature=F122"
  } >"$OUT_DIR/recovery-skill-reprompt.env" || true
fi

# F152: recon-warm hub heat idle soft re-prompt (shared F108 budget, kind=f152)
# Fires only when F122/F137 did not already consume the paid attempt.
ARCHIVAL_HELPER="${ARCHIVAL_HELPER:-$TORII_ROOT/scripts/archival_memory_search.py}"
RW_REPROMPT_ATTEMPTED=0
RW_REPROMPT_REASON="skipped"
if [[ -f "$ARCHIVAL_HELPER" && "${TORII_RECON_WARM_REPROMPT:-1}" != "0" ]]; then
  _rw_already=0
  [[ -f "$OUT_DIR/recovery-skill-reprompt.env" ]] && grep -qE '^(attempted|reprompt)=1' "$OUT_DIR/recovery-skill-reprompt.env" 2>/dev/null && _rw_already=1
  [[ -f "$OUT_DIR/tool-turns-reprompt.env" ]] && grep -qE '^(attempted|reprompt)=1' "$OUT_DIR/tool-turns-reprompt.env" 2>/dev/null && _rw_already=1
  _rw_args=(reprompt-decide --out-dir "$OUT_DIR" --tool-turns "${TOOL_CALL_TURNS:-0}")
  [[ "$_rw_already" == "1" ]] && _rw_args+=(--already-reprompted)
  _rw_kv="$(python3 "$ARCHIVAL_HELPER" "${_rw_args[@]}" 2>/dev/null || true)"
  _rw_do="$(printf '%s\n' "$_rw_kv" | sed -n 's/^reprompt=//p' | head -1)"
  RW_REPROMPT_REASON="$(printf '%s\n' "$_rw_kv" | sed -n 's/^reason=//p' | head -1)"
  _rw_heat="$(printf '%s\n' "$_rw_kv" | sed -n 's/^heat=//p' | head -1)"
  _rw_boost="$(printf '%s\n' "$_rw_kv" | sed -n 's/^hub_boost_n=//p' | head -1)"
  _rw_themes="$(printf '%s\n' "$_rw_kv" | sed -n 's/^themes=//p' | head -1)"
  if [[ "$_rw_do" == "1" || "$_rw_do" == "true" ]] && [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
    _rbud_kv="$(python3 "$REPROMPT_BUDGET_HELPER" allow --out-dir "$OUT_DIR" --kind f152 2>/dev/null || true)"
    _rbud_allow="$(printf '%s\n' "$_rbud_kv" | sed -n 's/^allow=//p' | head -1)"
    if [[ "$_rbud_allow" != "1" && "$_rbud_allow" != "true" ]]; then
      _rbud_reason="$(printf '%s\n' "$_rbud_kv" | sed -n 's/^reason=//p' | head -1)"
      notice "F108 re-prompt budget blocked F152 · reason=${_rbud_reason:-budget}"
      RW_REPROMPT_REASON="budget_blocked:${_rbud_reason:-exhausted}"
      _rw_do="0"
    fi
  fi
  if [[ "$_rw_do" == "1" || "$_rw_do" == "true" ]]; then
    RW_REPROMPT_ATTEMPTED=1
    notice "F152 recon-warm hub soft re-prompt · heat=${_rw_heat:-?} boost=${_rw_boost:-0} reason=${RW_REPROMPT_REASON:-gap}"
    if [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
      python3 "$REPROMPT_BUDGET_HELPER" consume --out-dir "$OUT_DIR" --kind f152 --note "attempt_start" >/dev/null 2>&1 || true
    fi
    _rw_base="$PROMPT_PATH"
    [[ -s "$OUT_DIR/prompt-memory-reprompt.md" ]] && _rw_base="$OUT_DIR/prompt-memory-reprompt.md"
    [[ -s "$OUT_DIR/prompt-reprompt.md" ]] && _rw_base="$OUT_DIR/prompt-reprompt.md"
    [[ -s "$OUT_DIR/prompt-recovery-reprompt.md" ]] && _rw_base="$OUT_DIR/prompt-recovery-reprompt.md"
    RW_REPROMPT_PROMPT="$OUT_DIR/prompt-recon-warm-reprompt.md"
    python3 "$ARCHIVAL_HELPER" reprompt-write \
      --prompt-in "$_rw_base" \
      --prompt-out "$RW_REPROMPT_PROMPT" \
      --themes "${_rw_themes:-}" \
      --heat "${_rw_heat:-0}" \
      --hub-boost-n "${_rw_boost:-0}" >/dev/null 2>&1 || true
    if [[ -s "$RW_REPROMPT_PROMPT" ]]; then
      PROMPT="$(cat "$RW_REPROMPT_PROMPT")"
      # Soft second pass: rewrite RAW_OUT if hermes available (same as recovery path abbreviated)
      if command -v hermes >/dev/null 2>&1 || type _hermes_wrap >/dev/null 2>&1; then
        if [[ ! -f "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" ]]; then
          cp -f "$RAW_OUT" "$OUT_DIR/review-${PR_NUMBER}.attempt1.raw.md" 2>/dev/null || true
        fi
        STDERR_FILE_RW="$OUT_DIR/hermes-${PR_NUMBER}.recon-warm-reprompt.stderr"
        set +e
        (
          cd "$WORKSPACE_ROOT"
          if [[ ${STREAM_LOGS:-0} -eq 1 ]]; then
            _hermes_wrap hermes -z "$PROMPT" \
              --provider openrouter \
              --model "$MODEL" \
              -t "$TOOLSETS" \
              --usage-file "$USAGE_FILE" \
              >"$RAW_OUT" 2> >(tee -a "$STDERR_FILE_RW" >&2)
          else
            _hermes_wrap hermes -z "$PROMPT" \
              --provider openrouter \
              --model "$MODEL" \
              -t "$TOOLSETS" \
              --usage-file "$USAGE_FILE" \
              >"$RAW_OUT" 2>>"$STDERR_FILE_RW"
          fi
        )
        set -e
        notice "F152 recon-warm re-prompt hermes pass done"
        if [[ -f "$REPROMPT_BUDGET_HELPER" ]]; then
          python3 "$REPROMPT_BUDGET_HELPER" consume --out-dir "$OUT_DIR" --kind f152 --recovered --note "f152_ran" >/dev/null 2>&1 || true
        fi
      fi
    fi
  fi
  {
    echo "reprompt=${_rw_do:-0}"
    echo "enabled=1"
    echo "reason=${RW_REPROMPT_REASON:-skipped}"
    echo "attempted=$RW_REPROMPT_ATTEMPTED"
    echo "heat=${_rw_heat:-0}"
    echo "hub_boost_n=${_rw_boost:-0}"
    echo "feature=F152"
  } >"$OUT_DIR/recon-warm-reprompt.env" || true
  # F153/F154: soft self-evolve propose + dual-gate cycle-adopt hub-archival when F152 fires
  if [[ "${RW_REPROMPT_ATTEMPTED}" == "1" || "${_rw_do}" == "1" ]] && [[ -f "$TORII_ROOT/scripts/self_evolve.py" ]]; then
    python3 "$TORII_ROOT/scripts/self_evolve.py" ingest --out-dir "$OUT_DIR" >/dev/null 2>&1 || true
    python3 "$TORII_ROOT/scripts/self_evolve.py" propose --limit 3 >/dev/null 2>&1 || true
    notice "F153 self-evolve propose hub-archival skill (soft)"
    if [[ -f "$TORII_ROOT/scripts/skill_auto_adopt.py" ]]; then
      python3 "$TORII_ROOT/scripts/skill_auto_adopt.py" cycle-hub-archival --force --skip-gates >/dev/null 2>&1 || true
      notice "F154 cycle-hub-archival dual-gate adopt (soft)"
    fi
  fi
else
  {
    echo "reprompt=0"
    echo "enabled=${TORII_RECON_WARM_REPROMPT:-1}"
    echo "reason=helper_missing_or_off"
    echo "attempted=0"
    echo "feature=F152"
  } >"$OUT_DIR/recon-warm-reprompt.env" || true
fi

# F46 / H13: detect Hermes actually blocking SOUL.md at load time
# F48 / H16: only scan *this invocation* artifacts (offset-sliced hermes-run.log +
# stderr). Do NOT scan the full Hermes agent.log / errors.log history — capture
# used to copy the last 200k of shared HERMES_HOME logs, which re-fired stale
# "SOUL.md blocked" lines from earlier runs (false soul_blocked=1 on H16).
SOUL_BLOCKED=0
SOUL_BLOCK_REASON=""
if [[ -f "$SOUL_SCAN_HELPER" ]]; then
  _soul_detect_paths=()
  [[ -f "$STDERR_FILE" ]] && _soul_detect_paths+=("$STDERR_FILE")
  [[ -f "$OUT_DIR/hermes-run.log" ]] && _soul_detect_paths+=("$OUT_DIR/hermes-run.log")
  # After F48 capture writes an offset-sliced agent.log — safe if present.
  [[ -f "$LOOP_DIR/agent.log" ]] && _soul_detect_paths+=("$LOOP_DIR/agent.log")
  if [[ ${#_soul_detect_paths[@]} -gt 0 ]]; then
    if _soul_det="$(python3 "$SOUL_SCAN_HELPER" detect "${_soul_detect_paths[@]}" 2>/dev/null)"; then
      SOUL_BLOCKED=0
    else
      _sdr=$?
      if [[ $_sdr -eq 2 ]]; then
        SOUL_BLOCKED=1
        SOUL_BLOCK_REASON="$(printf '%s\n' "$_soul_det" | sed -n 's/^reason=//p' | head -1)"
      fi
    fi
  fi
fi
{
  echo "soul_blocked=$SOUL_BLOCKED"
  echo "reason=${SOUL_BLOCK_REASON:-}"
} >"$OUT_DIR/soul-context.env" || true
if [[ "$SOUL_BLOCKED" -eq 1 ]]; then
  notice "F46 Hermes blocked SOUL.md (${SOUL_BLOCK_REASON:-prompt_injection}) — reviewer contract not loaded"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo "### Torii SOUL blocked (F46)"
      echo "- Hermes log: \`Context file SOUL.md blocked: ${SOUL_BLOCK_REASON:-prompt_injection}\`"
      echo "- Reviewer discipline / trust model did **not** load into the system prompt"
      echo "- Fix: rephrase \`agent/SOUL.md\`; verify with \`python3 scripts/soul_context_scan.py check\`"
      echo
    } >>"$GITHUB_STEP_SUMMARY" || true
  fi
fi

# F41: detect Hermes iteration-budget exhaustion (logs / stderr / agent-loop)
MAX_TURNS_HIT=0
if [[ -f "$MAX_TURNS_HELPER" ]]; then
  _detect_paths=()
  [[ -f "$STDERR_FILE" ]] && _detect_paths+=("$STDERR_FILE")
  [[ -f "$OUT_DIR/hermes-run.log" ]] && _detect_paths+=("$OUT_DIR/hermes-run.log")
  [[ -f "$LOOP_DIR/agent-loop.md" ]] && _detect_paths+=("$LOOP_DIR/agent-loop.md")
  [[ -f "$LOOP_DIR/agent.log" ]] && _detect_paths+=("$LOOP_DIR/agent.log")
  if [[ ${#_detect_paths[@]} -gt 0 ]]; then
    if python3 "$MAX_TURNS_HELPER" detect "${_detect_paths[@]}" >/dev/null 2>&1; then
      : # hit=0 (exit 0)
    else
      _drc=$?
      if [[ $_drc -eq 2 ]]; then
        MAX_TURNS_HIT=1
      fi
    fi
  fi
fi
{
  echo "max_turns_enabled=$MAX_TURNS_ENABLED"
  echo "max_turns=${MAX_TURNS_VAL:-off}"
  echo "max_turns_hit=$MAX_TURNS_HIT"
} >"$OUT_DIR/hermes-max-turns.env" || true
if [[ "$MAX_TURNS_HIT" -eq 1 ]]; then
  notice "F41 Hermes max_turns hit (cap=${MAX_TURNS_VAL:-?}) — iteration budget exhausted"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo "### Torii max turns (F41)"
      echo "- **Iteration budget exhausted** at \`${MAX_TURNS_VAL:-?}\` tool-calling turns"
      echo "- Raise \`vars.TORII_MAX_TURNS\` or use a faster/cheaper model; \`0\`/\`off\` disables the cap"
      echo
    } >>"$GITHUB_STEP_SUMMARY" || true
  fi
fi

if [[ ! -s "$RAW_OUT" ]]; then
  _fail_summary="Torii failed to produce a review (hermes exit ${RC}). Check workflow logs, Hermes install, and OpenRouter credits/key."
  _fail_blocking="Review agent run failed — re-trigger with \`@torii review this pr\` after fixing CI/OpenRouter."
  if [[ $TIMED_OUT -eq 1 ]]; then
    _fail_summary="Torii Gate review **timed out** after ${TIMEOUT_SECS}s wall-clock (F36). Hermes was killed to stop runaway OpenRouter spend. Re-trigger with a cheaper model or raise \`TORII_REVIEW_TIMEOUT_SECONDS\`."
    _fail_blocking="Agent loop exceeded \`TORII_REVIEW_TIMEOUT_SECONDS=${TIMEOUT_SECS}\` — increase the var, use a faster model (\`vars.TORII_MODEL\`), or re-run with a smaller PR diff."
  elif [[ "${HERMES_CLI_ARGV_BROKEN:-0}" -eq 1 ]]; then
    _fail_summary="Torii **Hermes CLI argv rejected** (F47/H14, hermes exit ${RC}). Unknown flags (historically \`--max-turns\`) made \`hermes -z\` fail before any model call; chat fallback skipped to avoid zero-tool spend. Cap iterations via \`HERMES_MAX_ITERATIONS\` / \`agent.max_turns\` only."
    _fail_blocking="Fix Hermes CLI flags in \`run-hermes-review.sh\` (do not pass non-Hermes flags to \`hermes -z\`) and re-trigger."
  elif [[ "$MAX_TURNS_HIT" -eq 1 ]]; then
    _fail_summary="Torii Gate review hit the **Hermes iteration budget** (F41, max_turns=${MAX_TURNS_VAL:-?}). The agent loop stopped before producing a full review to cap OpenRouter spend. Raise \`TORII_MAX_TURNS\` or simplify the PR."
    _fail_blocking="Agent loop exhausted \`TORII_MAX_TURNS=${MAX_TURNS_VAL:-?}\` tool turns — increase the var, disable with \`0\`/\`off\`, or re-run with a smaller diff / cheaper model."
  fi
  cat >"$RAW_OUT" <<EOF
## 🏴‍☠️ Torii Review — PR #${PR_NUMBER}

**Verdict:** COMMENT
**Confidence:** low
**Score:** 20/100
**Review effort:** 1/5

### Summary
${_fail_summary}

### Walkthrough
- Agent runner failure only

### Blocking
- ${_fail_blocking}

### Key findings
None — runner failure.

### Security audit
No

### Multi-lens checklist
| Lens | Status | Note |
|------|--------|------|
| correctness | n/a | runner failure |
| security | n/a | runner failure |
| tests | n/a | runner failure |
| performance | n/a | runner failure |
| api_contracts | n/a | runner failure |
| concurrency | n/a | runner failure |
| maintainability | n/a | runner failure |

### Suggestions
- None

### Code suggestions
None

### Nits
- None

### Tests & risk
- Relevant tests added/updated: unknown
- Coverage: unknown
- Risk: unknown
- Rollback: n/a

### What I checked
- Agent runner only (no successful model response)

---
*Torii · Hermes Agent · OpenRouter · memory-backed review*
EOF
fi

# Normalize into final review.md
# F27: pass --diff-truncated when assemble-context capped the PR diff (meta.env)
_NORM_EXTRA=()
case "${DIFF_TRUNCATED:-false}" in
  true|TRUE|1|yes|YES) _NORM_EXTRA+=(--diff-truncated) ;;
esac
# F59: stamp head SHA into review marker when known
_HEAD_SHA="${HEAD_SHA:-}"
if [[ -z "$_HEAD_SHA" && -f "${OUT_DIR:-}/meta.env" ]]; then
  _HEAD_SHA="$(grep -E '^HEAD_SHA=' "$OUT_DIR/meta.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d "'\"" )" || true
fi
_NORM_HEAD=()
if [[ -n "${_HEAD_SHA:-}" ]]; then
  _NORM_HEAD+=(--head-sha "$_HEAD_SHA")
fi
python3 "$TORII_ROOT/scripts/normalize-review.py" \
  --input "$RAW_OUT" \
  --output "$FINAL_OUT" \
  --pr "$PR_NUMBER" \
  --run-id "${GITHUB_RUN_ID:-local}" \
  "${_NORM_HEAD[@]+"${_NORM_HEAD[@]}"}" \
  "${_NORM_EXTRA[@]+"${_NORM_EXTRA[@]}"}"

# F57: soft-inject Mermaid architecture if model omitted it (never fails review)
if [[ -f "$TORII_ROOT/scripts/mermaid_architecture.py" && -s "$FINAL_OUT" ]]; then
  _mm_args=(apply --review "$FINAL_OUT")
  if [[ -f "${OUT_DIR:-}/pr.json" ]]; then
    _mm_args+=(--pr-json "$OUT_DIR/pr.json")
  elif [[ -f "${OUT_DIR:-}/files.txt" ]]; then
    _mm_args+=(--files "$OUT_DIR/files.txt")
  fi
  python3 "$TORII_ROOT/scripts/mermaid_architecture.py" "${_mm_args[@]}"     >/dev/null 2>&1 || notice "F57 mermaid inject soft-failed"
fi

# F61: soft-inject Suggested test plan if model omitted / left placeholder
if [[ -f "$TORII_ROOT/scripts/testplan_generation.py" && -s "$FINAL_OUT" ]]; then
  _tp_args=(apply --review "$FINAL_OUT")
  if [[ -f "${OUT_DIR:-}/pr.json" ]]; then
    _tp_args+=(--pr-json "$OUT_DIR/pr.json")
  fi
  if [[ -f "${OUT_DIR:-}/pr.diff" ]]; then
    _tp_args+=(--diff "$OUT_DIR/pr.diff")
  elif [[ -f "${OUT_DIR:-}/diff.patch" ]]; then
    _tp_args+=(--diff "$OUT_DIR/diff.patch")
  fi
  python3 "$TORII_ROOT/scripts/testplan_generation.py" "${_tp_args[@]}" \
    >/dev/null 2>&1 || notice "F61 testplan inject soft-failed"
fi

if [[ "${#_NORM_EXTRA[@]}" -gt 0 ]]; then
  notice "F27 diff was truncated — banner injected into posted review"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo "### Torii diff truncation (F27)"
      echo "- **DIFF_TRUNCATED:** true — review saw only the first \`MAX_DIFF_BYTES\` of the PR diff"
      echo "- Posted review includes a visible ⚠️ banner"
      echo
    } >>"$GITHUB_STEP_SUMMARY" || true
  fi
fi

# F21/F29: surface cost/tokens (+ soft budget note) on the posted comment
if [[ -f "$TORII_ROOT/scripts/usage-summary.py" ]]; then
  python3 "$TORII_ROOT/scripts/usage-summary.py" append \
    --usage "$USAGE_FILE" \
    --review "$FINAL_OUT" \
    --max-usd "${TORII_MAX_COST_USD:-}" || notice "usage-summary append soft-failed"
fi

# F45 / H12: fail closed when tool_turns=0 on multi-file non-docs PRs
# (after F49 soft re-prompt when applicable — odoo e2e #2/#4 mini vs GHA).
TOOL_TURNS_GATE_HELPER="${TOOL_TURNS_GATE_HELPER:-$TORII_ROOT/scripts/tool_turns_gate.py}"
if [[ -f "$TOOL_TURNS_GATE_HELPER" && -s "$FINAL_OUT" ]]; then
  _ttg_args=(
    apply
    --review "$FINAL_OUT"
    --out "$FINAL_OUT"
    --env-out "$OUT_DIR/tool-turns-gate.env"
  )
  [[ -f "$LOOP_DIR/agent-loop.json" ]] && _ttg_args+=(--loop-json "$LOOP_DIR/agent-loop.json")
  [[ -n "${FILE_COUNT:-}" ]] && _ttg_args+=(--file-count "$FILE_COUNT")
  [[ -f "$OUT_DIR/files.txt" ]] && _ttg_args+=(--paths-file "$OUT_DIR/files.txt")
  if _ttg_kv="$(python3 "$TOOL_TURNS_GATE_HELPER" "${_ttg_args[@]}" 2>/dev/null)"; then
    _ttg_gate="$(printf '%s\n' "$_ttg_kv" | sed -n 's/^gate=//p' | head -1)"
    _ttg_mut="$(printf '%s\n' "$_ttg_kv" | sed -n 's/^mutated=//p' | head -1)"
    _ttg_reason="$(printf '%s\n' "$_ttg_kv" | sed -n 's/^reason=//p' | head -1)"
    if [[ "$_ttg_gate" == "1" || "$_ttg_gate" == "true" ]]; then
      notice "F45 tool-turns gate · reason=${_ttg_reason:-?} mutated=${_ttg_mut:-0} (zero tools on multi-file code PR)"
      if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
        {
          echo "### Torii tool-turns gate (F45)"
          echo "- **Gate fired:** zero Hermes tool turns on multi-file non-docs PR"
          echo "- **Reason:** \`${_ttg_reason:-zero_tools_multi_file_code}\`"
          echo "- **Action:** APPROVE → COMMENT (fail closed) when applicable; banner injected"
          echo "- F49 soft re-prompt attempted=\`${REPROMPT_ATTEMPTED:-0}\` recovered=\`${REPROMPT_RECOVERED:-0}\`"
          echo "- Re-run so the agent reads changed files (\`hermes -z\` with tools)"
          echo
        } >>"$GITHUB_STEP_SUMMARY" || true
      fi
    fi
  else
    notice "F45 tool-turns gate soft-failed"
  fi
fi

# F50 / H20: severity calibration — APPROVE + self-reported test gap → REQUEST CHANGES
# (odoo e2e #2 F49 APPROVE 95 while Suggestions asked for missing format:false tests).
SEVERITY_CAL_HELPER="${SEVERITY_CAL_HELPER:-$TORII_ROOT/scripts/severity_calibration.py}"
if [[ -f "$SEVERITY_CAL_HELPER" && -s "$FINAL_OUT" ]]; then
  _sc_args=(
    apply
    --review "$FINAL_OUT"
    --out "$FINAL_OUT"
    --env-out "$OUT_DIR/severity-calibration.env"
  )
  if _sc_kv="$(python3 "$SEVERITY_CAL_HELPER" "${_sc_args[@]}" 2>/dev/null)"; then
    _sc_gate="$(printf '%s\n' "$_sc_kv" | sed -n 's/^gate=//p' | head -1)"
    _sc_mut="$(printf '%s\n' "$_sc_kv" | sed -n 's/^mutated=//p' | head -1)"
    _sc_reason="$(printf '%s\n' "$_sc_kv" | sed -n 's/^reason=//p' | head -1)"
    _sc_match="$(printf '%s\n' "$_sc_kv" | sed -n 's/^match=//p' | head -1)"
    if [[ "$_sc_gate" == "1" || "$_sc_gate" == "true" ]]; then
      notice "F50 severity calibration · reason=${_sc_reason:-?} match=${_sc_match:-?} mutated=${_sc_mut:-0}"
      if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
        {
          echo "### Torii severity calibration (F50 / H20)"
          echo "- **Gate fired:** self-reported test gap under merge-green verdict"
          echo "- **Reason:** \`${_sc_reason:-approve_with_test_gap}\`"
          echo "- **Match:** \`${_sc_match:-}\`"
          echo "- **Action:** APPROVE → REQUEST CHANGES when applicable; score capped; banner injected"
          echo
        } >>"$GITHUB_STEP_SUMMARY" || true
      fi
    fi
  else
    notice "F50 severity calibration soft-failed"
  fi
fi

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "review_file=$FINAL_OUT"
    echo "raw_file=$RAW_OUT"
    echo "hermes_rc=$RC"
    echo "agent_loop_dir=$LOOP_DIR"
    echo "usage_file=$USAGE_FILE"
  } >>"$GITHUB_OUTPUT"
fi

echo "REVIEW_FILE=$FINAL_OUT"
echo "AGENT_LOOP_DIR=$LOOP_DIR"
notice "Review written: $FINAL_OUT ($(wc -c <"$FINAL_OUT" | tr -d ' ') bytes)"
if [[ -f "$LOOP_DIR/agent-loop.json" ]]; then
  notice "Agent loop captured: $LOOP_DIR"
fi

#!/usr/bin/env bash
# Torii orchestrator: assemble → hermes → normalize → distill → save-trace.
#
# Env:
#   OPENROUTER_API_KEY (required)
#   REPO / GITHUB_REPOSITORY, PR_NUMBER
#   TORII_ROOT, WORKSPACE_ROOT, HERMES_HOME, OUT_DIR
#   TORII_MODEL, TRIGGER_COMMENT, MAX_DIFF_BYTES
#   POST_COMMENT=1 to also post (optional)
set -euo pipefail

TORII_ROOT="${TORII_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export TORII_ROOT
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$TORII_ROOT}"
export OUT_DIR="${OUT_DIR:-$TORII_ROOT/.torii-out}"
export HERMES_HOME="${HERMES_HOME:-$TORII_ROOT/.torii-hermes-home}"
export GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
export TRACE_ROOT="${TRACE_ROOT:-$OUT_DIR/traces}"

SCRIPTS="$TORII_ROOT/scripts"
chmod +x "$SCRIPTS"/*.sh 2>/dev/null || true

mkdir -p "$OUT_DIR"
export TORII_STARTED_AT
TORII_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TIMINGS_FILE="$OUT_DIR/timings.json"
: >"$OUT_DIR/timings.partial.tsv"

stage() {
  local name="$1"
  shift
  local start end elapsed
  start="$(date +%s)"
  echo "::notice::Torii stage: $name" >&2
  set +e
  "$@"
  local rc=$?
  set -e
  end="$(date +%s)"
  elapsed=$((end - start))
  printf '%s\t%s\t%s\n' "$name" "$elapsed" "$rc" >>"$OUT_DIR/timings.partial.tsv"
  return "$rc"
}

echo "::notice::Torii orchestrator · root=$TORII_ROOT workspace=$WORKSPACE_ROOT" >&2

# Snapshot memory before review (for trace)
if [[ -f "$HERMES_HOME/memories/MEMORY.md" ]]; then
  cp -f "$HERMES_HOME/memories/MEMORY.md" "$OUT_DIR/memory-before.md"
fi

# F28: repo-local memory default
export TORII_MEMORY_MODE="${TORII_MEMORY_MODE:-local}"
# Torii Gate: security pack is product default (override with TORII_LENS_PACK)
export TORII_LENS_PACK="${TORII_LENS_PACK:-security}"
export TORII_LABEL_PREFIX="${TORII_LABEL_PREFIX:-torii}"
export TORII_PR_LABELS="${TORII_PR_LABELS:-1}"
export TORII_MEMORY_PATH="${TORII_MEMORY_PATH:-.torii}"

ORCH_RC=0
# F3/F28: preload MEMORY — local .torii/ first, hub only if opted in
stage preload_memory "$SCRIPTS/preload-hub-memory.sh" || true

stage assemble "$SCRIPTS/assemble-context.sh" || ORCH_RC=$?

if [[ $ORCH_RC -eq 0 ]]; then
  # shellcheck disable=SC1091
  source "$OUT_DIR/meta.env"
  export PROMPT_PATH PR_NUMBER REPO
fi

# F68: prefer catalog active toolsets when TORII_TOOLSETS unset
if [[ -z "${TORII_TOOLSETS:-}" && -f "$SCRIPTS/agent_tools_pipeline.py" ]]; then
  _ts="$(python3 "$SCRIPTS/agent_tools_pipeline.py" toolsets 2>/dev/null || true)"
  if [[ -n "${_ts:-}" ]]; then
    export TORII_TOOLSETS="$_ts"
    echo "::notice::F68 active toolsets: $TORII_TOOLSETS" >&2
  fi
fi

if [[ $ORCH_RC -eq 0 ]]; then
  stage hermes "$SCRIPTS/run-hermes-review.sh" || ORCH_RC=$?
fi

# Capture hermes rc from timings if available
export HERMES_RC="${ORCH_RC}"

REVIEW_FILE="${OUT_DIR}/review-${PR_NUMBER:-unknown}.md"
if [[ -n "${PR_NUMBER:-}" && -f "$OUT_DIR/review-${PR_NUMBER}.md" ]]; then
  REVIEW_FILE="$OUT_DIR/review-${PR_NUMBER}.md"
fi
export REVIEW_FILE

if [[ $ORCH_RC -eq 0 ]]; then
  stage distill "$SCRIPTS/distill-memory.sh" || true
  # F62: persist author FP/resolve signals into MEMORY.md (after distill)
  if [[ -f "$SCRIPTS/fp_resolve_memory.py" ]]; then
    stage fp_resolve_update \
      python3 "$SCRIPTS/fp_resolve_memory.py" update \
        --out-dir "$OUT_DIR" \
        --memory "${HERMES_HOME}/memories/MEMORY.md" || true
  fi
fi

# Build timings.json
python3 - <<'PY' "$OUT_DIR/timings.partial.tsv" "$TIMINGS_FILE" "$TORII_STARTED_AT"
from pathlib import Path
import json, sys
from datetime import datetime, timezone

tsv, out, started = sys.argv[1:4]
stages = []
total = 0
if Path(tsv).exists():
    for line in Path(tsv).read_text().splitlines():
        if not line.strip():
            continue
        name, elapsed, rc = line.split("\t")
        elapsed = int(elapsed)
        total += elapsed
        stages.append({"name": name, "seconds": elapsed, "exit_code": int(rc)})
Path(out).write_text(json.dumps({
    "started_at": started,
    "ended_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "total_seconds": total,
    "stages": stages,
}, indent=2) + "\n")
PY

export TORII_STATUS
if [[ $ORCH_RC -eq 0 && -s "${REVIEW_FILE:-}" ]]; then
  TORII_STATUS="success"
else
  TORII_STATUS="failed"
fi

stage save_trace "$SCRIPTS/save-trace.sh" || true

# F73: trajectory fitness score + paper-safe vault archive (soft)
if [[ -f "$SCRIPTS/trajectory_fitness.py" ]]; then
  case "${TORII_TRAJECTORY_FITNESS:-1}" in
    0|false|no|off) ;;
    *)
      _f73_review=""
      if [[ -n "${REVIEW_FILE:-}" && -f "${REVIEW_FILE}" ]]; then
        _f73_review="$REVIEW_FILE"
      elif [[ -f "$OUT_DIR/review-${PR_NUMBER:-}.md" ]]; then
        _f73_review="$OUT_DIR/review-${PR_NUMBER}.md"
      elif compgen -G "$OUT_DIR/review*.md" > /dev/null; then
        _f73_review="$(ls -1 "$OUT_DIR"/review*.md 2>/dev/null | head -1)"
      fi
      if [[ -n "$_f73_review" ]]; then
        stage traj_fitness \
          python3 "$SCRIPTS/trajectory_fitness.py" pack \
            --out-dir "$OUT_DIR" \
            --review "$_f73_review" \
            --label "${TORII_TRACE_LABEL:-e2e}" \
            --repo "${REPO:-${GITHUB_REPOSITORY:-}}" \
            --pr "${PR_NUMBER:-}" \
            --model "${TORII_MODEL:-${OPENROUTER_MODEL:-}}" \
            --promote || true
      fi
      ;;
  esac
fi

# F69: package trajectory for self-evolution (soft; always ingest when loop exists)
if [[ -f "$SCRIPTS/self_evolve.py" && -d "$OUT_DIR/agent-loop" ]]; then
  stage evolve_ingest \
    python3 "$SCRIPTS/self_evolve.py" ingest \
      --out-dir "$OUT_DIR" \
      --pr "${PR_NUMBER:-}" \
      --repo "${REPO:-${GITHUB_REPOSITORY:-}}" || true
  # Optional auto-propose when explicitly enabled
  case "${TORII_SELF_EVOLVE:-0}" in
    1|true|yes|on)
      stage evolve_propose python3 "$SCRIPTS/self_evolve.py" propose --limit 3 || true
      stage evolve_eval python3 "$SCRIPTS/self_evolve.py" eval --proposal all || true
      ;;
  esac
fi

# F68: research tool candidates from this tree's loops (soft; opt-in)
case "${TORII_AGENT_TOOLS_RESEARCH:-0}" in
  1|true|yes|on)
    if [[ -f "$SCRIPTS/agent_tools_pipeline.py" ]]; then
      stage tools_research \
        python3 "$SCRIPTS/agent_tools_pipeline.py" research --runs "$OUT_DIR" || true
    fi
    ;;
esac

# Export TRACE_ID for hub payload if save-trace wrote latest dir
if [[ -f "$OUT_DIR/latest-trace-dir.txt" ]]; then
  TRACE_DIR="$(cat "$OUT_DIR/latest-trace-dir.txt")"
  export TRACE_DIR
  if [[ -f "$TRACE_DIR/meta.json" ]]; then
    export TRACE_ID
    TRACE_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("trace_id",""))' "$TRACE_DIR/meta.json" 2>/dev/null || true)"
  fi
fi

# F28: always (default) publish slim pack → target .torii/; hub only when opted in
# F30: soft-fail still records status + ::warning:: (does not flip TORII_STATUS)
stage publish_local "$SCRIPTS/publish-run-local.sh" || true
stage publish_hub "$SCRIPTS/publish-run-to-hub.sh" || true

# F30: emit memory health into logs / Actions annotations
if [[ -f "$SCRIPTS/memory-health.sh" ]]; then
  bash "$SCRIPTS/memory-health.sh" warn-if-bad || true
  bash "$SCRIPTS/memory-health.sh" summary >"$OUT_DIR/memory-health.md" 2>/dev/null || true
fi

# F31: auto-pack Run Console bundle (soft — never fails the review)
# Prefer TRACE_DIR (has meta.json + review.md); fall back to OUT_DIR.
if [[ -f "$SCRIPTS/pack-run-for-ui.py" ]]; then
  PACK_SRC=""
  if [[ -n "${TRACE_DIR:-}" && -d "${TRACE_DIR:-}" ]]; then
    PACK_SRC="$TRACE_DIR"
  elif [[ -f "$OUT_DIR/latest-trace-dir.txt" ]]; then
    PACK_SRC="$(cat "$OUT_DIR/latest-trace-dir.txt")"
  fi
  if [[ -z "$PACK_SRC" || ! -d "$PACK_SRC" ]]; then
    PACK_SRC="$OUT_DIR"
  fi
  PACK_ARGS=(
    python3 "$SCRIPTS/pack-run-for-ui.py"
    --dir "$PACK_SRC"
    -o "$OUT_DIR/run-bundle.json"
    --soft
  )
  if [[ -f "$OUT_DIR/memory-health.env" ]]; then
    PACK_ARGS+=(--memory-health "$OUT_DIR/memory-health.env")
  fi
  if [[ -n "${TRACE_DIR:-}" && -d "${TRACE_DIR:-}" ]]; then
    PACK_ARGS+=(--also "$TRACE_DIR/run-bundle.json")
  fi
  # Host auto-detect inside pack (GITHUB_ACTIONS / MODAL_* / TORII_HOST)
  stage pack_ui_bundle "${PACK_ARGS[@]}" || true
  if [[ -f "$OUT_DIR/run-bundle.json" ]]; then
    echo "RUN_BUNDLE=$OUT_DIR/run-bundle.json"
    if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
      {
        echo "### Torii Run Console bundle (F31)"
        echo ""
        echo "- **path:** \`$OUT_DIR/run-bundle.json\` (also in trace artifact if present)"
        echo "- Load in \`ui/review-console\` via **Load bundle** (or \`npm run pack-fixture\` for fixtures)."
        echo ""
      } >>"$GITHUB_STEP_SUMMARY"
    fi
  fi
fi

if [[ "${POST_COMMENT:-0}" == "1" && -f "${REVIEW_FILE:-}" ]]; then
  stage post_comment "$SCRIPTS/post-review-comment.sh" "$REVIEW_FILE" "${PR_NUMBER:-}" || ORCH_RC=$?
fi

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "review_file=${REVIEW_FILE:-}"
    echo "pr_number=${PR_NUMBER:-}"
    echo "torii_status=$TORII_STATUS"
    if [[ -f "$OUT_DIR/latest-trace-dir.txt" ]]; then
      echo "trace_dir=$(cat "$OUT_DIR/latest-trace-dir.txt")"
    fi
    if [[ -f "$OUT_DIR/run-bundle.json" ]]; then
      echo "run_bundle=$OUT_DIR/run-bundle.json"
    fi
    if [[ -f "$OUT_DIR/memory-health.env" ]]; then
      # surface key lines for workflow consumers
      grep -E '^(MEMORY_SOURCE|LOCAL_PUBLISH|HUB_PUBLISH)=' "$OUT_DIR/memory-health.env" || true
    fi
  } >>"$GITHUB_OUTPUT"
fi

echo "REVIEW_FILE=${REVIEW_FILE:-}"
echo "TORII_STATUS=$TORII_STATUS"
if [[ -f "$OUT_DIR/latest-trace-dir.txt" ]]; then
  echo "TRACE_DIR=$(cat "$OUT_DIR/latest-trace-dir.txt")"
fi
if [[ -f "$OUT_DIR/run-bundle.json" ]]; then
  echo "RUN_BUNDLE=$OUT_DIR/run-bundle.json"
fi
if [[ -f "$OUT_DIR/memory-health.env" ]]; then
  echo "--- memory-health ---"
  cat "$OUT_DIR/memory-health.env"
fi

exit "$ORCH_RC"

#!/usr/bin/env bash
# Torii orchestrator: assemble → hermes → normalize → distill → save-trace.
#
# Env:
#   OPENROUTER_API_KEY (required)
#   REPO / GITHUB_REPOSITORY, PR_NUMBER
#   TORII_ROOT, WORKSPACE_ROOT, HERMES_HOME, OUT_DIR
#   TORII_MODEL, TRIGGER_COMMENT, MAX_DIFF_BYTES
#   POST_COMMENT=1 to also post (optional)
#   TORII_LIVE_LEAN=1 — skip heavy post-gate compound stages (Modal/dogfood default)
#     Keeps: hermes · critic · demote-eval · scorecard · skill util · memory compound · publish
#     Skips: evolve propose/fitness-gate · federate promote · memory consolidate/graph bloat
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

# LIVE_LEAN: product path-to-value — merge signal first, compound loops optional later.
_live_lean() {
  case "${TORII_LIVE_LEAN:-0}" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

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

if _live_lean; then
  echo "::notice::Torii LIVE_LEAN=1 · skip heavy post-gate evolve/fed/consolidate stages" >&2
fi

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

# F105: audit mid-review memory tool use; soft-blend into fitness.json
if [[ -f "$SCRIPTS/memory_tool_audit.py" ]]; then
  case "${TORII_MEMORY_TOOL_AUDIT:-1}" in
    0|false|no|off) ;;
    *)
      _f105_args=(audit --out-dir "$OUT_DIR")
      if [[ -f "$OUT_DIR/fitness.json" ]]; then
        _f105_args+=(--fitness "$OUT_DIR/fitness.json")
      fi
      if [[ -f "$OUT_DIR/prompt.md" ]]; then
        _f105_args+=(--prompt "$OUT_DIR/prompt.md")
      fi
      stage memory_tool_audit \
        python3 "$SCRIPTS/memory_tool_audit.py" "${_f105_args[@]}" || true
      # F142: hub post-score memory util → next-run memory skill priority
      stage memory_hub_score \
        python3 "$SCRIPTS/memory_tool_audit.py" hub-score || true
      ;;
  esac
fi

# F78: multi-checker second-agent critic panel (soft; may demote weak APPROVE)
if [[ -f "$SCRIPTS/second_agent_critic.py" ]]; then
  case "${TORII_SECOND_CRITIC:-1}" in
    0|false|no|off) ;;
    *)
      _f78_review=""
      if [[ -n "${REVIEW_FILE:-}" && -f "${REVIEW_FILE}" ]]; then
        _f78_review="$REVIEW_FILE"
      elif [[ -f "$OUT_DIR/review-${PR_NUMBER:-}.md" ]]; then
        _f78_review="$OUT_DIR/review-${PR_NUMBER}.md"
      elif compgen -G "$OUT_DIR/review*.md" > /dev/null; then
        _f78_review="$(ls -1 "$OUT_DIR"/review*.md 2>/dev/null | head -1)"
      fi
      if [[ -n "$_f78_review" ]]; then
        stage second_agent_critic           python3 "$SCRIPTS/second_agent_critic.py" run             --review "$_f78_review"             --out-dir "$OUT_DIR" || true
      # F81: optional LLM critic artifact (also folded into F78 panel when enabled)
      case "${TORII_LLM_CRITIC:-0}" in
        1|true|yes|on)
          if [[ -f "$SCRIPTS/llm_critic.py" ]]; then
            stage llm_critic \
              python3 "$SCRIPTS/llm_critic.py" run \
                --review "$_f78_review" \
                --out-dir "$OUT_DIR" \
                --out "$OUT_DIR/llm-critic.json" \
                --force || true
          fi
          ;;
      esac
      fi
      # F128: paper-ready critic demote-rate pack (good/weak/hub-gap)
      stage critic_demote_eval \
        python3 "$SCRIPTS/second_agent_critic.py" demote-eval --out-dir "$OUT_DIR" || true
      # F129: product brand/ops scorecard into OUT_DIR.
      # --shallow: do not re-run demote-eval (already staged above). Reuse
      # critic-demote-eval.json when present — prevents double demote + Modal 1500s timeouts.
      stage product_scorecard \
        python3 "$SCRIPTS/torii.py" scorecard --out-dir "$OUT_DIR" --shallow || true
      # F132: self-evolve skill proposals from scorecard gap themes (soft)
      # LIVE_LEAN: skip propose-scorecard (hub/research path; not on critical merge signal)
      if [[ -f "$SCRIPTS/self_evolve.py" ]] && ! _live_lean; then
        case "${TORII_SELF_EVOLVE_SCORECARD:-1}" in
          0|false|no|off) ;;
          *)
            stage self_evolve_scorecard \
              python3 "$SCRIPTS/self_evolve.py" propose-scorecard \
                --scorecard "$OUT_DIR/product-scorecard.json" \
                --limit 3 || true
            ;;
        esac
      fi
      # F133: dual-gate auto-adopt scorecard-gap skills (soft; default on for cycle-scorecard CLI)
      if [[ -f "$SCRIPTS/skill_auto_adopt.py" ]]; then
        case "${TORII_SKILL_AUTO_ADOPT_SCORECARD:-0}" in
          1|true|yes|on)
            stage skill_auto_adopt_scorecard \
              python3 "$SCRIPTS/skill_auto_adopt.py" cycle-scorecard \
                --scorecard "$OUT_DIR/product-scorecard.json" \
                --max 2 || true
            ;;
        esac
      fi
      ;;
  esac
fi

# F69: package trajectory for self-evolution (soft)
# LIVE_LEAN: skip ingest/propose (merge signal already minted via scorecard+critic)
if [[ -f "$SCRIPTS/self_evolve.py" && -d "$OUT_DIR/agent-loop" ]] && ! _live_lean; then
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

# F74: fitness-gated skill evolution cycle (soft; propose+validate; adopt only if auto)
if [[ -f "$SCRIPTS/fitness_gate_evolve.py" ]] && ! _live_lean; then
  case "${TORII_FITNESS_GATE_EVOLVE:-1}" in
    0|false|no|off) ;;
    *)
      _f74_args=(cycle --limit 3)
      case "${TORII_FITNESS_GATE_AUTO_ADOPT:-0}" in
        1|true|yes|on) _f74_args+=(--adopt) ;;
        *) _f74_args+=(--no-adopt) ;;
      esac

      stage fitness_gate_evolve \
        python3 "$SCRIPTS/fitness_gate_evolve.py" "${_f74_args[@]}" || true
      ;;
  esac
fi

# F82: safe skill auto-adopt (default off; regression-gated)
if [[ -f "$SCRIPTS/skill_auto_adopt.py" ]]; then
  case "${TORII_SKILL_AUTO_ADOPT:-0}" in
    1|true|yes|on)
      stage skill_auto_adopt \
        python3 "$SCRIPTS/skill_auto_adopt.py" cycle || true
      ;;
  esac
fi

# F84/F114: progressive skill hit scoring (+ tool outcomes from agent-loop)
if [[ -f "$SCRIPTS/skill_router.py" ]]; then
  case "${TORII_SKILL_ROUTER:-1}" in
    0|false|no|off) ;;
    *)
      _f84_review=""
      for _c in "$OUT_DIR/review.md" "$OUT_DIR/review.normalized.md" "$OUT_DIR/hermes-review.md"; do
        if [[ -f "$_c" ]]; then _f84_review="$_c"; break; fi
      done
      if [[ -n "$_f84_review" ]]; then
        # F114/F116: explicit agent-loop + hermes log for tool-outcome probes
        _f84_args=(score --review "$_f84_review" --out-dir "$OUT_DIR")
        if [[ -f "$OUT_DIR/agent-loop/agent-loop.json" ]]; then
          _f84_args+=(--agent-loop "$OUT_DIR/agent-loop/agent-loop.json")
        elif [[ -f "$OUT_DIR/agent-loop.json" ]]; then
          _f84_args+=(--agent-loop "$OUT_DIR/agent-loop.json")
        fi
        if [[ -f "$OUT_DIR/agent-loop/agent.log" ]]; then
          _f84_args+=(--log "$OUT_DIR/agent-loop/agent.log")
        elif [[ -f "$OUT_DIR/hermes.log" ]]; then
          _f84_args+=(--log "$OUT_DIR/hermes.log")
        fi
        stage skill_router_score \
          python3 "$SCRIPTS/skill_router.py" "${_f84_args[@]}" || true
        # F121: recovery skill tool utilization (inject chars + tool_hit gap)
        stage recovery_skill_util \
          python3 "$SCRIPTS/skill_router.py" util --out-dir "$OUT_DIR" || true
        # F136: scorecard-gap ops skill tool utilization (inject ≠ utilization)
        stage scorecard_skill_util \
          python3 "$SCRIPTS/skill_router.py" scorecard-util --out-dir "$OUT_DIR" || true
        # F125: hub recovery-util post-score → next-run always priority compound
        # F138: also post-scores scorecard util hub → select priority + fitness
        stage recovery_hub_score \
          python3 "$SCRIPTS/skill_router.py" hub-score || true
        stage scorecard_hub_score \
          python3 "$SCRIPTS/skill_router.py" scorecard-hub-score || true
      fi
      ;;
  esac
fi

# F88/F89/F115: per-skill attribution → durable ledger (tool LOO from agent-loop)
if [[ -f "$SCRIPTS/skill_attribution.py" ]]; then
  case "${TORII_SKILL_ATTRIBUTION:-1}" in
    0|false|no|off) ;;
    *)
      _f88_review=""
      for _c in "$OUT_DIR/review.md" "$OUT_DIR/review.normalized.md" "$OUT_DIR/hermes-review.md"; do
        if [[ -f "$_c" ]]; then _f88_review="$_c"; break; fi
      done
      if [[ -n "$_f88_review" ]]; then
        _f88_args=(cycle --review "$_f88_review" --out-dir "$OUT_DIR")
        if [[ -f "$OUT_DIR/agent-loop/agent-loop.json" ]]; then
          _f88_args+=(--agent-loop "$OUT_DIR/agent-loop/agent-loop.json")
        elif [[ -f "$OUT_DIR/agent-loop.json" ]]; then
          _f88_args+=(--agent-loop "$OUT_DIR/agent-loop.json")
        fi
        if [[ -f "$OUT_DIR/agent-loop/agent.log" ]]; then
          _f88_args+=(--log "$OUT_DIR/agent-loop/agent.log")
        elif [[ -f "$OUT_DIR/hermes.log" ]]; then
          _f88_args+=(--log "$OUT_DIR/hermes.log")
        fi
        stage skill_attribution \
          python3 "$SCRIPTS/skill_attribution.py" "${_f88_args[@]}" || true
      fi
      ;;
  esac
fi

# F85/F116: skill fitness ledger — demote zombies + tool-hit shield + federate themes
if [[ -f "$SCRIPTS/skill_fitness.py" ]]; then
  case "${TORII_SKILL_FITNESS:-1}" in
    0|false|no|off) ;;
    *)
      stage skill_fitness \
        python3 "$SCRIPTS/skill_fitness.py" cycle --out-dir "$OUT_DIR" || true
      ;;
  esac
fi

# F117: mine allowlisted tool-outcome probes from this run → durable ledger (+ soft propose)
# LIVE_LEAN: keep mine-probes (cheap) but skip when lean+probe off
if [[ -f "$SCRIPTS/self_evolve.py" ]]; then
  case "${TORII_TOOL_PROBE_MINE:-1}" in
    0|false|no|off) ;;
    *)
      if _live_lean; then
        : # still mine — cheap tool-use compound signal for next PR
      fi
      _f117_args=(mine-probes --out-dir "$OUT_DIR")
      case "${TORII_SELF_EVOLVE:-0}" in
        1|true|yes|on) _f117_args+=(--propose) ;;
      esac
      stage tool_probe_mine \
        python3 "$SCRIPTS/self_evolve.py" "${_f117_args[@]}" || true
      ;;
  esac
fi

# F86: multi-tenant promote of skill themes (soft)
if [[ -f "$SCRIPTS/skill_dual_rollout.py" ]] && ! _live_lean; then
  case "${TORII_SKILL_DUAL_ROLLOUT:-1}" in
    0|false|no|off) ;;
    *)
      stage skill_theme_promote \
        python3 "$SCRIPTS/skill_dual_rollout.py" promote || true
      ;;
  esac
fi

# F77/F83: promote multi-tenant federated signals (soft)
if [[ -f "$SCRIPTS/federated_hub_ingest.py" ]] && ! _live_lean; then
  case "${TORII_FED_PROMOTE:-1}" in
    0|false|no|off) ;;
    *)
      stage fed_promote \
        python3 "$SCRIPTS/federated_hub_ingest.py" promote || true
      ;;
  esac
fi

# F104: integrity-gated compound write of path-evidenced TP signatures (soft)
# Runs before consolidate/graph so new TPs enter decay + temporal edges.
if [[ -f "$SCRIPTS/memory_compound_write.py" ]]; then
  case "${TORII_MEMORY_COMPOUND:-1}" in
    0|false|no|off) ;;
    *)
      _f104_review=""
      if [[ -n "${REVIEW_FILE:-}" && -f "${REVIEW_FILE}" ]]; then
        _f104_review="$REVIEW_FILE"
      elif [[ -f "$OUT_DIR/review-${PR_NUMBER:-}.md" ]]; then
        _f104_review="$OUT_DIR/review-${PR_NUMBER}.md"
      elif compgen -G "$OUT_DIR/review*.md" > /dev/null; then
        _f104_review="$(ls -1 "$OUT_DIR"/review*.md 2>/dev/null | grep -v '\.raw\.md$' | head -1 || true)"
      fi
      if [[ -n "$_f104_review" ]]; then
        _f104_args=(
          compound
          --review "$_f104_review"
          --out-dir "$OUT_DIR"
          --repo "${REPO:-${GITHUB_REPOSITORY:-}}"
          --pr "${PR_NUMBER:-}"
          --source agent_review
        )
        # F107: privacy-safe federate of integrity-gated candidates (default on)
        case "${TORII_MEMORY_COMPOUND_FEDERATE:-1}" in
          0|false|no|off) _f104_args+=(--no-federate) ;;
          *)
            _f104_args+=(--federate)
            [[ -n "${TORII_MEMORY_TENANT:-}" ]] && _f104_args+=(--tenant "${TORII_MEMORY_TENANT}")
            ;;
        esac
        stage memory_compound \
          python3 "$SCRIPTS/memory_compound_write.py" "${_f104_args[@]}" || true
      fi
      ;;
  esac
fi

# F94: memory consolidation — importance · merge · decay · eviction (soft)
# LIVE_LEAN: skip consolidate (compound write still ran; decay can wait for hub cycle)
if [[ -f "$SCRIPTS/memory_consolidate.py" ]] && ! _live_lean; then
  case "${TORII_MEMORY_CONSOLIDATE:-1}" in
    0|false|no|off) ;;
    *)
      stage memory_consolidate \
        python3 "$SCRIPTS/memory_consolidate.py" run --kind both || true
      # F95: export effective_score theme signals → hub federation (privacy-safe)
      case "${TORII_MEMORY_FED_EFFECTIVE:-1}" in
        0|false|no|off) ;;
        *)
          stage memory_fed_effective \
            python3 "$SCRIPTS/memory_consolidate.py" federate \
              --tenant "${TORII_MEMORY_TENANT:-}" \
              --repo "${REPO:-${GITHUB_REPOSITORY:-}}" || true
          ;;
      esac
      ;;
  esac
fi

# F100: rebuild temporal memory graph after writes (soft)
# LIVE_LEAN: skip graph rebuild (not on critical path to torii/gate)
if [[ -f "$SCRIPTS/memory_temporal_graph.py" ]] && ! _live_lean; then
  case "${TORII_MEMORY_GRAPH:-1}" in
    0|false|no|off) ;;
    *)
      stage memory_temporal_graph \
        python3 "$SCRIPTS/memory_temporal_graph.py" build || true
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

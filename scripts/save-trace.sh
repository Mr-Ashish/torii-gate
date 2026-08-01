#!/usr/bin/env bash
# Package a durable per-run trace (no secrets).
#
# Env:
#   TORII_ROOT, OUT_DIR, HERMES_HOME
#   REPO, PR_NUMBER
#   GITHUB_RUN_ID, GITHUB_RUN_ATTEMPT, GITHUB_SHA, GITHUB_REF (optional)
#   TRACE_ROOT (default: $TORII_ROOT/.torii-out/traces)
#   TORII_MODEL, WORKSPACE_ROOT
#
# Writes:
#   $TRACE_DIR/
#     meta.json          # run identity + status
#     prompt.md          # full agent prompt
#     context.md         # assembled PR context
#     pr.json            # gh pr view JSON
#     pr.diff            # (truncated) diff
#     files.txt          # file list summary
#     review.raw.md      # hermes stdout before normalize
#     review.md          # posted review body
#     hermes.stderr      # hermes stderr if any
#     memory-before.md   # optional snapshot if present
#     memory-after.md    # MEMORY.md after distill
#     timings.json       # stage durations if available
#     trace.json         # index + file inventory (SHA256)
set -euo pipefail

log() { echo "$*" >&2; }

TORII_ROOT="${TORII_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_DIR="${OUT_DIR:-$TORII_ROOT/.torii-out}"
HERMES_HOME="${HERMES_HOME:-$TORII_ROOT/.torii-hermes-home}"
TRACE_ROOT="${TRACE_ROOT:-$OUT_DIR/traces}"

if [[ -f "$OUT_DIR/meta.env" ]]; then
  # shellcheck disable=SC1091
  source "$OUT_DIR/meta.env"
fi

PR_NUMBER="${PR_NUMBER:-unknown}"
REPO="${REPO:-${GITHUB_REPOSITORY:-unknown}}"
RUN_ID="${GITHUB_RUN_ID:-local}"
RUN_ATTEMPT="${GITHUB_RUN_ATTEMPT:-1}"
MODEL="${TORII_MODEL:-${OPENROUTER_MODEL:-unknown}}"
STATUS="${TORII_STATUS:-unknown}"
STARTED_AT="${TORII_STARTED_AT:-}"
ENDED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

TRACE_ID="pr${PR_NUMBER}-run${RUN_ID}-a${RUN_ATTEMPT}"
TRACE_DIR="${TRACE_ROOT}/${TRACE_ID}"
mkdir -p "$TRACE_DIR"

copy_if() {
  local src="$1" dest="$2"
  if [[ -f "$src" ]]; then
    cp -f "$src" "$dest"
  fi
}

copy_if "$OUT_DIR/prompt.md" "$TRACE_DIR/prompt.md"
copy_if "$OUT_DIR/context.md" "$TRACE_DIR/context.md"
copy_if "$OUT_DIR/pr.json" "$TRACE_DIR/pr.json"
copy_if "$OUT_DIR/pr.diff" "$TRACE_DIR/pr.diff"
copy_if "$OUT_DIR/files.txt" "$TRACE_DIR/files.txt"
copy_if "$OUT_DIR/meta.env" "$TRACE_DIR/meta.env"
copy_if "$OUT_DIR/timings.json" "$TRACE_DIR/timings.json"
copy_if "$OUT_DIR/review-${PR_NUMBER}.raw.md" "$TRACE_DIR/review.raw.md"
copy_if "$OUT_DIR/review-${PR_NUMBER}.md" "$TRACE_DIR/review.md"
copy_if "$OUT_DIR/hermes-${PR_NUMBER}.stderr" "$TRACE_DIR/hermes.stderr"
copy_if "$OUT_DIR/hermes-usage.json" "$TRACE_DIR/hermes-usage.json"
copy_if "$OUT_DIR/hermes-run.log" "$TRACE_DIR/hermes-run.log"
copy_if "$OUT_DIR/hermes-pin.txt" "$TRACE_DIR/hermes-pin.txt"
copy_if "$OUT_DIR/tool-turns-gate.env" "$TRACE_DIR/tool-turns-gate.env"
copy_if "$OUT_DIR/tool-turns-reprompt.env" "$TRACE_DIR/tool-turns-reprompt.env"
copy_if "$OUT_DIR/severity-calibration.env" "$TRACE_DIR/severity-calibration.env"
copy_if "$OUT_DIR/linked-issue-context.env" "$TRACE_DIR/linked-issue-context.env"
copy_if "$OUT_DIR/linked-issues.md" "$TRACE_DIR/linked-issues.md"
copy_if "$OUT_DIR/prompt-reprompt.md" "$TRACE_DIR/prompt-reprompt.md"
copy_if "$OUT_DIR/prompt-memory-reprompt.md" "$TRACE_DIR/prompt-memory-reprompt.md"
copy_if "$OUT_DIR/prompt-recovery-reprompt.md" "$TRACE_DIR/prompt-recovery-reprompt.md"
copy_if "$OUT_DIR/hermes-max-turns.env" "$TRACE_DIR/hermes-max-turns.env"
# F123: paper-ready recovery skill loop artifacts (F119–F122)
copy_if "$OUT_DIR/skill-router.json" "$TRACE_DIR/skill-router.json"
copy_if "$OUT_DIR/skill-hits.json" "$TRACE_DIR/skill-hits.json"
copy_if "$OUT_DIR/skill-attribution.json" "$TRACE_DIR/skill-attribution.json"
copy_if "$OUT_DIR/recovery-skill-util.json" "$TRACE_DIR/recovery-skill-util.json"
# F136: scorecard-gap skill utilization (tool_hit vs inject)
copy_if "$OUT_DIR/scorecard-skill-util.json" "$TRACE_DIR/scorecard-skill-util.json"
if [[ -f "$TORII_ROOT/memory/federation/scorecard-util-signals.json" ]]; then
  copy_if "$TORII_ROOT/memory/federation/scorecard-util-signals.json" "$TRACE_DIR/scorecard-util-signals.fed.json"
fi
copy_if "$OUT_DIR/scorecard-util-signals.json" "$TRACE_DIR/scorecard-util-signals.json"
copy_if "$OUT_DIR/recovery-skill-reprompt.env" "$TRACE_DIR/recovery-skill-reprompt.env"
# F124: privacy-safe federated recovery util themes (also under memory/federation)
copy_if "$OUT_DIR/recovery-util-signals.json" "$TRACE_DIR/recovery-util-signals.json"
if [[ -f "$TORII_ROOT/memory/federation/recovery-util-signals.json" ]]; then
  copy_if "$TORII_ROOT/memory/federation/recovery-util-signals.json" "$TRACE_DIR/recovery-util-signals.fed.json"
fi
# F125: hub recovery-util post-score → always priority compound
copy_if "$OUT_DIR/recovery-hub-score.json" "$TRACE_DIR/recovery-hub-score.json"
# F126: hub gap re-prompt decide + fitness compound artifact
copy_if "$OUT_DIR/recovery-reprompt-decide.json" "$TRACE_DIR/recovery-reprompt-decide.json"
# F137: scorecard util soft re-prompt decide + prompt
copy_if "$OUT_DIR/scorecard-reprompt-decide.json" "$TRACE_DIR/scorecard-reprompt-decide.json"
copy_if "$OUT_DIR/prompt-recovery-reprompt.md" "$TRACE_DIR/prompt-recovery-reprompt.md"
# F128: paper critic demote-rate eval
copy_if "$OUT_DIR/critic-demote-eval.json" "$TRACE_DIR/critic-demote-eval.json"
# F129: product brand/ops scorecard (doctor + demote metrics)
copy_if "$OUT_DIR/product-scorecard.json" "$TRACE_DIR/product-scorecard.json"
if [[ -f "$TORII_ROOT/.torii/product-scorecard.json" ]]; then
  copy_if "$TORII_ROOT/.torii/product-scorecard.json" "$TRACE_DIR/product-scorecard.torii.json"
fi
# F130: memory tool utilization paper pack (Mem0/Letta tool-call discipline)
copy_if "$OUT_DIR/memory-util-eval.json" "$TRACE_DIR/memory-util-eval.json"
# F134: federated scorecard skill themes (privacy-safe)
if [[ -f "$TORII_ROOT/memory/federation/scorecard-skill-signals.json" ]]; then
  copy_if "$TORII_ROOT/memory/federation/scorecard-skill-signals.json" "$TRACE_DIR/scorecard-skill-signals.json"
fi
copy_if "$OUT_DIR/scorecard-skill-signals.json" "$TRACE_DIR/scorecard-skill-signals.out.json"
copy_if "$OUT_DIR/memory-tool-reprompt.env" "$TRACE_DIR/memory-tool-reprompt.env"
copy_if "$OUT_DIR/memory-tool-audit.json" "$TRACE_DIR/memory-tool-audit.json"
copy_if "$OUT_DIR/reprompt-budget.json" "$TRACE_DIR/reprompt-budget.json"
# second-agent critic panel (includes F121 recovery util checker)
copy_if "$OUT_DIR/second-agent-critic.json" "$TRACE_DIR/second-agent-critic.json"
copy_if "$OUT_DIR/second_agent_critic.json" "$TRACE_DIR/second_agent_critic.json"
if [[ -d "$OUT_DIR/agent-loop-attempt1" ]]; then
  rm -rf "$TRACE_DIR/agent-loop-attempt1"
  cp -a "$OUT_DIR/agent-loop-attempt1" "$TRACE_DIR/agent-loop-attempt1" 2>/dev/null || true
fi
copy_if "$OUT_DIR/model-tier.env" "$TRACE_DIR/model-tier.env"
copy_if "$OUT_DIR/preflight-cost.env" "$TRACE_DIR/preflight-cost.env"
copy_if "$OUT_DIR/soul-context.env" "$TRACE_DIR/soul-context.env"
copy_if "$OUT_DIR/soul-context-preflight.env" "$TRACE_DIR/soul-context-preflight.env"

# Full agentic loop package (prompts / steps / tool calls / usage)
if [[ -d "$OUT_DIR/agent-loop" ]]; then
  rm -rf "$TRACE_DIR/agent-loop"
  cp -a "$OUT_DIR/agent-loop" "$TRACE_DIR/agent-loop"
  log "Included agent-loop package → $TRACE_DIR/agent-loop"
fi

# Memory snapshots (never include HERMES_HOME/.env)
if [[ -f "$HERMES_HOME/memories/MEMORY.md" ]]; then
  cp -f "$HERMES_HOME/memories/MEMORY.md" "$TRACE_DIR/memory-after.md"
fi
if [[ -f "$OUT_DIR/memory-before.md" ]]; then
  cp -f "$OUT_DIR/memory-before.md" "$TRACE_DIR/memory-before.md"
fi

# Redact any accidental API keys in copied text files
python3 - <<'PY' "$TRACE_DIR"
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
patterns = [
    (re.compile(r"sk-or-v1-[A-Za-z0-9_-]{10,}"), "[OPENROUTER_KEY_REDACTED]"),
    (re.compile(r"(OPENROUTER_API_KEY=)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)([^\"'\s]+)", re.I), r"\1[REDACTED]"),
]
for path in root.rglob("*"):
    if not path.is_file():
        continue
    if path.suffix.lower() in {".png", ".jpg", ".zip", ".gz", ".tar"}:
        continue
    try:
        text = path.read_text(errors="replace")
    except OSError:
        continue
    new = text
    for rx, repl in patterns:
        new = rx.sub(repl, new)
    if new != text:
        path.write_text(new)
PY

# Build inventory + meta
export TRACE_DIR TRACE_ID REPO PR_NUMBER RUN_ID RUN_ATTEMPT MODEL STATUS STARTED_AT ENDED_AT
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-}"
export GITHUB_SHA="${GITHUB_SHA:-}"
export GITHUB_REF="${GITHUB_REF:-}"
export GITHUB_EVENT_NAME="${GITHUB_EVENT_NAME:-}"
export HERMES_RC="${HERMES_RC:-}"
export TRIGGER_COMMENT="${TRIGGER_COMMENT:-}"

python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

trace_dir = Path(os.environ["TRACE_DIR"])
files = {}
for p in sorted(trace_dir.rglob("*")):
    if not p.is_file():
        continue
    rel = str(p.relative_to(trace_dir))
    if rel in {"trace.json", "meta.json"}:
        continue
    data = p.read_bytes()
    files[rel] = {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }

meta = {
    "trace_id": os.environ["TRACE_ID"],
    "schema_version": 1,
    "repo": os.environ.get("REPO"),
    "pr_number": os.environ.get("PR_NUMBER"),
    "run_id": os.environ.get("RUN_ID"),
    "run_attempt": os.environ.get("RUN_ATTEMPT"),
    "model": os.environ.get("MODEL"),
    "status": os.environ.get("STATUS"),
    "started_at": os.environ.get("STARTED_AT") or None,
    "ended_at": os.environ.get("ENDED_AT"),
    "workspace_root": os.environ.get("WORKSPACE_ROOT") or None,
    "github_sha": os.environ.get("GITHUB_SHA") or None,
    "github_ref": os.environ.get("GITHUB_REF") or None,
    "github_event_name": os.environ.get("GITHUB_EVENT_NAME") or None,
    "hermes_rc": os.environ.get("HERMES_RC") or None,
    "trigger_comment": (os.environ.get("TRIGGER_COMMENT") or "")[:500],
    "files": files,
}

(trace_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
(trace_dir / "trace.json").write_text(
    json.dumps(
        {
            "trace_id": meta["trace_id"],
            "schema_version": 1,
            "meta": "meta.json",
            "artifacts": list(files.keys()),
            "review": "review.md" if "review.md" in files else None,
            "prompt": "prompt.md" if "prompt.md" in files else None,
            "raw_review": "review.raw.md" if "review.raw.md" in files else None,
        },
        indent=2,
    )
    + "\n"
)
print(trace_dir)
PY

# F73: also write paper-safe vault entry under docs/benchmarks/traces/ (soft)
if [[ -f "$(dirname "${BASH_SOURCE[0]}")/trajectory_fitness.py" ]]; then
  case "${TORII_TRACE_VAULT:-1}" in
    0|false|no|off) ;;
    *)
      _review_for_vault=""
      if [[ -f "$TRACE_DIR/review.md" ]]; then
        _review_for_vault="$TRACE_DIR/review.md"
      elif [[ -f "$OUT_DIR/review-${PR_NUMBER}.md" ]]; then
        _review_for_vault="$OUT_DIR/review-${PR_NUMBER}.md"
      fi
      if [[ -n "$_review_for_vault" ]]; then
        python3 "$(dirname "${BASH_SOURCE[0]}")/trajectory_fitness.py" archive \
          --out-dir "$OUT_DIR" \
          --review "$_review_for_vault" \
          --label "${TORII_TRACE_LABEL:-trace}" \
          --repo "${REPO:-}" \
          --pr "${PR_NUMBER:-}" \
          --model "${MODEL:-}" \
          --force \
          >"$OUT_DIR/vault-archive.json" 2>"$OUT_DIR/vault-archive.stderr" || true
        if [[ -f "$OUT_DIR/vault-archive.json" ]]; then
          copy_if "$OUT_DIR/vault-archive.json" "$TRACE_DIR/vault-archive.json"
          copy_if "$OUT_DIR/fitness.json" "$TRACE_DIR/fitness.json"
        fi
      fi
      ;;
  esac
fi

# Pointer for orchestrator / GITHUB_OUTPUT
echo "$TRACE_DIR" >"$OUT_DIR/latest-trace-dir.txt"
echo "TRACE_DIR=$TRACE_DIR"
echo "TRACE_ID=$TRACE_ID"
log "Trace stored at $TRACE_DIR ($(du -sh "$TRACE_DIR" | awk '{print $1}'))"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "trace_dir=$TRACE_DIR"
    echo "trace_id=$TRACE_ID"
  } >>"$GITHUB_OUTPUT"
fi

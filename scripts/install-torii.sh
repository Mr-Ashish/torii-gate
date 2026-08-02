#!/usr/bin/env bash
# F20/F10: install Torii into a target repository.
#
# Modes:
#   pack (default)  Copy agent/, runtime scripts/, thin caller + reusable workflow
#                   so the target is self-contained (scripts live on its default branch).
#   --caller        F10 hub-managed: only copy pack/torii-pr-review-caller.yml
#                   (runtime checked out from hub each run — free upgrades).
#
# Usage:
#   ./scripts/install-torii.sh /path/to/target-repo
#   ./scripts/install-torii.sh --caller /path/to/target-repo
#   ./scripts/install-torii.sh --dest /path/to/target-repo --dry-run
#   ./scripts/install-torii.sh --dest . --force   # re-install over existing
#
# Options:
#   --dest DIR          Target repo root (required unless positional DIR)
#   --caller            Hub-managed thin workflow only (no agent/scripts copy)
#   --minimal           5-minute pack: runtime gate scripts only (no bench/eval/modal)
#   --tenant ID         Optional enterprise-light tenant id (stamp + .torii/tenant.env)
#   --dry-run           Print actions; do not write
#   --force             Overwrite existing files without prompting
#   --with-hub-ingest   Also copy ingest-torii-run.yml (hub repo only; pack mode)
#   --with-runner-build Also copy build-torii-runner.yml + docker/torii-runner/
#   --source DIR        Torii source root (default: parent of scripts/)
#   -h | --help
#
# Exit: 0 ok (skips existing files unless --force), 1 usage/error
set -euo pipefail

SRC=""
DEST=""
DRY_RUN=0
FORCE=0
WITH_INGEST=0
WITH_RUNNER=0
CALLER_MODE=0
MINIMAL=0
TENANT=""

log() { printf '%s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  # Header comment only (stop before set -euo pipefail)
  sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)
      DEST="${2:-}"
      shift 2
      ;;
    --source)
      SRC="${2:-}"
      shift 2
      ;;
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    --caller) CALLER_MODE=1; shift ;;
    --minimal) MINIMAL=1; shift ;;
    --tenant)
      TENANT="${2:-}"
      shift 2
      ;;
    --with-hub-ingest) WITH_INGEST=1; shift ;;
    --with-runner-build) WITH_RUNNER=1; shift ;;
    -h | --help) usage 0 ;;
    --)
      shift
      break
      ;;
    -*)
      die "unknown option: $1 (try --help)"
      ;;
    *)
      if [[ -z "$DEST" ]]; then
        DEST="$1"
        shift
      else
        die "unexpected argument: $1"
      fi
      ;;
  esac
done

SRC="${SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
[[ -n "$DEST" ]] || die "target directory required (positional or --dest)"
DEST="$(cd "$DEST" 2>/dev/null && pwd)" || die "target not found: $DEST"
SRC="$(cd "$SRC" && pwd)"

[[ -d "$SRC/agent" ]] || die "source missing agent/: $SRC"
[[ -d "$SRC/scripts" ]] || die "source missing scripts/: $SRC"
[[ -f "$SRC/.github/workflows/torii-pr-review.yml" ]] || die "source missing torii-pr-review.yml"
[[ -f "$SRC/.github/workflows/torii-review-reusable.yml" ]] || die "source missing torii-review-reusable.yml (F10)"
[[ -f "$SRC/pack/torii-pr-review-caller.yml" ]] || die "source missing pack/torii-pr-review-caller.yml (F10)"

# Refuse installing pack into itself unless forced (avoids half-copies)
if [[ "$SRC" == "$DEST" && "$FORCE" != "1" ]]; then
  die "refusing to install into the Torii source tree itself (use --force if intentional)"
fi

# Runtime script allowlist — exclude image build / bench from target packs by default
# (still available when --with-runner-build copies docker tooling separately).
RUNTIME_SCRIPTS=(
  apply-verdict-labels.py
  assemble-context.sh
  association-allowed.sh
  build-hub-payload.py
  capture-hermes-loop.py
  cooldown-check.sh
  dismiss-prior-pr-reviews.sh
  distill-memory.sh
  feature_toggles.py
  hermes-pin.sh
  incremental_review.py
  linked_issue_context.py
  lens_recipes.py
  hub-ingest-run.py
  install-torii.sh
  memory-health.sh
  normalize-review.py
  ops_footer.py
  pack-run-for-ui.py
  parse-verdict.py
  path-skip-check.py
  post-inline-comments.py
  reply_on_thread.py
  post-review-comment.sh
  preload-hub-memory.sh
  publish-run-local.sh
  publish-run-to-hub.sh
  report-verdict.sh
  review-local.sh
  run-hermes-review.sh
  run-torii-gate.sh
  run-torii-review.sh
  run-with-timeout.py
  smoke-torii-gate.sh
  torii_gate_status.py
  max_turns.py
  mermaid_architecture.py
  model_tier.py
  preflight_cost.py
  pr_description_filler.py
  testplan_generation.py
  fp_resolve_memory.py
  tool_turns_gate.py
  severity_calibration.py
  soul_context_scan.py
  save-trace.sh
  review-to-openui.py
  sparse-pr-paths.sh
  trigger-review.sh
  usage-summary.py
  webhook_auth.py
  write-failure-review.sh
  bench_security_gate.py
  taint_prefilter.py
  chain_revalidate.py
  trajectory_fitness.py
  fitness_gate_evolve.py
  scoped_memory_recall.py
  federated_hub_ingest.py
  second_agent_critic.py
  self_evolve.py
  bench_corpus.py
  workflow_as_code.py
  modal_secrets_bootstrap.py
  llm_critic.py
  skill_auto_adopt.py
  eval_trace_report.py
  skill_router.py
  skill_fitness.py
  skill_dual_rollout.py
  skill_attribution.py
  skill_loop_status.py
  memory_event_policy.py
  memory_compound_write.py
  memory_tool_audit.py
  reprompt_budget.py
  memory_consolidate.py
  memory_loop_status.py
  memory_tiers.py
  archival_memory_search.py
  memory_temporal_graph.py
  torii_memory.py
  torii.py
  install_ux_check.py
  quieter_over_time.py
  gate_certificate.py
  tool_use_quality.py
)

# Scripts omitted from --minimal (bench / eval / modal / heavy evolution).
# Full pack remains default for day-2 compound loops.
MINIMAL_EXCLUDE=(
  bench_security_gate.py
  bench_corpus.py
  eval_trace_report.py
  modal_secrets_bootstrap.py
  self_evolve.py
  skill_auto_adopt.py
  skill_dual_rollout.py
  skill_attribution.py
  fitness_gate_evolve.py
  pack-run-for-ui.py
  review-to-openui.py
  hub-ingest-run.py
  publish-run-to-hub.py
  publish-run-local.sh
  build-hub-payload.py
)

runtime_scripts_list() {
  if [[ "$MINIMAL" != "1" ]]; then
    printf '%s\n' "${RUNTIME_SCRIPTS[@]}"
    return 0
  fi
  local s ex skip
  for s in "${RUNTIME_SCRIPTS[@]}"; do
    skip=0
    for ex in "${MINIMAL_EXCLUDE[@]}"; do
      if [[ "$s" == "$ex" ]]; then skip=1; break; fi
    done
    [[ "$skip" == "1" ]] || printf '%s\n' "$s"
  done
}

copy_file() {
  local from="$1" to="$2"
  if [[ -e "$to" && "$FORCE" != "1" ]]; then
    log "exists (skip, use --force): $to"
    return 0
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY  $from → $to"
    return 0
  fi
  mkdir -p "$(dirname "$to")"
  cp -f "$from" "$to"
  # Preserve executable bit for scripts
  if [[ -x "$from" ]]; then
    chmod +x "$to"
  fi
  log "OK   $to"
}

copy_tree_files() {
  # copy selected files under a subdir (not full recursive junk)
  local rel="$1"
  shift
  local f
  for f in "$@"; do
    local from="$SRC/$rel/$f"
    local to="$DEST/$rel/$f"
    [[ -f "$from" ]] || {
      log "WARN missing in source: $rel/$f"
      continue
    }
    copy_file "$from" "$to"
  done
}

# Sanitize tenant id for stamp / env (enterprise light — no paths/snippets).
sanitize_tenant() {
  local raw="${1:-}"
  # allow alnum . _ - only; collapse others to -
  raw="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//; s/-{2,}/-/g')"
  # cap length for filesystem safety
  printf '%s' "${raw:0:64}"
}

write_tenant_env() {
  # Optional enterprise-light: stamp TORII_MEMORY_TENANT for multi-org fleets.
  # Default remains repo-local .torii/ with no tenant id required.
  local tid
  tid="$(sanitize_tenant "${TENANT}")"
  [[ -n "$tid" ]] || return 0
  local envf="$DEST/.torii/tenant.env"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY  would write $envf TORII_MEMORY_TENANT=$tid"
    return 0
  fi
  mkdir -p "$DEST/.torii"
  {
    echo "# Torii enterprise light — optional multi-org tenant id"
    echo "# Repo-local memory stays under .torii/; hub federation (opt-in) uses a tenant hash only."
    echo "# Docs: docs/enterprise/ORG-ISOLATION.md · docs/enterprise/PRIVACY.md"
    echo "TORII_MEMORY_TENANT=$tid"
  } >"$envf"
  log "OK   $envf (TORII_MEMORY_TENANT=$tid)"
}

write_stamp() {
  local mode="$1"
  local STAMP="$DEST/.torii-install-stamp"
  local VERSION
  local tid
  VERSION="$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  tid="$(sanitize_tenant "${TENANT}")"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY  would write $STAMP (mode=$mode source_sha=$VERSION tenant_id=${tid:-none})"
    return 0
  fi
  {
    echo "installed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "source_sha=$VERSION"
    echo "source_path=$SRC"
    echo "mode=$mode"
    echo "memory_default=repo-local"
    echo "tenant_id=${tid:-}"
    echo "enterprise_docs=docs/enterprise/"
    if [[ "$mode" == "caller" ]]; then
      echo "pack=torii-pr-review-caller.yml (hub-managed F10)"
    else
      echo "pack=agent,scripts(runtime),torii-pr-review.yml,torii-review-reusable.yml"
    fi
  } >"$STAMP"
  log "OK   $STAMP"
}

log "Torii install · source=$SRC"
log "               dest=$DEST dry_run=$DRY_RUN force=$FORCE caller=$CALLER_MODE"

# ---------------------------------------------------------------------------
# F10: hub-managed caller only
# ---------------------------------------------------------------------------
if [[ "$CALLER_MODE" == "1" ]]; then
  if [[ "$WITH_INGEST" == "1" || "$WITH_RUNNER" == "1" ]]; then
    log "WARN --with-hub-ingest / --with-runner-build ignored in --caller mode"
  fi
  copy_file \
    "$SRC/pack/torii-pr-review-caller.yml" \
    "$DEST/.github/workflows/torii-pr-review.yml"
  write_stamp "caller"
  write_tenant_env
  log ""
  log "Next steps (hub-managed / F10 caller):"
  log "  1. Commit .github/workflows/torii-pr-review.yml and push to the default branch."
  log "  2. Add secret OPENROUTER_API_KEY."
  log "  3. Memory defaults to repo-local .torii/ (F28). Optional hub: TORII_MEMORY_MODE=both|hub and/or TORII_HUB_PUBLISH=1 + TORII_HUB_TOKEN."
  log "  4. Optional vars: TORII_MODEL, TORII_HERMES_COMMIT, TORII_COOLDOWN_SECONDS, TORII_RUNNER_IMAGE, TORII_MEMORY_PATH."
  log "  5. Branch protection: require status check context torii/gate (security-aware merge signal)."
  log "  6. On a PR, comment: @torii review this pr"
  log "  7. Capability matrix: python3 scripts/workflow_as_code.py install-guide"
  log "  8. Offline smoke: ./scripts/smoke-torii-gate.sh && python3 scripts/workflow_as_code.py validate"
  log "  Runtime agent/scripts are fetched from Mr-Ashish/torii-gate@main each run."
  log "  Tip: pin the uses: ref to a commit SHA (not @main) to avoid blast radius from hub main."
  log "  Tip: seed .torii/MEMORY.md on the target default branch (or re-install pack mode once)."
  log "  Tip: enterprise light — optional --tenant acme-org → TORII_MEMORY_TENANT (docs/enterprise/)."
  log "  Tip: quieter-over-time after torii/gate: python3 scripts/torii.py quieter -- status"
  log "Done."
  exit 0
fi

# ---------------------------------------------------------------------------
# Default pack mode (self-contained target)
# ---------------------------------------------------------------------------
# agent/*
AGENT_FILES=()
while IFS= read -r -d '' f; do
  AGENT_FILES+=("$(basename "$f")")
done < <(find "$SRC/agent" -maxdepth 1 -type f -print0 | sort -z)

copy_tree_files "agent" "${AGENT_FILES[@]}"

# F83: evolved skills (active/) + tool catalog — required for F69/F82 inject on targets
if [[ -d "$SRC/agent/skills" ]]; then
  if [[ "$DRY_RUN" == "1" ]]; then
    log "dry-run: would copy agent/skills/"
  else
    mkdir -p "$DEST/agent/skills"
    # full pack: active + proposals; --minimal: active only (smaller surface)
    if command -v rsync >/dev/null 2>&1; then
      if [[ "$MINIMAL" == "1" ]]; then
        rsync -a --delete --exclude '.DS_Store' --exclude 'proposals/' \
          "$SRC/agent/skills/" "$DEST/agent/skills/"
      else
        rsync -a --delete --exclude '.DS_Store' "$SRC/agent/skills/" "$DEST/agent/skills/"
      fi
    else
      rm -rf "$DEST/agent/skills"
      cp -R "$SRC/agent/skills" "$DEST/agent/skills"
      if [[ "$MINIMAL" == "1" && -d "$DEST/agent/skills/proposals" ]]; then
        rm -rf "$DEST/agent/skills/proposals"
      fi
    fi
    log "copied agent/skills/ (active=$(find "$DEST/agent/skills/active" -name '*.md' 2>/dev/null | wc -l | tr -d ' ') minimal=$MINIMAL)"
    # F120: pack must ship recovery always skills (F113/F118 dual-gate adopted)
    for _rs in \
      skill-prefer-memory-cli-early.md \
      skill-prefer-product-cli.md \
      skill-prefer-critic-early.md
    do
      if [[ ! -f "$DEST/agent/skills/active/$_rs" ]]; then
        die "pack missing active recovery skill: agent/skills/active/$_rs (F120)"
      fi
    done
    log "verified recovery skills (memory + product-cli + critic) in pack active/"
  fi
fi

# F68+: adopted tool catalog JSON
if [[ -d "$SRC/agent/tools" ]]; then
  if [[ "$DRY_RUN" == "1" ]]; then
    log "dry-run: would copy agent/tools/"
  else
    mkdir -p "$DEST/agent/tools"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --exclude '__pycache__' --exclude '.DS_Store' "$SRC/agent/tools/" "$DEST/agent/tools/"
    else
      rm -rf "$DEST/agent/tools"
      cp -R "$SRC/agent/tools" "$DEST/agent/tools"
    fi
    log "copied agent/tools/"
  fi
fi

# F56: named lens recipe packs (agent/packs/*.json)
if [[ -d "$SRC/agent/packs" ]]; then
  if [[ "$DRY_RUN" == "1" ]]; then
    log "dry-run: would copy agent/packs/"
  else
    mkdir -p "$DEST/agent/packs"
    for f in "$SRC/agent/packs"/*.json; do
      [[ -f "$f" ]] || continue
      base="$(basename "$f")"
      if [[ -e "$DEST/agent/packs/$base" && "$FORCE" != "1" ]]; then
        log "exists (skip, use --force): agent/packs/$base"
      else
        cp -f "$f" "$DEST/agent/packs/$base"
        log "copied agent/packs/$base"
      fi
    done
  fi
fi

# runtime scripts (full pack or --minimal gate surface)
# Portable array fill (macOS bash 3.2 has no mapfile)
_RUNTIME_COPY=()
while IFS= read -r _rscript; do
  [[ -n "$_rscript" ]] && _RUNTIME_COPY+=("$_rscript")
done < <(runtime_scripts_list)
if [[ "$MINIMAL" == "1" ]]; then
  log "mode=minimal (5-minute pack: excluded bench/eval/modal/heavy evolution scripts)"
fi
copy_tree_files "scripts" "${_RUNTIME_COPY[@]}"

# F10: thin caller + reusable implementation (target keeps a copy of reusable for offline pin)
copy_file \
  "$SRC/.github/workflows/torii-pr-review.yml" \
  "$DEST/.github/workflows/torii-pr-review.yml"
copy_file \
  "$SRC/.github/workflows/torii-review-reusable.yml" \
  "$DEST/.github/workflows/torii-review-reusable.yml"

if [[ "$WITH_INGEST" == "1" ]]; then
  copy_file \
    "$SRC/.github/workflows/ingest-torii-run.yml" \
    "$DEST/.github/workflows/ingest-torii-run.yml"
fi

if [[ "$WITH_RUNNER" == "1" ]]; then
  copy_file \
    "$SRC/.github/workflows/build-torii-runner.yml" \
    "$DEST/.github/workflows/build-torii-runner.yml"
  if [[ -f "$SRC/docker/torii-runner/Dockerfile" ]]; then
    copy_file \
      "$SRC/docker/torii-runner/Dockerfile" \
      "$DEST/docker/torii-runner/Dockerfile"
  fi
  if [[ -f "$SRC/docker/torii-runner/README.md" ]]; then
    copy_file \
      "$SRC/docker/torii-runner/README.md" \
      "$DEST/docker/torii-runner/README.md"
  fi
  for extra in build-torii-runner-image.sh benchmark-hermes-startup.sh; do
    [[ -f "$SRC/scripts/$extra" ]] && copy_file "$SRC/scripts/$extra" "$DEST/scripts/$extra"
  done
fi

# F28: seed repo-local memory stub (committed; grows after each review)
seed_local_memory() {
  local mem_dir="$DEST/.torii"
  local mem_file="$mem_dir/MEMORY.md"
  if [[ -e "$mem_file" && "$FORCE" != "1" ]]; then
    log "exists (skip, use --force): $mem_file"
    return 0
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY  seed $mem_file"
    return 0
  fi
  mkdir -p "$mem_dir"
  if [[ -f "$SRC/agent/MEMORY.seed.md" ]]; then
    cp -f "$SRC/agent/MEMORY.seed.md" "$mem_file"
  else
    cat >"$mem_file" <<'EOF'
# Torii Gate review memory

Cumulative notes from Torii PR reviews (repo-local under `.torii/`).
EOF
  fi
  log "OK   $mem_file"
}

# Customer quieter vault bootstrap: .torii/runs/ README + labeled demo packs
seed_runs_vault() {
  local runs_dir="$DEST/.torii/runs"
  local readme="$runs_dir/README.md"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY  seed $readme (+ demo packs)"
    return 0
  fi
  mkdir -p "$runs_dir"
  touch "$runs_dir/.gitkeep"
  if [[ -e "$readme" && "$FORCE" != "1" ]]; then
    log "exists (skip readme, use --force): $readme"
  else
    cat >"$readme" <<'EOF'
# Torii run vault (customer quieter path)

Each review lands a slim pack here after the gate runs:

```text
.torii/runs/{trace_id}/meta.json
.torii/runs/{trace_id}/summary.md
.torii/runs/{trace_id}/review.md
```

Install seeds **labeled demo** packs (`demo-*-001`, meta `demo: true`) so
`quieter -- status` works offline. Organic packs replace the demo story after
you require **`torii/gate`** and run real reviews.

## Measure quieter over time (no hub clone)

```bash
python3 scripts/torii.py quieter -- status
python3 scripts/torii.py quieter -- report
# → .torii/quieter-over-time.md
```

## First organic fill

1. Require status check **`torii/gate`** on the default branch  
2. `@torii review this pr` on a real PR  
3. Re-run `quieter -- status` — `local_organic_n` should rise  

Docs: `docs/QUIETER.md` · install path: `docs/INSTALL.md`.  
Do not hand-edit run packs — the gate writes them (demo packs are install-only).
EOF
    log "OK   $readme (customer quieter vault)"
  fi
  # Path-to-value: seed demo packs via quieter bootstrap (TORII_ROOT = DEST when scripts present)
  if [[ -f "$DEST/scripts/quieter_over_time.py" ]]; then
    local force_flag=()
    [[ "$FORCE" == "1" ]] && force_flag=(--force)
    if TORII_ROOT="$DEST" python3 "$DEST/scripts/quieter_over_time.py" bootstrap --demo "${force_flag[@]}" >/dev/null 2>&1; then
      log "OK   .torii/runs demo packs (install-demo · quieter path-to-value)"
    else
      log "warn: quieter demo seed skipped (run: python3 scripts/torii.py quieter -- bootstrap --demo)"
    fi
  fi
}

seed_local_memory
seed_runs_vault

write_stamp "pack"
write_tenant_env

log ""
log "Next steps (5-minute path — see docs/INSTALL.md):"
log "  1. Commit installed pack + .torii/MEMORY.md + .torii/runs/; push default branch."
log "  2. Secret: OPENROUTER_API_KEY."
log "  3. Branch protection: require status check **torii/gate**."
log "  4. On a PR: @torii review this pr"
log "  5. Day-2: python3 scripts/torii.py status --text  (one-screen commercial · cost · cert · quieter)"
log "  6. Day-2 doctor: python3 scripts/torii.py doctor"
log "  7. Day-2 cost/PR: python3 scripts/torii.py ops -- status  (docs/ops/cost-pr-dashboard.md)"
log "  8. Quieter chart (own repo): python3 scripts/torii.py quieter -- status  (docs/QUIETER.md)"
log "One CLI: python3 scripts/torii.py help|status|doctor|memory|gate|ops|enterprise  (not peer scripts on day one)"
if [[ "$MINIMAL" == "1" ]]; then
  log "Pack surface: minimal (gate/review). Re-install without --minimal for full compound-loop scripts."
else
  log "Pack surface: full runtime. Use --minimal for a smaller 5-minute surface."
fi
log "  Tip: offline smoke: bash scripts/smoke-torii-gate.sh"
log "  Tip: hub-managed thin caller: re-run with --caller"
log "  Tip: measured dogfood cost is local vault only (never federated) — docs/enterprise/PRIVACY.md"
log "  Tip: enterprise light multi-org: --tenant <id> or TORII_MEMORY_TENANT · python3 scripts/torii.py enterprise -- status"
log "  Tip: install stamp records tenant_id= + memory_default=repo-local (.torii-install-stamp)"
log "Done."

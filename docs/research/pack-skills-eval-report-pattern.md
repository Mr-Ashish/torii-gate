# F83 research note — pack skills + paper eval report

**Date:** 2026-08-01  
**Fire:** F83

## Gap

`install-torii.sh` only copied top-level `agent/*` files — **not** `agent/skills/` or `agent/tools/`. F82 auto-adopt was invisible on target packs.

## Pattern

1. Pack rsync `agent/skills/` + `agent/tools/`.
2. Aggregate vault summaries into EVAL-REPORT for paper/eval.
3. Soft `federated_hub_ingest promote` post-run.

## Success

- install --force ships skill-f74-*.md
- eval report n_runs≥1 privacy_ok

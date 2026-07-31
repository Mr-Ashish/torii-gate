# F61 — Suggested test plan generation

**Date:** 2026-08-01  
**Status:** shipping  
**Tag:** PRODUCT_FEATURE | DETERMINISTIC | AGENT_QUALITY

## Problem

Milvus e2e (mean ~37/50) repeatedly shows **soft D3 actionability**: empty Key
findings, vague “add tests” nits, no concrete scenarios. F58 PR-description
checklists help authors at describe-time but do not land on the **review
comment** as a first-class section.

## Fix

1. **`scripts/testplan_generation.py`** — pure code from `pr.json` + optional
   unified diff:
   - classify prod vs test paths
   - extract new symbols (`func`/`def`/`fn`/…) from `+` lines
   - heuristics: security, migration, config, hot-path, title/body claims
     (skip/limit/fix)
   - prioritized cases P0/P1/P2 with kind + target + scenario
2. **Assemble** writes `testplan.md` / `testplan-section.md`, injects trusted
   block into prompt (`apply_to_prompt`).
3. **Post-normalize** soft-injects `### Suggested test plan` when missing or
   placeholder (same pattern as F57 mermaid).
4. **Prompt template** gains the section; normalize soft-sections list updated.
5. **Toggles:** `testplan` (default on), `testplan_max_cases` (12).

## Design split

| Layer | Role |
|-------|------|
| TOOLS | CLI `generate|section|plan|apply` |
| WORKFLOW | assemble + run-hermes post-normalize |
| PROMPT | judgment refines P0/P1; must not drop P0 without reason |
| MD | section contract in `review-prompt.md` |

## Tests

`tests/test_testplan_generation.py`

## Verify

```bash
pytest tests/test_testplan_generation.py -q
python3 scripts/testplan_generation.py section \
  --pr-json .torii-out-e2e-milvus-pr1/pr.json \
  --diff .torii-out-e2e-milvus-pr1/pr.diff | head
```

## Expected benchmark lift

D3 Actionability (+concrete scenarios even when Key findings empty); secondary
D9/D10 via risk-aligned P0 ordering.

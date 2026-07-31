# F62 — FP resolve + memory update

**Date:** 2026-08-01  
**Status:** shipping  
**Tag:** PRODUCT_FEATURE | DETERMINISTIC | MEMORY | AGENT_QUALITY

## Problem

Milvus / odoo e2e show **D1 signal** and **D8 memory** gaps: re-reviews re-raise
nits authors already dismissed (“false positive”, “by design”, “won’t fix”) or
claimed fixed. MEMORY.md only distilled verdicts/blocking — no structured FP
patterns for the next run to respect.

## Fix

1. **`scripts/fp_resolve_memory.py`** — pure code:
   - classify author bodies → `false_positive` | `resolved` (regex)
   - mine replies on Torii inline roots (+ path-citing PR conversation comments)
   - merge with MEMORY.md `## FP patterns`
   - emit `fp-resolve.json` / section markdown
2. **Assemble** calls `assemble()` → inject trusted table into prompt before
   changed-files summary.
3. **Post-distill** `update` merges new thread signals into Hermes `MEMORY.md`.
4. **Prompt + MEMORY.seed** document the contract (no re-raise without new evidence).
5. **Toggles:** `fp_resolve` (default on), `fp_resolve_max` (24).

## Design split

| Layer | Role |
|-------|------|
| TOOLS | CLI `classify|plan|assemble|update|section|merge-memory` |
| WORKFLOW | assemble-context + run-torii-review after distill |
| PROMPT | judgment may re-raise only with **new** evidence |
| MD | `## FP patterns` memory pack + review-prompt F62 section |

## Tests

`tests/test_fp_resolve_memory.py`

## Verify

```bash
pytest tests/test_fp_resolve_memory.py -q
python3 scripts/fp_resolve_memory.py classify --body "false positive by design"
```

## Expected benchmark lift

D1 (less noise on re-review), D8 (FP patterns compound in local memory).

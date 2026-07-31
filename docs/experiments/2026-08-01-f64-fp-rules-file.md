# F64 — Durable fp-rules.json self-learn store

**Date:** 2026-08-01  
**Status:** shipping  
**Tag:** PRODUCT_FEATURE | MEMORY | SELF_LEARN

## Problem

F62 stores FP patterns as free-text MEMORY.md bullets. That works for prompt
injection but is fragile for merge/preload and does not round-trip cleanly
through local `.torii/` publish → next-run assemble.

## Fix

1. **`fp-rules.json`** schema (`schema_version=1`, `rules[]`) written next to
   MEMORY on F62 `update` and under `OUT_DIR`.
2. **Assemble** loads durable rules (OUT_DIR / HERMES / `TORII_FP_RULES_FILE`)
   into the FP plan alongside thread + MEMORY signals.
3. **Preload** fetches `.torii/fp-rules.json` into Hermes + OUT_DIR (soft).
4. **Hub payload + ingest** carry `fp_rules` and merge into local/hub memory
   root so re-reviews compound structured suppressions.

This is the thin local self-learn loop (not multi-tenant federation). Hub
cross-deployment federation remains deferred.

## Tests

`tests/test_fp_resolve_memory.py` (RulesFile)

## Verify

```bash
pytest tests/test_fp_resolve_memory.py -q
python3 scripts/fp_resolve_memory.py update --out-dir OUT --memory MEMORY.md
# → OUT/fp-rules.json + MEMORY.md ## FP patterns
```

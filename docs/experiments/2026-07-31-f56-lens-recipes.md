# F56 — Review lens recipes + named prompt packs

**Date:** 2026-07-31  
**Status:** shipped (MERGED PR #6)  
**Tag:** PRODUCT_FEATURE | AGENT_QUALITY | MULTI_LENS

## Problem

F52 multi-lens is a single fixed 7-row checklist. Security-heavy, docs-only, and
Odoo/ORM PRs need different **focus hints** and lens ordering without a second
Hermes loop or multi-agent fan-out.

## Fix (code-first)

1. **`agent/packs/*.json`** — named recipes: `default`, `security`, `docs`, `odoo`, `performance`.
2. **`scripts/lens_recipes.py`** — list/get/render/apply/resolve; rewrites
   `### Multi-lens pass` + `### Multi-lens checklist` in assembled `prompt.md`.
3. **Assemble wire:** soft apply after template fill; meta `LENS_PACK` / `LENS_PACKS`.
4. **Toggles (F55):** `lens_packs` (bool, default on), `lens_pack` (str, default `default`).

Judgment (ok/concern/n/a + findings) stays in the model. Pack files are config/MD-adjacent JSON, not prompt spaghetti.

## Tests

`tests/test_lens_recipes.py`

## Verify

```bash
pytest tests/test_lens_recipes.py -q
python3 scripts/lens_recipes.py list
TORII_LENS_PACK=odoo python3 scripts/lens_recipes.py render
```

## Next

Auto-select pack from path globs (docs/** → docs, addons/** → odoo); live e2e D10 depth on odoo pack.

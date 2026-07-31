# F63 — Domain lens packs (milvus/go/cpp) + auto-select

**Date:** 2026-08-01  
**Status:** shipping  
**Tag:** PRODUCT_FEATURE | AGENT_QUALITY | MULTI_LENS

## Problem

F56 packs cover default/security/docs/odoo/performance. Milvus/Go/C++ eval
corpus still uses generic multi-lens hints — D10 depth and domain signal stay
thin. Manual `TORII_LENS_PACK` is easy to forget on multi-repo installs.

## Fix

1. **New packs:** `agent/packs/milvus.json`, `go.json`, `cpp.json` with
   domain-ordered lenses + `extra_focus` + `path_globs`.
2. **`path_globs` + auto-select** in `lens_recipes.py`:
   - `select_pack_for_paths` scores packs by glob hits + specificity
   - `TORII_LENS_PACK=auto` (new **default**) picks pack from PR changed files
   - Explicit pack ids still win
3. **Assemble** passes file paths into `apply_file(..., paths=...)`.
4. **odoo/docs** packs gain `path_globs` for auto-detect.

Judgment stays in the model. Pack JSON is config, not prompt spaghetti.

## Tests

`tests/test_lens_recipes.py` (auto-select + list milvus/go/cpp)

## Verify

```bash
pytest tests/test_lens_recipes.py -q
python3 scripts/lens_recipes.py list
python3 scripts/lens_recipes.py select --paths \
  internal/flushcommon/writebuffer/x.go
# → milvus
```

## Expected lift

D10 multi-lens depth on milvus/go/cpp PRs; secondary D1/D8 via domain focus
hints (less generic nits).

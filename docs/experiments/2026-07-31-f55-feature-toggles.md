# F55 — Unified feature toggle system

**Date:** 2026-07-31  
**Status:** shipped (MERGED PR #5)  
**Tag:** PRODUCT_FEATURE | AGENT_DESIGN

## Problem

Product gates (`TORII_FIXIT_PROMPTS`, `TORII_ISSUE_CONTEXT`, inline, labels, …)
were ad-hoc `os.environ` parses duplicated across scripts with slightly different
falsey sets and no single inventory. Operators and agents could not dump resolved
product toggles; repo-level overrides required editing CI vars only.

## Fix (code-first)

1. **`scripts/feature_toggles.py`** — registry of short keys + `TORII_*` env +
   kind/default/category/feature id. Precedence: **env > file > default**.
2. **File overrides:** `TORII_TOGGLES_FILE` or `.torii/toggles.json` (JSON map of
   short keys or env names). Stdlib only (no Dynaconf fork).
3. **CLI:** `list | get | enabled | dump | product | shell` for operators and
   agent tools.
4. **Consumers wired:** `post-inline-comments.py` (inline / suggestions / fixit),
   `linked_issue_context.py` (`issue_context`) resolve via registry.

Judgment stays in prompts; gate resolution is deterministic code.

## Tests

`tests/test_feature_toggles.py` + existing inline/issue tests still green.

## Verify

```bash
pytest tests/test_feature_toggles.py -q
python3 scripts/feature_toggles.py product --values-only --no-file | jq .
python3 scripts/feature_toggles.py enabled fixit_prompts --no-file; echo $?
```

## Next

Optional: migrate remaining scripts to `is_enabled()`; OpenFeature provider later
if multi-tenant remote flags needed. Named lens recipe packs stay separate (F56).

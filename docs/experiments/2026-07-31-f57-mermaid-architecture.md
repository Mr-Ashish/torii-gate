# F57 — Mermaid architecture diagram in PR review

**Date:** 2026-07-31  
**Status:** shipped (MERGED PR #7)  
**Tag:** PRODUCT_FEATURE | DETERMINISTIC

## Problem

Reviews walk files but rarely show **structure**. Authors and reviewers lack a
quick map of which packages a PR touches; LLM-drawn diagrams invent fake deps.

## Fix (code-first)

1. **`scripts/mermaid_architecture.py`** — parse `pr.json` / `files.txt` / paths →
   Mermaid `flowchart LR` with package subgraphs + file nodes. Caps via
   `TORII_MERMAID_MAX_NODES`.
2. **Assemble:** write `architecture.md`, inject into `prompt.md` (soft).
3. **Post-normalize soft inject:** if review lacks diagram, apply section
   (toggle-aware; never fails review).
4. **Prompt/normalize:** `### Architecture diagram` soft section + heading alias.
5. **Toggles:** `TORII_MERMAID`, `TORII_MERMAID_MAX_NODES` (F55 registry).

No second model call. Edges between groups are **adjacency**, not dependencies.

## Tests

`tests/test_mermaid_architecture.py`

## Verify

```bash
pytest tests/test_mermaid_architecture.py -q
python3 scripts/mermaid_architecture.py section --paths addons/a/x.py odoo/tools/y.py
```

## Next

Optional true import-graph edges for Python-only PRs; PR description filler (F58).

# F72 — Full-chain revalidation (maker/checker)

**Date:** 2026-08-01  
**Type:** agent_quality, tools, bench

## Problem

F70 dual-pass critic and F71 taint prefilter still left the **maker** free to mark REQUEST CHANGES on narrative findings. Research (VulAgent, QASecClaw, Argus) and Loop Engineering both require a **separate checker**.

## Design

Deterministic pipeline stage `scripts/chain_revalidate.py`:

1. Parse finding chunks from review (Blocking / Security audit / Key findings)
2. Match **hypotheses** (CWE/theme keyword catalog)
3. Attach **path** evidence (local + document inheritance)
4. Confirm against **F71 taint candidates** (source→sink / sink-only)
5. Ladder: `full_chain` | `theme_path` | `path_only` | `unvalidated` | `likely_fp`
6. Independent `verdict_checker` + Loop-Ready-style scorecard

Prompt inject: `<!-- torii-f72-chain-revalidate -->` (checker brief for the maker).

Toggle: `TORII_CHAIN_REVALIDATE` / `chain_revalidate` (default on).

## Metrics

| Mode | Result |
|------|--------|
| Offline fixture good | full_chain_rate=1.0, recall=1.0, verdict_checker=REQUEST_CHANGES |
| Offline fixture weak | precision_proxy=0.0, verdict_checker=APPROVE |
| Delta | full_chain_rate +1.0, precision +1.0 |
| Live Hermes (gpt-4.1-mini) | F70 recall=1.0 tp=4; F72 full_chain_rate=1.0 scorecard L3 |
| pytest | 451 passed |

## Files

- `scripts/chain_revalidate.py`
- `tests/test_chain_revalidate.py`
- `agent/tools/adopted/chain-revalidate.json`
- wire: `assemble-context.sh`, `feature_toggles.py`

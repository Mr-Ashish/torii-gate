# F70 — Labeled vuln e2e bench + dual-pass critic + TP compound memory

**Date:** 2026-08-01  
**Status:** shipping  
**Tag:** PRODUCT_FEATURE | AGENT_QUALITY | MEMORY | BENCHMARK

## Problem

Self-evolution and FP memory existed, but detection quality was not **measured** against ground truth. No dual of FP rules for confirmed true positives. Juice Shop harness was stub-only.

## Research

QASecClaw / VulAgent: validation pass after discovery is the high-ROI FP reducer. Self-evolving agents survey: inter-test-time memory updates compound skill without weight training.

## Fix

| Stage | Action |
|-------|--------|
| **score** | review.md × cases.json → TP/FN/recall/verdict_ok |
| **critic** | dual-pass offline: extract findings → path evidence + FP demote + TP boost |
| **promote** | confirmed cases → `tp-signatures.json` (schema v1, dual of F64) |
| **inject** | trusted prompt section `<!-- torii-f70-tp-signatures -->` |
| **fixture** | good vs weak offline e2e metrics |
| **live** | optional bounded Hermes review of `demo/insecure` when API key present |

## Tests

```bash
pytest tests/test_bench_security_gate.py -q
python3 scripts/bench_security_gate.py fixture
```

## Success metric

`fixture_pass=1` (good finds all 4 required cases + REQUEST_CHANGES; weak fails).

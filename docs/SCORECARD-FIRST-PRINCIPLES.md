# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T21:30:46Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | merge authority · ICP |
| 2 | Diff vs SAST | 8.2 | DIFF.md · labeled tp=18 |
| 3 | JTBD | 8.5 | quieter · torii/gate |
| 4 | Agent tools | 8.0 | tool_use_rate≈0.875 |
| 5 | Memory | 8.0 | L3 |
| 6 | Self-evolution | 7.8 | dual_gate_safe |
| 7 | Install | 8.5 | 5-min path |
| 8 | Ops | **8.8** | **no double demote-eval on live scorecard** (this fire) · fail_closed |
| 9 | Enterprise | 8.0 | isolation · tenant |
| 10 | Pricing | 8.0 | open core |
| 11 | GTM | 7.5 | pilot · DIFF · Pages |
| 12 | Simplicity | 8.2 | status 4 beats |

**Overall ~8.2** (cap **8.0** until paid pilot) · commercial **8.5**.

## This fire

**SCORECARD_NO_DOUBLE_DEMOTE:** live `product_scorecard` uses `--shallow` after demote-eval stage; reuses `critic-demote-eval.json` — fixes Modal 1500s hangs.

## Remaining gaps

| Rank | Gap | Status |
|-----:|-----|--------|
| 1 | First design partner / paid pilot | human GTM |
| 2 | Live customer quieter vault | partner install |
| 3 | Public eval age &lt;72h | standing |
| 4 | No F185+ without customer win | standing |

```bash
python3 scripts/torii.py scorecard --shallow --out-dir DIR
# live path: demote-eval then scorecard --shallow
```

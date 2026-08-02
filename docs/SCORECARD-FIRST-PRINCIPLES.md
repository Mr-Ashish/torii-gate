# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T03:06:43Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | merge authority · torii/gate |
| 2 | Diff vs SAST | **8.6** | merge beat vs SAST labeled_tp=18 good_recall=1.00 weak_fp=0.00 |
| 3 | JTBD | 9.3 | cert reasons + path_p50 + vs SAST on merge |
| 4 | Agent tools | 8.7 | tool-use rate 0.90 · n=92 |
| 5 | Memory | 8.4 | L3 · doctor=True |
| 6 | Self-evolution | 8.3 | pending=0 · dual_gate |
| 7 | Install | 8.9 | bootstrap --demo |
| 8 | Ops | 9.1 | LIVE_LEAN · model pin |
| 9 | Enterprise | 8.5 | themes-only · isolation |
| 10 | Pricing | 8.5 | open_core=$0 pre-revenue |
| 11 | GTM | 8.4 | PILOT-PROOF |
| 12 | Simplicity | 9.2 | merge one-liner: quieter · certs · vs SAST |

**Overall ~8.75 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**MERGE_DIFF_VS_SAST:** day2 peeks good_recall + weak_fp_proxy; merge beat surfaces `vs SAST labeled_tp=… good_recall=… weak_fp=…` next to certs (buyer differentiation on the merge job, not growth fluff).

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM | high / non-code |
| 2 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py status --text
python3 scripts/torii.py diff -- status
python3 scripts/diff_vs_sast.py status
```

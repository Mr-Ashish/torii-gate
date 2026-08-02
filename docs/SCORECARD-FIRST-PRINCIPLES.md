# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T02:49:30Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | merge authority · torii/gate |
| 2 | Diff vs SAST | 8.2 | DIFF.md · labeled_tp=18 |
| 3 | JTBD | **9.3** | cert reasons + path_p50 on merge beat |
| 4 | Agent tools | **8.7** | tool-use rate 0.90 · n=92 · SUMMARY parse |
| 5 | Memory | 8.4 | L3 · doctor=True |
| 6 | Self-evolution | 8.3 | pending=0 · dual_gate |
| 7 | Install | 8.9 | bootstrap --demo |
| 8 | Ops | 9.1 | LIVE_LEAN · model pin |
| 9 | Enterprise | 8.5 | themes-only · isolation |
| 10 | Pricing | 8.5 | open_core=$0 pre-revenue |
| 11 | GTM | 8.4 | PILOT-PROOF |
| 12 | Simplicity | **9.2** | merge reasons · path_p50 · zero_tool |

**Overall ~8.7 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**MERGE_CERT_TOOLUSE_REFRESH:** parse SUMMARY.md for tool turns; vault cert reason codes + path_p50 on merge beat; tool-use measured_n 72→92 · rate 0.90.

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM | high / non-code |
| 2 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py status --text
python3 scripts/torii.py tool-use -- status
python3 scripts/torii.py certificate -- status
```

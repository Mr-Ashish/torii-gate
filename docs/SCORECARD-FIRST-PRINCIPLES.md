# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T03:26:41Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | merge authority · torii/gate |
| 2 | Diff vs SAST | 8.6 | merge + proof packet labeled_tp=18 |
| 3 | JTBD | **9.4** | proof packet vs SAST row · growth apply= |
| 4 | Agent tools | 8.7 | tool-use rate 0.90 · n=92+ |
| 5 | Memory | 8.4 | L3 · doctor=True |
| 6 | Self-evolution | 8.3 | pending=0 · dual_gate |
| 7 | Install | 8.9 | bootstrap --demo |
| 8 | Ops | 9.1 | LIVE_LEAN · model pin |
| 9 | Enterprise | 8.5 | themes-only · isolation |
| 10 | Pricing | 8.5 | open_core=$0 pre-revenue |
| 11 | GTM | **8.7** | growth apply=design-partner · gtm=docs/GTM.md · proof vs SAST |
| 12 | Simplicity | 9.2 | status → apply path on one growth line |

**Overall ~8.8 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**PILOT_PROOF_GTM_APPLY:** proof packet embeds measured vs SAST row; growth beat surfaces `apply=design-partner issue` + `gtm=docs/GTM.md` so status → partner outreach is one glance (dims 11+3+2).

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM | high / non-code |
| 2 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py status --text
python3 scripts/torii.py pilot -- packet
```

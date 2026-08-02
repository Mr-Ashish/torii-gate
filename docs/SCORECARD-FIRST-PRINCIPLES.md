# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T02:11:00Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | merge authority · torii/gate |
| 2 | Diff vs SAST | 8.2 | DIFF.md · labeled_tp=18 |
| 3 | JTBD | 9.2 | quieter · TTS · proof packet |
| 4 | Agent tools | **8.4** | tool-use rate + zero_tool on status |
| 5 | Memory | 8.0 | L3 |
| 6 | Self-evolution | 8.3 | pending=0 · dual_gate |
| 7 | Install | 8.9 | bootstrap --demo |
| 8 | Ops | 9.1 | LIVE_LEAN · model pin |
| 9 | Enterprise | **8.5** | org beat: themes-only · privacy_ok · mt_themes · isolation |
| 10 | Pricing | 8.0 | open core |
| 11 | GTM | 8.4 | PILOT-PROOF |
| 12 | Simplicity | **9.0** | org+cost beats carry privacy + zero_tool |

**Overall ~8.6 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**ORG_PRIVACY_STATUS:** day-2 Org beat shows federation themes-only + privacy_ok + multi-tenant themes; Cost & trust shows zero_tool rate; enterprise status one_liner.

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM | high / non-code |
| 2 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py status --text
python3 scripts/torii.py enterprise -- status
```

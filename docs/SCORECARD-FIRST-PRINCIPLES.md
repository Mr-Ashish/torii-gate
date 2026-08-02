# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T03:48:00Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.6 | merge authority · open-core pill · Pages CTAs |
| 2 | Diff vs SAST | 8.7 | merge + proof + landing **18 TP** hero stat |
| 3 | JTBD | **9.4** | status apply= · pages= · proof packet |
| 4 | Agent tools | 8.7 | tool-use rate 0.90 · n=92+ |
| 5 | Memory | 8.4 | L3 · doctor=True |
| 6 | Self-evolution | 8.3 | pending=0 · dual_gate |
| 7 | Install | 8.9 | bootstrap --demo · Install free CTA |
| 8 | Ops | 9.1 | LIVE_LEAN · model pin |
| 9 | Enterprise | 8.5 | themes-only · isolation |
| 10 | Pricing | 8.5 | open_core=$0 pre-revenue |
| 11 | GTM | **9.0** | landing design-partner CTAs · no Hub71 detour · growth pages= |
| 12 | Simplicity | 9.3 | status → apply + pages on one growth line |

**Overall ~8.9 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**LANDING_PARTNER_CTA:** public Pages landing primary CTAs are **Apply design partner** + **Install free** (removed Hub71 + wrong-repo control plane); fixture enforces design-partner.yml + no hub71.com; growth beat surfaces `pages=mr-ashish.github.io/torii-gate` (dims 11+1+12).

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM | high / non-code |
| 2 | Partner week-1 success CLI (optional) | code | med / low |
| 3 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py status --text
python3 scripts/build_landing_site.py fixture
python3 scripts/torii.py pilot -- packet
```

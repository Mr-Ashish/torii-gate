# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T22:54:15Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | merge authority |
| 2 | Diff vs SAST | 8.2 | DIFF.md |
| 3 | JTBD | **8.9** | **customer .torii/runs bootstrap + FS publish** (**this fire**) |
| 4 | Agent tools | 8.0 | tool_use |
| 5 | Memory | 8.0 | compound |
| 6 | Self-evolution | 7.8 | dual_gate |
| 7 | Install | **8.7** | install stamps `.torii/runs/README` |
| 8 | Ops | 8.9 | LIVE_LEAN · FS vault without bot push |
| 9 | Enterprise | 8.0 | isolation |
| 10 | Pricing | 8.0 | open core |
| 11 | GTM | 8.0 | GTM.md |
| 12 | Simplicity | 8.2 | status 4 beats + bootstrap_hint |

**Overall ~8.3** (cap **8.0** until first design partner).

## This fire

**CUSTOMER_QUIETER_VAULT:** install seeds `.torii/runs` · `quieter -- bootstrap` · FS local publish for Actions workspace · status bootstrap fields.

## Remaining

| Rank | Gap | Status |
|-----:|-----|--------|
| 1 | First closed design partner (send GTM.md) | human |
| 2 | Customer quieter vault | **shipped** bootstrap; fill needs real partner PRs |
| 3 | No F185+ without customer win | standing |

```bash
python3 scripts/torii.py quieter -- bootstrap
python3 scripts/torii.py quieter -- status
```

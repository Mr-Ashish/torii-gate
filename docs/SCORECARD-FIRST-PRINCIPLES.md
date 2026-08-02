# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T04:57:00Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.6 | merge authority · open-core · Pages CTAs |
| 2 | Diff vs SAST | 8.7 | merge + proof + 18 TP |
| 3 | JTBD | **9.5** | quieter delta · week1 · apply |
| 4 | Agent tools | **8.9** | tool-use rate · **mean_turns=6.9** · zero_tool |
| 5 | Memory | 8.7 | L3 · tp/fp on growth · doctor |
| 6 | Self-evolution | **8.7** | active=10 **buyer=8** auto_adopt=off dual_gate |
| 7 | Install | 9.1 | pilot -- week1 · INSTALL |
| 8 | Ops | 9.1 | LIVE_LEAN · model pin |
| 9 | Enterprise | **8.7** | isolation · **no cross-tenant path/snippet** |
| 10 | Pricing | 8.5 | open_core=$0 pre-revenue |
| 11 | GTM | 9.1 | landing CTAs · PARTNER-WEEK1 |
| 12 | Simplicity | **9.5** | four beats carry buyer/mean_turns/isolation |

**Overall ~9.05 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**SELF_EVOLVE_BUYER_TOOLS:** growth surfaces `buyer=N` product skills + `auto_adopt=off`; cost/trust `mean_turns=`; org `no cross-tenant path/snippet` (dims 6+4+9+12).

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM | high / non-code |
| 2 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py status --text
python3 scripts/torii.py self-evolve -- status
```

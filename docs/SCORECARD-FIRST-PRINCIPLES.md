# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T05:50:00Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.8 | merge authority · **require_check live/off honesty** |
| 2 | Diff vs SAST | 8.7 | merge + proof + 18 TP |
| 3 | JTBD | **9.6** | live require-check · week1 · apply |
| 4 | Agent tools | 8.9 | rate · mean_turns · zero_tool |
| 5 | Memory | 8.7 | L3 · tp/fp · doctor |
| 6 | Self-evolution | 8.7 | buyer=8 · auto_adopt=off |
| 7 | Install | **9.3** | INSTALL + **quieter -- require-check** |
| 8 | Ops | 9.1 | LIVE_LEAN · model pin |
| 9 | Enterprise | 8.9 | isolation · fed heat |
| 10 | Pricing | 8.8 | open_core · unit=$/PR |
| 11 | GTM | **9.2** | design-partner template · require-check commitment |
| 12 | Simplicity | **9.5** | merge require_check=off|live |

**Overall ~9.2 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**REQUIRE_CHECK_LIVE:** `quieter -- require-check` queries GitHub for live **torii/gate** required status; day-2 merge shows `require_check=live|off|missing`; week1 + INSTALL + design-partner template wire it (dims 3+7+11). Hub currently honest `require_check=off` (main not protected).

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | Enable hub branch protection with torii/gate | ops / human | high (dogfood) |
| 2 | First closed design partner | human GTM | high / non-code |
| 3 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py quieter -- require-check
python3 scripts/torii.py status --text
```

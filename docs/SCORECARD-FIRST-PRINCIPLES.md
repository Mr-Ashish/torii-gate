# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T06:05:00Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | **9.0** | hub dogfoods **require_check=live** |
| 2 | Diff vs SAST | 8.7 | merge + proof + 18 TP |
| 3 | JTBD | **9.7** | live require-check + --enable path |
| 4 | Agent tools | 8.9 | rate · mean_turns · zero_tool |
| 5 | Memory | 8.7 | L3 · tp/fp · doctor |
| 6 | Self-evolution | 8.7 | buyer=8 · auto_adopt=off |
| 7 | Install | **9.4** | require-check --enable for partners |
| 8 | Ops | **9.2** | hub branch protection applied |
| 9 | Enterprise | 8.9 | isolation · fed heat |
| 10 | Pricing | 8.8 | open_core · unit=$/PR |
| 11 | GTM | **9.3** | dogfood proof on hub main |
| 12 | Simplicity | **9.5** | merge require_check=live |

**Overall ~9.3 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**HUB_REQUIRE_GATE_LIVE:** enabled GitHub branch protection on **Mr-Ashish/torii-gate@main** requiring **`torii/gate`**; `status` shows `require_check=live`; added `quieter -- require-check --enable [--yes]` for partners (dims 1+3+7+8+11).

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM | high / non-code |
| 2 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py quieter -- require-check
python3 scripts/torii.py status --text
```

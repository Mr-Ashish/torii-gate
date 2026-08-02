# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T00:42:00Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | merge authority · torii/gate |
| 2 | Diff vs SAST | 8.2 | DIFF.md · labeled_tp=18 |
| 3 | JTBD | **9.1** | quieter demo vault path-to-value · TTS p50 · FS vault |
| 4 | Agent tools | 8.0 | tool_use rate 0.875 |
| 5 | Memory | 8.0 | L3 compound |
| 6 | Self-evolution | 7.8 | dual_gate · active=10 |
| 7 | Install | **8.9** | bootstrap --demo seeds local vault offline |
| 8 | Ops | 9.0 | LIVE_LEAN product_default · FS vault · commercial |
| 9 | Enterprise | 8.0 | isolation · tenants |
| 10 | Pricing | 8.0 | open core |
| 11 | GTM | 8.0 | GTM.md · pilot 8/8 · 0 closed partners |
| 12 | Simplicity | **8.5** | status: local demo/organic · live_lean product_default |

**Overall ~8.5 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**QUIETER_DEMO_SEED:** install + `quieter -- bootstrap --demo` seeds two labeled demo packs so path-to-value quieter works offline; trajectory prefers organic/hub; status shows demo vs organic; live_lean reports product_default when env unset.

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM | high / non-code |
| 2 | Organic local quieter on customer PR | partner runs | proves JTBD |
| 3 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py status --text
python3 scripts/torii.py quieter -- status
python3 scripts/torii.py quieter -- bootstrap --demo
```

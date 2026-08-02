# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T07:33:00Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 9.0 | require_check=live · merge authority |
| 2 | Diff vs SAST | 8.7 | merge + proof + 18 TP |
| 3 | JTBD | **9.7** | dual_gate · free_riders=0 · tool_gate |
| 4 | Agent tools | 9.0 | mean_turns · tool_gate=on |
| 5 | Memory | 9.0 | L3 · tp/fp install-demo |
| 6 | Self-evolution | **9.0** | buyer=8 · **demoted=0 free_riders=0 top=** |
| 7 | Install | 9.4 | require-check · FP/quieter demos |
| 8 | Ops | 9.2 | hub protection · LIVE_LEAN |
| 9 | Enterprise | 8.9 | isolation · fed heat |
| 10 | Pricing | 8.8 | open_core · unit=$/PR |
| 11 | GTM | 9.3 | dogfood hub · partner path |
| 12 | Simplicity | **9.5** | fitness glance on growth beat |

**Overall ~9.4 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**SELF_EVOLVE_FITNESS:** growth surfaces measured skill fitness `demoted=N free_riders=N top=<id>` from fitness+attribution ledgers (dims 6+3+12).

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM | high / non-code |
| 2 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py status --text
python3 scripts/skill_fitness.py status
```

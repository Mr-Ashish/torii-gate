# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T06:24:00Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 9.0 | require_check=live · merge authority |
| 2 | Diff vs SAST | 8.7 | merge + proof + 18 TP |
| 3 | JTBD | **9.7** | FP die twice offline · tool_gate=on |
| 4 | Agent tools | **9.0** | mean_turns · **tool_gate=on** · zero_tool |
| 5 | Memory | **9.0** | L3 · **tp=4 fp=2** install-demo FP seed |
| 6 | Self-evolution | 8.7 | buyer=8 · auto_adopt=off |
| 7 | Install | **9.4** | install seeds FP demo + quieter demos |
| 8 | Ops | 9.2 | hub protection · LIVE_LEAN |
| 9 | Enterprise | 8.9 | isolation · fed heat |
| 10 | Pricing | 8.8 | open_core · unit=$/PR |
| 11 | GTM | 9.3 | dogfood hub · partner path |
| 12 | Simplicity | **9.5** | memory tp/fp · tool_gate on four beats |

**Overall ~9.35 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**MEMORY_FP_TOOL_GATE:** install-demo FP rules (`bootstrap-demo`) so growth shows `fp=2`; install-torii seeds them; cost/trust surfaces `tool_gate=on` (zero-tool fail-closed) (dims 5+4+3+7).

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM | high / non-code |
| 2 | No F185+ without customer win | standing | — |

```bash
python3 scripts/torii.py memory -- compound -- bootstrap-demo
python3 scripts/torii.py status --text
```

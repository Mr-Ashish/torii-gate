# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T20:44:23Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | merge authority · ICP |
| 2 | Diff vs SAST | 8.2 | DIFF.md · labeled tp=18 |
| 3 | JTBD | 8.5 | quieter · require torii/gate on status beat 1 |
| 4 | Agent tools | 8.0 | tool_use_rate=0.875 |
| 5 | Memory | 8.0 | L3 on growth beat |
| 6 | Self-evolution | 7.8 | dual_gate_safe on status |
| 7 | Install | 8.5 | 5-min · four-beat status in INSTALL |
| 8 | Ops | 8.5 | fail_closed on cost/trust beat |
| 9 | Enterprise | 8.0 | org beat · isolation |
| 10 | Pricing | 8.0 | open core |
| 11 | GTM | 7.5 | Pages · pilot · DIFF |
| 12 | Simplicity | **8.2** | **status 4 beats** · help day-2 primary table (**this fire**) |

**Overall ~8.1** (cap **8.0** until paid pilot) · commercial **8.5**.

## This fire

**STATUS_COMPACT:** `status --text` → four buyer beats; `--verbose` expanded; help day-2 primary + “Also day-2” line.

## Remaining gaps

| Rank | Gap | Status |
|-----:|-----|--------|
| 1 | First design partner / paid pilot | human GTM |
| 2 | Live customer quieter vault | partner install |
| 3 | Diff-vs-SAST one-pager | shipped |
| 4 | Status cognitive collapse | **shipped** |
| 5 | Public eval age &lt;72h | standing |
| 6 | No F185+ without customer win | standing |

```bash
python3 scripts/torii.py status --text
python3 scripts/torii.py status --verbose
python3 scripts/torii.py help
```

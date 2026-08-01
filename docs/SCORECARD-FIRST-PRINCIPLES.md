# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T23:13:05Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | merge authority |
| 2 | Diff vs SAST | 8.2 | DIFF.md |
| 3 | JTBD | **9.0** | **FS quieter vault even when git publish off** (**this fire**) |
| 4 | Agent tools | 8.0 | tool_use |
| 5 | Memory | 8.0 | compound |
| 6 | Self-evolution | 7.8 | dual_gate |
| 7 | Install | 8.7 | .torii/runs seed |
| 8 | Ops | **9.0** | FS vault independent of TORII_LOCAL_PUBLISH |
| 9 | Enterprise | 8.0 | isolation |
| 10 | Pricing | 8.0 | open core |
| 11 | GTM | 8.0 | GTM.md |
| 12 | Simplicity | 8.2 | status 4 beats |

**Overall ~8.4** (cap **8.0** until first design partner).

## This fire

**FS_VAULT_ALWAYS:** publish-run-local FS path runs when LOCAL_PUBLISH=0 (Modal); quieter chart can fill without bot git push.

## Remaining

| Rank | Gap | Status |
|-----:|-----|--------|
| 1 | First closed design partner | human GTM |
| 2 | No F185+ without customer win | standing |

```bash
TORII_LOCAL_FS_PUBLISH=1   # default
TORII_LOCAL_PUBLISH=0      # skip git push; FS vault still writes
```

# F170 — GEPA refine compound loop EVAL pack (F165–F169)

## Mental model E
```
util gap → GEPA refine → dual-gate LOO → dual_pp → federate promote → hub critic
```

**refine_loop_ok:** `True` · brand_ready=True · level L3

## Live proofs (Modal pytorch, POST_COMMENT=0)

| Fire | Title | Local recall | util_rate | tool_pp | Modal PR | Outcome |
|------|-------|-------------:|----------:|--------:|---------:|---------|
| F165 | GEPA-lite skill refine-from-util | 1.0 | 1.0 | None | 191831 | BIT3_OK |
| F166 | dual-gate LOO floor + fitness shield | 1.0 | 1.0 | None | 191829 | BIT3_OK |
| F167 | dual-rollout contribution_pp | 1.0 | 1.0 | 50.0 | 191832 | BIT3_OK |
| F168 | multi-tenant federate+promote | 1.0 | 1.0 | 50.0 | 191830 | BIT3_OK |
| F169 | hub always-prio + dual_fail critic | 1.0 | 1.0 | 50.0 | 191836 | BIT3_OK |

## Product surface
- PRODUCT Mental model E
- doctor/scorecard `refine_loop_ok`
- landing + TORII one-liners
- docs/brand/scorecard-metrics.md rows


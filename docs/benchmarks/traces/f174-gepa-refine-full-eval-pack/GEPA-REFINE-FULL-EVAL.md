# F174 — GEPA refine full EVAL pack (F165–F173)

## Mental model E (complete)
```
util gap → refine → dual-gate → dual_pp → promote → hub critic
       → chronic decay → multi-tenant federate decay → decay hub demote
```

**refine_loop_ok:** `True` · brand_ready=True · level L3
**decay demote:** dual_fail=True · multi-tenant decay hub=True

## Live proofs (Modal pytorch, POST_COMMENT=0)

| Fire | Title | Local recall | util | tool_pp | Modal PR | Outcome |
|------|-------|-------------:|-----:|--------:|---------:|---------|
| F165 | GEPA-lite skill refine-from-util | 1.0 | 1.0 | None | 191831 | BIT3_OK |
| F166 | dual-gate LOO floor + fitness shield | 1.0 | 1.0 | None | 191829 | BIT3_OK |
| F167 | dual-rollout contribution_pp | 1.0 | 1.0 | 50.0 | 191832 | BIT3_OK |
| F168 | multi-tenant federate+promote | 1.0 | 1.0 | 50.0 | 191830 | BIT3_OK |
| F169 | hub always-prio + dual_fail critic | 1.0 | 1.0 | 50.0 | 191836 | BIT3_OK |
| F170 | brand pack refine_loop_ok (F165–F169) | 1.0 | 1.0 | None | 191829 | BIT3_OK |
| F171 | chronic dual_fail always-priority decay | 1.0 | 1.0 | 50.0 | 191831 | BIT3_OK |
| F172 | multi-tenant decay federate | 1.0 | 1.0 | 50.0 | 191832 | BIT3_OK |
| F173 | multi-tenant decay hub critic | 1.0 | 1.0 | None | 191830 | BIT3_OK |

## Product surface
- PRODUCT Mental model E (F165–F173)
- doctor/scorecard `refine_loop_ok`
- landing + TORII one-liners (decay included)
- scorecard-metrics.md refine_* + decay demote rows


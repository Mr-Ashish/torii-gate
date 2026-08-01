# F178 — GEPA refine full EVAL pack (F165–F177)

## Mental model E (complete through revive gates)
```
util gap → refine → dual-gate → dual_pp → promote → hub critic
       → chronic decay → multi-tenant federate decay → decay hub demote
       → dual_pass revive → free-rider MT gate → contribution_pp floor
```

**refine_loop_ok:** measured on doctor/scorecard · brand_ready surface  
**revive gates:** free_rider_revive_ok · revive_pp_gate_ok · demote paper metrics

## Live proofs (Modal pytorch, POST_COMMENT=0)

| Fire | Title | Trace dir | Modal PR | Outcome |
|------|-------|-----------|---------:|---------|
| F165 | GEPA-lite skill refine-from-util | `f165-gepa-lite-skill-refine/` | 191831 | BIT3_OK |
| F166 | dual-gate LOO floor + fitness shield | `f166-gepa-refine-dual-gate-attr/` | 191829 | BIT3_OK |
| F167 | dual-rollout contribution_pp | `f167-gepa-refine-dual-rollout/` | 191832 | BIT3_OK |
| F168 | multi-tenant federate+promote | `f168-refine-dual-federate-promote/` | 191830 | BIT3_OK |
| F169 | hub always-prio + dual_fail critic | `f169-refine-dual-hub-critic/` | 191836 | BIT3_OK |
| F170 | brand pack refine_loop_ok (F165–F169) | `f170-gepa-refine-eval-pack/` | 191829 | BIT3_OK |
| F171 | chronic dual_fail always-priority decay | `f171-refine-dual-fail-decay/` | 191831 | BIT3_OK |
| F172 | multi-tenant decay federate | `f172-refine-decay-federate/` | 191832 | BIT3_OK |
| F173 | multi-tenant decay hub critic | `f173-refine-decay-hub-critic/` | 191830 | BIT3_OK |
| F174 | full brand+EVAL pack F165–F173 | `f174-gepa-refine-full-eval-pack/` | 191836 | BIT3_OK |
| F175 | dual_pass revive after multi-tenant decay | `f175-refine-dual-pass-revive/` | 191836 | BIT3_OK |
| F176 | free-rider multi-tenant dual_pass revive gate | `f176-free-rider-revive-gate/` | 191836 | BIT3_OK |
| F177 | contribution_pp floor for dual_pass revive | `f177-revive-pp-floor/` | 191836 | BIT3_OK |

## Demote paper metrics (offline pack)
| Metric | Meaning |
|--------|---------|
| refine_dual_fail_idle_demoted | F169 dual_fail after inject |
| refine_decay_hub_idle_demoted | F173 multi-tenant decay hub |
| free_rider_revive_idle_demoted | F176 free-rider local revive |
| low_pp_revive_idle_demoted | F177 contribution_pp floor |

## Product surface (F178)
- PRODUCT Mental model E (F165–F177)
- scorecard metrics: refine_dual_revive_ok · free_rider_revive_ok · revive_pp_gate_ok
- brand_lines pipeline through free-rider + pp-floor
- landing + TORII one-liners
- This pack supersedes partial F174 (F165–F173 only)

## Scorecard source
`python3 scripts/torii.py scorecard` → `docs/brand/scorecard-metrics.md`

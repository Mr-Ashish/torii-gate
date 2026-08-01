# F184 — GEPA + hub×GEPA compound full EVAL pack (F165–F183)

## Mental model E (complete through dual-loop compound)
```
util gap → refine → dual-gate → dual_pp → promote → hub critic
       → chronic decay → multi-tenant demote → dual_pass revive
       → free-rider MT + pp floor + LOO floor
       → hub×GEPA compound demote → inject → always → re-prompt
```

**refine_loop_ok:** F165–F183 · brand_ready surface  
**dual compound:** hub_gepa_compound_ok · inject · always · reprompt_compound_ok

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
| F178 | full brand+EVAL pack F165–F177 | `f178-gepa-refine-full-eval-pack/` | 191836 | BIT3_OK |
| F179 | LOO attribution floor for dual_pass revive | `f179-revive-loo-floor/` | 191836 | BIT3_OK |
| F180 | hub-archival × GEPA compound demote | `f180-hub-gepa-compound/` | 191836 | BIT3_OK |
| F181 | hub×GEPA compound prompt inject | `f181-hub-gepa-compound-inject/` | 191836 | BIT3_OK |
| F182 | hub×GEPA compound always priority | `f182-hub-gepa-compound-always/` | 191836 | BIT3_OK |
| F183 | hub×GEPA compound re-prompt budget | `f183-hub-gepa-compound-reprompt/` | 191836 | BIT3_OK |

## Demote + budget paper metrics
| Metric | Feature |
|--------|---------|
| refine_dual_fail_idle_demoted | F169 |
| refine_decay_hub_idle_demoted | F173 |
| free_rider_revive_idle_demoted | F176 |
| low_pp_revive_idle_demoted | F177 |
| loo_revive_idle_demoted | F179 |
| hub_gepa_compound_idle_demoted | F180 |
| reprompt_compound_ok (fixture f183_ok) | F183 |

## Product surface (F184)
- PRODUCT Mental model E (F165–F183)
- scorecard: refine_loop_ok + hub_gepa_* + reprompt_compound_ok
- brand_lines through re-prompt budget
- This pack supersedes F178 (F165–F177 only)

## Scorecard source
`python3 scripts/torii.py scorecard` → `docs/brand/scorecard-metrics.md`

_modal_bit3_ok_n ≈ 19_

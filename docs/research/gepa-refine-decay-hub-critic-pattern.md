# F173 research note — Multi-tenant decay hub critic + refine_loop_ok F171–F172

**Date:** 2026-08-01  
**Fire:** F173

## Sources
1. FederatedSkill + F172 multi-tenant decay without panel demote on APPROVE.
2. F169 dual_fail critic; F127/F139 hub gap critic pattern.
3. Optional LLM critic soft endorse_demote_hint (TORII_LLM_CRITIC).
4. F170 refine_loop_ok lagged F171–F172 wires.

## Gap
Multi-tenant chronic dual_fail decay demoted always budget but not APPROVE verdicts; refine_loop_ok stopped at F169.

## Pattern
| Layer | Role |
|-------|------|
| f173_refine_decay_hub | multi_tenant_decay + tenants≥2 → demote APPROVE |
| LLM panel_draft hint | soft endorse_demote when F173 fires |
| refine_loop_ok | AND F165–F173 |
| demote-eval | refine_decay_hub_idle_demoted |

## Success
- demote-eval refine_decay_hub_idle_demoted
- refine_loop_ok includes F171–F173

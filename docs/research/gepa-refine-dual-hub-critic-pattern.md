# F169 research note — Refine dual hub always-priority + dual_fail critic

**Date:** 2026-08-01  
**Fire:** F169

## Sources

1. FederatedSkill / F168: promoted refine dual themes must change next-run always budget.
2. F125/F161 hub post-score pattern: priority deltas + prompt inject.
3. F156 maker/checker: idle recovery tools demote APPROVE.
4. SkillsBench dual_fail after inject is free-rider APPROVE risk.

## Gap

F168 promoted refine dual themes but did not inject into always-priority ranking or demote APPROVE on dual_fail after refined skills inject.

## Pattern

| Layer | Role |
|-------|------|
| post_score_refine_dual_hub | promoted → Δalways priority |
| inject_refine_dual_hub_into_prompt | privacy-safe F169 section |
| f169_refine_dual_fail critic | dual_fail + inject → demote APPROVE |
| demote-eval | refine_dual_fail_idle_demoted paper bit |

## Success

- hub deltas > 0 for promoted skill; inject marker present
- demote-eval refine_dual_fail_idle_demoted
- skill_loop refine_dual_hub_ok

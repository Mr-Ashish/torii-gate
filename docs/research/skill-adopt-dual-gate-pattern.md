# F87 research note — dual contribution gate on skill auto-adopt

**Date:** 2026-08-01  
**Fire:** F87

## Sources

1. **SkillsBench** (arXiv 2602.12670): with vs without skills is the only honest skill utility metric.
2. **SkillOpt / Loop Engineering**: default REJECT until held-out gates pass.
3. Prior Torii F82: critic + fitness fixtures but no skill contribution delta.
4. Prior Torii F86: dual-rollout metrics existed but were not wired into adopt.

## Pattern

| Gate | Pass criterion |
|------|----------------|
| F78 critic fixture | fixture_pass |
| F74 fitness fixture | fixture_pass |
| **F86 dual (F87)** | dual_pass **and** skill_contribution_pp > 0 |
| F76 corpus (opt) | all_pass |

Env: `TORII_SKILL_AUTO_ADOPT_DUAL=1` (default). Set 0 to skip dual for emergency adopts.

## Success metric

- `skill_auto_adopt.py gate` includes `f86_dual_contribution` with contribution_pp>0
- Auto-adopt cycle refuses when dual fails (unless --force)

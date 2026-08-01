# F86 research note — dual-rollout skill contribution + multi-tenant promote

**Date:** 2026-08-01  
**Fire:** F86

## Sources

1. **SkillsBench** (arXiv 2602.12670): no-Skills vs Skills paired eval; curated +16.2pp; self-gen ~0.
2. **Agent Skill Evaluation** (arXiv 2606.11435): dual-rollout gap = skill contribution signal.
3. **FederatedSkill** (arXiv 2606.03143): multi-tenant skill theme promote (min_tenants).
4. Prior Torii F84/F85: hits + demote without with/without delta or tenant gate on skill themes.

## Pattern

| Idea | Torii F86 |
|------|-----------|
| With vs without | hit_rate(with skill language) − hit_rate(ablated) |
| Hold detection | F70 recall must not collapse after skill ablation |
| Multi-tenant promote | skill-tagged signals only if tenants≥2 and hits≥2 |
| Non-skill exclusion | sql_injection-style security themes not in skill promote file |

## Success metric

- Offline fixture: dual_pass, contribution_pp>0, single-tenant skill blocked, privacy_ok
- Live: promote stage soft on Modal/local after skill_fitness

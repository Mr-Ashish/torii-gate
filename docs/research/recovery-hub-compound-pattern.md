# F125 research note — Hub recovery-util post-score compound

**Date:** 2026-08-01  
**Fire:** F125

## Sources

1. **FederatedSkill** (arXiv 2606.03143): skill library as federation unit — share themes, not trajectories; compounds multi-tenant success when consumed.
2. **HASP** (arXiv 2605.17734): skills as runtime interventions — hub scores must change next-loop priority, not sit inert.
3. **MMG2Skill** early-stop / skill budget: multi-tenant util bins guide which recovery skills keep always slots under SkillReducer caps.
4. Loop-eng: measure → feedback path; write-only federation fails the readiness habit.

## Pattern

| Layer | Role |
|-------|------|
| F124 federate | recovery-util-signals (skill_id + util bins + tenant_hash) |
| F125 post-score | `hub-score` → priority_delta per recovery skill |
| select always | always_priority + hub Δ (cap +40) under ALWAYS_MAX |
| inject | `<!-- torii-f125-recovery-hub -->` privacy-safe section |
| traces | recovery-hub-score.json |

## Env

- `TORII_RECOVERY_HUB_COMPOUND=1` (default)

## Success

- Fixture hub_ok + privacy; mem priority_delta ≥ 5; hub section inject
- No paths / raw tenant strings in hub score or prompt

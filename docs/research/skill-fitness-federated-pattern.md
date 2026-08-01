# F85 research note — skill fitness ledger + federated skill themes

**Date:** 2026-08-01  
**Fire:** F85

## Sources

1. **FederatedSkill** (arXiv 2606.03143): skill library as federation unit; privacy-safe patches/themes beat raw trajectory sharing (+44% success in paper).
2. **Agent Skill Evaluation & Evolution** (arXiv 2606.11435): longitudinal skill quality; drop non-contributing skills; dual-rollout mindset (with/without skill contribution).
3. **MUSE-Autoskill**: lifecycle create → evaluate → demote/refine.
4. Prior Torii F84: per-run skill-hits.json with no durable action.

## Pattern

| Idea | Torii F85 |
|------|-----------|
| Longitudinal fitness | `.torii/skill-fitness.json` selected_n / hit_n / hit_rate |
| Demote zombies | hit_rate < 0.25 after ≥3 samples → index-only (skip full inject) |
| Boost winners | hit_rate × conf → path score delta in F84 router |
| Federated skill themes | F77-shaped signals: skill id + hits + tenant_hash only |
| Privacy | no paths, no raw tenant names, no skill body text in federation |

## Success metric

- Offline fixture: zombie demoted, good boosted, privacy_ok, cycle ingests hits
- Router: demoted ids in `demoted_skipped`, not in `selected` full bodies
- Live: skill_fitness stage after skill_router_score on Modal/local

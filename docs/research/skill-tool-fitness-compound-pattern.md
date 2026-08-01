# F116 research note — Tool-fitness compound (shield + boost + federate)

**Date:** 2026-08-01  
**Fire:** F116

## Sources

1. **Trajectory eval 2026 / Mem2Act:** tool path is first-class quality signal.
2. **FederatedSkill:** share privacy-safe skill themes, not raw trajectories.
3. **SigLeak / contrastive signatures:** portable skill evidence from tool outcomes.
4. **Torii F114/F115:** tool_hit scored and attributed; fitness demote still prose-rate only.

## Gap

`tool_hit_n` was tracked in the fitness ledger but **ignored** for demote, boost weight, and federation tags. Recovery skills that fire via `torii.py memory` could still be zombie-demoted if combined hit_rate dipped. Live post-run also omitted explicit `--agent-loop` for score/attr.

## Pattern

| Layer | Role |
|-------|------|
| F114 score | prose OR tool → hit; writes skill-hits.json |
| F115 attr | LOO credits tool_hit (1.5) |
| F116 demote | `tool_hit_n≥1` → never demote (shield) |
| F116 boost | +0.5×max_boost × tool_hit_rate |
| F116 federate | tags `tool_outcome` + `f116`; `tool_hits` count only |
| Live wire | run-torii-review passes agent-loop/agent-loop.json + agent.log |

## Env

- `TORII_SKILL_FITNESS_TOOL=1` (default)

## Success

- Offline fixture: tool_shielded, tool_in_fed, zombie still demoted
- Live Modal: skill_fitness cycle after score/attr with agent-loop path

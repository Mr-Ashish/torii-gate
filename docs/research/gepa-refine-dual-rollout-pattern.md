# F167 research note — GEPA refine dual-rollout contribution_pp

**Date:** 2026-08-01  
**Fire:** F167

## Sources

1. **SkillsBench** (arXiv 2602.12670): with vs without skills paired eval; self-gen ≈0pp without dual.
2. **Agent Skill Evaluation** (arXiv 2606.11435): dual-rollout protocol = skill contribution signal.
3. **GEPA** (ICLR 2026) + F165/F166: refined bodies need measured contribution_pp, not slogans.
4. Loop Engineering: design the loop, get a score — paper metric next to doctor flags.

## Gap

F165–F166 mutate, gate, floor, and shield refined skills but did not emit a **with-refine vs ablated-refine** dual-rollout paper metric. Without it, GEPA refine effectiveness is unmeasured.

## Pattern

| Layer | Role |
|-------|------|
| `run_refine_dual` | with refine enrich+tools vs ablated strip+weak tools |
| `refine_tool_contribution_pp` | tool_hit_rate delta (paper primary) |
| `refine_probe_delta` | hub_boost / archival probe presence delta |
| hermes soft | refine-dual → refine-dual.json after F166 |
| skill_loop | `refine_dual_ok` |

## Success

- fixture f167_ok; refine_tool_contribution_pp > 0
- Live hermes notice F167; Modal BIT3

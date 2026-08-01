# F118 research note — Tool-aware dual-gate adopt for F117 skills

**Date:** 2026-08-01  
**Fire:** F118

## Sources

1. SkillsBench dual-rollout: contribution_pp > 0 before ship.
2. F88 LOO free-rider gate — F115 tool credit required for tool-only skills.
3. F117 mine/propose product-cli/critic — proposals sat unadopted (attr free-rider).
4. Loop-eng: default REJECT until verifier evidence.

## Gap

F117 wrote proposals + static probes missing for product-cli/critic. `_proposal_attribution` used prose-only LOO → free_rider on silent recovery skills → dual-gate adopt blocked.

## Pattern

| Gate | Role |
|------|------|
| validate_proposal | structure/safety (fitness_gate) |
| F86 dual | pack contribution_pp > 0 |
| F118 tool attr | synthetic allowlisted tool_blob per skill-prefer-* id |
| adopt | copy → agent/skills/active/ |
| smoke | F117 fixture + F118 fixture + active product-cli |

## Success

- Offline: free_without tools; tool_attr_ok; product-cli active
- pytest + smoke pass; Modal BIT3_OK

# F168 research note — Federate refine dual + multi-tenant promote

**Date:** 2026-08-01  
**Fire:** F168

## Sources

1. **FederatedSkill** (arXiv 2606.03143): promote skill themes only when complementary clients agree (min_tenants).
2. **SkillsBench / F167**: refine_tool_contribution_pp is local; without federation it does not compound multi-tenant.
3. F86 promote_skill_themes + F165–F167 GEPA refine stack.
4. Loop Engineering: measure → score → promote only when gate passes.

## Gap

F167 measured refine contribution_pp per run but did not federate bins or multi-tenant promote — write-only dual metrics.

## Pattern

| Layer | Role |
|-------|------|
| federate_refine_dual | skill id + tool_contrib_pp bin + tenant_hash |
| promote_refine_dual_themes | ≥2 tenants, hits, min_pp |
| soft fitness boost | hub_priority_delta for promoted refine skills |
| hermes | promote after refine-dual |

## Success

- fixture f168_ok: multi-tenant promote, single blocked, privacy_ok
- skill_loop refine_promote_ok

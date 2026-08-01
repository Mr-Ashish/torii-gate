# F172 research note — Multi-tenant federate chronic dual_fail decay

**Date:** 2026-08-01  
**Fire:** F172

## Sources
1. FederatedSkill (arXiv 2606.03143): promote only when complementary clients agree.
2. F168 promote of positive refine_pp; F171 local chronic dual_fail decay without multi-tenant compound.
3. Assay: multi-tenant idle evidence should strengthen local demote.

## Gap
F171 decay was tenant-local write-only — multi-tenant chronic dual_fail did not amplify always demotion.

## Pattern
| Layer | Role |
|-------|------|
| federate_refine_dual_decay | fail_rate bin + decay + tenant_hash |
| promote_refine_dual_decay | ≥2 tenants → amplify local decay |
| post_score_refine_dual_hub | loads promoted decay themes |
| hermes | federate+promote after F171 ingest |

## Success
- f172_ok: multi promote, single blocked, privacy_ok, Δprio<0

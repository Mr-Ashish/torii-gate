# F156 research note — Hub-archival util gap critic demote + LOO floor

**Date:** 2026-08-01  
**Fire:** F156

## Sources

1. **Assay** (arXiv 2606.15390): not all skills help — measure idle/negative contribution.
2. Dual-rollout skill contribution (arXiv 2606.11435): with/without skill gap as contribution signal.
3. Torii F121 full recovery util gap demote only when *all* recovery idle; live F155 showed partial util (memory hit, hub-archival idle).
4. F150 recon-warm hub critic + F151 demote-eval paper pack patterns.

## Gap

F155 measures `hub_archival_util_gap` but APPROVE still ships when util_rate=0.5 (other recovery tools fire). Critic and LOO attribution did not act on the hub-archival slice.

## Pattern

| Layer | Role |
|-------|------|
| run_f156_hub_archival_util | checker: inject ∧ ¬hub_boost tools |
| decide_verdict | APPROVE → COMMENT on hub_archival_util_gap |
| demote-eval hub_archival_util_idle_approve | paper demote metric |
| skill_attribution LOO floor | multi-tenant recovery-util hub_archival hits floor contribution |
| skill_loop / doctor | hub_archival_util_critic_ok soft surface |

## Success

- Fixture f156_ok; demote-eval hub_archival_util_idle_demoted
- skill_loop hub_archival_util_critic_ok

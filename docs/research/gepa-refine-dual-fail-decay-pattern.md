# F171 research note — Chronic refine dual_fail always-priority decay

**Date:** 2026-08-01  
**Fire:** F171

## Sources
1. Assay (arXiv 2606.15390): skills with zero/negative effect must be suppressed.
2. F158 chronic hub-archival util gap demote — same longitudinal scorecard for dual_fail.
3. F166 refine shield without expiry left chronic dual_fail always-boosted.
4. Loop Engineering: measure → score → demote zombies under budget.

## Gap
F169 demotes APPROVE per-run on dual_fail; F166 shield + F169 promote boosts left chronic dual_fail skills in always budget across PRs.

## Pattern
| Layer | Role |
|-------|------|
| ingest_refine_dual | dual_pass/fail rates into fitness |
| apply_demotions F171 | chronic fail → demote + lift shield |
| post_score_refine_dual_hub | negative priority_deltas |
| hermes | ingest-refine-dual after F167 |

## Success
- 3 fails → chronic + demoted + Δprio < 0
- skill_loop refine_dual_decay_ok

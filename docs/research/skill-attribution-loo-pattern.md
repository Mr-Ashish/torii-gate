# F88 research note — per-skill LOO attribution

**Date:** 2026-08-01  
**Fire:** F88

## Sources

1. **Not All Skills Help / Assay** (arXiv 2606.15390): retire inert skills; per-task masking.
2. SkillsBench dual aggregate (F86) + adopt gate (F87) — still pack-level free-riders.
3. Ablation LOO as component attribution for trustworthy gates.

## Pattern

| Signal | Meaning |
|--------|---------|
| solo_hit | skill keywords match review alone |
| unique | matches not covered by other selected skills |
| free_rider | no solo_hit and no unique (and not always-on) |
| contribution | 1.0*solo + 0.5*n_unique (floor 0.5 if always) |

Auto-adopt: `f88_zero_attribution` rejects free-riders unless `--force`.

## Success metric

- fixture: contributing ≥1; free-rider proposal contribution=0
- gate includes f88_skill_attribution
- adopt_one blocks free-rider ids

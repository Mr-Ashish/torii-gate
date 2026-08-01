# F165 research note — GEPA-lite skill body refine from util traces

**Date:** 2026-08-01  
**Fire:** F165

## Sources

1. **GEPA** (ICLR 2026 Oral, arXiv 2507.19457): reflective prompt evolution — read full trajectories, diagnose *why* candidates fail, mutate text artifacts under evaluation; outperforms scalar RL with far fewer rollouts.
2. **Hermes Agent Self-Evolution**: DSPy+GEPA skill evolution with constraint gates (pytest, size ≤15KB, semantic preservation) before adopt/PR.
3. Loop Engineering: design the loop, get a score — package measured recovery into skill text that compounds next PR.
4. Mem0 / F155 discipline: inject ≠ utilization — recovery skills that never fire tools are idle prompt cost.

## Gap

F155–F163 measure and re-prompt hub-archival util; F153/F154 propose+adopt skills. Chronic idle still left **skill body text** unchanged — next PR re-spent F108 budget instead of evolving the procedure that failed.

## Pattern

| Layer | Role |
|-------|------|
| `diagnose_util_gaps` | Reflect on recovery-skill-util + fitness ledger (run idle, hub_archival_util_gap, chronic gap_rate) |
| `refine_skill_body` | Deterministic tool-first mutation (no LLM required) |
| `constraint_validate_skill` | Hermes gates: size ≤15KB, id preserved, required tool probes |
| hermes soft wire | After F163 fitness cycle → `refine-from-util --apply` |
| skill-loop | `skill_refine_ok` / `hermes_skill_refine` readiness |

## Success

- Weak hub-archival body fails constraint; after refine passes + marker present
- Fixture `fixture-refine` / `f165_ok`
- Live Modal/local still BIT3 / recall without secrets

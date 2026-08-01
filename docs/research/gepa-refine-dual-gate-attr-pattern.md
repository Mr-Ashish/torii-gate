# F166 research note — GEPA refine dual-gate LOO floor + fitness shield

**Date:** 2026-08-01  
**Fire:** F166

## Sources

1. **GEPA** (ICLR 2026): constraint-gated evolution — mutants only ship after gates.
2. **Hermes Agent Self-Evolution**: size/test constraints before adopt; dual-gate not silent body edit.
3. **Assay** (arXiv 2606.15390): free-rider / inert skills must be measured — but constraint-passed refine is investment, not free-ride.
4. F165 GEPA-lite refine-from-util without attribution/fitness compound left refined skills exposed to LOO demote before next tool hit.

## Gap

F165 mutated skill bodies under constraint gates but did not (a) stamp dual-gate adopt metadata, (b) floor LOO contribution, or (c) shield fitness demote — so free-rider ledger could demote a just-refined recovery skill before contribution_pp compounds.

## Pattern

| Layer | Role |
|-------|------|
| `stamp_dual_gate_refine` | Frontmatter dual_gate: constraint_ok + F166 |
| `federate_refine_skills` | privacy-safe skill-refine-signals.json |
| `ingest_refine` fitness | tool_hit soft sample + demote shield |
| `_load_refined_skills` + LOO floor | contribution ≥0.85, not free_rider |
| hermes soft | ingest-refine + refine-floor --write |

## Success

- fixture f166_ok: silent review + refined skill → refine_floor, not free_rider
- adversarial TORII_SKILL_ATTR_REFINE=0 drops floor
- skill_loop skill_refine_attr_ok

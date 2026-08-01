# F74 research note — SkillOpt / GEPA-lite fitness gate

**Date:** 2026-08-01  
**Fire:** F74

## Sources

1. **SkillOpt** (arXiv 2605.23904v2) — skills as external agent state; bounded add/delete/replace; held-out validation gate; rejected-edit buffer; zero deploy-time LLM cost.
2. **Hermes Agent Self-Evolution** — multi-dim `FitnessScore` + `ConstraintValidator` (size/growth/structure) before adopt; GEPA reads traces.
3. **GEPA / RSEA** — trajectory feedback guides reflective mutation of prompts/skills.
4. **Loop Engineering loop-verifier** — independent checker, default REJECT until evidence.
5. **Memory OSS (Mem0 / Letta / Zep, 2026 surveys)** — selective compound memory; filesystem + tiered memory often enough; port *policy* not full vendor stacks. Torii already has F64 FP rules, F70 TP sigs, F71 federated signals — F74 compounds **procedural** memory (skills) from fitness, not chat vectors.

## Pattern stolen

| Idea | Port into Torii |
|------|-----------------|
| Held-out gate | `validate` default REJECT unless constraints + score |
| Bounded edits | dim-templated skill patches only |
| Rejected-edit buffer | `ledger.rejected_edits` |
| Multi-dim fitness | consume F73 `fitness_signals` weak dims |
| Constraints | size, growth, structure, safety, keyword coverage |

## Non-goals this fire

- LLM-as-judge GEPA optimizer (cost); deterministic templates first
- Auto-adopt in CI by default (`TORII_FITNESS_GATE_AUTO_ADOPT=0`)
- Full Mem0/Zep graph memory

## Success metric

- Offline fixture: weak dims → ≥1 adopt-recommended skill; malicious auto-approve → reject; inject marker present
- Live e2e: cycle runs post-review without breaking pytorch review path

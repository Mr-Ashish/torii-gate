# Research note: Hermes multi-dim fitness + loop-verifier → F73

**Date:** 2026-08-01  
**Sources:** hermes-agent-self-evolution, loop-engineering, H9 trajectory packaging

## Patterns extracted

### 1. Hermes Agent Self-Evolution — fitness on execution traces
- GEPA reads **execution traces** (not only pass/fail) to propose targeted mutations.
- `FitnessScore` dimensions: correctness, procedure_following, conciseness + length_penalty.
- Composite ≈ 0.5·correctness + 0.3·procedure + 0.2·conciseness − penalty.
- Constraint gates (tests, size limits) before adopt.

**Torii mapping:** deterministic multi-dim scorer without LLM-as-judge:
`path_evidence` (0.40) + `procedure` (0.25) + `tool_use` (0.20) + `chain_quality` (0.15).

### 2. Loop Engineering — loop-verifier (independent checker)
- Default REJECT until evidence is strong.
- Checklist: scope, intent, tests, no cheating, risk escalation.
- Separate role from implementer (maker/checker — continues F72).

**Torii mapping:** inject procedure rubric into prompt; score review structure + path cites post-run.

### 3. H9 — trajectory packaging for offline eval
- Slim, redacted, versioned vault for paper/eval.
- INDEX + summary.json always committed; huge agent.log truncated/gitignored.

## Product decision
Ship **F73 trajectory_fitness + trace vault** rather than another detection heuristic:
the agent loop was measurable on *findings* (F70–F72) but not on *procedure fitness*,
and live traces were not paper-indexed under `docs/benchmarks/traces/`.

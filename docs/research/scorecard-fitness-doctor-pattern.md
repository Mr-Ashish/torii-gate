# F135 research note — Scorecard skill fitness ingest + doctor panel

**Date:** 2026-08-01  
**Fire:** F135

## Sources

1. FederatedSkill (arXiv 2606.03143): skill themes as multi-tenant unit — F134 exported themes.
2. CoEvoSkills / EvoSkills: adopted skills without fitness feedback rot (no boost/shield).
3. Hermes multi-dim fitness: ops readiness must soft-blend into local fitness ledger.
4. F126 hub recovery → fitness ingest already existed; scorecard ops did not.

## Pattern

| Layer | Role |
|-------|------|
| F134 federate | scorecard-skill-signals.json (ids + tags) |
| F135 ingest | skill_fitness.ingest_scorecard_skills → ledger tool_hit shield |
| cycle | hits → hub recovery → **scorecard** → demote → federate |
| doctor | scorecard_ops panel (soft; not doctor_pass gate) |
| product scorecard | metrics.scorecard_ops_ok + fitness_ingested_n |

## Env

- `TORII_SKILL_FITNESS_SCORECARD=1` (default)

## Success

- Fixture f135_sc_shielded + privacy_ok; scorecard skill not demoted
- Federate tags include `scorecard_ops` + `f135`
- Doctor surfaces scorecard_ops without failing when idle
- No `/Users/` or raw tenant strings

## Loop-engineering practice

**Measure → federate → fitness → doctor surface** — same as recovery F124/F126, for scorecard ops.

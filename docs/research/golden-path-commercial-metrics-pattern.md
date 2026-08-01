# Pattern: golden path commercial metrics (not F-stack depth)

## Source
- Loop Engineering: design the **customer-visible** loop and score it (time-to-signal, not internal stage IDs).
- Torii priority queue →7.5: install → required check `torii/gate` → real PR dogfood → FP/TP chart.
- AppSec install UX: one doc path beats twenty research F-numbers on the landing surface.

## Steal for Torii
1. Publish `docs/GOLDEN-PATH.md` as the only buyer install→gate path.
2. Aggregate vault dogfood (`timings` + `hermes-usage`) + labeled bench recall into `docs/benchmarks/golden-path-metrics.md`.
3. Keep live OSS verdicts **unlabelled** (verdict distribution only); TP/FP from offline good/weak harnesses.
4. CLI: `torii.py golden-path -- fixture|status|report`.

## Anti-pattern
Shipping F185+ compound loops while `golden-path-metrics.md` is missing — tech score without commercial score.

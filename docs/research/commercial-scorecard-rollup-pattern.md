# Pattern: commercial scorecard rollup (tools-as-code)

## Source
- Loop Engineering: design the loop, get a score — after shipping surfaces, roll them up.
- Priority queue 1–6 landed as separate fixtures; buyers need one overall number.
- Prefer tools-as-code over new compound F-loops when 1–3 already ship.

## Steal for Torii
1. `commercial_scorecard.py` runs golden/buyer/public-eval/install/ops/enterprise fixtures.
2. Heuristic overall_est from baseline 6.6 + weighted lifts (cap 8.5).
3. Publish `docs/benchmarks/commercial-scorecard.md` + CI smoke step.
4. CLI `torii.py commercial`.

## Anti-pattern
Shipping six commercial docs with no single “are we at 7.5?” operator command.

# F164 research note — Hub-archival brand + paper EVAL pack

**Date:** 2026-08-01  
**Fire:** F164

## Sources

1. Loop Engineering: *Stop prompting. Design the loop. Get a score.* — package measured loops as product readiness (doctor/scorecard), not script archaeology.
2. F155–F163 hub-archival stack: util → critic → re-prompt → fitness → hub pressure → inject → `hub_archival_loop_ok`.
3. Mem0 discipline (OSS): memory/skills only help if tools are called — inject ≠ utilization.

## Gap

Doctor/scorecard already computed `hub_archival_loop_ok`, but brand surfaces (PRODUCT, landing, TORII one-liners, scorecard-metrics table) and the paper EVAL vault did not roll F155–F163 into a single customer-facing pack.

## Pattern

| Layer | Role |
|-------|------|
| PRODUCT Mental model D | util→critic→reprompt→fitness→hub inject |
| TORII + landing one-liners | eng + AppSec lines for hub-archival |
| scorecard-metrics.md | all hub_archival_* measured rows |
| EVAL pack f164 | paper table of F155–F163 live Modal proofs |

## Success

- scorecard `hub_archival_loop_ok=True` written to brand md
- PRODUCT + landing mention the loop
- `docs/benchmarks/traces/f164-hub-archival-eval-pack/` paper-ready

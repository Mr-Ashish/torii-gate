# F180 — hub-archival × GEPA compound demote

## Sources
- Loop Engineering: independent checkers miss joint free-rider paths.
- Torii F156 hub-archival util gap + F173–F179 GEPA decay/revive gates run separately.
- FederatedSkill / multi-tenant pressure: dual-loop heat compounds trust failure.

## Insight
APPROVE can survive one weak loop while the other is elevated. Highest ROI: when hub-archival util gap **and** GEPA refine pressure co-occur, demote harder (compound free-rider).

## Ship
- `run_f180_hub_gepa_compound` checker (score 0.15 when both high)
- decide_verdict escalates to REQUEST_CHANGES on compound
- demote-eval `hub_gepa_compound_idle_approve`
- skill_loop `hub_gepa_compound_ok`; refine_loop_ok AND F180
- scorecard paper metric `hub_gepa_compound_idle_demoted`

## Metric
- Offline demote-eval hub_gepa_compound_idle_demoted
- Live Modal BIT3 + hermes F180 notice

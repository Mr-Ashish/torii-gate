# F182 — hub×GEPA compound always priority

## Sources
- F119 always budget + F125/F161/F169 hub priority_deltas compound.
- F181 assess computes priority_deltas but inject alone does not select skills.
- Loop Engineering: measure → inject → budget — close the loop into always slots.

## Insight
Compound free-rider heat without always-budget fuel leaves recovery skills deferred.
Highest ROI: fold assess_hub_gepa_compound deltas into select_skills always ranking.

## Ship
- hub_gepa_compound_always_enabled + hgc_report in select_skills
- _effective_always_prio + residual score bumps when compound high
- skill_loop hub_gepa_compound_always_ok; refine_loop_ok AND F182

## Metric
- Offline: high compound → deltas≥24 + hub-archival in always_selected
- Live Modal BIT3 + hermes F182 notice

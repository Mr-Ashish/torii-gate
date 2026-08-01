# F151 research note — Recon-warm hub demote-eval + doctor surface

**Date:** 2026-08-01  
**Fire:** F151

## Sources

1. F128 recovery hub gap demote-eval paper path.
2. F150 recon-warm hub critic without paper metric / doctor surface.
3. Loop-eng observability: demote rates must be measured offline packs.

## Gap

F150 demotes in panel but EVAL vault lacked `recon_warm_hub_idle_demoted` and doctor/scorecard did not surface `recon_warm_hub_ok`.

## Pattern

| Layer | Role |
|-------|------|
| demote-eval case | recon_warm_hub_idle_approve |
| paper | recon_warm_hub_idle_demoted |
| skill_loop | recon_warm_hub_ok wire |
| doctor/scorecard | soft surface + brand metrics |

## Success

- demote-eval eval_pass with recon_warm demote
- skill-loop scorecard recon_warm_hub_ok=true

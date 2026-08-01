# F162 research note — Hub-archival hub pressure prompt inject + demote-eval

**Date:** 2026-08-01  
**Fire:** F162

## Sources

1. F125 recovery hub inject (privacy-safe skill ids + bins).
2. F161 multi-tenant hub-archival gap_pressure post-score.
3. F151/F156 demote-eval paper packs for multi-tenant idle APPROVE.

## Gap

F161 computed gap_pressure but did not surface it in the agent prompt; paper demote-eval lacked multi-tenant hub-archival pressure case.

## Pattern

| Layer | Role |
|-------|------|
| render_hub_archival_hub_section | F162 markers + hub_boost nudge |
| inject_hub_archival_hub_into_prompt | after F125 recovery hub |
| inject_into_prompt | soft wire |
| demote-eval hub_archival_hub_pressure_idle_approve | paper metric |

## Success

- Fixture f162_ok inject marker + hub_boost text
- demote-eval hub_archival_hub_pressure_idle_demoted

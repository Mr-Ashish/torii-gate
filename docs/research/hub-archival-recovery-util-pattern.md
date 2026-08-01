# F155 research note — Hub-archival recovery util (inject ≠ hub_boost)

**Date:** 2026-08-01  
**Fire:** F155

## Sources

1. **Assay** (arXiv 2606.15390): attribution-based skill selection — skills that don't help must be measured idle.
2. **Agent Skills survey** (arXiv 2605.07358): cost/utility-aware selection under budget.
3. Mem2Act / SkillsBench: always-injected recovery skills must fire tools or they are idle prompt cost.
4. Torii F121–F128 recovery util stack + F154 always adopt of hub-archival.

## Gap

F154 dual-gate cycle-adopted `skill-prefer-hub-archival-early` with always_priority 95, but it was **outside** `RECOVERY_SKILL_IDS`. So F121 util, F122 re-prompt, F124 federate, and F125 hub compound never measured hub-archival inject≠use. Generic `archival_memory_search` also counted as tool_hit without hub_boost evidence.

## Pattern

| Layer | Role |
|-------|------|
| RECOVERY_SKILL_IDS + hub-archival | F155 membership |
| hub-boost-strict TOOL_OUTCOME_PROBES | generic archival alone insufficient |
| score_recovery_util hub_archival_* | slice util_gap / tool_hit |
| federate tags hub_archival/f155 | multi-tenant warm paging util |
| skill_loop + doctor soft | readiness surface |
| re-prompt suffix F155 | nudge hub_boost archival |

## Success

- Fixture f155_ok; hub-boost probe match; generic archival not enough
- skill_loop hub_archival_util_ok when active skill present
- Privacy: tenant hashes only in federate signals

# F157 research note — Hub-archival util soft re-prompt under F108

**Date:** 2026-08-01  
**Fire:** F157

## Sources

1. Assay / Mem2Act: idle always skills are free-riders; recover before demote.
2. Torii F122 recovery util re-prompt + F108 shared budget.
3. Live F155/F156: partial util (memory hit, hub-archival idle) skipped F122 full-gap re-prompt; only critic demote after the fact.

## Gap

F156 demotes APPROVE when hub-archival util gaps, but does not give the agent a paid recovery turn to fire hub_boost archival. F122 only re-prompts when *all* recovery tools are idle.

## Pattern

| Layer | Role |
|-------|------|
| decide_recovery_reprompt | hub_archival_util_gap → reprompt=1, budget_kind=f157 |
| F108 KINDS | f157 shares max_extra with f49/f106/f122/… |
| build_recovery_reprompt_suffix | F157 title + hub_boost archival nudge |
| run-hermes-review | allow/consume kind=f157; pass ha_gap to reprompt-write |

## Success

- Fixture f157_ok; partial util re-prompts; tool_hit ok does not; zero tools defers F49
- skill_loop hub_archival_reprompt_ok

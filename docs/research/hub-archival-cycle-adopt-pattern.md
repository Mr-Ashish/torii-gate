# F154 research note — Hub-archival cycle-adopt + F119 always priority

**Date:** 2026-08-01  
**Fire:** F154

## Sources

1. F118 dual-gate adopt for skill-prefer-*.
2. F119 always budget (max 3 full-body slots by priority).
3. F153 proposal skill-prefer-hub-archival-early without active adopt.

## Gap

Proposals do not inject. Without cycle-adopt + always_priority, hub-archival never enters the recovery always budget.

## Pattern

| Layer | Role |
|-------|------|
| ensure_hub_archival_proposal | durable proposal body |
| cycle_hub_archival | dual-gate / force adopt |
| always_priority 95 | F119 rank under memory |
| hermes soft | F152 → cycle-hub-archival |

## Success

- Fixture f154_ok; active skill always:true prio 95
- Router ALWAYS_PRIORITY_DEFAULT includes hub-archival

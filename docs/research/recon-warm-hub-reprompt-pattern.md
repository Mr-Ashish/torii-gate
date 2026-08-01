# F152 research note — Recon-warm hub soft re-prompt (F108)

**Date:** 2026-08-01  
**Fire:** F152

## Sources

1. F108 shared re-prompt budget (F49/F106/F122/F137).
2. F150/F151 critic demote when hub heat ignored.
3. F122 recovery re-prompt: demote-only leaves no second chance under budget.

## Gap

F150 demotes APPROVE after the fact. Without a budgeted soft re-prompt, agents never get one paid chance to honor multi-tenant warm themes mid-run.

## Pattern

| Layer | Role |
|-------|------|
| should_reprompt_recon_warm | high heat + local_idle + tool_turns≥1 |
| F108 kind=f152 | shared max_extra attempt |
| reprompt-write | F152 prompt nudge |
| hermes wire | soft second pass when budget allows |

## Success

- Fixture f152_ok: gap→reprompt=1; already/zero-tool→0; write marker
- TORII_RECON_WARM_REPROMPT=1

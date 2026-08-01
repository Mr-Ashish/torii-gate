# F108 research note — Shared soft-re-prompt budget

**Date:** 2026-08-01  
**Fire:** F108

## Sources

1. Agent cost guides 2026: multi-turn re-prompts roughly double LLM spend.
2. Braintrust / Portal26: kill switches + attempt ceilings per agent run.
3. Torii F49 + F106: two independent soft re-prompts stacked to 2× DeepSeek cost.

## Pattern

| Knob | Default | Meaning |
|------|---------|---------|
| `TORII_REPROMPT_MAX_EXTRA` | 1 | max paid soft re-prompts after first Hermes |
| `TORII_REPROMPT_BUDGET` | 1 | master on/off |
| allow(kind) | once per kind within remaining | F49 then F106 cannot both fire at max=1 |

## Success

- fixture: max=1 allows first blocks second; max=2 allows both; max=0 blocks all
- `run-hermes-review.sh` init + allow before F49/F106 + consume on attempt

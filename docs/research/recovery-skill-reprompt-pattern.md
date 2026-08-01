# F122 research note — Recovery skill soft re-prompt (F108 budget)

**Date:** 2026-08-01  
**Fire:** F122

## Sources

1. Mem2Act / F106: utilization gap → soft re-prompt once.
2. F108 shared max_extra: F49 + F106 + F122 cannot stack unbounded paid retries.
3. F121: measure recovery util_rate / gap after always inject.

## Pattern

| Stage | Role |
|-------|------|
| score + util | post-Hermes skill_hits + recovery-skill-util.json |
| reprompt-decide | gap ∧ tool_turns≥1 ∧ not already → reprompt=1 |
| F108 allow f122 | shared budget slot (default max_extra=1) |
| reprompt-write | nudge doctor/memory/critic CLIs into prompt |
| re-run Hermes | score util again; recovered if tool_hit_n≥1 |

## Env

- `TORII_RECOVERY_SKILL_REPROMPT=1`
- `TORII_REPROMPT_MAX_EXTRA=1` (shared)

## Success

- Offline: decide reprompt=1 on gap; budget blocks f122 after f49; fixture_pass
- Live Modal: soft path; may budget_block if F106 already spent slot

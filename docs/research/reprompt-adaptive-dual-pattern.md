# F159 research note — Adaptive dual-recovery re-prompt slot

**Date:** 2026-08-01  
**Fire:** F159

## Sources

1. Agent cost guides: shared attempt caps prevent multi-kind re-prompt burn.
2. Live F157: F106 memory util re-prompt consumed max_extra=1 → hub-archival F157 never fired.
3. Loop Engineering: budgeted recovery before demote, but dual independent gaps need dual budget.

## Gap

F108 default max_extra=1 is correct against runaway stacks, but memory util (f106) and hub-archival util (f157) are **complementary** recoveries — blocking the second loses hub_boost recovery.

## Pattern

| Layer | Role |
|-------|------|
| complementary_kinds | memory ↔ recovery/hub-archival/recon |
| ensure_adaptive_slot | once: max_extra += bonus when complement used base |
| decide_allow | reason=adaptive_within_budget |
| hermes | notice F159 when adaptive_expanded |

## Success

- Fixture f159_ok: f106→f157 allow; adaptive once; off blocks; reverse f157→f106
- f49 still does not unlock adaptive (zero-tool separate)

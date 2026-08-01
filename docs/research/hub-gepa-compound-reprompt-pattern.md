# F183 — hub×GEPA compound re-prompt budget slot

## Sources
- F108/F159 shared re-prompt budget + complementary adaptive slot.
- F180–F182 dual-loop compound heat without recovery re-prompt fuel after f49 burn.
- Agent cost guides: selective dual-recovery, not unbounded multi-reprompt.

## Insight
Base max_extra=1 + f49/f106 can exhaust before hub-archival util recovery. F159 only unlocks via complementary kinds. Highest ROI: when hub×GEPA compound high, grant one f157/f122 compound slot.

## Ship
- `ensure_compound_slot` + TORII_REPROMPT_COMPOUND
- decide_allow reason `compound_within_budget`
- fixture f183_ok; refine_loop_ok AND F183

## Metric
- Offline: f49 then f157 allow under compound high; off blocks
- Live Modal BIT3 + hermes F183 notice

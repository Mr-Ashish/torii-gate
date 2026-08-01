# F106 research note — Soft re-prompt on memory utilization gap

**Date:** 2026-08-01  
**Fire:** F106

## Sources

1. F49/H15 tool-turns soft re-prompt (Torii): second attempt when zero tools on multi-file.
2. F105 memory tool audit: measures inject-offered-but-unused gap.
3. Mem2ActBench / MemoryAgentBench: memory value is **proactive use**, not passive inject.
4. Loop-eng: close the loop with a recoverable stage, not only a scorecard.

## Pattern

| Case | Owner |
|------|--------|
| tool_turns==0 multi-file | F49 re-prompt |
| tool_turns≥1 ∧ inject ∧ memory_hits==0 | **F106** memory re-prompt |
| already memory-reprompted | skip |

## Success

- fixture: weak → reprompt=1; good → 0; zero tools → defer_f49; write has torii_memory cmds
- `run-hermes-review.sh` stage after F49 writes `memory-tool-reprompt.env`

# F105 research note — Mid-review memory tool utilization audit

**Date:** 2026-08-01  
**Fire:** F105

## Sources

1. **IFCMemoryBench** (arXiv 2607.26072): memory eval = ingestion · retrieval · **utilization**.
2. **WorldMemArena**: write / maintain / retrieve / **use** decomposition.
3. Loop-eng: score the loop; do not assume SOUL prose was followed.
4. Torii F103/F104: front door + compound write shipped; utilization unmeasured.

## Pattern

| Stage | Artifact |
|-------|----------|
| scan | agent-loop tool args + agent.log for `torii_memory.py` / memory scripts |
| score | 0–1 utilization; `utilization_gap` when inject offered but unused |
| blend | soft weight into trajectory fitness composite |
| inject | prompt rubric so Hermes knows it is graded |

## Success

- fixture: good score ≫ weak; gap detected when inject unused
- stage `memory_tool_audit` after traj_fitness
- `torii_memory.py audit` dispatch

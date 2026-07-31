# Product feature progress

**Updated:** 2026-08-01 (F68 agent tools + F69 self-evolution)  
**Loop:** continuous product backlog

## SHIPPED

| ID | Feature | Type | Notes |
|----|---------|------|-------|
| F44–F61 | Agent quality + product suite | agent_quality, product | through testplan |
| F62 | FP resolve + memory update | product, memory | MERGED PR #12 |
| F63 | Domain packs milvus/go/cpp + auto | product, agent_quality | MERGED PR #14 |
| F64 | Durable fp-rules.json self-learn | product, memory | MERGED PR #15 |
| F65 | Multi-tenant federated hub memory | product, memory | MERGED PR #16 |
| F66 | Modal default prod live e2e host | product, ops | MERGED PR #16 |
| F67 | Modal live Hermes/orch log streaming | product, ops | MERGED `0.8.0-f67` |
| F68 | Agent tools research→eval→adopt | product, agent_quality | **shipping** |
| F69 | Torii-native self-evolution (skills) | product, memory | **shipping** |

## IN_PROGRESS

| ID | Feature | Notes |
|----|---------|-------|
| — | — | named product backlog complete |

## LEFT

— (named product backlog empty; future fires = corpus/e2e or new research)

## Counts

- **features_built_count:** 26 (F44–F69)
- **types_built:** agent_quality, product, memory, ops
- **left_count:** 0 named
- **progress_pct:** ~100% of listed backlog
- **eta:** open research only
- **active_worktrees:** none
- **federated_memory_note:** F65 tenant path
- **agent_design_note:** F68/F69 pure code I/O; judgment stays in model + human adopt gates
- **meta_loop_note:** research→eval→adopt + trajectory skills close Hermes-pattern gaps natively
- **milvus_corpus:** 3 + complex #6 F67 e2e

## Status line

`features_built_count=26 types_built=agent_quality,product,memory,ops left_count=0 progress_pct=100 active_worktrees=0 f68=tools_pipeline f69=self_evolve`

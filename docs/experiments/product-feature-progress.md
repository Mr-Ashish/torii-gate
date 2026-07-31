# Product feature progress

**Updated:** 2026-08-01 (F70 labeled bench + dual critic + TP memory)  
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
| F70 | Labeled vuln bench + dual critic + TP sigs | agent_quality, memory, bench | **shipping** |

## IN_PROGRESS

| ID | Feature | Notes |
|----|---------|-------|
| — | — | open: Juice Shop vendor corpus, live dual-agent critic LLM |

## LEFT

— Juice Shop full cases; federated TP aggregate across tenants; LLM critic pass

## Counts

- **features_built_count:** 27 (F44–F70)
- **types_built:** agent_quality, product, memory, ops, bench
- **left_count:** open research
- **progress_pct:** n/a (open research loop)
- **eta:** open research only
- **active_worktrees:** none
- **federated_memory_note:** F65 tenant path; F70 TP local (federation of TP next)
- **agent_design_note:** F70 dual-pass offline critic; live LLM critic optional
- **meta_loop_note:** bench metrics close the measure→promote→inject loop
- **milvus_corpus:** 3 + complex #6 F67 e2e

## Status line

`features_built_count=27 types_built=agent_quality,product,memory,ops,bench f70=bench_dual_critic_tp`

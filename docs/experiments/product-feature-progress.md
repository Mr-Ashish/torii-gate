# Product feature progress

**Updated:** 2026-08-01 (F73 trajectory fitness + eval-trace vault)  
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
| F71 | Taint prefilter + federated sanitized signals | agent_quality, tools, memory | **shipping** |
| F72 | Full-chain revalidation maker/checker | agent_quality, tools, bench | **shipping** |
| F73 | Trajectory fitness + paper-safe trace vault | agent_quality, memory, bench, tools | **shipping** |
| F74 | Fitness-gated skill evolution (SkillOpt/GEPA-lite) | agent_quality, memory, tools | **shipping** |
| F75 | Scoped memory recall (Mem0 multi-scope TP/FP) | memory, agent_quality, tools | **shipping** |
| F76 | Multi-corpus bench + Juice Shop synthetic | bench, agent_quality, tools | **shipping** |
| F77 | Cross-tenant hub federated signal ingest | memory, product, tools | **shipping** |
| F78 | Multi-checker second-agent critic panel | agent_quality, product, tools | **shipping** |
| F79 | Workflows-as-code + install capability guide | product, ops, tools | **shipping** |

## IN_PROGRESS

| ID | Feature | Notes |
|----|---------|-------|
| — | — | open: optional LLM critic atop F78; real Juice Shop pin; Modal secrets for live logs |

## LEFT

— Optional real Juice Shop pin; optional LLM critic atop F78; Modal secrets for streaming

## Counts

- **features_built_count:** 36 (F44–F79)
- **types_built:** agent_quality, product, memory, ops, bench, tools
- **left_count:** open research
- **progress_pct:** n/a (open research loop)
- **eta:** open research only
- **active_worktrees:** none
- **federated_memory_note:** F65–F71–F75 local; F77 hub multi-tenant aggregate + promote gate
- **agent_design_note:** F70–F77 gates/memory/federation; F78 multi-checker second-agent panel
- **meta_loop_note:** measure findings → chain gate → trajectory fitness → paper vault
- **milvus_corpus:** 3 + complex #6 F67 e2e

## Status line

`features_built_count=36 types_built=agent_quality,product,memory,ops,bench,tools f79=workflow_as_code`

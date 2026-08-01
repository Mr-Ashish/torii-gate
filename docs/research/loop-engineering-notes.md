# Loop Engineering notes (meta → product)

Source: [cobusgreyling/loop-engineering](https://github.com/cobusgreyling/loop-engineering) (cloned under `../loop-engineering`).

## Practice applied this fire — Maker / Checker split + scorecard

From `docs/loop-design-checklist.md` §4 **Maker / Checker Split** and §9 **Observability**:

1. **Implementer and verifier are separate** — the agent (maker) drafts findings; a deterministic checker must not be the same pass that invented them.
2. **Implementer cannot mark its own work done** — REQUEST CHANGES should require chain evidence the checker can recompute offline.
3. **Success metrics / readiness score** — Loop Ready style scorecard (`passed/total` + level L0–L3), not only prose.

### How applied (F72)

| Loop-eng concept | Torii product mapping |
|------------------|----------------------|
| Maker | Hermes review agent (draft findings, verdict) |
| Checker | `scripts/chain_revalidate.py` — offline, no LLM |
| Verifier isolation | Pure function over `review.md` + F71 taint candidates |
| Scorecard | `chain_revalidate scorecard` → `pct` + `level` (L0–L3) |
| Run log | Append-only `docs/research/log.md` this fire |

Checker confidence ladder: `full_chain` → `theme_path` → `path_only` → `unvalidated` / `likely_fp`.

Only `full_chain` and `theme_path` may drive blocking (`keep_for_blocking`).

Also mirrored from LOOP.md budget/observability: each fire records metrics (recall, full_chain_rate, live e2e) rather than shipping unmeasured prompt text.

## Prior fires (brief)

- F70/F71 used eval-first + compound memory; F72 adds the **separate checker role** those benches lacked as a named gate.
- F135: scorecard skill fitness ingest (FederatedSkill themes → ledger shield) + doctor panel
- F136: scorecard skill util (inject≠use) + federate + f136 critic demote
- F137: scorecard util soft re-prompt (F122-style) under F108 budget
- F138: scorecard hub post-score → select priority (F125-style for ops skills)
- F139: scorecard hub gap critic demotes APPROVE (F127 mirror for ops)
- F140: scorecard hub LOO attribution floor (F127 mirror for ops skills)
- F141: memory util federate + critic demote (Mem0/Letta tools-must-be-called)
- F142: memory util hub post-score → memory skill priority (F125 mirror)
- F143: memory hub gap critic demotes APPROVE (F127/F139 mirror for Mem0 util)
- F144: temporal multi-hop themes expand archival auto → core promote (MemGPT+Zep)
- F145: supersede-aware archival promote (MemoTime temporal faithfulness on F144 paging)
- F146: archival reconsolidation on promote (retrieval warms durable TP store)
- F147: recon-warm → core tier promote (F146 timestamps compound into F97 core budget)
- F148: recon-warm theme federate + hub post-score (multi-tenant retrieval heat)
- F149: hub warm themes expand archival auto-query + hit boost (cross-tenant page)
- F150: recon-warm hub critic demotes APPROVE when multi-tenant heat ignored
- F151: recon-warm hub demote-eval paper metric + doctor/scorecard surface
- F152: recon-warm hub soft re-prompt under F108 (budgeted recovery before demote-only)
- F153: F152 signals propose hub-archival skill + dual-gate tool blob (compound next PR)
- F154: cycle-hub-archival adopt + always_priority 95 under F119 budget
- F155: hub-archival joins recovery util stack (Assay inject≠use + F121) — always skill measured for hub_boost tool outcomes; federate multi-tenant util themes
- F156: hub-archival util gap critic demote APPROVE (partial recovery idle) + LOO floor from federated hub_archival hits (Assay)
- F157: hub-archival util soft re-prompt under F108 (recover hub_boost before F156 demote-only)
- F158: hub-archival util fitness demote/boost (chronic inject≠hub_boost compounds into ledger)
- F159: F108 adaptive dual-recovery slot (f106↔f157) — one bonus when complementary kind used base
- F160: skill-router synth for bench live (always recovery inject measurable when assemble skipped)
- F161: multi-tenant hub-archival gap_pressure post-score → always prio + F157/F156 bias
- F162: inject hub-archival hub pressure into prompt + demote-eval paper metric

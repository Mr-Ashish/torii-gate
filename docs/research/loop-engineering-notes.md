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

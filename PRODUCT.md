# Torii Gate — product brief

## One sentence
Torii Gate is a PR/CI **security merge authority**: agent review with tools, path-evidenced findings, maker/checker critics, and compound skill+memory loops — so AI-written code does not merge unguarded.

## Tagline
**Nothing ships without crossing the gate.**

## ICP (who buys)

| Persona | Pain | Why Torii |
|---------|------|-----------|
| **Platform / DevEx eng** | Need a required check that is honest, not chatty | Install pack → `@torii review` → labels/block |
| **AppSec eng** | SAST noise + AI PR volume | Maker agent + deterministic checker; FP/TP memory |
| **Security-minded eng lead** | AI code without a security owner | Evidence-backed REQUEST_CHANGES, not nits |

**Not ICP (v1):** full ASPM buyers, red-team agencies, teams that only want style comments.

## v1 scope
- GitHub comment trigger `@torii review this pr`
- Security pack default + progressive skills
- Comment + labels (`torii/*`)
- Local `.torii/` memory (FP, TP, fitness, skill attribution)
- Redacted traces as paper/eval artifacts; Modal live with log streaming

## Non-goals (v1)
- Full ASPM dashboard
- Autonomous offensive red team
- Auto-merge patches without human

## Success metrics
- Time-to-first-signal on PR
- Measured FP rate (memory growth of suppressions)
- PRs blocked with path-evidenced findings
- Skill contribution_pp > 0 (dual-rollout) before auto-adopt

---

## Mental model A — Maker / Checker (F78)

**Maker.** Hermes agent runs tools on the PR and writes a security review.

**Checker.** A deterministic second-agent panel (path evidence, chain revalidation, trajectory fitness, scoped memory, optional LLM critic) re-scores every run and demotes weak APPROVE without path evidence — default path is free (no extra LLM).

**Measured gate.** Multi-corpus labeled benches score recall before shipping harness changes.

---

## Mental model B — Skill compound loop (F84–F89)

Torii does not dump a static SOUL forever. Skills are **measured, ranked, and retired**:

```text
route → hit → fitness → dual → attr → inject
  │       │       │        │      │       └─ next PR: full bodies only for winners
  │       │       │        │      └─ LOO free-riders blocked at adopt + inject
  │       │       │        └─ with vs ablated contribution_pp must be > 0
  │       │       └─ hit-rate ledger demotes zombies
  │       └─ post-run keyword hit score
  └─ progressive: index all, full body for path themes
```

| Stage | What ships | Customer-facing meaning |
|-------|------------|-------------------------|
| **Route** | Progressive skill router | Relevant discipline, not context spam |
| **Hit** | skill-hits.json | Did the review actually use the skill? |
| **Fitness** | skill-fitness ledger | Unused skills go index-only |
| **Dual** | SkillsBench-style with/ablated | Skills must beat a no-skill baseline |
| **Attr** | LOO + unique keywords | Free-riders cannot bulk-adopt |
| **Inject** | Attribution-ranked inject | Next PR prefers proven skills |

**One-liner (eng):** *Skills that do not contribute do not ship in the next prompt.*

**One-liner (AppSec):** *The gate gets stricter and quieter over time — not noisier.*

---

## Mental model C — Memory compound loop (F93–F104)

Torii does not dump every past finding into the next prompt. Memory is **written with integrity, events, consolidated, strength-ranked, tiered, and paged on demand**:

```text
compound → write → consolidate → effective_critic → federate → scoped_recall → tiers → archival_search
  │          │         │               │              │            │            │           └─ cold hits → core
  │          │         │               │              │            │            └─ core (hot) vs archival (cold)
  │          │         │               │              │            └─ path/scope/effective inject budget
  │          │         │               │              └─ privacy-safe multi-tenant strength signals
  │          │         │               └─ confirm TP only above effective floor (stale ≠ precision)
  │          │         └─ importance × half-life; merge near-dups; evict dead noise
  │          └─ ADD/UPDATE/DELETE/NONE; path FP supersedes overlapping TP
  └─ post-review path-evidenced findings only; reject poison / pathless
```

| Stage | What ships | Customer-facing meaning |
|-------|------------|-------------------------|
| **Compound** | memory_compound_write (F104) | Live reviews grow TP store safely |
| **Write** | memory_event_policy | Same FP does not resurrect after resolve |
| **Consolidate** | memory_consolidate | Store stays lean (merge/decay/evict) |
| **Effective critic** | dual_pass + floor | Stale TP cannot inflate “confirmed” |
| **Federate** | hub signals | Orgs share themes without paths/snippets |
| **Scoped recall** | path + effective rank | Prompt budget prefers this PR’s files |
| **Tiers** | core / archival | Hot always in; cold stays cold |
| **Archival search** | just-in-time promote | Cold knowledge pages in when paths match |

**One-liner (eng):** *Stale memory does not confirm findings or crowd the inject budget.*

**One-liner (AppSec):** *False positives die twice — and true positives stay sharp.*

**Temporal graph (F100–F102).** Zep-style edges (`supersedes`, `same_theme`, `co_path`) with `valid_from` / `valid_until`. Dual-pass critic **demotes findings that match actively superseded TPs**, with **multi-hop** path kinship (co_path/same_theme) so sibling files inherit resolve caution.

**Agent front door (F103):** `python3 scripts/torii_memory.py help|search|graph|loop|compound|doctor` — one CLI for Hermes/terminal over the whole memory stack.

**Integrity compound (F104):** after each review, only path-evidenced findings become durable TP signatures (provenance + no absolute-home/secret blobs); weak narrative never poisons the store.

**Ops:** `python3 scripts/memory_loop_status.py scorecard` → L0–L3. Smoke requires L3 on the hub tree. CI job summary annotates readiness; optional advisory `torii/memory-loop` via `TORII_MEMORY_LOOP_STATUS_COMMIT=1`.

---

## Self-evolution (F82 + F87/F88)

Validated skill proposals enter `agent/skills/active/` only after offline regression gates (critic + fitness + dual contribution + per-skill attribution). Default off (`TORII_SKILL_AUTO_ADOPT=0`). Force exists for emergencies; product default is REJECT until measured.

---

## Positioning (vs market 2026)

| We are | We are not |
|--------|------------|
| Security merge authority on every PR | Generic AI code-review chatbot |
| Maker + checker + compound skills/memory | SAST dump with an LLM veneer |
| Evidence + measured contribution | “Zero false positives” theater |
| Pipeline-native AppSec (install pack) | Day-one ASPM suite |

## Skill loop readiness (F91/F92)

Ops scorecard: `python3 scripts/skill_loop_status.py scorecard` → L0–L3 for
`route → hit → fitness → dual → attr → inject`. Embedded in install-guide and
`workflow_as_code.py scorecard`. **Smoke** requires L3 on the hub tree.
CI job summary annotates readiness; optional advisory commit status
`torii/skill-loop` via `TORII_SKILL_LOOP_STATUS_COMMIT=1` (never the merge gate —
that remains `torii/gate`).

## Live proof
Modal + Hermes + DeepSeek V4 Pro on real open-source PRs (e.g. pytorch), `POST_COMMENT=0` for dogfood, log streaming to Modal UI, redacted traces under `docs/benchmarks/traces/`.

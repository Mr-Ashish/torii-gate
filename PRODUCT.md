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

**Compound memory (F93–F97).** Write-path Mem0-style events (ADD/UPDATE/DELETE/NONE): path-anchored FP can supersede overlapping TP so deleted noise does not resurface. Maintenance pass consolidates with **importance × half-life decay**, merges near-dup themes, and evicts stale low-value items. Dual-pass critic **confirms TP only above effective floor**; privacy-safe **effective_score** themes federate and **rank inject**. **Letta-style tiers:** core (path/high-eff) always injects; archival stays cold. Ops: `memory_loop_status` L0–L3 + CI job summary.

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

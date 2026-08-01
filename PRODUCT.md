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

## Mental model C — Memory compound loop (F93–F108)

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

**Product front door (F110):** `python3 scripts/torii.py help|status|doctor|memory|gate|budget` — loop-eng-style umbrella; memory still available as `torii_memory.py` (F103).

**Agent memory front door (F103):** `python3 scripts/torii_memory.py help|search|graph|loop|compound|audit|doctor` — memory stack for Hermes/terminal.

**Integrity compound (F104):** after each review, only path-evidenced findings become durable TP signatures (provenance + no absolute-home/secret blobs); weak narrative never poisons the store.

**Utilization audit (F105):** mid-review memory tool calls (search/graph/…) are **scored** from the agent loop — inject offered but unused is a measured gap, soft-blended into trajectory fitness.

**Memory soft re-prompt (F106):** when tools ran but memory CLI was never called despite inject, Hermes gets **one** soft re-prompt (F49-style) to call `torii_memory search|graph` before finalizing — zero-tool recovery stays F49.

**Integrity federate (F107):** path-evidenced compound TPs export as **privacy-safe hub signals** (theme/CWE/keywords/basenames + tenant hash only) so multi-tenant learning compounds without snippets or home paths.

**Re-prompt budget (F108):** F49 (zero-tool) and F106 (memory gap) share a **max paid retry** (default 1). Quality recovery stays available; double Hermes spend does not stack by default.

**Self-evolve adopt (F112/F113):** F106 recovery signals propose `skill-prefer-memory-cli-early`; dual-gate (F86 contribution + F88 attribution + regression) adopts into `active/` so the next PR calls memory tools **before** burning the re-prompt budget.

**Skill tool outcomes (F114):** adopted skills that teach CLI calls are scored on **agent-loop invocations** (e.g. `torii.py memory`, `torii_memory.py`), not review prose alone — F105 also counts the F110 product CLI as memory utilization.

**Tool-aware attribution (F115):** dual-rollout and LOO attribution credit **tool_hit** (weight 1.5) so recovery skills that only fire in the terminal are not free-rider demoted; durable ledger tracks `tool_hits` for router ranking.

**Tool-fitness compound (F116):** fitness ledger **shields** skills with `tool_hit_n≥1` from zombie demote, adds tool boosts for next inject, and federates privacy-safe `tool_outcome` themes; post-run score/attr pass explicit agent-loop paths.

**Tool-probe self-evolve (F117):** allowlisted CLI patterns observed mid-review are mined into `.torii/tool-outcome-probes.json` (merged by F114 scoring) and can propose `skill-prefer-product-cli` / `skill-prefer-critic-early` — no free-form regex from logs.

**Tool dual-gate adopt (F118):** F117 product-cli/critic proposals adopt only when tool-aware attribution (synthetic allowlisted tool_blob) proves contribution — free-riders without tools stay proposals; active skills ship after dual+attr gates.

**Always-on budget (F119):** full-body inject is capped (`TORII_SKILL_ROUTER_ALWAYS_MAX=3`); recovery skills (memory → product-cli → critic) outrank soft always (tool-depth/preserve) so F118 skills ship in the prompt without context bloat (SkillReducer).

**Always body compact (F120):** SkillReducer-lite keeps actionable steps/code under `TORII_SKILL_ALWAYS_MAX_CHARS` (default 480) on inject; pack install verifies memory/product-cli/critic active skills ship.

**Recovery skill utilization (F121):** post-run measure inject_chars + tool_hit for always recovery skills; idle recovery tools set utilization_gap and soft-demote APPROVE in the second-agent critic panel.

**Recovery soft re-prompt (F122):** on F121 gap with tool_turns≥1, soft re-prompt once under shared F108 budget (kind `f122`) to force doctor/memory/critic CLIs.

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

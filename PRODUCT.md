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
- Skill contribution before auto-adopt (must beat baseline)

---

## How Torii works (buyer)

**Primary story:** *The gate gets stricter and quieter over time — not noisier.*

One diagram (full write-up: [`docs/brand/BUYER-DIAGRAM.md`](docs/brand/BUYER-DIAGRAM.md)):

```text
  PR / CI ──► TORII GATE ──► merge signal (torii/gate)
                 │
     1. REVIEW + CHECK     tools on the diff; demote empty APPROVE
     2. COMPOUND           skills that measure in · memory that pages in
     3. MERGE SIGNAL       required check · labels · comment
                 │
                 ▼
        next PR is quieter and sharper
```

| Beat | Buyer language |
|------|----------------|
| **Review + check** | Agent reads the change with tools; a second pass kills weak approvals |
| **Compound** | Every run teaches the next — useful skills stay, false positives die twice |
| **Merge signal** | Branch protection requires **`torii/gate`** |

Install path: [`docs/GOLDEN-PATH.md`](docs/GOLDEN-PATH.md) · metrics: [`docs/benchmarks/golden-path-metrics.md`](docs/benchmarks/golden-path-metrics.md).

**Gate certificate:** every open/close of **`torii/gate`** ships reason codes + path evidence (tools-as-code, not chat) → [`docs/GATE.md`](docs/GATE.md) · `python3 scripts/torii.py certificate -- fixture`.

**Enterprise light:** multi-tenant org isolation + federation privacy (themes only — no paths/snippets) → [`docs/enterprise/`](docs/enterprise/).

**CLI:** `python3 scripts/torii.py help` · `doctor` · `golden-path -- status` · `certificate -- fixture` · `enterprise -- status`

> **Advanced** content below (mental models A–E, feature IDs, loop stage tables) is for engineers and research. Buyers can stop here.

---

## Advanced — mental models & research IDs

Feature numbers (Fnn) are **implementation / paper IDs**, not marketing. Prefer the buyer diagram above on landing and sales decks.

### A — Maker / Checker

**Maker.** Hermes agent runs tools on the PR and writes a security review.

**Checker.** A deterministic second-agent panel (path evidence, chain revalidation, trajectory fitness, scoped memory, optional LLM critic) re-scores every run and demotes weak APPROVE without path evidence — default path is free (no extra LLM).

**Measured gate.** Multi-corpus labeled benches score recall before shipping harness changes.

---

### B — Skill compound loop

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

### C — Memory compound loop

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

---

### D — Recovery skill loop (research IDs in body)

Always-on recovery skills teach terminal CLIs. Torii does not stop at inject:

```text
budget always → compact body → score tool_hit → util gap? → budgeted re-prompt → archive
```

| Stage | What ships | Customer-facing meaning |
|-------|------------|-------------------------|
| **Always budget** | F119 max 3 slots | Recovery outranks soft always skills |
| **Compact** | F120 SkillReducer-lite | Less context tax, same action rules |
| **Util** | F121 recovery-skill-util.json | Inject without tools is a measured gap |
| **Re-prompt** | F122 under F108 | One paid recovery attempt, not two |
| **Traces** | F123 save-trace + scorecard | Paper-ready inject_chars / util_rate |

**One-liner (eng):** *Always skills that never call their CLI do not silently APPROVE.*

**One-liner (AppSec):** *The gate teaches tools, measures use, and recovers once — under budget.*

**Federate + doctor (F124):** privacy-safe recovery util themes (skill id + util bins + tenant hash only) federate to the hub; `torii.py doctor` fails closed unless recovery skills are active (`recovery_ok`).

**Hub recovery compound (F125):** federated recovery-util themes are post-scored into always-priority deltas and a privacy-safe prompt section (`hub-score` / inject) so multi-tenant tool hits compound into the next run's recovery skill budget — not write-only federation.

**Hub gap re-prompt + fitness (F126):** multi-tenant `gap_pressure` biases F122 soft re-prompt when recovery tools are only partially used (idle skill ids), and hub tool-hit themes soft-ingest into the skill fitness ledger (demote shield + boost) under the shared F108 budget.

**Hub gap critic + hub attribution (F127):** second-agent critic panel weights multi-tenant recovery gap pressure (`f127_hub_gap`) and demotes weak APPROVE when hub gap is high and recovery tools are idle; skill attribution floors hub_ingested fitness skills so multi-tenant tool evidence is not free-rider demoted.

**Doctor + demote-eval (F128):** `torii.py doctor` fails closed without `recovery_hub_gap_ok` (f127 critic + demote-eval wire); `second_agent_critic demote-eval` emits paper metric `critic_approve_demote_rate` on good/weak/hub-gap cases for EVAL vault.

**Product scorecard (F129):** `python3 scripts/torii.py scorecard` aggregates doctor + skill/memory loop levels + demote-eval into brand/ops metrics (`brand_ready`, `critic_approve_demote_rate`) and writes `docs/brand/scorecard-metrics.md` — measured readiness on the landing story, not slogans.

**Memory util scorecard (F130):** Mem0/Letta pattern — memory only helps if tools are called. `memory_tool_audit.py util-eval` offline good vs inject-unused weak pack yields `memory_tool_util_delta`; product scorecard fails closed without it next to demote rate.

**Workflow + dual compound (F131):** workflows-as-code scorecard folds into `torii.py scorecard` / `torii.py workflow -- scorecard`; brand panel requires skill L3 + memory L3 + workflow L3 (`dual_compound.triple_ready`) so the pipeline graph is as visible as the two intelligence loops.

**Scorecard self-evolution (F132):** `self_evolve.py propose-scorecard` turns brand_ready metric gaps into skill proposals (hub-gap critic, demote-eval, memory util, workflow graph, dual-compound ops). Install guide documents the dual-compound day-2 habit and the propose-scorecard close-the-loop command.

**Scorecard dual-gate adopt (F133):** `skill_auto_adopt.py cycle-scorecard` proposes then dual-gate+tool-attr adopts F132 scorecard-gap skills (synthetic allowlisted tool blobs for scorecard/doctor/demote/util/workflow). Default REJECT until gates pass; optional post-run via `TORII_SKILL_AUTO_ADOPT_SCORECARD=1`.

**Scorecard skill federate + fitness blend (F134):** adopted scorecard-gap skills federate as privacy-safe themes (`scorecard-skill-signals.json`); trajectory fitness soft-blends brand_ready / scorecard skill presence into procedure+tool dims so ops readiness compounds into run quality scores.

**Scorecard fitness ingest + doctor panel (F135):** F134 themes enter the skill fitness ledger (`ingest-scorecard` / cycle) with tool-hit shield + router boost; doctor and product scorecard surface `scorecard_ops_ok` (soft metric). Adopted ops skills no longer rot as zombies before live hits.

**Scorecard skill utilization (F136):** mid-run measure whether injected scorecard-gap ops skills fire tool CLIs (`scorecard-skill-util.json`); federate privacy-safe util themes; second-agent critic soft-demotes APPROVE on idle scorecard skills (inject ≠ utilization, same as F121 recovery).

**Scorecard util soft re-prompt (F137):** when scorecard-gap skills are injected but idle after tools ran, Hermes soft-reprompts once (F108 budget) with doctor/scorecard CLI nudge — same close-the-loop as F122 recovery re-prompt; federated scorecard-util-gap biases partial idle.

**Scorecard hub compound (F138):** multi-tenant scorecard-util themes post-score into select priority deltas + prompt inject (`scorecard-hub-score`), with soft fitness ledger ingest — same F125 recovery-hub pattern for ops skills so tool-effective scorecard themes win residual inject slots.

**Scorecard hub gap critic (F139):** second-agent panel checker `f139_scorecard_hub_gap` demotes APPROVE when multi-tenant scorecard util gap_pressure is high and local scorecard-gap ops skills are idle (F127 recovery-hub-gap mirror for ops readiness).

**Scorecard hub attribution floor (F140):** LOO attribution floors scorecard hub / `scorecard_ops` fitness skills (F135/F138) so multi-tenant tool-effective ops skills are not free-rider demoted — same F127 hub_ingested floor for recovery, now for scorecard ops (`TORII_SKILL_ATTR_SCORECARD=1`).

**Memory util federate + critic (F141):** Mem0/Letta discipline — memory inject without tool calls is a measured gap. Federate privacy-safe util themes (`memory-util-signals.json`); second-agent checker `f141_memory_util` demotes APPROVE when inject was offered but unused.

**Memory util hub compound (F142):** multi-tenant memory-util themes post-score into memory-skill priority deltas + prompt inject (`hub-score`); soft fitness shield so tool-effective memory CLI skills win always slots next run.

**Memory util hub gap critic (F143):** second-agent checker `f143_memory_hub_gap` demotes APPROVE when multi-tenant memory util gap_pressure is high and local memory inject is idle (F127/F139 mirror for Mem0/Letta tool discipline).

**Graph multi-hop → archival promote (F144):** temporal graph multi-hop themes expand MemGPT-style archival auto-query (`TORII_ARCHIVAL_GRAPH_HOPS=2`) so cold TP themes linked only via co_path/same_theme page into core inject — Zep hop + Letta archival paging compound.

**Supersede-aware archival promote (F145):** MemoTime/Zep temporal faithfulness — multi-hop expanded hits that match active `supersedes` (F101/F102 multi-hop index) are **filtered before core inject** (`TORII_ARCHIVAL_SUPERSEDE_FILTER=1`). Resolved FPs cannot re-page as blocking via co_path kinship.

**Archival reconsolidation (F146):** successful non-superseded promote **warms** durable TP signatures (`hits++`, `last_retrieved_at`, soft `effective_score`) and writes `.torii/archival-reconsolidation.json` (`TORII_ARCHIVAL_RECONSOLIDATE=1`) — retrieval is not write-only inject; next PR ranks proven themes higher.

**Recon-warm → core tier (F147):** Letta-style tiers promote items with recent `last_retrieved_at` / F146 reconsolidation into **core** inject (`TORII_MEMORY_RECON_CORE=1`, window `TORII_MEMORY_RECON_CORE_HOURS=168`). Stale or superseded retrieves stay archival — retrieval warm compounds into always-attend budget.

**Recon-warm federate (F148):** privacy-safe multi-tenant signals of **retrieval-hot themes** (`memory/federation/recon-warm-signals.json`, `TORII_RECON_WARM_FEDERATE=1`) — themes/warm bins + tenant hash only; hub post-score ranks multi-tenant warm themes for next inject. No paths, signature ids, or snippets leave the tenant.

**Hub warm → archival query (F149):** multi-tenant recon-warm themes **expand archival auto-query and soft-boost hit ranking** (`TORII_RECON_WARM_HUB_QUERY=1`) so cross-tenant retrieval heat pages related cold TPs even without local co_path — F148 export compounds into the next PR’s search, not write-only federation.

**Recon-warm hub critic (F150):** second-agent checker `f150_recon_warm_hub` **demotes APPROVE** when multi-tenant retrieval-hot themes are present but this run ignored hub archival boost (`TORII_RECON_WARM_HUB_CRITIC=1`) — closed-loop federation enforced by maker/checker, not dashboards alone.

**Recon-warm hub demote-eval + doctor (F151):** `second_agent_critic demote-eval` paper metric `recon_warm_hub_idle_demoted`; skill-loop/doctor surface `recon_warm_hub_ok`; product scorecard lists recon-warm demote next to hub_gap demote — paper-ready, not slogans.

**Recon-warm hub soft re-prompt (F152):** when multi-tenant retrieval heat is high but hub archival boost was idle, Hermes gets **one** soft re-prompt under shared F108 budget (`kind=f152`, `TORII_RECON_WARM_REPROMPT=1`) to call hub-aware memory/archival CLIs before finalizing — demote alone is not the only recovery path.

**Hub-archival skill self-evolve (F153):** F152 fire signals (`recon-warm-reprompt.env`) propose `skill-prefer-hub-archival-early` via `self_evolve propose`; dual-gate adopt uses synthetic archival tool blob (F118) — next PR prefers hub-aware archival **before** burning the F108/F152 re-prompt slot.

**Hub-archival dual-gate adopt + always budget (F154):** `skill_auto_adopt cycle-hub-archival` adopts the F153 skill into `active/` with `always_priority=95` under F119 (memory 100 > hub-archival 95 > product 90 > critic 85). Soft post-F152 hermes wire closes propose→adopt so multi-tenant warm paging ships in the always inject budget.

**GEPA-lite skill refine-from-util (F165):** Hermes self-evolution / ICLR 2026 GEPA pattern — when recovery or hub-archival util traces show inject≠tool (or chronic fitness gap_rate), `self_evolve.py refine-from-util` mutates active skill bodies with tool-first nudges under constraint gates (size ≤15KB, id preserved, required tool probes). Soft hermes wire after F163 fitness cycle; skill-loop surfaces `skill_refine_ok`.

**Refine dual-gate LOO floor + fitness shield (F166):** constraint-passed F165 refinements stamp `dual_gate: constraint_ok`, federate privacy-safe refine themes, soft-shield fitness demote (`ingest-refine`), and LOO-floor contribution so free-rider demote cannot kill a just-refined recovery skill before the next tool hit compounds `contribution_pp`.

**Refine dual-rollout contribution_pp (F167):** SkillsBench/GEPA paper metric — `skill_dual_rollout.py refine-dual` measures with-refine (GEPA body + hub_boost tools) vs ablated baseline (`refine_tool_contribution_pp`, `refine_probe_delta`). Soft hermes wire writes `refine-dual.json`; skill-loop surfaces `refine_dual_ok`.

**Refine dual multi-tenant promote (F168):** FederatedSkill gate — privacy-safe `skill-refine-dual-signals.json` (skill id + contrib bins + tenant hash only); `promote-refine-dual` requires ≥2 tenants and positive `refine_tool_contribution_pp` before writing `promoted-refine-dual-themes.json` and soft fitness priority boost. Single-tenant high scores stay blocked.

**Refine dual hub inject + dual_fail critic (F169):** `post_score_refine_dual_hub` boosts always-priority for multi-tenant promoted refine skills and injects a privacy-safe prompt section; second-agent checker `f169_refine_dual_fail` demotes APPROVE when refine dual fails after refined recovery skills inject (paper demote-eval `refine_dual_fail_idle_demoted`).

---

### D2 — Hub-archival compound loop

Hub-prefer archival skills are not “always inject and hope.” Torii **measures tool use, demotes idle APPROVE, re-prompts under budget, federates multi-tenant heat, and packages readiness as one product bit**:

```text
always inject → util score → critic demote → soft re-prompt → fitness → hub pressure → hub inject
       │              │              │                │              │           │              └─ F162 prompt + demote-eval
       │              │              │                │              │           └─ F161 multi-tenant gap_pressure
       │              │              │                │              └─ F158 chronic hit/gap ledger
       │              │              │                └─ F157/F159 adaptive under F108 max_extra
       │              │              └─ F156 second-agent idle demote path
       │              └─ F155 hub_boost tools required (inject ≠ utilization)
       └─ F154 skill-prefer-hub-archival-early in always budget
```

| Stage | Feature | Customer-facing meaning |
|-------|---------|-------------------------|
| **Util** | F155 | Hub-archival inject without archival tools is a measured gap |
| **Critic** | F156 | Idle hub-archival soft-demotes weak APPROVE |
| **Re-prompt** | F157/F159 | One adaptive recovery attempt shares F108 budget with memory re-prompt |
| **Fitness** | F158 | Hit/gap rates shield winners and demote chronic idle skills |
| **Router synth** | F160 | Bench/recovery inject still gets hub-archival when assemble skips |
| **Hub pressure** | F161 | Multi-tenant util themes bias next priority (privacy-safe) |
| **Hub inject** | F162 | Gap pressure lands in the prompt + demote-eval pack |
| **Product bit** | F163 | `hub_archival_loop_ok` on doctor/scorecard — one readiness flag |

**One-liner (eng):** *Hub-archival skills that never page cold memory do not silently APPROVE.*

**One-liner (AppSec):** *Cross-tenant retrieval heat becomes next-run always budget — without sharing paths or snippets.*

**Brand pack (F164):** PRODUCT + landing + `docs/brand/scorecard-metrics.md` surface `hub_archival_loop_ok`; paper EVAL pack rolls F155–F163 live traces (util_rate, Modal BIT3, doctor flags).

**Ops:** `python3 scripts/torii.py doctor` / `scorecard` → `hub_archival_loop_ok`. Smoke requires recovery + hub-archival wires when skills are active.

**Ops (memory):** `python3 scripts/memory_loop_status.py scorecard` → L0–L3. Smoke requires L3 on the hub tree. CI job summary annotates readiness; optional advisory `torii/memory-loop` via `TORII_MEMORY_LOOP_STATUS_COMMIT=1`.

---

### E — GEPA refine compound loop

Torii does not leave recovery skill bodies static after util gaps. Skills **evolve from traces under gates**, prove contribution, multi-tenant promote, and **decay when dual_fail is chronic**:

```text
util gap → GEPA refine → dual-gate LOO → dual_pp → federate promote
       → always Δprio + dual_fail critic → chronic decay → multi-tenant demote
       → dual_pass revive → multi-tenant re-boost (F175)
       → free-rider MT gate (F176)
       → contribution_pp revive floor (F177)
       → LOO attribution revive floor (F179)
       → hub-archival × GEPA compound demote (F180)
       → hub×GEPA compound prompt inject (F181)
       → hub×GEPA compound always priority (F182)
       → hub×GEPA compound re-prompt budget (F183)
       → compound re-prompt fitness ingest (F185)
       → compound re-prompt chronic miss pressure (F186)
```

| Stage | Feature | Customer-facing meaning |
|-------|---------|-------------------------|
| **Refine** | F165 | Trace-reflective tool-first skill body mutate (size/probe gates) |
| **Dual-gate floor** | F166 | Constraint-passed refine LOO-floored + fitness shield |
| **Dual-rollout** | F167 | with-refine vs ablated `refine_tool_contribution_pp` paper metric |
| **Federate promote** | F168 | Multi-tenant min_tenants gate on refine_pp bins |
| **Hub + critic** | F169 | Promoted refine boosts always slots; dual_fail demotes APPROVE |
| **Product bit** | F170 | `refine_loop_ok` on doctor/scorecard — one readiness flag |
| **Chronic decay** | F171 | dual_fail_rate ≥ thr → always Δprio decay + lift shield |
| **Decay federate** | F172 | Multi-tenant gate amplifies local always demote |
| **Decay critic** | F173 | Multi-tenant decay elevated → demote weak APPROVE (+ LLM soft hint) |
| **Dual_pass revive** | F175 | After decay, dual_pass recovers + multi-tenant re-boosts always |
| **Free-rider MT gate** | F176 | Local dual_pass cannot clear multi-tenant decay alone |
| **Revive pp floor** | F177 | dual_pass needs min `refine_tool_contribution_pp` to re-enter always |
| **Revive LOO floor** | F179 | free-rider / low avg_contribution LOO blocks dual_pass revive |
| **Hub×GEPA compound** | F180 | hub-archival util gap + GEPA pressure → harder APPROVE demote |
| **Hub×GEPA inject** | F181 | Maker sees dual-loop compound heat in prompt before demote |
| **Hub×GEPA always** | F182 | Compound heat boosts hub-archival into always budget |
| **Hub×GEPA re-prompt** | F183 | Compound heat unlocks one f157/f122 re-prompt slot |
| **Compound re-prompt fitness** | F185 | Re-prompt under dual-loop heat compounds into fitness ledger |

**One-liner (eng):** *Skills that fail tool util get refined, measured, and multi-tenant promoted — or they stay out of always budget; recovery is measured too.*

**One-liner (AppSec):** *Idle recovery skills cannot silently APPROVE after GEPA refine inject.*

**Brand pack (F170/F174/F178/F184):** PRODUCT + landing + scorecard-metrics surface `refine_loop_ok` (F165–F177) plus `refine_dual_revive_ok` / `free_rider_revive_ok` / `revive_pp_gate_ok` and demote paper rows; paper EVAL pack rolls F165–F177 live Modal proofs (`f178-gepa-refine-full-eval-pack/`, supersedes F174 scope).

**Ops:** `python3 scripts/torii.py doctor` / `scorecard` → `refine_loop_ok` next to `hub_archival_loop_ok`.

**Chronic dual_fail decay (F171):** after min samples, high `refine_dual_fail_rate` lifts the F166 refine shield, soft-demotes the skill, and applies **negative always-priority** (`refine_priority_decay`) so idle refined skills fall out of the always budget until hub_boost tools recover contribution_pp.

**Multi-tenant decay federate (F172):** FederatedSkill gate for F171 — privacy-safe `skill-refine-dual-decay-signals.json` (skill id + fail_rate bin + decay + tenant hash); `promote-refine-decay` requires ≥2 tenants before amplifying local decay and always demotion. Single-tenant chronic fails stay local-only.

**Multi-tenant decay critic (F173):** second-agent `f173_refine_decay_hub` demotes APPROVE when multi-tenant chronic dual_fail decay is elevated; soft `endorse_demote_hint` for optional LLM critic (`TORII_LLM_CRITIC=1`). Paper demote-eval: `refine_decay_hub_idle_demoted`.

**Dual_pass revive (F175):** when dual_pass recovers contribution_pp after prior decay, clear local multi_tenant_decay + restore always-priority; privacy-safe federate revive bins; multi-tenant promote re-boosts and supersedes decay themes.

**Free-rider multi-tenant revive gate (F176):** local dual_pass after multi_tenant_decay is sticky — sets `local_revive_pending_mt` + soft boost only; full clear + always re-boost requires FederatedSkill promote (≥2 tenants). Critic `f176_free_rider_revive` demotes free-rider APPROVE; demote-eval `free_rider_revive_idle_demoted`.

**Full GEPA refine EVAL pack (F178):** scorecard brand rows for revive gates + paper pack F165–F177 (decay→revive→free-rider→pp-floor).

**Revive contribution_pp floor (F177):** SkillOpt-style validation — dual_pass with `refine_tool_contribution_pp` below `TORII_REFINE_REVIVE_MIN_PP` (default 10) sets `revive_pp_blocked` and does not re-enter always budget; multi-tenant promote also requires the floor. Critic `f177_revive_pp_gate` demotes low-pp recovery APPROVE; demote-eval `low_pp_revive_idle_demoted`. `refine_loop_ok` ANDs F165–F179.

**Revive LOO attribution floor (F179):** skill-attribution free_rider or avg_contribution below `TORII_REFINE_REVIVE_MIN_LOO` (default 0.5, after min_n samples) blocks dual_pass revive even with high tool_pp; positive LOO soft-boosts re-entry. Critic `f179_revive_loo_gate` demotes; demote-eval `loo_revive_idle_demoted`.

**Hub-archival × GEPA compound (F180):** when hub-archival util gap **and** GEPA decay/free-rider/pp/LOO pressure co-occur, second-agent `f180_hub_gepa_compound` demotes APPROVE harder (score 0.15, escalate to REQUEST_CHANGES). Paper: `hub_gepa_compound_idle_demoted`. `refine_loop_ok` ANDs F165–F180.

**Hub×GEPA compound prompt inject (F181):** `assess_hub_gepa_compound` + prompt section (`<!-- torii-f181-hub-gepa-compound -->`) so the maker sees dual-loop pressure before F180 demote. `refine_loop_ok` ANDs F165–F181.

**Hub×GEPA compound always priority (F182):** `select_skills` folds `assess_hub_gepa_compound` priority_deltas into always budget + residual score so dual-loop heat keeps hub-archival recovery skills selected. `refine_loop_ok` ANDs F165–F182.

**Hub×GEPA compound re-prompt budget (F183):** when dual-loop compound is high, `reprompt_budget.ensure_compound_slot` expands max_extra once for f157/f122 after base exhaustion (independent of F159 complementary kinds). Paper fixture: f183_ok. `refine_loop_ok` ANDs F165–F183.

**Compound re-prompt fitness (F185):** `ingest_compound_reprompt` folds `reprompt-budget.json` f157/f122 attempts under `compound_expanded` into hub-archival fitness (recover → tool hit shield; miss → gap fuel). Hermetic: `fixture-compound-reprompt`. `refine_loop_ok` ANDs F165–F186.

**Compound re-prompt chronic miss pressure (F186):** longitudinal F185 counters mark `compound_reprompt_chronic_miss` → always-priority boost + residual score + critic demote idle APPROVE (`f186_compound_reprompt_pressure`). Hermetic: `fixture-compound-reprompt-pressure`; paper: `compound_reprompt_chronic_idle_demoted`. `refine_loop_ok` ANDs F165–F186.

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

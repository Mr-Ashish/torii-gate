# Torii research → product log


## 2026-08-01 — F115 tool-outcome LOO attribution + dual tool contribution

### Papers / posts
- Mem2Act / proactive memory: inject ≠ utilization — score tool calls (F114).
- SkillsBench dual-rollout: contribution_pp must beat ablated baseline (F86).
- Assay / Not All Skills Help: LOO free-rider retire — must not mis-label tool-only skills.
- Hermes self-evolution: multi-dim fitness + constraints before adopt.
- Gap after F114: tool_hit measured but F88 LOO + F86 dual were prose-only → recovery skills look free-rider when review body is silent.

### OSS design patterns stolen
1. F114 TOOL_OUTCOME_PROBES reused in LOO + dual tool_blob_with vs ablated.
2. Tool contribution weight 1.5 > prose keyword 1.0 (Mem2Act priority).
3. Durable ledger `tool_hits` prevents free-rider demote of tool-effective skills.
4. Dual synthetic tool transcripts: taught CLIs vs generic shell.

### Insight
Self-evolved memory-CLI skills succeed via **terminal**, not review prose. Without tool-aware LOO/dual, fitness ranking and adopt gates undervalue the skill F113 just dual-gate adopted. Highest ROI close: credit tool_hit in attribution + dual contribution_pp.

### Feature shipped (F115)
- `skill_attribution.py` — tool_blob/agent_loop LOO; feature_tool=F115; fixture tool-only proof
- `skill_dual_rollout.py` — tool_contribution_pp; SYNTH tool with/ablated blobs
- PRODUCT one-liner; research note skill-tool-attr-dual-pattern
- traces `docs/benchmarks/traces/f115-tool-attr-dual/`

### Metric
- Offline: attr fixture_pass; dual tool_contribution_pp=50; cycle tool_contributors includes skill-prefer-memory-cli-early
- pytest 594; Modal pytorch#191813 BIT3_OK ~134s log_streaming=true POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Verifier LOO + multi-dim contribution** — independent tool outcome dimension; default REJECT free-riders until tool or prose evidence.

### SHA
`87cbfcf38ee69aa27dc9db9c02bd0f6241ad4832`
## 2026-08-01 — F114 tool-invocation skill outcome + product CLI memory detect

### Papers / posts
- Mem2Act / proactive memory: inject ≠ utilization — score tool calls.
- Vercel agent evals: skills often never invoked when dumped wholesale.
- F113 adopted skill-prefer-memory-cli-early teaching `torii.py memory`; F84 hit score was prose-only; F105 missed F110 product CLI.

### OSS design patterns stolen
1. TOOL_OUTCOME_PROBES map skill_id → agent-loop regexes (torii.py memory, rg -n, …).
2. Combined hit = prose_hit OR tool_hit; fitness tracks tool_hit_n.
3. F105 audit pattern for `torii.py memory` (torii_product_memory).
4. Always-on full body for recovery skill; free-rider accounting survives always budget fill.

### Insight
Self-evolved recovery skills succeed via **terminal**, not review prose. Without tool-outcome scoring, fitness zombie-demotes the skill that F113 just dual-gate adopted. Highest ROI close: measure invocations + count product CLI.

### Feature shipped (F114)
- `skill_router.score_hits` F114 tool_outcome fields; DEFAULT_TRIGGERS always for prefer-memory
- `memory_tool_audit` detects product CLI; fixture uses torii.py memory
- skill-prefer-memory-cli-early always:true; skill_fitness tool_hit_n
- free-rider residual skip when always skills fill max_full
- tests + research note skill-tool-outcome-pattern

### Metric
- Offline: skill_router fixture_pass; memory audit good_tools includes torii_product_memory
- pytest 592; Modal pytorch#191813 BIT3_OK ~83s skill always in prompt log_streaming=true

### SHA
`808aeed2b785159a915b0ea0e5633ccd52575567`

## 2026-08-01 — F113 dual-gate adopt of skill-prefer-memory-cli-early

### Papers / posts
- SkillsBench dual-rollout: contribution_pp must beat ablated baseline.
- F88 LOO attribution: free-riders do not adopt.
- F112 proposed memory-CLI skill; auto-adopt was f74-only.

### OSS design patterns stolen
1. Expand `skill_auto_adopt` globs to `skill-prefer-*` (F113).
2. Gates: validate + F86 dual + F88 attr + regression — then copy to active/.
3. Live prompt lists skill-prefer-memory-cli-early after adopt.

### Insight
Self-evolution without dual-gate adopt leaves recovery skills as proposals forever. Highest ROI close: open the adopt path for F112 skills with the same contribution gates as F74.

### Feature shipped (F113)
- `skill_auto_adopt.list_candidates` F112/prefer globs
- active skill `skill-prefer-memory-cli-early.md`
- PRODUCT note F112/F113 self-evolve adopt
- tests for active skill presence

### Metric
- dual_pass=true contribution_pp=50; adopt ok; free_rider=false
- pytest 589; Modal BIT3_OK ~157s skill in prompt log_streaming=true

### SHA
`c43bb3eac4ae54a1ab44bc5af012a4eee27955cd`

## 2026-08-01 — F112 self-evolve skill from F106 memory recovery

### Papers / posts
- Hermes self-evolution: trajectories → proposals → eval → adopt.
- Mem2ActBench: proactive memory use beats passive inject + re-prompt.
- Live F106 recovered hits 0→5; signal was not yet a skill proposal path.

### OSS design patterns stolen
1. Ingest signals: `f106_recovered`, `memory_utilization_gap`, `memory_tools_used` from reprompt env + audit JSON.
2. Propose `skill-prefer-memory-cli-early` (call `torii.py memory` / `torii_memory` early).
3. Dual-gate: eval recommend=adopt (20/25); no silent auto-adopt.

### Insight
Recovery re-prompts prove the agent *can* use memory tools — self-evolution must promote that into a durable skill so next PR does not burn the F108 budget.

### Feature shipped (F112)
- `self_evolve.py` F105/F106 signal extraction + proposal template
- proposal `agent/skills/proposals/skill-prefer-memory-cli-early.md`
- tests for F112 recovery path

### Metric
- Offline: ingest emits f106_recovered; propose creates skill; eval recommend=adopt
- pytest 588; Live Modal pytorch#191813 BIT3_OK ~164s log_streaming=true

### SHA
`ec96384af78e9a354d83a813e1316b666b3a4b0f`

## 2026-08-01 — F111 smoke product doctor + insecure compound/federate proof

### Papers / posts
- Loop-eng: doctor is day-2 habit; CI summary is the scorecard surface.
- F110 product CLI shipped; not yet smoke/CI annotated.
- F104/F107: live pytorch federate_signals=0 is correct; dogfood proof required.

### OSS design patterns stolen
1. Smoke steps 8–9: `torii.py doctor` + compound fixture fed_count≥1 on insecure-demo good review.
2. GHA job summary Product CLI doctor annotation.
3. Soft toggles TORII_SMOKE_PRODUCT_CLI / TORII_SMOKE_COMPOUND_FEDERATE.

### Insight
Without smoke/CI, product doctor and integrity federate are unmeasured on the install path. Highest ROI: close the dogfood scorecard.

### Feature shipped (F111)
- smoke-torii-gate.sh [8/9] doctor + [9/9] compound federate (fed_count=2)
- reusable workflow job-summary product CLI doctor
- research note smoke-product-cli-compound-pattern

### Metric
- Offline smoke PASS; compound federate fed_count=2; pytest 587
- Live Modal pytorch#191813 BIT3_OK ~164s log_streaming=true POST_COMMENT=0

### SHA
`bd8864f69c57df6b49bb4a3ace96f37e78850e0e`

## 2026-08-01 — F110 unified product CLI front door (loop-eng style)

### Papers / posts
- Loop Engineering CLI front door: one binary, pass-through, doctor/status.
- Torii F103 memory CLI; peer tools still tribal for agents.
- Prefer discoverable tools-as-code entrypoints over SOUL prose.

### OSS design patterns stolen
1. **Umbrella CLI** `scripts/torii.py` → memory/gate/budget/skill-loop/memory-loop/smoke.
2. **doctor** aggregates memory status + loops + re-prompt budget fixture.
3. Soft assemble inject-hint; F103 `torii_memory.py` remains supported.

### Insight
Memory front door alone is not enough for product UX — Hermes and operators need one product-level command surface. Highest ROI: thin dispatch + doctor.

### Feature shipped (F110)
- `scripts/torii.py` help/status/doctor/fixture + group dispatch
- assemble-context soft inject; install + README + PRODUCT
- Toggle `TORII_CLI`; adopted tool torii-product-cli

### Metric
- Offline fixture_pass=1; pytest 587 passed
- Live Modal pytorch#191813: BIT3_OK ~151s log_streaming=true POST_COMMENT=0; F110 inject in prompt

### SHA
`75d4ae229339eb4bc7efc3e6bc6fc4da46e5f4cf`

## 2026-08-01 — F109 brand packaging: integrity + budgeted memory story

### Papers / posts
- DevSecOps 2026: scanners generate findings; platforms/gates close risk.
- AppSec fatigue: AI multiplies PR volume — need stricter-and-quieter gates, not more bots.
- Torii F103–F108 product capabilities needed ICP-facing packaging (overdue since F99).

### OSS / eng patterns
1. Landing + brand lock one-liners for memory CLI, integrity compound, budgeted recovery.
2. Install tips: `torii_memory doctor` + `TORII_REPROMPT_MAX_EXTRA=1`.
3. README/PRODUCT memory diagram through F108 compound → search + budget.

### Insight
Intelligence without packaging loses adoption clarity. Highest ROI this fire: align brand with shipped gate capabilities (integrity, federate, utilization, re-prompt budget) without empty polish.

### Feature shipped (F109)
- `docs/brand/landing.html` + `TORII.md` one-liners + memory pipeline
- README + PRODUCT mental model C (F93–F108)
- install-torii.sh post-install memory doctor + budget tips
- research note brand-integrity-budget-packaging-pattern

### Metric
- pytest: 581 passed (no brand regressions)
- Live Modal pytorch#191813 deepseek-v4-pro: BIT3_OK ~196s log_streaming=true POST_COMMENT=0

### SHA
`cd70bb4559bcf2063c57b52612448d93b68ce0f0`

## 2026-08-01 — F108 shared soft-re-prompt budget (F49+F106)

### Papers / posts
- Agent cost 2026: multi-turn re-prompts roughly double LLM spend.
- Braintrust/Portal26: attempt ceilings + kill switches per agent run.
- Torii live: F49+F106 stacking → ~2× DeepSeek wall-time/cost without a shared cap.

### OSS design patterns stolen
1. **Shared max_extra** budget across recovery kinds (default 1).
2. **Reserve on attempt start** so failed paid re-runs still consume the slot.
3. **kind once** + remaining counter — F106 cannot fire after F49 at max=1.

### Insight
Soft re-prompts recover quality (F106 hits 0→1) but unbounded stacking is a cost bug. Highest ROI: deterministic shared budget before paid Hermes re-entry.

### Feature shipped (F108)
- `scripts/reprompt_budget.py` init/allow/consume/status/fixture
- Wire in `run-hermes-review.sh` before F49 and F106
- Toggles `TORII_REPROMPT_BUDGET` + `TORII_REPROMPT_MAX_EXTRA` (default 1)
- PRODUCT re-prompt budget one-liner

### Metric
- Offline fixture: max1 blocks second; max2 allows both; fixture_pass=1
- Live Modal pytorch#191813: BIT3_OK ~209s; F106 recovered hits 0→1 within budget; log_streaming=true
- pytest: 581 passed

### SHA
`ad24098fb04bfd7cb5bffad52712e6f66407ee66`

## 2026-08-01 — F107 privacy-safe federate of integrity-gated compound TPs

### Papers / posts
- Multi-tenant agent FL privacy (IETF-style): aggregate themes without raw tenant data.
- F77 hub + F95 effective-score federate already existed; F104 compound did not export immediately.
- Loop-eng: tools-as-code write → federate stage with privacy assert.

### OSS design patterns stolen
1. **Integrity-only export** — only candidates with integrity=ok become hub signals.
2. **Basenames / theme / CWE / keywords** — never snippets or `/Users` paths.
3. **Assert on sanitized** signals (tenant → hash) before privacy_ok.

### Insight
Local compound without hub export keeps multi-tenant learning cold. Highest ROI close: F104 candidates → F77 ingest tagged `integrity_gated`/`f107` so promote min_tenants can share proven themes.

### Feature shipped (F107)
- `memory_compound_write.py federate` + auto `--federate` on compound
- Toggle `TORII_MEMORY_COMPOUND_FEDERATE`
- Soft stage in `run-torii-review` memory_compound
- PRODUCT integrity federate one-liner

### Metric
- Offline fixture: fed_count≥1 privacy_ok tags_ok bases_ok fixture_pass=1
- Live Modal pytorch#191813: BIT3_OK ~147s; F106 hits 0→1; F104/F107 federate_signals=0 (non-security PR correct); log_streaming=true
- pytest: 577 passed

### SHA
`39f891f2fd02e7db3e11a22efd1bdaf09be9e2e3`

## 2026-08-01 — F106 soft re-prompt on memory utilization gap

### Papers / posts
- Mem2ActBench / MemoryAgentBench: value is **proactive memory use**, not passive inject.
- Torii F49/H15: soft re-prompt recovers zero-tool multi-file runs — same pattern for memory gap.
- F105 auditor: measures inject-offered-but-unused; F106 closes the recovery loop.
- Loop-eng: score + recoverable stage, not scorecard-only.

### OSS design patterns stolen
1. **Soft second attempt** (F49 mirror) only when tools already ran and memory unused.
2. **Defer zero-tool** cases to F49 (no double re-prompt storm).
3. **Recovered metric** hit_count before/after written to `memory-tool-reprompt.env`.

### Insight
Live F105 showed inject offered but zero memory hits. Measuring gap is insufficient — agents need one recoverable nudge mid-pipeline when utilization fails after real tool use.

### Feature shipped (F106)
- `memory_tool_audit.py` `reprompt-decide` / `reprompt-write`
- Soft stage in `run-hermes-review.sh` after F49
- Toggle `TORII_MEMORY_TOOL_REPROMPT`
- PRODUCT mental model C + F106 one-liner

### Metric
- Offline fixture: weak→reprompt=1; good→0; zero tools→defer_f49; write_ok
- Live Modal pytorch#191813 deepseek-v4-pro: BIT3_OK ~149s; F106 recovered hits **0→5**; post-audit F105 score=1.0 L3; log_streaming=true
- pytest: 576 passed

### SHA
`c8ec797c3b625560665d640f46e53de7b1b5a2f3`

## 2026-08-01 — F105 mid-review memory tool utilization audit

### Papers / posts
- **IFCMemoryBench** (arXiv 2607.26072): memory eval = ingestion · retrieval · **utilization**.
- **WorldMemArena**: write / maintain / retrieve / use decomposition — Torii lacked the use score.
- Loop-eng: score the loop; do not assume SOUL prose was followed.
- MemGPT/Letta: memory tools only help if agents call them mid-trajectory.

### OSS design patterns stolen
1. **Utilization auditor** on agent-loop tool args (not only inject presence).
2. **utilization_gap** flag when inject offered + tools used but memory never queried.
3. Soft **fitness blend** (small weight) so path evidence stays dominant.

### Insight
F103/F104 shipped front door + compound write. Without measuring mid-review retrieval, we cannot prove the memory stack is used. Highest ROI: deterministic scan of terminal commands for `torii_memory` / graph / archival, score 0–1, soft-blend fitness, trace artifact.

### Feature shipped (F105)
- `scripts/memory_tool_audit.py` — scan / score / audit / inject / fixture / status
- Soft assemble-context rubric inject; post-run stage after traj_fitness
- Soft blend into `fitness.json` when present
- `torii_memory.py audit` + memory_loop stage (L3 12/12)
- Toggles `TORII_MEMORY_TOOL_AUDIT` / `TORII_MEMORY_TOOL_FITNESS`

### Metric
- Offline fixture: good=1.0 weak=0.15 delta=0.85 fixture_pass=1
- Live Modal pytorch#191813: BIT3_OK ~41s log_streaming=true; F105 inject_offered=true score=0.1 hit=0 (zero tool turns measured)
- pytest: 574 passed

### SHA
`c29d9e14281a379a08bc424bb3799e93bbb1ebbf`

## 2026-08-01 — F104 integrity-gated post-review memory compound write

### Papers / posts
- **AgenticCyOps** (arXiv 2603.09134): multi-agent attack surfaces collapse to tool orchestration + **memory management**.
- **LASM** layered agent security (arXiv 2604.23338): Memory Integrity Controls — write restrictions + consistency validation before durable store.
- Letta/MemGPT memory hierarchy + filesystem tools: agents need discoverable write paths, not only recall.
- Loop-eng: tools-as-code + Loop Ready stages over SOUL prose.

### OSS design patterns stolen
1. **Memory integrity gate** before durable write (status ∈ path_evidenced|confirmed_tp; reject absolute-home, secret-like blobs, pathless narrative).
2. **Provenance-only store** — theme/keywords/path_globs + source; never raw finding snippets (privacy).
3. **F93 event policy** as the sole apply path (ADD/UPDATE/NONE) so compound does not bypass supersession.

### Insight
F103 unified the **read/search** front door; live reviews still only distilled narrative MEMORY.md. Durable `tp-signatures.json` did not compound from path-evidenced agent findings automatically — and had no poison gate. Highest ROI close of the memory loop: post-review extract → integrity filter → F93 write → consolidate/graph.

### Feature shipped (F104)
- `scripts/memory_compound_write.py` — `plan` / `apply` / `compound` / `fixture` / `status`
- Integrity policy: path-evidenced only; reject `/Users|/home`, secret-like tokens, weak_evidence
- Soft stage in `run-torii-review.sh` **before** consolidate + temporal graph
- `torii_memory.py compound` dispatch + doctor fixture
- `memory_loop_status` stage `compound_write` (L3 11/11)
- Toggle `TORII_MEMORY_COMPOUND`; adopted tool `memory-compound-write`
- PRODUCT mental model C extended F93–F104

### Metric
- Offline fixture: good_promoted≥1, weak=0, poison_ok, store_clean, fixture_pass=1
- Live Modal pytorch#191813: BIT3_OK ~48s, tool_call_turns=4, log_streaming=true; F104 stage promoted=0 (correct — non-security PR)
- pytest: 569 passed

### SHA
`1daf8af18c65b03c44c98f17d72139121ada52df`

## 2026-08-01 — F103 unified torii_memory CLI for Hermes

### Papers / posts / OSS
- MemGPT/Letta: memory as explicit agent tools; Torii had many scripts, no front door.
- Loop-eng: discoverable entrypoints beat tribal SOUL prose.

### OSS / eng patterns
1. `torii_memory.py` dispatches search/graph/tiers/consolidate/events/recall/loop/federate.
2. `doctor` soft fixture matrix (shallow loop scorecard — no recursion).
3. assemble-context inject-hint + skill card points at CLI.

### Insight
Agents cannot invent the right script. Highest ROI: **one memory front door**.

### Feature shipped (F103)
- scripts/torii_memory.py help/status/doctor/dispatch/fixture
- pack + memory_loop stage; PRODUCT agent front door

### Loop-engineering practice used
**Tools-as-code catalog surface** — help is the API.

### Metric
- Offline: fixture doctor_ok; memory_loop L3 10/10; 563 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~92s; log_streaming=true; POST_COMMENT=0

### SHA
e6844640fcd688cd74d55db3db69b6dda6b21b39

## 2026-08-01 — F102 multi-hop co_path → supersede demote

### Papers / posts / OSS
- Zep multi-hop temporal retrieval; F101 was 1-hop supersedes only.
- Path kinship (co_path) unused by critic despite F100 edges.

### OSS / eng patterns
1. BFS expand co_path/same_theme from path seeds (hops default 2).
2. superseded_index(paths=…) path-local neighborhood + dual_pass per-chunk.
3. query --hops N for inject/debug.

### Insight
Supersession on a sibling file should caution the same theme on co-path. Highest ROI: **multi-hop path kinship into demote**.

### Feature shipped (F102)
- expand_neighborhood / path-scoped superseded_index
- dual_pass multi-hop; toggle TORII_GRAPH_MULTI_HOP

### Loop-engineering practice used
**Structural multi-hop checker signal** — offline BFS, no embeddings.

### Metric
- Offline: fixture multi_hop_ok; 558 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~83s; log_streaming=true; POST_COMMENT=0

### SHA
89f0d108bf031e9b8fc67efad7e01a6bf97308a4

## 2026-08-01 — F101 graph supersede demote in dual-pass critic

### Papers / posts / OSS
- F100 temporal supersedes edges; F70/F95 dual_pass ignored graph.
- Loop-eng checker must recompute offline — supersession is a structural signal.

### OSS / eng patterns
1. `superseded_index` from active supersedes edges (target ids + themes).
2. dual_pass: filter TP hits; if none remain → `superseded_tp` (not confirmed).
3. F78 panel surfaces counts; toggle `TORII_GRAPH_SUPERSEDE`.

### Insight
Graph without critic is inject-only. Highest ROI: **demote confirmed TP on active supersedes**.

### Feature shipped (F101)
- dual_pass graph_supersede demote; superseded_index API
- second_agent detail; tests; PRODUCT

### Loop-engineering practice used
**Checker uses the same graph the writer builds** — tools-as-code, no LLM.

### Metric
- Offline: supersede demote + cmdi still confirm; 555 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~83s; log_streaming=true; POST_COMMENT=0

### SHA
24c69c118b09e092cf0f56ccad5314732d02689d

## 2026-08-01 — F100 Zep-style temporal memory graph edges

### Papers / posts / OSS
- **Zep:** temporal knowledge graph — facts as edges with validity windows.
- Torii F93 `superseded_by` was field-only; F97–F98 tiers/search still flat bags.

### OSS / eng patterns
1. Edges: supersedes / same_theme / co_path / updated_from + valid_from/until.
2. Query 1-hop by path/theme/id; inject supersession warnings into prompt.
3. Soft assemble-context + post-review rebuild; memory_loop stage.

### Insight
Supersession without a graph is invisible at inject. Highest ROI: **temporal edges as tools-as-code**.

### Feature shipped (F100)
- `scripts/memory_temporal_graph.py` build/query/inject/fixture
- assemble + run-torii-review wire; pack; PRODUCT note

### Loop-engineering practice used
**Structural memory over prose** — edges are deterministic and testable.

### Metric
- Offline: fixture super+theme+path; memory_loop L3 (9 stages); 553 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~86s; log_streaming=true; POST_COMMENT=0

### SHA
0ba3f704ccb272b75ac06e91b02beefc7030b54c

## 2026-08-01 — F99 brand dual compound loops (skills + memory)

### Papers / posts / OSS
- 2026 DevSecOps: AI multiplies PR volume; buyers want workflow-native gates that get **quieter**, not scanner theater.
- Torii shipped F84–F98 intelligence; brand only packaged the skill loop clearly (F90).

### OSS / eng patterns
1. PRODUCT mental model C — memory loop table + diagram (parity with skills).
2. Landing dual pipelines; one-liners: measure-in skills / page-in memory.
3. Install-guide embeds both readiness scorecards; archival-search skill card.

### Insight
Intelligence without a dual-loop story under-sells the moat. Highest ROI: **package skills + memory as equal compound loops**.

### Feature shipped (F99)
- PRODUCT / brand TORII.md / landing / README dual-loop story
- workflow_as_code install-guide memory block
- skill-archival-memory-search active skill card

### Loop-engineering practice used
**Ship what you measure** — brand describes L0–L3 loops already in smoke/CI.

### Metric
- Offline: 550 pytest; smoke PASS; install-guide shows memory L3
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~110s; log_streaming=true; POST_COMMENT=0

### SHA
11e8f88dcf7e9c8531eb5929b85934a2ef370c67

## 2026-08-01 — F98 MemGPT-style archival search + promote-to-core

### Papers / posts / OSS
- **MemGPT/Letta:** `archival_memory_search` + core append — agent pages cold facts on demand.
- Torii F97 archival tier had no retrieval path; MEMORY.md distill was append-only.

### OSS / eng patterns
1. Deterministic keyword score over TP/FP/federated + MEMORY.md recall blocks.
2. `auto` from changed basenames; promote inject section for current PR.
3. Soft wire assemble-context after F75; privacy redaction on index.

### Insight
Tiers without search leave cold knowledge dead. Highest ROI: **just-in-time archival search → core inject**.

### Feature shipped (F98)
- `scripts/archival_memory_search.py` search/promote/auto/fixture
- assemble-context soft; memory_loop stage; pack + PRODUCT

### Loop-engineering practice used
**On-demand tools over full dump** — retrieve when path tokens match, not always-on prose.

### Metric
- Offline: fixture TP+FP+MEMORY; memory_loop L3 (8 stages); 550 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~96s; log_streaming=true; POST_COMMENT=0

### SHA
d32b300595133a70f5ab0ca187fa6b5f8f7fd7c7

## 2026-08-01 — F97 Letta-style core/archival memory tiers + CI memory-loop summary

### Papers / posts / OSS
- **MemGPT/Letta:** OS hierarchy — core (always-in-context) vs archival (cold) vs recall.
- Torii F75 flat top-N inject equalized path-matched and stale theme noise once selected.
- F92 skill-loop CI job summary pattern → memory_loop mirror.

### OSS / eng patterns
1. Deterministic tier: path_match>0 OR effective≥floor OR path-FP → **core**; else archival.
2. Separate CORE_MAX / ARCHIVAL_MAX budgets; render core first in prompt.
3. CI job summary + optional `torii/memory-loop` commit status; memory_loop stage `tiers`.

### Insight
Effective scores without tiering still waste context on cold noise. Highest ROI: **Letta-style inject tiers**.

### Feature shipped (F97)
- `scripts/memory_tiers.py` classify/inject/fixture
- scoped_memory_recall soft-apply tiers + render
- reusable workflow memory_loop job summary; pack + PRODUCT

### Loop-engineering practice used
**Context budget as a measured resource** — core/archival split is tools-as-code, not SOUL prose.

### Metric
- Offline: tiers fixture; memory_loop L3 (7 stages); 547 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~159s; log_streaming=true; POST_COMMENT=0

### SHA
79aa3ac6293d02f188cf31a26709338c0bc5b99e

## 2026-08-01 — F96 memory loop readiness + promoted effective inject rank

### Papers / posts / OSS
- Loop Engineering readiness scorecards (skill_loop F91 pattern applied to memory).
- F75 inject ranked path/scope/hits; F95 federated effective floats not preferred at inject.
- Memory stack F70–F95 lacked a single ops surface for "is compound memory ready?"

### OSS / eng patterns
1. Prefer `promoted-signals.json` in F75 `_fed_path`; load + rank by `effective_score`.
2. `memory_loop_status` L0–L3: write→consolidate→effective_critic→federate→scoped_recall→tp_store.
3. Smoke [7/7] + `torii_gate_status --memory-loop-only`.

### Insight
Intelligence without readiness rots. Highest ROI: **scorecard the memory loop** and **inject promoted strength**.

### Feature shipped (F96)
- scoped_memory_recall promoted prefer + effective rank/merge
- memory_loop_status status/scorecard/fixture/markdown
- smoke + gate ops surface; pack install; PRODUCT

### Loop-engineering practice used
**Readiness scorecard on the compound memory loop** — measured stages, not prose.

### Metric
- Offline: memory_loop L3; scoped fixture promoted+effective_rank; 543 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~80s; log_streaming=true; POST_COMMENT=0

### SHA
8c978b490aab964c97312d453ccd620612e593fd

## 2026-08-01 — F95 effective-aware dual-pass critic + federated strength

### Papers / posts / OSS
- Agent memory 2026: high-hit **stale** facts poison ranking; strength must enter checkers not only stores.
- F94 effective_score; F77 multi-tenant privacy; F70 dual_pass treated all TP hits equal.
- Federated learning privacy patterns: share aggregates (floats), not paths/snippets.

### OSS / eng patterns
1. dual_pass: confirm TP only if max matching `effective_score ≥ floor` (default 0.25); else `stale_tp_match`.
2. Federated sanitize/merge keeps max `effective_score`; promote optional `min_effective`.
3. `memory_consolidate federate` exports privacy-safe strength signals post-review.

### Insight
Consolidation without checker integration leaves stale TP boosting precision. Highest ROI: **effective-aware critic + federated strength**.

### Feature shipped (F95)
- dual_pass_critic effective floor + effective_precision
- federated_hub_ingest effective merge/promote/INDEX
- consolidate federate stage; F78 panel detail; PRODUCT F95

### Loop-engineering practice used
**Checker uses the same measured signal as memory** — effective_score is tools-as-code evidence for confirm vs stale.

### Metric
- Offline: federated fixture effective_max+eff_promote; bench fixture; 539 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~157s; log_streaming=true; tool_call_turns=20; POST_COMMENT=0

### SHA
a47643c5b6c5874c9290fb5517b7521e890bd949

## 2026-08-01 — F94 memory consolidation (importance · merge · decay · eviction)

### Papers / posts / OSS
- **Hindsight consolidation framework (2026):** four levers — importance, merge, decay, eviction.
- **Mem0** ECAI 2025 / state-of-memory 2026: write-time events + consolidation; high-hit staleness is hard.
- **Zep:** temporal edge strength / age as retrieval signal.
- Prior Torii F93 write events + F75 scoped recall lacked temporal maintenance.

### OSS / eng patterns
1. Deterministic `importance × half-life_decay` → `effective_score` on each TP/FP item.
2. Near-dup MERGE (theme + keyword Jaccard) then EVICT below threshold.
3. Soft-wire after F93 merge + post-review stage; F75 rank blends effective_score.

### Insight
Write-path events without maintenance still bloat recall. Highest ROI: **tools-as-code consolidation** so stale low-value themes leave the budget.

### Feature shipped (F94)
- `scripts/memory_consolidate.py` plan/apply/run/score/inject/fixture/status
- `merge_tp_signatures` → `_maybe_consolidate_tp`; run-torii-review stage
- F75 MemoryItem + rank_score annotations; toggle `TORII_MEMORY_CONSOLIDATE`
- pack install + catalog adopted tool; PRODUCT compound memory note

### Loop-engineering practice used
**Verifier-style maintenance loop** — consolidation is a separate deterministic pass (not the writer), with measurable fixture ops (merge/evict/decay rank).

### Metric
- Offline: fixture_pass (merge+decay+evict); bench fixture_pass=1; 534 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~79s; log_streaming=true; tool_call_turns=4; POST_COMMENT=0

### SHA
9c3d896d8a987424568ca3ab856c1d466e397872

## 2026-08-01 — F93 Mem0-style ADD/UPDATE/DELETE/NONE memory write policy

### Papers / posts / OSS
- **Mem0** (Apache-2.0): UPDATE_MEMORY prompt — ADD|UPDATE|DELETE|NONE; supersession chains.
- Prior Torii F75 conflict-at-recall; F70/F64 writes were naive append/union.

### OSS / eng patterns
1. plan_events: duplicate→NONE, merge→UPDATE, new→ADD, path FP→DELETE TP.
2. superseded_by audit field; deleted items excluded from active store.
3. Soft-wire merge_tp_signatures when TORII_MEMORY_EVENTS=1.

### Insight
Recall-time conflict without write-path events lets deleted noise re-enter. Highest ROI: **Mem0 event policy on TP/FP writes**.

### Feature shipped (F93)
- `scripts/memory_event_policy.py` plan/apply/promote/fixture
- bench_security_gate merge uses events; pack + PRODUCT

### Loop-engineering practice used
**Tools-as-code memory** — explicit events over silent append.

### Metric
- Offline: fixture_pass (NONE+UPDATE+ADD+DELETE); bench fixture; 530 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~105s; log_streaming=true; POST_COMMENT=0

### SHA
e81a1a56d3021ef859372502a7051fbf0504bd98

## 2026-08-01 — F92 smoke skill-loop L3 + CI job-summary annotation

### Papers / posts / OSS
- Loop Engineering: readiness must be in smoke/CI, not only CLI.
- Prior F91 scorecard existed; smoke stopped at F79; CI never showed skill-loop.

### OSS / eng patterns
1. smoke step 6: skill_loop fixture L3 + gate --skill-loop-only.
2. Reusable workflow job summary for skill loop after torii/gate.
3. Optional advisory commit status `torii/skill-loop` (TORII_SKILL_LOOP_STATUS_COMMIT=1).

### Insight
Scorecards that are not in smoke rot. Highest ROI: **smoke L3 + CI annotation**.

### Feature shipped (F92)
- smoke-torii-gate.sh [6/6] skill loop
- torii-review-reusable.yml skill-loop summary (+ optional status)
- PRODUCT F91/F92 note

### Loop-engineering practice used
**Verifier in the default path** — smoke fails if skill loop not L3.

### Metric
- Offline: smoke PASS with skill_loop L3; 527 pytest
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~91s; log_streaming=true; POST_COMMENT=0

### SHA
5dd5d47df2879f7a5b907cae4695cba4881376be

## 2026-08-01 — F91 skill compound loop readiness scorecard

### Papers / posts / OSS
- Loop Engineering readiness scorecards L0–L3 for explicit loops.
- F90 branded skill loop; ops could not answer "is skill path ready?".

### OSS / eng patterns
1. `skill_loop_status.py` — stages/pack/active skills/wiring/deep fixtures.
2. Embed in workflow scorecard + install-guide markdown.
3. `torii_gate_status --skill-loop-only` ops surface (merge exit unchanged).

### Insight
Brand without ops readiness is untestable. Highest ROI: **L0–L3 skill-loop scorecard**.

### Feature shipped (F91)
- skill_loop_status status/scorecard/fixture/markdown
- workflow_as_code + install-guide + pack; PRODUCT note

### Loop-engineering practice used
**Readiness scorecard on the loop itself.**

### Metric
- Offline: fixture L3 100%; workflow scorecard skill_loop ready; 527 pytest; smoke PASS
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~120s; log_streaming=true; POST_COMMENT=0

### SHA
5da51871070b3c6e1651273179aff14fc87fb90f

## 2026-08-01 — F90 brand skill loop + ICP packaging

### Papers / posts / OSS
- AppSec fatigue 2026: AI multiplies alerts — need quieter automation.
- Market one-liners (Endor/OX): workflow-native AppSec, not annual theater.
- Torii F78–F89 shipped intelligence; brand lagged the skill compound loop.

### OSS / eng patterns
1. PRODUCT consolidates maker/checker + skill loop mental models + ICP table.
2. Landing: Compounds stat, ICP card, skill pipeline pipes, maker/checker/compound.
3. One-liners lock: fatigue + skills + tagline.

### Insight
Intelligence without a customer-facing skill loop story under-sells the moat. Highest ROI: **package route→hit→fitness→dual→attr→inject**.

### Feature shipped (F90)
- PRODUCT.md rewrite; brand/TORII.md ICP + one-liners; landing.html; README; INSTALL-GUIDE
- research note brand-skill-loop-icp-pattern.md

### Loop-engineering practice used
**Ship what you measure** — brand describes measured loops, not aspirational ASPM.

### Metric
- Offline: smoke PASS; 522 pytest
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~80s; log_streaming=true; POST_COMMENT=0

### SHA
3645a46416fca34b94b67fb8514a6425ab81039e

## 2026-08-01 — F89 attribution-ranked skill inject (router free-rider skip)

### Papers / posts / OSS
- Assay / Not All Skills Help: mask inert skills at inference, not only at adopt.
- Prior F88: LOO at adopt; inject still path-only — free-riders could re-enter full bodies.
- F85 demote pattern: durable ledger → router score delta.

### OSS / eng patterns
1. skill_attribution cycle → `.torii/skill-attribution.json` (avg contribution).
2. skill_router attr_boost + free_rider_skipped (index-only).
3. Soft post-run stage after skill_router_score.

### Insight
Attribution that never ranks inject is half a loop. Highest ROI: **feed LOO ledger into progressive router**.

### Feature shipped (F89)
- skill_attribution ledger/ingest/cycle/router_boosts
- skill_router select uses attr boosts + free-rider skip
- run-torii-review stage; PRODUCT + tests

### Loop-engineering practice used
**Ship the feedback path** — measure → durable ledger → next-run inject policy.

### Metric
- Offline: fixture_pass; free_rider_skipped; chain boost>0; 522 pytest
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~92s; log_streaming=true; POST_COMMENT=0

### SHA
3d803c91e9cf81f726d3df47c1a879adf97071f2

## 2026-08-01 — F88 per-skill LOO attribution (reject free-riders)

### Papers / posts / OSS
- **Not All Skills Help / Assay** (arXiv 2606.15390): retire inert skills; per-task masking beats global purge.
- Ablation LOO as component attribution for trustworthy gates.
- Prior F86/F87: pack-level contribution_pp only — free-riders could still bulk-adopt.

### OSS / eng patterns
1. solo_hit + unique keywords + LOO delta → contribution score.
2. free_rider = no solo_hit and no unique (always-on floored).
3. auto-adopt reject `f88_zero_attribution` unless --force.

### Insight
Pack dual-rollout is necessary but not sufficient. Highest ROI: **attribute which skill drives the delta**.

### Feature shipped (F88)
- `scripts/skill_attribution.py` attribute/rank/filter/fixture
- skill_auto_adopt F88 gate + per-proposal attribution filter
- pack/workflow/PRODUCT; tests

### Loop-engineering practice used
**Component ablation** — LOO + unique coverage before promote.

### Metric
- Offline: fixture_pass; free-rider contribution=0; gate f88 ok; 520 pytest
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~93s; log_streaming=true; POST_COMMENT=0

### SHA
e02ed8cbf103409122fe0a3cf6cc2b147d02ae62

## 2026-08-01 — F87 dual contribution gate on skill auto-adopt

### Papers / posts / OSS
- **SkillsBench**: with vs without is the only honest skill utility metric.
- SkillOpt / Loop Engineering: default REJECT until held-out gates pass.
- Prior F82: critic+fitness fixtures; F86 dual metrics not wired into adopt.

### OSS / eng patterns
1. `run_regression_gates` runs `skill_dual_rollout dual` as f86_dual_contribution.
2. Fail adopt when dual_pass false or skill_contribution_pp ≤ 0.
3. Toggle TORII_SKILL_AUTO_ADOPT_DUAL (default on).

### Insight
Auto-adopt without contribution proof reintroduces dead skills. Highest ROI: **wire F86 dual into F82 gates**.

### Feature shipped (F87)
- skill_auto_adopt regression gates + dual contribution_pp>0
- status dual_gate flag; tests for gate/status; PRODUCT + workflow

### Loop-engineering practice used
**Verifier before promote** — dual-rollout is a hard pre-adopt gate.

### Metric
- Offline: gate passed; dual contribution_pp=50; fixture_pass; 516 pytest
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~84s; log_streaming=true; POST_COMMENT=0

### SHA
668ff8955ad0d361145fcb9e87dd3748fb303af0

## 2026-08-01 — F86 dual-rollout skill contribution + multi-tenant skill promote

### Papers / posts / OSS
- **SkillsBench** (arXiv 2602.12670): paired no-Skills vs Skills; curated +16.2pp.
- **Agent Skill Evaluation** (arXiv 2606.11435): dual-rollout gap = contribution signal.
- **FederatedSkill**: multi-tenant skill theme promote (min_tenants≥2).
- Prior F84/F85: hits + demote without with/without delta or skill promote gate.

### OSS / eng patterns
1. hit_rate(with skill language) − hit_rate(ablated) while F70 recall holds.
2. Multi-tenant promote of skill-tagged signals only; block single-tenant noise.
3. Non-skill security themes excluded from promoted-skill-themes.json.

### Insight
Skills without a measurable contribution delta are unvalidated library bulk. Highest ROI: **SkillsBench-style dual-rollout + tenant promote**.

### Feature shipped (F86)
- `scripts/skill_dual_rollout.py` — dual / all / promote / fixture / status
- Soft promote stage after skill_fitness; pack + workflow + toggle
- PRODUCT dual-rollout mental model

### Loop-engineering practice used
**Paired baseline** — every skill claim needs with vs without (ablated) evidence.

### Metric
- Offline: fixture_pass; contribution_pp=50; multi-tenant promote; single blocked
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~120s; log_streaming=true; POST_COMMENT=0
- pytest: 514 passed

### SHA
55be798e2646965b3174383412680a610d101b4c

## 2026-08-01 — F85 skill fitness ledger + federated skill themes

### Papers / posts / OSS
- **FederatedSkill** (arXiv 2606.03143): skill library as federation unit; privacy-safe themes (+44% success).
- **Agent Skill Evaluation & Evolution** (arXiv 2606.11435): longitudinal skill quality; drop non-contributors.
- MUSE-Autoskill lifecycle evaluate → demote/refine.
- Prior Torii F84: skill-hits.json with no durable demote/federate action.

### OSS / eng patterns
1. Compound hits into `.torii/skill-fitness.json` (selected_n / hit_n / hit_rate).
2. Soft demote low hit_rate after min samples → index-only in F84 router.
3. Federate skill themes as F77 signals (id + hits + tenant_hash only).

### Insight
Measure without action is theater. Highest ROI: **fitness ledger closes F84 → demote zombies + federate winners**.

### Feature shipped (F85)
- `scripts/skill_fitness.py` — ingest/demote/boosts/federate/cycle/fixture
- skill_router applies boosts + skips demoted full inject
- run-torii-review stage; pack + workflow + toggle; PRODUCT fitness model

### Loop-engineering practice used
**Verifier-driven evolution** — hit_rate is the fitness signal; demote is the gate.

### Metric
- Offline: fixture_pass; zombie demoted; good boost 2.0; privacy_ok; router skips demoted
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~92s; log_streaming=true; POST_COMMENT=0
- pytest: 510 passed

### SHA
58df5c4f24d0d2209b08549d5a151aecf3ceb177

## 2026-08-01 — F84 progressive skill router + hit scoring

### Papers / posts / OSS
- Progressive disclosure (Claude Skills / Simon Willison / HN): index all skills; full body only for relevant verticals.
- Vercel agent evals: ~56% of cases skills never invoked when dump-only — routing + measurement required.
- **FederatedSkill** (arXiv 2606.03143): privacy-preserving collaborative skill evolution via themes, not raw trajectories.
- Prior Torii: F69 bulk inject ≤8 skills; F82 auto-adopt; no path relevance or post-run hit rate.

### OSS / eng patterns
1. EXT_THEMES + skill frontmatter/DEFAULT_TRIGGERS → rank top-K; always-on core skills.
2. Replace F69 bulk block with index + selected full skills (TORII_SKILL_ROUTER_REPLACE).
3. Post-run keyword/title hit score → skill-hits.json; federated_skill_themes = ids only.

### Insight
Shipping skills without progressive load or invocation metrics wastes context and evolution signal. Highest ROI: **route by path themes + measure hits**.

### Feature shipped (F84)
- `scripts/skill_router.py` — index / select / inject / score / fixture / status
- assemble-context progressive inject; run-torii-review skill_router_score stage
- Pack + workflow capability + feature toggle `TORII_SKILL_ROUTER` (default on)
- PRODUCT progressive-skills mental model; adopted tool skill-router

### Loop-engineering practice used
**Ship what you measure** — skill hit_rate is a first-class post-run metric for F74/F82.

### Metric
- Offline: fixture_pass; py selects f74+always; good hit_rate=1.0 > weak=0.0; privacy_ok
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~77s; log_streaming=true; tool_call_turns=7; POST_COMMENT=0
- pytest: 506 passed

### SHA
6bd7d30a81da44bc4443093125265208c9ad56ee

## 2026-08-01 — F83 pack skills ship + paper eval-trace report

### Papers / posts / OSS
- Pack completeness: evolved skills must reach targets (install matrix).
- Eval vaults for agent papers need aggregate tables, not only raw dirs.
- Prior Torii: F82 adopted skills; install maxdepth-1 dropped `agent/skills/`.

### OSS / eng patterns
1. rsync agent/skills + agent/tools on pack install.
2. Aggregate summary.json → EVAL-REPORT.md/json for paper.
3. Soft federated promote post-run.

### Insight
Self-evolution that never ships in `install-torii.sh` does not compound for customers. Highest ROI: **fix pack path + paper report**.

### Feature shipped (F83)
- install-torii copies `agent/skills/` + `agent/tools/`
- `scripts/eval_trace_report.py` report/fixture/status
- `docs/benchmarks/traces/EVAL-REPORT.md` + eval-report.json
- fed promote soft stage; pack + GATE docs

### Loop-engineering practice used
**Ship what you measure** — skills + eval report as first-class artifacts.

### Metric
- Offline: fixture_pass; install ships skill-f74-*; eval report n_runs≥11; privacy_ok
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~115s; skills in prompt; log_streaming=true; POST_COMMENT=0
- pytest: 500 passed

### SHA
`4720d97ad07a3eb6416a1649f5a6298b8fde854f`

## 2026-08-01 — F82 safe skill auto-adopt (self-evolution close-loop)

### Papers / posts / OSS
- SkillOpt / Hermes: held-out gates before skill adopt.
- Loop Engineering: REJECT until verified.
- Prior Torii: F74 `validated_adopt` skills never entered `active/`.

### OSS / eng patterns
1. Pre/post regression fixtures (F78 critic + F74 fitness).
2. Rollback active skills if post-adopt gates fail.
3. Default off; malicious proposals never candidates.

### Insight
Evolution without adopt is theater. Highest ROI: **safe auto-adopt with offline gates** for already-validated F74 skills.

### Feature shipped (F82)
- `scripts/skill_auto_adopt.py` — candidates/gate/adopt/cycle/fixture/status
- Adopted into active: skill-f74-prefer-chain-json, skill-f74-exploit-scenario
- Wire run-torii-review when TORII_SKILL_AUTO_ADOPT=1
- Brand/README Modal-live + PRODUCT self-evolution note

### Loop-engineering practice used
**Verifier before promote** — fixtures must pass before and after adopt.

### Metric
- Offline fixture_pass; gates_passed; adopted skill-f74-prefer-chain-json + skill-f74-exploit-scenario
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK ~74s; F74 skills in maker prompt; log_streaming=true; POST_COMMENT=0
- pytest: 497 passed

### SHA
`224a37c9818a6d1c5fc54219687c1f1c8dbdb919`

## 2026-08-01 — F81 optional LLM checker atop F78

### Papers / posts / OSS
- QASecClaw / VulAgent: separate validation agent after discovery.
- Prior Torii F78 deterministic panel; optional semantic pass was the open gap.

### OSS / eng patterns
1. Bounded OpenRouter chat → JSON-only schema.
2. Soft-skip when disabled/no key/API fail (F78 remains authority).
3. Redact secrets/paths before model; fold into F78 weights.

### Insight
LLM critics without a free deterministic base burn money and fail closed poorly. Highest ROI: **optional F81 on top of F78**, default off.

### Feature shipped (F81)
- `scripts/llm_critic.py` — run / fixture / status (+ mock)
- Integrated into `second_agent_critic` as `f81_llm` checker
- `run-torii-review.sh` stage when `TORII_LLM_CRITIC=1`
- Toggle default off; pack + workflow capability

### Loop-engineering practice used
**Cheap default + optional expensive verifier** — deterministic first, LLM second.

### Metric
- Offline fixture_pass; weak endorse_demote; privacy_ok
- Live: **Modal** pytorch#191813 deepseek/deepseek-v4-pro --llm-critic BIT3_OK ~143s; f81 recommended_verdict=REQUEST_CHANGES; log_streaming=true; POST_COMMENT=0
- pytest: 494 passed

### SHA
`39d55323aa90648f5d6b05d71ff5e7c3df276a27`

## 2026-08-01 — F80 Modal secrets bootstrap (live e2e unblock)

### Papers / posts / OSS
- Modal secrets model: named secrets injected into functions; missing names fail at run.
- Ops pattern: filtered dotenv → `modal secret create --from-dotenv` (never log values).
- Prior Torii: F67 Modal log streaming unusable without secrets.

### OSS / eng patterns
1. Bootstrap from local `.env` + `gh auth token`.
2. Configurable secret names for multi-brand workspaces (torii vs luffy).
3. Soft preflight in `trigger-review.sh modal`.

### Insight
Intelligence loops that never reach Modal waste F67 streaming. Highest ROI: **make secrets a one-command deterministic tool**.

### Feature shipped (F80)
- `scripts/modal_secrets_bootstrap.py` — status / plan / apply / fixture
- Creates `torii-openrouter` + `torii-github` from OPENROUTER_API_KEY + gh token
- `modal_app/app.py` honors TORII_MODAL_*_SECRET; entrypoint prints expected names
- `trigger-review.sh` modal path soft-applies secrets
- Pack + workflow capability entry

### Loop-engineering practice used
**Deterministic ops pipeline** — secrets as code path with dry-run plan + no value leakage.

### Metric
- Offline fixture_pass; apply creates both secrets; status ready=true
- Live: **Modal** pytorch/pytorch#191813 deepseek/deepseek-v4-pro BIT3_OK elapsed≈87s log_streaming=true tool_call_turns=10 POST_COMMENT=0; secrets torii-* bootstrapped
- pytest: 490 passed

### SHA
`2cd2963e7f68ffc53e358c394984647580f117f9`

## 2026-08-01 — F79 workflows-as-code + install capability guide

### Papers / posts / OSS
- Loop Engineering: loops as validated artifacts + readiness scorecards.
- Declarative agent/CI pipelines (stages, soft-fail, entries).
- Install gap: pack RUNTIME_SCRIPTS lagged F70–F78 intelligence tools.

### OSS / eng patterns
1. Single YAML source of truth for stages + capabilities.
2. Validate → L0–L3 readiness without LLM.
3. install-guide deep-links Maker/Checker/Memory features for adopters.

### Insight
Intelligence features that never ship in `install-torii.sh` pack are dead to customers. Highest ROI: **workflows-as-code + pack completeness + install matrix**.

### Feature shipped (F79)
- `docs/workflows/torii-gate.workflow.yaml` + `scripts/workflow_as_code.py`
- Commands: validate / plan / status / install-guide / pack-check / fixture / scorecard
- Pack RUNTIME_SCRIPTS gains F70–F78 scripts; smoke F79 step
- `docs/workflows/INSTALL-GUIDE.md`; GATE.md pointer
- Adopted tool `workflow-as-code`

### Loop-engineering practice used
**Readiness scorecard on the loop itself** — validate scripts/stages; L3 only when complete.

### Metric
- Offline: fixture L3 100%; pack-check install_lists_all; smoke F79 green
- Live: pytorch/pytorch#191813 deepseek/deepseek-v4-pro fitness 0.8294 L2; critic present; workflow status ready=true; POST_COMMENT=0; Modal blocked → local Hermes
- pytest: 487 passed

### SHA
`40a471bf098f5b6d722b4bc2d151243f421fa7ef`

## 2026-08-01 — F78 multi-checker second-agent critic (maker/checker)

### Papers / posts / OSS
- **QASecClaw** (arXiv 2605.01885): multi-agent validation after discovery cuts FPs.
- **VulAgent / Argus**: decouple maker findings from confirmation.
- Loop Engineering **loop-verifier**: default REJECT until evidence.
- Prior Torii F70–F75 checkers were siloed; missing a single post-run panel.

### OSS / eng patterns
1. Orchestrate existing deterministic checkers as a second "agent" (no LLM).
2. Demote weak APPROVE without path evidence.
3. Product mental model: security merge authority = maker + checker + memory.

### Insight
Shipping more maker intelligence without an independent checker lets weak APPROVE slip. Highest ROI: **compose F70+F72+F73+F75 into one critic panel** and demote.

### Feature shipped (F78)
- `scripts/second_agent_critic.py` — run / inject / fixture / scorecard / status
- Panel: structure + F70 dual critic + F72 chain + F73 fitness + F75 memory
- Wire assemble-context inject + run-torii-review post stage; optional demote
- Brand/PRODUCT mental model: Maker/Checker; toggle `TORII_SECOND_CRITIC`
- Adopted tool `second-agent-critic`

### Loop-engineering practice used
**Independent verifier panel** — maker writes review; checker scorecard L0–L3; demote on weak evidence.

### Metric
- Offline: good composite≈0.74 weak≈0.39 delta≈0.35; weak APPROVE→COMMENT; inject_ok
- Live: pytorch/pytorch#191813 deepseek/deepseek-v4-pro fitness 0.8694 L3; SECOND_CRITIC=1 panel L1 composite=0.54; no demote (maker REQUEST_CHANGES); POST_COMMENT=0; Modal blocked → local Hermes
- pytest: 481 passed

### SHA
`bc847f97e6696b0084abd1ca547a6999c8467c66`

## 2026-08-01 — F77 cross-tenant hub federated signal ingest

### Papers / posts / OSS
- IETF multi-tenant agent FL privacy draft (2026): aggregate without raw tenant payloads.
- Multi-tenant RAG isolation: path/snippet leakage is the failure mode.
- Prior Torii: F65 tenant dirs, F71 local federate, F75 scoped recall — hub merge missing.

### OSS / eng patterns
1. Privacy-safe signal schema (theme/CWE/keywords/basenames + tenant_hash).
2. Unique tenant_hashes for true multi-tenant counts (not naive +1).
3. Promote gate min_tenants/min_hits; poison path/secret strip.

### Insight
Local federation compounds one org; **hub multi-tenant promote** is what turns every customer run into shared security intelligence without leaking code.

### Feature shipped (F77)
- `scripts/federated_hub_ingest.py` — collect/ingest/promote/status/fixture/from-run
- Hub write: `memory/federation/federated-signals.json` + INDEX; tenant-local federation copy
- `hub-ingest-run.py` + `build-hub-payload.py` wire; F75 prefers hub federation path
- Toggle `TORII_FEDERATED_HUB`; adopted tool `federated-hub-ingest`

### Loop-engineering practice used
**Privacy-preserving aggregation + promote scorecard** — default strip; multi-tenant evidence required to promote.

### Metric
- Offline fixture: sqli tenants=2; privacy_file_ok; promote only multi-tenant
- Live: pytorch/pytorch#191813 deepseek/deepseek-v4-pro fitness 0.8294 L2; hub-payload federated_signals count=4; hub ingest privacy_ok; POST_COMMENT=0; Modal blocked (torii-openrouter) → local Hermes
- pytest: 476 passed

### SHA
`ad9338d7ab461eb30e02c62338af278b7fdf07ff`

## 2026-08-01 — F76 multi-corpus bench + Juice Shop synthetic

### Papers / posts / OSS
- OWASP Juice Shop challenge taxonomy (themes only — no fork).
- Prior Torii F70 labeled pack + F71 JS taint sinks.
- 2026 AI PR review market: security-gate differentiation vs general code-quality bots.

### OSS / eng patterns
1. Multi-pack ground truth registry → aggregate offline recall.
2. License-safe synthetic Express routes for JS vulns.
3. Expand taint catalog (express sources, XSS, hardcoded JWT/API key).

### Insight
Single Python demo under-tests JS/web packs. Highest ROI: **second labeled corpus** + corpus runner so every gate feature is measured on PY+JS.

### Feature shipped (F76)
- `demo/juice-shop-synthetic/` (routes.js + stubs)
- `docs/benchmarks/cases/juice-shop-synthetic.json` (5 required cases)
- good/weak fixtures; `scripts/bench_corpus.py` list/fixture/all/taint/index
- F71 JS rules: src-js-express, sink-js-xss, sink-js-hardcoded-secret
- Adopted tool `bench-corpus`

### Loop-engineering practice used
**Measured multi-pack scorecard** — all packs must fixture_pass; average delta_recall tracked.

### Metric
- Offline: insecure-demo + juice-shop-synthetic all_pass; good_recall=1.0 weak=0; avg_delta_recall=1.0; taint_ok
- Live: pytorch/pytorch#191813 deepseek/deepseek-v4-pro fitness 0.8294 L2; POST_COMMENT=0; Modal blocked (torii-github secret) → local Hermes
- pytest: 472 passed

### SHA
`903a7cb3a57bb70c9d207303d72f398592de9cdc`

## 2026-08-01 — F75 scoped memory recall (Mem0 multi-scope TP/FP)

### Papers / posts / OSS
- **Mem0** (arXiv 2504.19413, Apache-2.0 clone `oss-memory-mem0`): multi-scope user/agent/run/app; selective retrieval; conflict detection.
- **Memory security** (arXiv 2604.16548; longitudinal safety 2026): segment memory, provenance, resist poisoning.
- Prior Torii: F64 FP, F70 TP, F71 federated, F65 tenant — inject was unscoped dump.

### OSS / eng patterns
1. Mem0 scope filters → run > repo > tenant > agent > global rank.
2. Selective retrieval → path_match + hits budget (`TORII_SCOPED_TP_MAX`).
3. Conflict policy → path-anchored FP suppresses theme-only TP; path TP beats unanchored FP.

### Insight
Compound TP/FP memory without scope ranking wastes tokens and can re-raise dismissed paths. Highest ROI: **budgeted, path-aware recall with explicit conflict resolution**.

### Feature shipped (F75)
- `scripts/scoped_memory_recall.py` — `ingest` / `recall` / `conflict` / `inject` / `fixture` / `score` / `status`
- Unified `.torii/scoped-memory.json`; prompt `<!-- torii-f75-scoped-memory -->`
- Optional supersede bulk F70 TP section; assemble-context wire; toggle `TORII_SCOPED_MEMORY`
- Adopted tool `scoped-memory-recall`

### Loop-engineering practice used
**Selective context + provenance** — only path-relevant memory enters the maker prompt; checker conflict list is explicit.

### Metric
- Offline fixture: path rank sqli>xss; conflict; privacy strip `/Users/`; inject+replace F70; pytest F75 5/5
- Live: pytorch/pytorch#191813 deepseek/deepseek-v4-pro fitness 0.8694 L3; SCOPED_MEMORY=1 TP=4 FP=0; POST_COMMENT=0; Modal blocked (torii-openrouter secret) → local Hermes
- pytest: 467 passed

### SHA
`9857d14012e867c4bbd62c79677e79e7dbc4f704`

## 2026-08-01 — F74 fitness-gated skill evolution (SkillOpt / GEPA-lite)

### Papers / posts / OSS
- **SkillOpt** (arXiv 2605.23904): skills as external state; held-out validation gate; bounded add/delete/replace; rejected-edit buffer; zero deploy LLM cost.
- **Hermes Agent Self-Evolution**: multi-dim FitnessScore + ConstraintValidator before adopt; GEPA reads traces.
- **RSEA / GEPA lineage**: trajectory feedback → reflective mutation of NL artifacts.
- Memory OSS (Mem0/Letta/Zep 2026): selective compound memory; port policy — F74 compounds *procedural* skills from fitness dims, not chat vectors.
- Loop Engineering **loop-verifier**: default REJECT until evidence.

### OSS / eng patterns
1. Hermes constraints (size/growth/structure/safety) → hard reject.
2. SkillOpt held-out gate → recommend adopt only if score≥18/25 + constraints.
3. F73 fitness_signals weak dims → deterministic dim-templated skill patches.

### Insight
F69 proposes skills from trajectory *flags*; F73 scores procedure quality but never closes the loop. Highest ROI: **fitness → bounded mutate → gate → (optional) adopt**.

### Feature shipped (F74)
- `scripts/fitness_gate_evolve.py` — `analyze` / `mutate` / `validate` / `adopt` / `inject` / `fixture` / `cycle` / `status`
- Consumes `memory/evolution/ledger.json` fitness_signals
- Ledger: `fitness_mutations`, `rejected_edits`
- Prompt inject `<!-- torii-f74-fitness-gate-evolve -->`; assemble + run-torii-review wire
- Toggles `TORII_FITNESS_GATE_EVOLVE` / `TORII_FITNESS_GATE_AUTO_ADOPT` (default off for auto-adopt)
- Adopted tool `fitness-gate-evolve`

### Loop-engineering / Hermes practice used
**Verifier-gated evolution** — maker proposes dim patches; checker constraints + held-out score; default REJECT.

### Metric
- Offline fixture: weak dims≥2; ≥1 adopt; malicious reject; inject_ok; pytest F74 5/5
- Live: pytorch/pytorch#191813 deepseek/deepseek-v4-pro fitness composite=0.8694 L3; F74 cycle proposed skill-f74-prefer-chain-json + skill-f74-exploit-scenario (both validate adopt); POST_COMMENT=0; Modal blocked (secret torii-openrouter missing) → local Hermes fallback
- pytest: 462 passed

### SHA
`165cf24c0cf6abb22ec2d9b79c71086cc361d085`

## 2026-08-01 — F73 trajectory fitness + eval-trace vault

### Papers / posts / OSS
- **Hermes Agent Self-Evolution** (NousResearch): GEPA reads execution traces; multi-dim FitnessScore (correctness / procedure / conciseness) + constraint gates before adopt.
- **Loop Engineering** loop-verifier skill: independent checker, default REJECT until evidence; checklist (scope/intent/tests).
- **H9** trajectory packaging backlog: offline eval datasets from agent-loop packages.
- Prior Torii: F69 trajectory ingest, F70 label score, F72 chain checker — none scored *loop procedure* or paper-indexed vault.

### OSS / eng patterns
1. Hermes fitness weights → deterministic path/procedure/tool/chain composite (no LLM judge cost).
2. Loop-verifier procedure contract injected into prompt as soft rubric.
3. Paper-safe vault: redacted slim summary + INDEX; large agent.log truncated/gitignored.

### Insight
Detection quality (F70–F72) was measurable; **agent procedure quality** and **durable eval traces for paper** were not. Highest ROI: score every run’s tool_use/path/procedure/chain and archive under `docs/benchmarks/traces/`.

### Feature shipped (F73)
- `scripts/trajectory_fitness.py` — `score` / `archive` / `inject` / `fixture` / `promote` / `pack`
- Multi-dim fitness + L0–L3 levels; evolution ledger `fitness_signals`
- Prompt inject `<!-- torii-f73-trajectory-fitness -->`; assemble + run-torii-review + save-trace wire
- Toggles `TORII_TRAJECTORY_FITNESS` / `TORII_TRACE_VAULT`; adopted tool `trajectory-fitness`

### Loop-engineering / Hermes practice used
**Verifier checklist + multi-dim fitness on traces** — independent post-run scorer; vault for GEPA-style future evolution.

### Metric
- Offline fixture: good composite=0.77 weak=0.38 delta=0.39; inject_ok; path deep vs basename
- Live: pytorch/pytorch#191813 deepseek/deepseek-v4-pro composite=0.8694 L3 POST_COMMENT=0
- pytest: 457 passed

### SHA
`3f82f0370411fa85880cb6992ab8187b5922988b`

## 2026-08-01 — F72 full-chain revalidation (maker/checker)

### Papers / posts
- **VulAgent** (ACL Findings 2026): hypothesis-validation multi-agent — decouple discovery from confirmation; FPR cuts when checker is separate.
- **QASecClaw** (arXiv 2605.01885): multi-agent SAST + coding-LLM contextual review for FP reduction (~88% FP cut on OWASP-style benches while holding recall).
- **Argus** (arXiv 2604.06633): multi-agent full-chain vuln detection — dependency + source→sink orchestration, not single-shot prose.
- **AutoPatch** (arXiv 2505.04195): taint similarity as symbolic flow match for verification.
- Loop Engineering (cobusgreyling): **Maker/Checker split** + readiness scorecard (checklist §4 / §9).

### OSS / eng patterns
1. deepsec revalidation pass after AI investigation.
2. Semgrep Assistant Memories compound triage — here: chain evidence is code, not only memory prose.
3. Loop-ready scorecard: mechanical `passed/total` + level rather than vibes.

### Insight
F70/F71 measure and surface evidence; the agent could still **self-approve** weak claims. Highest ROI: a **deterministic checker** that re-scores findings on path + theme + taint chain and demotes `unvalidated` narrative.

### Feature shipped (F72)
- `scripts/chain_revalidate.py` — `revalidate` / `score` / `inject` / `fixture` / `scorecard`
- Hypothesis catalog (CWE/theme keywords) + document path inheritance
- Confidence ladder: full_chain → theme_path → path_only → unvalidated / likely_fp
- Independent `verdict_checker` + Loop-Ready scorecard (L0–L3)
- Prompt inject `<!-- torii-f72-chain-revalidate -->`; assemble-context soft wire
- Toggle `TORII_CHAIN_REVALIDATE`; adopted tool `chain-revalidate`

### Loop-engineering practice used
**Maker/Checker split + scorecard** — agent is maker; `chain_revalidate` is isolated checker; scorecard command mirrors Loop Ready levels.

### Metric
- Offline fixture: good full_chain_rate=1.0 recall=1.0; weak precision=0; fixture_pass=1
- Live Hermes e2e: F70 recall=1.0 tp=4 fn=0; F72 full_chain_rate=1.0 scorecard L3 (6/6)
- pytest: 451 passed

### SHA
`dcbe5314c66c5b469e0c1e944cbe0107bfd73f05`

## 2026-08-01 — F71 deterministic taint prefilter + federated sanitized signals

### Papers / posts
- **SemTaint** (arXiv 2601.10865): multi-agent taint-spec extraction — sources/sinks/call edges; static-led + demand-driven LLM repair; modular reusable specs compound across analyses (65% of previously undetectable CodeQL JS vulns).
- **SAST-Genius** (arXiv 2509.15433): hybrid Semgrep + LLM triage/exploit validation pipeline — deterministic first, semantic second.
- **OpenAnt** (arXiv 2606.19149v2): staged agentic discovery — exposure classification then vuln detection with tool-assisted navigation.
- Eng: Semgrep “Comparing Open-Source AI Code Security Harnesses” (2026-07) — deepsec regex-prefilter → AI investigation → revalidation; VVAH adversarial verify; Assistant Memories compound triage learning.

### OSS design patterns stolen
1. **deepsec**: cheap deterministic prefilter before LLM spend (candidate sites, not free-form hunt).
2. **SemTaint**: modular source/sink catalog as code artifacts that compound; privacy-safe federation mirrors “specs not raw code”.

### Insight
F70 measured TP compound memory locally. Missing was (a) a **tools-as-code** stage that surfaces source→sink flows without LLM, and (b) **federated** sanitized signals so orgs share themes/CWEs/keywords without path trees or snippets.

### Feature shipped (F71)
- `scripts/taint_prefilter.py` — `scan` / `score` / `inject` / `federate` / `fixture`
- Modular RULES catalog (sources + sinks + JS light); function-window co-location heuristic
- Prompt inject `<!-- torii-f71-taint-prefilter -->` + `<!-- torii-f71-federated-signals -->`
- `assemble-context.sh` wires prefilter on changed files + soft federate write
- Privacy: basenames only, tenant SHA, no `/Users/`, no raw tenant strings, no snippets
- Catalog + adopted tool `taint-prefilter`; toggles `TORII_TAINT_PREFILTER` / `TORII_FEDERATED_SIGNALS`

### Metric
- Offline fixture: prefilter recall=1.0 on insecure-demo (4/4), privacy_ok=1, inject both sections
- Live Hermes e2e (`bench_security_gate.py live`): recall=1.0 tp=4 fn=0 verdict=REQUEST_CHANGES
- pytest: 444 passed

### SHA
`b9844d3764501316db976d8b9241b59346649d30`

## 2026-08-01 — F70 labeled vuln bench + dual-pass critic + TP compound memory

### Papers / posts
- **QASecClaw** (arXiv 2605.01885): multi-agent LLM + SAST filter cuts FPs ~88% on OWASP Benchmark while holding recall — validation agent after discovery is the ROI lever.
- **VulAgent** (ACL Findings 2026): hypothesis-validation multi-agent design improves accuracy and cuts FPR ~36% by decoupling discovery from confirmation.
- **Survey of Self-Evolving Agents** (arXiv 2507.21046): what/when/how to evolve — memory + inter-test-time feedback loops compound quality without weight updates.
- Eng: continual learning for agents (LangChain/Letta) — traces → memory distillation → harness/context updates.

### Insight
Torii already had FP self-learn (F62/F64) and skill evolution (F69). Missing was a **measured** detection loop: ground-truth cases, dual-pass critic (path evidence + FP demote + TP boost), and **TP signature** promotion so true positives compound like FPs. Without a scorer, self-evolution is unguided.

### Feature shipped (F70)
- `scripts/bench_security_gate.py` — `score` / `critic` / `promote` / `inject` / `fixture` / `live`
- `docs/benchmarks/cases/insecure-demo.json` — 4 required vulns (SQLi, pickle, cmdi, secrets)
- Fixtures good/weak reviews; dual-pass offline critic
- Durable `.torii/tp-signatures.json` (+ out_dir copy); assemble-context injects TP section
- Juice Shop harness doc now points at real e2e bench path

### Metric (offline fixture)
- good recall = 1.0, weak recall ≪ 0.5, `fixture_pass=1`, delta_recall > 0.5
- TP signatures promoted ≥ 4 from good fixture

### SHA
`7f054909726157148d6c877de10d3b9c8ca1a644`

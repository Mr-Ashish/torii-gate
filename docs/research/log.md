# Torii research → product log

## 2026-08-01 — F154 hub-archival cycle-adopt + F119 always priority

### Papers / posts
- F118 dual-gate adopt; F119 always budget max 3 by priority.
- F153 proposal without active inject re-spends F152 every run.
- Recovery skills must ship in always slots (memory > hub-archival > product).

### OSS design patterns stolen
1. cycle_hub_archival ensure proposal → adopt → stamp always_priority 95.
2. SKILL_DEFAULTS + TOOL_OUTCOME_PROBES for hub-archival.
3. hermes soft cycle-hub-archival after F152; fixture f154_ok.
4. F119 ranking: memory 100 > hub 95 > product 90 > critic 85.

### Insight
Proposals do not inject. Highest ROI: dual-gate cycle-adopt into always budget so hub-aware archival pages multi-tenant warm themes every PR.

### Feature shipped (F154)
- skill_auto_adopt cycle-hub-archival; skill_router always prio 95
- active skill adopted; PRODUCT/research; fixture f154_ok

### Metric
- Offline: fixture f154_ok; pytest 620
- Live: Modal pytorch#191813 BIT3_OK ~61s REQUEST_CHANGES POST_COMMENT=0 log_streaming=true

### Loop-engineering / Hermes practice used
**Propose → dual-gate adopt → always inject** — recovery skills ship under budget.

### SHA
`e2ee4a11aa8f99d435c649621843d05211ed25aa`


## 2026-08-01 — F153 hub-archival skill self-evolve from F152

### Papers / posts
- F112 memory-cli skill from F106 re-prompt signals (compound next PR).
- F152 recon-warm re-prompt without durable skill re-spends F108 every run.
- F118 dual-gate tool_blob for skill-prefer-* recovery skills.

### OSS design patterns stolen
1. _signals_from_loop: f152_recon_warm_reprompt / heat_idle from env+decide.
2. propose skill-prefer-hub-archival-early (F153 body, hub query on).
3. PROPOSAL_TOOL_BLOBS dual-gate archival auto + memory search.
4. hermes soft ingest+propose when F152 fires; fixture f153_ok.

### Insight
Soft re-prompt without skill proposal is one-shot. Highest ROI: F153 proposes hub-archival early skill so next PR avoids F152 spend.

### Feature shipped (F153)
- self_evolve F152 signals + propose hub-archival; skill_auto_adopt blob
- hermes soft wire; fixture f153_ok; PRODUCT/research

### Metric
- Offline: fixture f153_ok; pytest 620
- Live: Modal pytorch#191813 BIT3_OK ~47s REQUEST_CHANGES POST_COMMENT=0 log_streaming=true

### Loop-engineering / Hermes practice used
**Trajectory → skill compound** — recovery signals become always-on procedure.

### SHA
`bd2a2cccdbbe8d833eede5f414d7317a131a4d24`


## 2026-08-01 — F152 recon-warm hub soft re-prompt (F108)

### Papers / posts
- F108 shared soft re-prompt budget; F122/F137 recovery paths.
- F150/F151 demote when hub heat ignored — demote-only leaves no mid-run recovery.
- Agent cost guides: one paid attempt max under budget.

### OSS design patterns stolen
1. should_reprompt_recon_warm via F150 checker (heat + local_idle + tool_turns).
2. F108 kind=f152 shared with f49/f106/f122/f137.
3. reprompt-write marker + hermes soft second pass.
4. fixture f152_ok; TORII_RECON_WARM_REPROMPT.

### Insight
Critic demote without budgeted re-prompt is post-mortem only. Highest ROI: one F108 soft re-prompt to honor multi-tenant warm themes before final verdict.

### Feature shipped (F152)
- archival_memory_search reprompt-decide/write; reprompt_budget f152; hermes wire
- fixture f152_ok; PRODUCT/research

### Metric
- Offline: fixture f152_ok; pytest 620
- Live: Modal pytorch#191813 BIT3_OK ~57s REQUEST_CHANGES POST_COMMENT=0 log_streaming=true

### Loop-engineering / Hermes practice used
**Budgeted recovery before reject** — shared attempt ceiling compounds quality without runaway spend.

### SHA
`357f4bf7eef10ade5108057e61fcb6ed5202bd47`


## 2026-08-01 — F151 recon-warm hub demote-eval + doctor surface

### Papers / posts
- F128 demote-eval paper path for hub gap critics.
- F150 recon-warm hub critic without offline demote pack / doctor surface.
- Loop-eng observability: demote rates must be measured, not only panel-local.

### OSS design patterns stolen
1. demote-eval case recon_warm_hub_idle_approve + paper recon_warm_hub_idle_demoted.
2. skill_loop recon_warm_hub_ok wire (f150 + demote-eval case strings).
3. doctor soft surface recon_warm_hub_ok; product scorecard metrics F151.
4. fixture skill-loop requires recon_warm_hub_ok.

### Insight
Panel demote without paper metric leaves EVAL vault blind. Highest ROI: F151 demote-eval + doctor/scorecard surface for recon-warm hub.

### Feature shipped (F151)
- demote-eval recon-warm case; skill_loop/doctor/scorecard surface
- PRODUCT/research/brand; traces

### Metric
- Offline: demote-eval eval_pass; recon_warm_hub_ok; pytest 620
- Live: Modal pytorch#191813 BIT3_OK ~48s REQUEST_CHANGES POST_COMMENT=0 log_streaming=true

### Loop-engineering / Hermes practice used
**Measured demote rate** — paper metric next to critic panel.

### SHA
`1b97f0e8d3c7c41fd8ba0508659808bfa9b07a6e`


## 2026-08-01 — F150 recon-warm hub critic demote

### Papers / posts
- F127/F139/F143 hub gap critics: multi-tenant pressure + local idle → demote.
- F148/F149 recon-warm federate + hub query without enforcement leave APPROVE free.
- Loop-eng maker/checker: federation without demote is dashboard theater.

### OSS design patterns stolen
1. run_f150_recon_warm_hub heat from multi-tenant recon-warm signals.
2. local_idle when archival-search hub_boost_n=0 / hub themes empty under heat.
3. decide_verdict demotes APPROVE; inject brief F150; fixture f150_ok.
4. TORII_RECON_WARM_HUB_CRITIC / THR.

### Insight
Hub warm query without critic demote can be soft-disabled. Highest ROI: F150 demotes APPROVE when multi-tenant retrieval heat is ignored.

### Feature shipped (F150)
- second_agent f150_recon_warm_hub + decide_verdict + fixture/tests
- PRODUCT/research/brand; traces

### Metric
- Offline: fixture f150_ok; pytest 620 passed
- Live: Modal pytorch#191813 BIT3_OK ~61s REQUEST_CHANGES POST_COMMENT=0 log_streaming=true

### Loop-engineering / Hermes practice used
**Maker/checker demote on multi-tenant recon-warm ignore** — closed-loop federation.

### SHA
`41a34cc3dbf69ba142a94e12bfe74801108097f9`


## 2026-08-01 — F149 hub recon-warm → archival auto-query

### Papers / posts
- F148 hub post-score without query bias is write-only federation.
- F144 multi-hop expands local graph themes into auto-query.
- Mem0 multi-tenant: shared themes must change next retrieval.

### OSS design patterns stolen
1. post_score_recon_warm_hub themes fold into auto_from_paths query.
2. apply_hub_theme_boost soft score on matching hits.
3. TORII_RECON_WARM_HUB_QUERY; mode auto_hub; fixture f149_ok.
4. PRODUCT/research/brand + traces.

### Insight
Federated warm themes that never enter archival search leave cross-tenant heat inert. Highest ROI: hub themes expand auto-query + boost ranking like F144 graph expand.

### Feature shipped (F149)
- archival_memory_search hub warm query expand + hit boost
- fixture f149_ok; PRODUCT/research

### Metric
- Offline: fixture f149_ok; pytest 619 passed
- Live: Modal pytorch#191813 BIT3_OK ~51s REQUEST_CHANGES POST_COMMENT=0 log_streaming=true

### Loop-engineering / Hermes practice used
**Closed-loop federation** — multi-tenant export must bias next retrieval.

### SHA
`1ed3d373a5d8170413a14b92d435b61a3c52a75b`


## 2026-08-01 — F148 recon-warm theme federate + hub post-score

### Papers / posts
- Mem0 multi-tenant: share theme/util signals not raw memory content.
- F141/F142 memory util federate + hub post-score pattern.
- F146/F147 local recon-warm without multi-tenant heat export.

### OSS design patterns stolen
1. federate_recon_warm: themes + warm_bin + tenant_hash only.
2. recon-warm-signals.json merge hits across tenants.
3. post_score_recon_warm_hub priority themes for next inject.
4. TORII_RECON_WARM_FEDERATE; fixture f148_ok privacy.

### Insight
Local reconsolidation without federation leaves multi-tenant retrieval heat silent. Highest ROI: privacy-safe warm-theme hub signals after F146 promote.

### Feature shipped (F148)
- archival_memory_search federate_recon_warm + hub post-score on reconsolidate
- fixture f148_ok; PRODUCT/research

### Metric
- Offline: fixture f148_ok; pytest 619 passed
- Live: Modal pytorch#191813 BIT3_OK ~54s REQUEST_CHANGES POST_COMMENT=0 log_streaming=true

### Loop-engineering / Hermes practice used
**Privacy-safe multi-tenant compound** — retrieval heat federates as themes only.

### SHA
`6b94884ff91e87f032247e18e02c806ae92c5269`


## 2026-08-01 — F147 recon-warm → core tier promote

### Papers / posts
- MemGPT/Letta: core = always-in-context; archival cold until paged.
- F146 reconsolidation stamps last_retrieved_at without tier promote.
- OS hierarchy must compound retrieval warm into core budget.

### OSS design patterns stolen
1. recon_warm_meta windowed last_retrieved / recon flag (skip superseded).
2. classify_item warm → core; metrics core_recon_warm.
3. scoped_memory_recall passes recon fields on TP load.
4. TORII_MEMORY_RECON_CORE + HOURS; fixture f147_ok.

### Insight
Reconsolidation without tier promotion leaves warm TPs archival. Highest ROI: F147 promotes recent retrieves into core inject slots.

### Feature shipped (F147)
- memory_tiers recon-warm core promote + scoped recall field pass-through
- fixture f147_ok; PRODUCT/research

### Metric
- Offline: fixture f147_ok; pytest 619 passed
- Live: Modal pytorch#191813 BIT3_OK ~59s REQUEST_CHANGES POST_COMMENT=0 log_streaming=true

### Loop-engineering / Hermes practice used
**Warm store → hot context** — retrieval write-back compounds into OS hierarchy inject.

### SHA
`57c87b4f32b1f6154c936b68813a16f9f7d2f8b4`


## 2026-08-01 — F146 archival reconsolidation on promote

### Papers / posts
- Human-inspired reconsolidation upon retrieval; MemGPT/Letta archival→core should warm durable state.
- SuperLocalMemory / agent-memory surveys: retrieval without learning is write-only context tax.
- F145 supersede filter: only non-superseded hits may reconsolidate.

### OSS design patterns stolen
1. `reconsolidate_hits` after F145 filter: hits++ / last_retrieved_at / soft effective bump.
2. Ledger `.torii/archival-reconsolidation.json` (ids only, privacy-safe).
3. `TORII_ARCHIVAL_RECONSOLIDATE=1`; `--no-reconsolidate`; fixture f146_ok.
4. PRODUCT/research/brand + traces f146-archival-reconsolidation/.

### Insight
Paging cold memory into the prompt without updating the store leaves next PR cold. Highest ROI: reconsolidate surviving TP hits on promote so retrieval compounds rank.

### Feature shipped (F146)
- archival_memory_search reconsolidation on auto/promote
- fixture f146_ok + tests; PRODUCT/research

### Metric
- Offline: fixture f146_ok; pytest 619 passed
- Live: Modal pytorch#191813 BIT3_OK ~62s REQUEST_CHANGES POST_COMMENT=0 log_streaming=true

### Loop-engineering / Hermes practice used
**Retrieval strengthens memory** — maker/checker filter first; reconsolidation is measured write-back.

### SHA
`d0f6a90fb4de942e9ea17a20b4338f074db66a1c`


## 2026-08-01 — F145 supersede-aware archival promote

### Papers / posts
- **MemoTime** (arXiv 2510.13614): temporal faithfulness in multi-hop TKG reasoning — operator-aware paths must not revive invalid facts.
- Zep/F100–F102 supersedes + multi-hop path kinship; F144 multi-hop archival expand without filter.
- Graph agent memory survey (arXiv 2602.05665): temporal edges need retrieval-time validity checks.

### OSS design patterns stolen
1. `filter_superseded_hits` over F101/F102 `superseded_index` (multi-hop path seeds).
2. Promote section lists F145 filtered hits as do-not-re-raise (not core).
3. `TORII_ARCHIVAL_SUPERSEDE_FILTER=1`; `--no-supersede` CLI; fixture f145_ok.
4. PRODUCT/research/brand + traces f145-archival-supersede-filter/.

### Insight
F144 multi-hop paging without supersede filter resurrects resolved cold TPs as core inject. Highest ROI: MemoTime-style temporal faithfulness on the promote path so critic and paging share one validity index.

### Feature shipped (F145)
- archival_memory_search supersede filter on auto/promote
- fixture f145_ok + tests; PRODUCT/research

### Metric
- Offline: fixture f145_ok; pytest 619 passed
- Live: Modal pytorch#191813 BIT3_OK ~80s REQUEST_CHANGES POST_COMMENT=0 log_streaming=true

### Loop-engineering / Hermes practice used
**Temporal validity on retrieval** — multi-hop expand compounds with supersede demote before inject.

### SHA
`414cc3dd26bfd2645f4e1350ca0fa7bd15825537`


## 2026-08-01 — F144 graph multi-hop → archival promote

### Papers / posts
- MemGPT archival paging (F98) + Zep multi-hop (F100–F102).
- Cold TP themes only linked via co_path never paged if auto uses basenames alone.
- Letta core/archival: just-in-time page cold facts into working context.

### OSS design patterns stolen
1. graph_themes_for_paths multi-hop theme harvest (privacy themes only).
2. auto_from_paths folds themes into archival query; promote lists F144.
3. TORII_ARCHIVAL_GRAPH_HOPS=2; --no-graph / --graph-hops CLI.
4. fixture f144_ok; PRODUCT/research.

### Insight
Graph multi-hop without archival expand leaves cold related vulns unpaged. Highest ROI: compound hop themes into MemGPT auto-promote.

### Feature shipped (F144)
- archival_memory_search graph multi-hop auto + promote
- fixture/tests; traces f144-graph-archival-promote/

### Metric
- Offline: fixture f144_ok; pytest archival
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Compound retrieval paths** — temporal hop feeds archival paging.

### SHA
`0925b30362ad935d63d3bdfe25ea763827d889f5`


## 2026-08-01 — F143 memory util hub gap critic

### Papers / posts
- F127/F139 hub gap critic: multi-tenant gap_pressure + local idle → demote APPROVE.
- F141/F142 memory util federate + hub without panel demote on hub gap.
- Mem0 multi-tenant: under-use of memory tools is a systemic risk signal.

### OSS design patterns stolen
1. run_f143_memory_hub_gap (weight 0.07) + decide_verdict demote.
2. post_score_memory_util_hub gap_pressure + local audit inject unused.
3. fixture f143_ok; inject brief; PRODUCT/research.
4. TORII_MEMORY_HUB_GAP_CRITIC / THR defaults on.

### Insight
Hub post-score without critic demote is dashboard. Highest ROI: F127-style panel demote when multi-tenant memory util gap meets local inject-idle.

### Feature shipped (F143)
- second_agent f143_memory_hub_gap + fixture/tests
- PRODUCT/research/brand; traces f143-memory-hub-gap-critic/

### Metric
- Offline: fixture f143_ok; pytest second_agent_critic
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Maker/checker demote on multi-tenant gap** — memory mirrors recovery F127.

### SHA
`6e988cd639b0e2ff0371fa7b5d0dc8a191c6d7a2`


## 2026-08-01 — F142 memory util hub post-score compound

### Papers / posts
- F125/F138 hub post-score: federated util → skill priority for next inject.
- Mem0 multi-tenant: share util themes not raw memory content.
- F141 federate without post-score left memory skill rank inert.

### OSS design patterns stolen
1. post_score_memory_util_hub + hub-score CLI + inject marker.
2. skill_router always/select bump for skill-prefer-memory-cli-early.
3. soft fitness ingest_hub_recovery reshape; fixture f142_*.
4. run-torii-review/save-trace wiring.

### Insight
Federated memory util without hub post-score is inert. Highest ROI: F125-style priority compound so multi-tenant tool-effective memory skills win always slots.

### Feature shipped (F142)
- memory_tool_audit hub post-score/inject/hub-score
- skill_router memory hub deltas; PRODUCT/research
- traces f142-memory-util-hub-compound/

### Metric
- Offline: fixture f142_ok privacy; pytest memory_tool_audit
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Federate → post-score → prioritize next cycle** — memory mirrors recovery F125.

### SHA
`61e5c3c5cb12b6257ec8505ad7a8a7e12a6fd780`


## 2026-08-01 — F141 memory util federate + critic demote

### Papers / posts
- Mem0/Letta: memory only helps if tools are called mid-run.
- IFCMemoryBench: utilization is a first-class memory quality axis.
- F105/F106 audit+re-prompt without federate/panel demote left gap local-only.

### OSS design patterns stolen
1. federate_memory_util → memory-util-signals.json (bins + tool ids).
2. second_agent f141_memory_util weight 0.07 demote inject_unused.
3. audit soft federate; fixture f141_*; save-trace; PRODUCT.
4. TORII_MEMORY_UTIL_FEDERATE / TORII_MEMORY_UTIL_CRITIC defaults on.

### Insight
Memory inject without tool calls is theater. Highest ROI: F121-style federate + critic demote for Mem0/Letta tool discipline.

### Feature shipped (F141)
- memory_tool_audit federate + critic checker
- PRODUCT/research/brand; traces f141-memory-util-federate-critic/

### Metric
- Offline: fixtures f141_ok privacy; pytest memory_tool_audit + critic
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Measure utilization → federate → critic demote** — memory mirrors skill util F121/F136.

### SHA
`eee5338d2661e9aeb6f5df830165fd01deffc9df`


## 2026-08-01 — F140 scorecard hub attribution LOO floor

### Papers / posts
- Assay / Not All Skills Help: LOO free-rider retirement without multi-tenant shield kills ops skills.
- F127 recovery hub_ingested floor; F138/F139 scorecard hub without attr floor.
- FederatedSkill: hub themes must compound into attribution, not only demote/priority.

### OSS design patterns stolen
1. _load_scorecard_hub_skills (fitness scorecard_ops + F138 hub deltas).
2. attribute() scorecard_floor ≥0.85 (tool ≥1.0); free_rider blocked.
3. fixture f140_ok + off-flag free-rider; tests; PRODUCT.
4. TORII_SKILL_ATTR_SCORECARD default on.

### Insight
Hub post-score + critic without attribution floor still LOO-kills multi-tenant ops skills. Highest ROI: F127-style contribution floor for scorecard hub evidence.

### Feature shipped (F140)
- skill_attribution scorecard hub LOO floor + fixture f140_*
- PRODUCT/research/brand; traces f140-scorecard-hub-attr/

### Metric
- Offline: fixture f140_ok; pytest skill_attribution
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Measure → federate → attribute floor** — scorecard ops mirror recovery F127 attr shield.

### SHA
`3ac766bafbfad426ab13a36db6c8c0afdc60eb9d`


## 2026-08-01 — F139 scorecard hub gap critic

### Papers / posts
- F127 recovery hub gap critic: multi-tenant gap_pressure + local idle → demote APPROVE.
- Loop-eng maker/checker: independent validation demote rate is the ship gate.
- F136/F138 scorecard util + hub without panel demote left systemic idle unactioned.

### OSS design patterns stolen
1. run_f139_scorecard_hub_gap checker (weight 0.07) + decide_verdict demote.
2. demote-eval scorecard_hub_gap_idle_approve case; fixture f139_ok.
3. inject policy brief F139; skill_loop critic_scorecard_hub_gap wire.
4. PRODUCT packaging; traces f139-scorecard-hub-gap-critic/.

### Insight
Hub post-score without critic demote is dashboard. Highest ROI: F127-style panel demote when multi-tenant scorecard util gap meets local idle ops skills.

### Feature shipped (F139)
- second_agent_critic f139_scorecard_hub_gap + demote-eval/fixture
- PRODUCT/research/brand; skill_loop wire
- Modal e2e POST_COMMENT=0

### Metric
- Offline: fixture f139_ok; demote-eval scorecard_hub_gap_demote_ok; pytest
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Maker/checker demote on multi-tenant gap** — scorecard ops mirror recovery F127.

### SHA
`8c3c537e8327f1ff2d52e371fc79c626d0e52030`


## 2026-08-01 — F138 scorecard hub post-score compound

### Papers / posts
- F125 recovery hub: federated util themes → priority deltas for next inject.
- FederatedSkill: share skill themes not trajectories across tenants.
- F136/F134 federated scorecard themes without post-score never ranked inject.

### OSS design patterns stolen
1. post_score_scorecard_hub + scorecard-hub-score CLI.
2. select_skills score bump + inject `<!-- torii-f138-scorecard-hub -->`.
3. hub-score nests scorecard_hub + fitness ingest_scorecard_skills.
4. run-torii-review/save-trace wiring; fixture f138_*.

### Insight
Federated scorecard util without hub post-score is inert data. Highest ROI: F125-style priority compound so multi-tenant tool-effective ops skills win residual slots.

### Feature shipped (F138)
- skill_router scorecard hub post-score/inject/select
- hub-score + scorecard-hub-score; PRODUCT/research
- traces f138-scorecard-hub-compound/

### Metric
- Offline: fixture f138_ok privacy; pytest skill_router
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Federate → post-score → prioritize next cycle** — scorecard ops mirror recovery F125.

### SHA
`8927504cc973bc0f1f126833f2c33f0dca355e33`


## 2026-08-01 — F137 scorecard util soft re-prompt

### Papers / posts
- F122 recovery re-prompt: measure util gap → one paid nudge under F108.
- SoK Agentic Skills: availability ≠ quality; idle skills need recovery loops.
- F136 measured scorecard util gap but demote-only left no second chance.

### OSS design patterns stolen
1. decide_scorecard_reprompt + composite reprompt-decide (OR with recovery).
2. F137 prompt marker + doctor/scorecard CLI nudge; scorecard-only write path.
3. Hermes F122 path scores scorecard-util; F108 kind f137 when scorecard-only.
4. Federated scorecard-util-gap biases partial idle.

### Insight
Measuring idle scorecard skills without a soft re-prompt leaves intelligence on the table. Highest ROI: one budgeted re-run that closes F136 gaps like F122 closes recovery gaps.

### Feature shipped (F137)
- skill_router decide/write scorecard re-prompt + fixture f137_*
- run-hermes-review composite decide; save-trace artifacts
- PRODUCT/research; traces f137-scorecard-reprompt/

### Metric
- Offline: fixture f137_ok; pytest skill_router
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Measure → re-prompt once under budget** — scorecard ops mirror recovery F122.

### SHA
`223bfd69a180a94ba3f416412216425deafb23e9`


## 2026-08-01 — F136 scorecard skill utilization (inject ≠ use)

### Papers / posts
- Mem2Act / SkillsBench / F121: inject presence ≠ utilization — measure tool hits mid-run.
- Ragas ToolCallAccuracy / agent eval 2026: mid-run tool selection is the quality signal.
- F132–F135 adopt/federate/fitness scorecard skills without mid-run util left idle ops unmeasured.

### OSS design patterns stolen
1. skill_router.score_scorecard_util + scorecard-util CLI → scorecard-skill-util.json.
2. federate_scorecard_util privacy-safe bins; second-agent f136 checker + APPROVE demote.
3. run-torii-review + save-trace wiring; trajectory soft ops_bonus ±0.03.
4. Fixture good/gap/none; tests; PRODUCT packaging.

### Insight
Adopted scorecard skills without tool-hit measurement are dashboard theater. Highest ROI: F121-style util gap + critic demote for ops skills.

### Feature shipped (F136)
- skill_router scorecard-util + federate + fixture f136_*
- second_agent_critic f136_scorecard_util weight 0.06 demote
- run-torii-review/save-trace; trajectory blend; PRODUCT/research
- traces f136-scorecard-skill-util/

### Metric
- Offline: fixture f136_sc_util_ok privacy; pytest skill_router
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Measure mid-run tool utilization** — scorecard ops mirror recovery util F121/F124.

### SHA
`dac45e1fe4433c468cd130be728d348df2ff020c`


## 2026-08-01 — F135 scorecard skill fitness ingest + doctor panel

### Papers / posts
- FederatedSkill (arXiv 2606.03143): themes need local fitness compound, not export-only.
- CoEvoSkills / EvoSkills: adopted skills without fitness feedback rot (zombie demote).
- F134 federated scorecard skills; F126 hub recovery already ingested into fitness — scorecard did not.

### OSS design patterns stolen
1. skill_fitness.ingest_scorecard_skills → tool_hit shield + router boost.
2. cycle: hits → hub recovery → scorecard → demote → federate.
3. doctor/product scorecard soft scorecard_ops panel (not brand_ready gate).
4. cycle-scorecard post-federate fitness ingest; CLI ingest-scorecard.

### Insight
Federated ops themes that never enter the fitness ledger still demote as zombies. Highest ROI: same F126 compound path for scorecard skills + doctor surface.

### Feature shipped (F135)
- skill_fitness F135 ingest + fixture + federate tags f135/scorecard_ops
- torii doctor/scorecard scorecard_ops metrics; skill_loop_status soft fields
- PRODUCT + research pattern; traces f135-scorecard-fitness-doctor/

### Metric
- Offline: fixture f135_sc_shielded privacy; pytest skill_fitness
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Measure → federate → fitness → doctor surface** — scorecard ops mirror recovery F124/F126.

### SHA
`98fe7010cace3cf0edff0e609671d7e8401f8106`


## 2026-08-01 — F134 federate scorecard skills + trajectory fitness blend

### Papers / posts
- FederatedSkill: share skill themes not trajectories across tenants.
- Hermes multi-dim fitness: ops readiness should soft-blend into procedure/tool dims.
- F133 adopts scorecard-gap skills but themes never federated or scored into fitness.

### OSS design patterns stolen
1. federate_scorecard_skills → scorecard-skill-signals.json (ids + tags only).
2. cycle-scorecard post-adopt federate; federate-scorecard CLI.
3. trajectory_fitness F134 ops bonus from brand_ready + scorecard skill count.
4. save-trace archives scorecard-skill-signals.json.

### Insight
Adopted ops skills without federation/fitness are local-only. Highest ROI: privacy-safe theme export + soft fitness blend so readiness compounds into run quality.

### Feature shipped (F134)
- skill_auto_adopt federate_scorecard_skills + trajectory_fitness blend
- fixture f134_fed_ok; PRODUCT; traces f134-scorecard-federate-fitness/

### Metric
- Offline: fixture f134_fed_ok privacy; fitness ops_bonus; pytest
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Measure → federate → fitness** — scorecard skills enter multi-tenant and run scoring.

### SHA
`8ef9e98dc312912d46a5b799552954b3c2da8dca`

## 2026-08-01 — F133 dual-gate adopt of scorecard-gap skills

### Papers / posts
- SkillOpt dual-gate: default REJECT until dual contribution + attribution.
- F132 propose-scorecard without adopt leaves readiness proposals inert.
- Loop-eng verifier before merge into active skills; Mem2Act tool_blob for ops skills.

### OSS design patterns stolen
1. cycle-scorecard: propose_from_scorecard → list_candidates(scorecard_only) → dual-gate adopt.
2. PROPOSAL_TOOL_BLOBS for F132 scorecard/doctor/demote/util/workflow skills.
3. Fixture hermetic: scorecard-gap skill tool-attr adopts; malicious blocked.
4. Optional post-run TORII_SKILL_AUTO_ADOPT_SCORECARD=1.

### Insight
Proposals without dual-gate adopt are backlog theater. Highest ROI: close F132 with the same adopt gates as F118 recovery skills.

### Feature shipped (F133)
- skill_auto_adopt cycle-scorecard + tool blobs + scorecard_only candidates
- fixture f133_*; PRODUCT + research; traces f133-scorecard-dual-adopt/

### Metric
- Offline: fixture f133_adopt_ok; pytest
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Verifier before merge** — scorecard-gap skills enter active only after dual+attr gates.

### SHA
`b711f25600b42eae59f76a32c862ac7d0461b356`

## 2026-08-01 — F132 self-evolve from scorecard gap themes

### Papers / posts
- Survey of Self-Evolving Agents (arXiv 2507.21046): inter-test-time feedback → skill evolution.
- Agent Skill Evaluation & Evolution (arXiv 2606.11435): measure gaps then propose skills.
- F129–F131 scorecard without evolution leaves readiness gaps static.

### OSS design patterns stolen
1. propose-scorecard maps brand metrics → skill proposals (privacy-safe themes).
2. Templates for hub-gap, demote-eval, memory util, workflow, dual-compound ops.
3. Install guide dual-compound day-2 + propose-scorecard close-the-loop.
4. run-torii-review soft stage after product_scorecard.

### Insight
Scorecard without self-evolution is a dashboard. Highest ROI: gap themes become durable skill proposals for the next PR.

### Feature shipped (F132)
- self_evolve propose-scorecard + templates
- workflow install-guide dual compound block
- PRODUCT + research; traces f132-scorecard-self-evolve/

### Metric
- Offline: force-gap creates ≥2 proposals; guide_ok; pytest
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Measure → propose → adopt** — scorecard gaps feed the skill library.

### SHA
`40b639aa3267512ab996d6ddb865fbb8ad2891d5`

## 2026-08-01 — F131 workflow scorecard + dual compound brand panel

### Papers / posts
- Loop engineering 2026: value is the outer agent cycle (workflow graph), not one-shot prompts.
- F79 workflows-as-code scored L0–L3 offline but never entered product brand_ready.
- Dual compound (skills + memory) needs a third leg: declared pipeline stages on disk.

### OSS design patterns stolen
1. workflow_as_code scorecard dual_compound (skill+memory+workflow levels).
2. torii.py workflow -- group; product_scorecard requires workflow_ok.
3. brand metrics + landing Workflow L3 pipe; triple_ready flag.
4. PRODUCT mental model: two intelligence loops + workflows-as-code graph.

### Insight
Scorecards without the pipeline graph under-claim install readiness. Highest ROI: fold F79 into the front-door scorecard and brand dual-compound panel.

### Feature shipped (F131)
- workflow dual_compound fields; torii workflow group
- product_scorecard F131 brand_ready + metrics
- landing/PRODUCT/research; traces f131-workflow-dual-compound/

### Metric
- Offline: triple_ready L3 brand_ready; pytest
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Workflows as code + readiness scorecard** — pipeline graph is first-class product metric.

### SHA
`4ce3a252c3572073f837760837f147ceb0f8d866`

## 2026-08-01 — F130 memory util-eval → product scorecard

### Papers / posts
- Mem0/Letta 2026: memory improves outcomes only when agents call memory tools.
- IFCMemoryBench: utilization is a first-class axis next to ingestion/retrieval.
- F129 scorecard packaged demote rate but memory util stayed eng-only fixture.

### OSS design patterns stolen (memory OSS)
1. memory_tool_audit util-eval: good CLI hits vs inject-offered unused weak.
2. paper metric memory_tool_util_delta for EVAL vault.
3. product scorecard brand_ready requires memory_util_eval_pass.
4. brand scorecard-metrics.md + landing line for util delta.

### Insight
Passive memory inject is theater. Highest ROI: fold measured tool utilization delta into the same front-door scorecard as demote rate.

### Feature shipped (F130)
- memory_tool_audit util-eval + artifact
- torii.py product_scorecard F130 metrics
- PRODUCT/landing/research; traces f130-memory-util-scorecard/

### Metric
- Offline: util delta=0.85 eval_pass; brand_ready; pytest
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Score the loop** — memory tools must fire; scorecard fails closed otherwise.

### SHA
`f763a9a286ef6abe82f631e687fde94e46ab5101`

## 2026-08-01 — F129 product scorecard brand packaging

### Papers / posts
- Agent eval 2026 scoreboards: demote/validation rates belong on the product surface, not only vault JSON.
- Loop-eng front door: doctor + scorecard as day-2 habit for installers.
- F128 demote-eval without landing/ops packaging stays eng-only.

### OSS design patterns stolen
1. torii.py scorecard aggregates doctor + skill/memory levels + demote-eval.
2. brand_ready + critic_approve_demote_rate as headline metrics.
3. docs/brand/scorecard-metrics.md + landing “Measured scorecard” pipeline.
4. run-torii-review product_scorecard stage; save-trace archives product-scorecard.json.

### Insight
Measured demote/recovery metrics only compound adoption when the product front door and brand story surface them. Highest ROI: one scorecard command + landing honesty.

### Feature shipped (F129)
- torii.py scorecard / product_scorecard
- brand scorecard-metrics.md + landing + TORII.md
- review wire + traces f129-product-scorecard-brand/

### Metric
- Offline: brand_ready L3 demote_rate=1.0; pytest
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Front-door scorecard** — install-day and brand-day same numbers.

### SHA
`f8fbd01863ae3ee859b4a323c4e253eeb7220ebb`

## 2026-08-01 — F128 doctor recovery_hub_gap_ok + demote-eval paper metric

### Papers / posts
- Agent eval 2026 scoreboards: recovery rate + validation/demote rate next to task success.
- Loop-eng doctor: day-2 habit must surface critic demote path readiness.
- F127 hub gap checker without scorecard is invisible to installers and paper vault.

### OSS design patterns stolen
1. skill_loop recovery_hub_gap_ok (f127 critic + demote-eval wire).
2. torii doctor fails closed without recovery_hub_gap_ok.
3. second_agent_critic demote-eval: good/weak/hub-gap → critic_approve_demote_rate.
4. save-trace + run-torii-review stage critic_demote_eval.

### Insight
Checker code without doctor/scorecard and paper demote_rate does not compound install or evaluation discipline. Highest ROI: fail-closed doctor + offline demote pack for EVAL.

### Feature shipped (F128)
- skill_loop_status recovery_hub_gap stage + scorecard fields
- torii.py doctor recovery_hub_gap_ok
- demote-eval CLI + artifact; PRODUCT + research note
- traces f128-doctor-demote-eval/

### Metric
- Offline: demote_rate=1.0 eval_pass; doctor_pass; pytest
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Doctor + scorecard habit** — demote path is install-day and paper-day visible.

### SHA
`c5e08df161a0bb8ebbfe449994bbe38c882589b4`

## 2026-08-01 — F127 hub gap critic + hub_ingested attribution

### Papers / posts
- QASecClaw / VulAgent: maker/checker — multi-tenant hub gap confirms local recovery idle is systemic.
- FederatedSkill + F126: gap_pressure re-prompt alone does not demote weak APPROVE.
- Assay LOO attribution: hub_ingested fitness skills need floor or free-rider demote kills recovery.
- Loop-eng verifier panel: weighted independent checkers.

### OSS design patterns stolen
1. f127_hub_gap checker (weight 0.08) on gap_pressure × local idle.
2. decide_verdict demotes APPROVE with hub_gap_pressure_idle reason.
3. skill_attribution hub floor from fitness hub_ingested_n / last_hub_at.
4. Inject policy lists F121+F127; fixture + unit demote proof.

### Insight
Re-prompt spends budget; critic must still fail closed when hub says recovery is under-used and tools stayed idle. Attribution without hub floor undoes F126 fitness ingest.

### Feature shipped (F127)
- second_agent_critic run_f127_hub_gap_recovery + demote + inject
- skill_attribution hub_ingested contribution floor
- PRODUCT + research note; traces f127-hub-gap-critic-attr/

### Metric
- Offline: fixture f127_ok; demote unit; attr floor; pytest pass
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Verifier panel weight** — hub multi-tenant signal is a first-class checker.

### SHA
`3c1dfb58eb20ab1abb24dcf80eb049bfba2862e1`

## 2026-08-01 — F126 hub gap_pressure re-prompt + fitness ingest

### Papers / posts
- FederatedSkill: multi-tenant themes must change runtime policy (re-prompt + fitness), not only always priority.
- HASP: hub gap pressure as intervention in agent loop under shared budget.
- MMG2Skill / F108: early analyzer + max paid retries — bias re-prompt choice, do not stack spend.
- Loop-eng: F125 closed priority compound; partial util still ignored without hub-biased F122.

### OSS design patterns stolen
1. decide_recovery_reprompt: partial util + gap_pressure ≥ thr → hub_gap_pressure_idle.
2. reprompt-write / Hermes wire pass hub_gap_pressure into F122 body.
3. skill_fitness.ingest_hub_recovery: soft tool_hit_n + demote shield from hub themes.
4. hub-score + cycle call fitness ingest; recovery-reprompt-decide.json in traces.

### Insight
Always-priority compound ranks skills; paid recovery still only fired on full local gap. Highest ROI: multi-tenant gap pressure re-prompts idle recovery CLIs and folds hub tool hits into fitness under F108.

### Feature shipped (F126)
- skill_router hub gap re-prompt bias + write suffix
- skill_fitness ingest_hub_recovery + cycle/hub-score wire
- run-hermes-review passes hub fields; save-trace decide artifact
- PRODUCT + research note; traces f126-hub-gap-reprompt-fitness/

### Metric
- Offline: f126_ok hub_gap_decide + fitness; pytest pass
- Live: Modal pytorch e2e POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Budgeted intervention** — hub bias chooses when to spend the one recovery re-prompt.

### SHA
`cce8981d1837d109ff60cc10f8cc18089891eea4`

## 2026-08-01 — F125 hub recovery-util post-score compound

### Papers / posts
- **FederatedSkill** (arXiv 2606.03143): multi-tenant skill themes compound only when consumed into policy.
- **HASP** (arXiv 2605.17734): skills as state-action interventions — hub scores must change next-loop always priority.
- **MMG2Skill**: attempt/skill budget + early analyzer — util bins guide which recovery skills keep always slots.
- Loop-eng readiness: measure → feedback; write-only federation is theater.

### OSS design patterns stolen
1. post_score_recovery_hub: skill_id → priority_delta from multi-tenant hits/tool_hits.
2. select_skills always rank uses effective priority (base + hub Δ).
3. inject `<!-- torii-f125-recovery-hub -->` + recovery-hub-score.json artifact.
4. run-torii-review stage recovery_hub_score; save-trace archives hub score.

### Insight
F124 federated recovery util themes but next run ignored them. Highest ROI: close the compound loop — hub post-score → always budget + prompt inject so multi-tenant tool hits rank recovery skills under SkillReducer caps.

### Feature shipped (F125)
- `skill_router.py` hub-score / post_score_recovery_hub / inject_recovery_hub
- always priority compound + residual score bump for deferred hub hits
- skill_loop_status recovery_hub stage; PRODUCT mental model; research note
- traces `f125-recovery-hub-compound/`

### Metric
- Offline: fixture hub_ok privacy; mem Δprio≥5; hub inject; pytest targeted pass
- Live: Modal pytorch e2e POST_COMMENT=0 (see fire status)

### Loop-engineering / Hermes practice used
**Measure → feedback path** — federated util is not write-only; doctor/scorecard surfaces hub wire.

### SHA
`ca954e8a3f756b72625ae04d513d0e713feef7d2`


## 2026-08-01 — F124 recovery util federate + doctor recovery_ok

### Papers / posts
- FederatedSkill / F77/F116: share skill themes not trajectories.
- Multi-tenant privacy: tenant hash + util bins only.
- Loop-eng doctor: day-2 habit must surface recovery readiness (F123 scorecard).

### OSS design patterns stolen
1. federate_recovery_util: skill_id + util_rate_bin + inject_chars_bucket + tenant_hash.
2. util --federate default on; recovery-util-signals.json under memory/federation.
3. torii.py doctor requires skill_loop.recovery_ok (memory/product/critic active).
4. save-trace archives federated recovery util signals.

### Insight
Util without federation does not compound across tenants; doctor without recovery_ok hides missing always skills. Highest ROI: privacy-safe util themes + doctor fail-closed.

### Feature shipped (F124)
- `skill_router.py` federate_recovery_util + util --no-federate
- `torii.py` doctor recovery_ok / feature_recovery F124
- skill_loop_status scorecard recovery fields; PRODUCT + research note
- traces `f124-recovery-util-federate/`

### Metric
- Offline: fed_ok privacy_ok; doctor recovery_ok; pytest 602
- smoke PASS; Modal pytorch#191813 BIT3_OK ~61s log_streaming=true POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Doctor + federated scorecard** — recovery readiness is install-day and hub-day habit.

### SHA
`e34ad50bfc3e19f4dd2a719b44b6f42e0d55eca9`
## 2026-08-01 — F123 recovery skill loop packaging (traces + brand + scorecard)

### Papers / posts
- Agent skills packaging 2026: skills without lifecycle packaging do not compound in product UX.
- Torii F119–F122 measured recovery (always budget → compact → util → re-prompt) needed ops/brand/trace closure.
- Loop-eng readiness scorecards: one surface for installers and paper.

### OSS design patterns stolen
1. save-trace archives skill-router / hits / recovery-util / re-prompt env for paper.
2. skill_loop_status stages + recovery_active + hermes F122 + save-trace wire.
3. Landing + TORII.md + PRODUCT mental model D: inject is not enough.
4. README one-liner for recovery skill loop.

### Insight
Intelligence without packaging loses adoption clarity. Highest ROI this fire: close the recovery loop in traces, scorecard L3, and brand without empty polish.

### Feature shipped (F123)
- `save-trace.sh` F119–F122 artifacts
- `skill_loop_status.py` recovery stages + recovery_ok
- brand landing/TORII.md/PRODUCT/README
- traces `f123-recovery-loop-packaging/`

### Metric
- skill_loop fixture L3 recovery_ok; save-trace copies util json
- pytest 600; smoke PASS; Modal pytorch#191813 BIT3_OK log_streaming=true POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Scorecard + trace archive as product surfaces** — dogfood readiness for recovery loop.

### SHA
`25e83e9cff8ea0b2a838291f218c93d3da35c4b8`
## 2026-08-01 — F122 recovery skill soft re-prompt under F108 budget

### Papers / posts
- Mem2Act / F106: utilization gap → soft re-prompt once.
- F108 shared max_extra: F49 + F106 + F122 cannot stack unbounded paid retries.
- F121: recovery util_rate/gap after always inject — measure without recover was incomplete.

### OSS design patterns stolen
1. reprompt-decide/write for recovery idle CLIs (doctor/memory/critic).
2. F108 kind `f122` shares TORII_REPROMPT_MAX_EXTRA (default 1).
3. Defer to F49 when tool_call_turns=0; no double storm.
4. EVAL-REPORT paper table for inject_chars + util_rate + re-prompt decide.

### Insight
F121 demote alone is passive. Highest ROI: budgeted soft re-prompt that forces recovery tool use before the review freezes.

### Feature shipped (F122)
- `skill_router.py` reprompt-decide / reprompt-write
- `reprompt_budget.py` kind f122
- `run-hermes-review.sh` F122 soft re-run path
- EVAL-REPORT F120–F122 metrics; traces `f122-recovery-reprompt/`

### Metric
- Offline: decide reprompt=1 on gap; budget blocks f122 after f49; fixture_pass
- pytest 600; smoke PASS; Modal pytorch#191813 BIT3_OK ~54s log_streaming=true POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Budgeted recovery loop** — one extra paid attempt max, kind-once accounting.

### SHA
`c331627e570351d75bcb4aa8eb09d53114c9f4fb`
## 2026-08-01 — F121 recovery skill utilization critic (inject ≠ tools)

### Papers / posts
- Mem2Act / F105: inject presence ≠ tool utilization.
- SkillsBench / SoK Agentic Skills: skills help only when applied.
- Gap after F119/F120: always recovery skills inject + compact, no post-run check they fired doctor/memory/critic CLIs.

### OSS design patterns stolen
1. score_recovery_util: util_rate = tool_hits / recovery_injected; gap if zero tools.
2. Measure inject_chars + f120_chars_saved from skill-router.json for paper traces.
3. F78 panel checker f121_recovery_util (weight 0.08).
4. Soft demote APPROVE → COMMENT on recovery_skill_idle_no_tool_hit.

### Insight
Always-on recovery skills without utilization measurement are dead weight. Highest ROI: post-run util score + critic demote when product/memory/critic tools never ran.

### Feature shipped (F121)
- `skill_router.py` util command + recovery-skill-util.json
- `second_agent_critic.py` F121 checker + demote reason
- run-torii-review recovery_skill_util stage; PRODUCT + research note
- traces `docs/benchmarks/traces/f121-recovery-util/`

### Metric
- Offline: util_ok; gap on idle; demote includes recovery_skill_idle
- pytest 599; smoke PASS; Modal pytorch#191813 BIT3_OK ~46s log_streaming=true POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Verifier measures tool outcomes of injected skills** — default REJECT idle recovery on APPROVE.

### SHA
`4f91b0b97bf5cc1e350c307209321109bbd892b0`
## 2026-08-01 — F120 SkillReducer-lite always body compact + pack verify

### Papers / posts
- SkillReducer (arXiv 2603.29919): ~39% body compression via progressive disclosure core vs background.
- Agent Skills composition cliff: instruction bloat dilutes attention.
- Gap after F119: always budget of 3 still injects multi-kB recovery prose.

### OSS design patterns stolen
1. compact_skill_body keeps headings/numbered steps/code; drops background prose.
2. ALWAYS_MAX_CHARS=480 / FULL_MAX_CHARS=900 caps on inject.
3. Lean on-disk recovery skill bodies (memory/product/critic).
4. install-torii.sh dies if pack missing F113/F118 recovery active skills.

### Insight
Always budget without body compaction still wastes context. Highest ROI: SkillReducer-lite on inject + pack verify so every install ships compact recovery skills.

### Feature shipped (F120)
- `skill_router.py` compact_skill_body + inject metrics f120_chars_saved
- compact active recovery skills; install pack verify; fixture F120
- traces `docs/benchmarks/traces/f120-skill-compact/`

### Metric
- Offline: fixture compact_ok; inject saves ≥1 char; pack install has 3 recovery skills
- pytest 598; smoke PASS; Modal pytorch#191813 BIT3_OK ~55s log_streaming=true POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Token budget constraint on always inject** — compact before ship.

### SHA
`cd24b3ca8bc90c3300e5782f72566a1977d53c95`
## 2026-08-01 — F119 always-on skill budget with recovery priority

### Papers / posts
- SkillReducer (arXiv 2603.29919): skill injection is context cost; unbounded always-on is skill bloat.
- Agent Skills progressive disclosure: index all, full body only when needed.
- Gap after F118: product-cli/critic active but always=false → max_full filled by soft always (tool-depth/preserve).

### OSS design patterns stolen
1. ALWAYS_MAX=3 always full-body slots (SkillReducer budget).
2. Priority: memory(100) > product-cli(90) > critic(85) > tool-depth(50) > preserve(40).
3. Deferred always compete on theme score (no 1000 boost).
4. Install already rsyncs agent/skills/ including new always skills.

### Insight
Dual-gate adopt without always budget still fails to inject recovery skills. Highest ROI: cap always slots and prioritize tool-recovery skills so doctor/memory/critic teach mid-review.

### Feature shipped (F119)
- `skill_router.py` always budget + priority; product/critic DEFAULT_TRIGGERS always
- active skills always:true frontmatter; fixture F119; PRODUCT + research note
- traces `docs/benchmarks/traces/f119-always-budget/`

### Metric
- Offline: always_selected memory+product+critic; tool-depth deferred; fixture_pass
- pytest 598; smoke PASS; Modal pytorch#191813 BIT3_OK ~45s log_streaming=true POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Context budget as a loop constraint** — always inject is rationed, not vibes.

### SHA
`e397f577f453b8abe0b5765c28578823131fd768`
## 2026-08-01 — F118 tool-aware dual-gate adopt of F117 product-cli/critic skills

### Papers / posts
- SkillsBench dual-rollout: contribution_pp > 0 before ship.
- F88 LOO free-rider gate; F115 tool credit required for tool-only skills.
- F117 mine/propose product-cli/critic — proposals blocked by prose-only attr.
- Loop-eng: default REJECT until verifier evidence.

### OSS design patterns stolen
1. Static TOOL_OUTCOME_PROBES for product-cli + critic-early (F118 baseline).
2. Synthetic allowlisted tool_blob per skill-prefer-* in adopt attribution.
3. free_without tools vs tool_attr_ok proof in auto-adopt fixture.
4. Smoke step 10: F117 mine fixture + F118 adopt fixture + active product-cli.

### Insight
Proposals without tool-aware adopt gates never leave `proposals/`. Highest ROI: dual-gate with synthetic tool transcripts so doctor/status/critic skills ship like F113 memory-cli.

### Feature shipped (F118)
- `skill_auto_adopt.py` tool-attr gate + F118 fixture; active product-cli/critic skills
- `skill_router.py` static probes for product-cli/critic
- smoke-torii-gate.sh [10/10]; PRODUCT + research note
- traces `docs/benchmarks/traces/f118-tool-dual-gate-adopt/`

### Metric
- Offline: adopt fixture free_without + tool_attr_ok + prod_active; smoke PASS
- pytest 597; Modal pytorch#191813 BIT3_OK ~62s log_streaming=true POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Verifier dual-gate before active skill merge** — tool evidence required.

### SHA
`e82b784ce0feda1f0ae553fad11f3402cd950079`
## 2026-08-01 — F117 tool-probe self-evolve (allowlisted mine + propose)

### Papers / posts
- Hermes self-evolution / GEPA-lite: trajectories → proposals → eval → adopt.
- SigLeak / contrastive skill signatures: portable tool evidence.
- Trajectory eval 2026 + Mem2Act: tool path first-class (F114–F116).
- Gap: static TOOL_OUTCOME_PROBES never learned doctor/status/critic CLIs from live runs.

### OSS design patterns stolen
1. Fixed allowlist catalog pattern→skill (never free-form log regex).
2. Durable `.torii/tool-outcome-probes.json` merged by skill_router F114.
3. Propose skill-prefer-product-cli / skill-prefer-critic-early from mined hits.
4. Soft post-run mine-probes after fitness; --propose when TORII_SELF_EVOLVE=1.

### Insight
Tool-outcome scoring without evolution is a closed set. Highest ROI: mine only safe product CLIs into durable probes so next PR scores the tools the agent actually learned to call.

### Feature shipped (F117)
- `self_evolve.py` mine-probes / fixture + F117 propose templates + ingest signals
- `skill_router.py` load_dynamic_probes merge
- `run-torii-review.sh` soft tool_probe_mine stage
- traces `docs/benchmarks/traces/f117-tool-probe-mine/`

### Metric
- Offline fixture_pass; mine doctor+critic+memory; match_ok
- pytest 596; Modal pytorch#191813 BIT3_OK ~85s log_streaming=true POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Trajectory packaging → bounded evolve** — allowlist constraints before any adopt.

### SHA
`2ed41613acc2c0db900e40c5f6dc3487c94fc276`
## 2026-08-01 — F116 tool-fitness compound (demote shield + federate + live wire)

### Papers / posts
- Trajectory eval 2026 / Mem2Act: tool path is first-class quality signal.
- FederatedSkill: privacy-safe skill themes not raw trajectories.
- SigLeak / contrastive skill signatures: portable tool-outcome evidence.
- Gap after F114/F115: tool_hit_n tracked in fitness ledger but ignored for demote/boost/federate; live score/attr lacked explicit agent-loop args.

### OSS design patterns stolen
1. Demote shield: tool_hit_n≥1 never zombie-demote recovery skills.
2. Boost: +0.5×max_boost × tool_hit_rate for router ranking.
3. Federate tags tool_outcome + f116; tool_hits count only (no commands/paths).
4. Live wire: run-torii-review score + attr pass agent-loop/agent-loop.json + agent.log.

### Insight
Measuring tool hits without acting on them is theater. Highest ROI: compound tool_hit into demote/boost/federate so F113 recovery skills stay full-body inject and multi-tenant promote.

### Feature shipped (F116)
- `skill_fitness.py` F116 tool shield/boost/federate; TORII_SKILL_FITNESS_TOOL
- `run-torii-review.sh` explicit --agent-loop/--log for F114 score + F115 attr
- skill_loop_status stage labels F114–F116; PRODUCT one-liner
- traces `docs/benchmarks/traces/f116-tool-fitness/`

### Metric
- Offline: fixture tool_shielded + tool_in_fed; compound summary tool_hit_n=1
- pytest 595; Modal pytorch#191813 BIT3_OK ~57s log_streaming=true POST_COMMENT=0

### Loop-engineering / Hermes practice used
**Verifier fitness gate on trajectories** — demote default REJECT unless tool or prose evidence compounds.

### SHA
`de692b82f0ae22a59963186ea103e992cbdd06fb`
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

## 2026-08-01 — F155 hub-archival recovery util (inject ≠ hub_boost)

### Papers / posts
- **Assay** (arXiv 2606.15390): attribution-based skill selection — idle/negative skills must be measured, not only adopted.
- **Agent Skills survey** (arXiv 2605.07358): cost- and utility-aware skill selection under budget.
- Mem2Act / SkillsBench: always-injected recovery skills must fire tool CLIs or they are idle prompt cost.
- Hermes batch durability (upstream): fsync trajectory before checkpoint — durability pattern for util artifacts (noted, not ported).

### OSS / memory patterns
- Recovery stack membership is the compound lever: F121 util → F122 re-prompt → F124 federate → F125 hub priority only apply to RECOVERY_SKILL_IDS.
- Hub-boost-strict tool probes: generic archival is not evidence for a hub-archival skill (Assay: not all skills help).

### Insight
F154 cycle-adopted hub-archival with always_priority 95, but it sat **outside** recovery util. Without F155, inject≠use was invisible and F122 never nudged hub_boost.

### Feature shipped (F155)
- `skill-prefer-hub-archival-early` ∈ `RECOVERY_SKILL_IDS`
- hub-boost-strict `TOOL_OUTCOME_PROBES` (generic archival alone insufficient)
- `score_recovery_util` hub_archival_* fields + federate f155/hub_archival tags
- re-prompt suffix F155 nudge + archival_memory_search line
- skill_loop + doctor soft surface `hub_archival_util_ok`
- fixture f155_ok + unit test

### Loop-engineering practice
Maker/Checker: adopt (F154) is maker; recovery util (F155) is checker that always-inject actually fired hub_boost tools. Scorecard surfaces readiness.

### Metric
- Offline: skill_router fixture f155_ok; pytest skill_router 18 passed
- Live insecure-demo Hermes: recall=1.0 tp=4 fn=0 verdict=REQUEST_CHANGES
- Live util demo: hub_archival_injected + hub_archival_util_gap when no hub_boost tools
- Modal pytorch/pytorch#191831 BIT3_OK ~55.6s log_streaming=true

### SHA
`6357b5e8c1d5fc02e69c12f498feca7915d83903`

## 2026-08-01 — F156 hub-archival util gap critic demote + LOO floor

### Papers / posts
- **Assay** (arXiv 2606.15390): skills with negative/zero effect must be suppressed — idle always skills are free-riders.
- **Agent skill evaluation survey** (arXiv 2606.11435): dual-rollout contribution = with/without skill gap.
- Live F155: util_rate=0.5 with hub_archival_util_gap while memory CLI hit — F121 full-gap demote missed the slice.

### Insight
F155 measured hub-archival inject≠hub_boost; F121 only demotes when *all* recovery tools idle. Highest ROI: dedicated F156 checker demotes APPROVE on hub_archival_util_gap (partial util), plus LOO floor when multi-tenant recovery-util federate proves hub_archival tool hits.

### Feature shipped (F156)
- `run_f156_hub_archival_util` checker + composite weight 0.08
- decide_verdict: APPROVE → COMMENT on hub_archival_util_gap_idle_no_hub_boost
- demote-eval case `hub_archival_util_idle_approve` + paper metric
- skill_attribution LOO floor from recovery-util hub_archival federate hits
- skill_loop/doctor soft `hub_archival_util_critic_ok`

### Loop-engineering
Maker/Checker: agent may APPROVE; F156 checker recomputes util slice offline and demotes without LLM.

### Metric
- Offline fixture f156_ok; demote-eval hub_archival_util_idle_demoted; eval_pass
- Live insecure-demo: recall=1.0 tp=4
- Modal pytorch#191831 BIT3_OK ~117.5s log_streaming

### SHA
`57df1b8f85a14d5fd4c336bb6f39d5912f066a14`

## 2026-08-01 — F157 hub-archival util soft re-prompt under F108

### Papers / posts
- Assay / Mem2Act: recover idle always skills before demote-only critics.
- Agent cost guides: shared re-prompt budgets prevent multi-kind stack burn.
- Live F155/F156: partial recovery util (memory hit, hub-archival idle) skipped F122 full-gap re-prompt.

### Insight
F156 demotes APPROVE after the fact. Highest ROI: F157 decides soft re-prompt on `hub_archival_util_gap` with `budget_kind=f157` under F108, so the agent gets one paid recovery turn for hub_boost archival before demote.

### Feature shipped (F157)
- `decide_recovery_reprompt` hub_archival_util_gap → reprompt + budget_kind=f157
- F108 KINDS + hermes allow/consume f157
- `build_recovery_reprompt_suffix` F157 title + hub_boost nudge
- fixture f157_ok; skill_loop hub_archival_reprompt_ok

### Loop-engineering
Budgeted recovery (F108) before checker demote (F156) — maker gets one chance.

### Metric
- Offline fixture f157_ok; decide demo reprompt=1 budget_kind=f157
- Live insecure-demo recall=1.0 (F106 used F108 slot; no recovery inject this run)
- Modal pytorch#191829 BIT3_OK ~132s log_streaming

### SHA
`8419005c2275b2a4bac4bea7aa25a808953c70f8`

## 2026-08-01 — F158 hub-archival util fitness demote/boost

### Papers / posts
- **SkillsBench** (arXiv 2602.12670): measure genuine skill utilization vs inject-only.
- **Agent skill evaluation survey** (arXiv 2606.11435): longitudinal fitness; drop non-contributors.
- Assay: chronic idle always skills must be suppressed after evidence.

### Insight
F155–F157 measure/re-prompt/demote per run. Highest ROI: compound hub_archival util into durable fitness ledger so chronic inject≠hub_boost demotes boosts across PRs and tool hits revive.

### Feature shipped (F158)
- `ingest_hub_archival_util` → gap_n/hit_n/util_rate counters
- `apply_demotions` F158: gap_rate≥0.67 after min_n → demote; tool hit revive
- fitness_boosts util_rate boost − gap_rate penalty
- cycle + CLI `ingest-hub-archival`; federate hub_archival/f158 tags
- fixture f158_ok; skill_loop hub_archival_fitness_ok

### Loop-engineering
Longitudinal scorecard: per-run checkers (F156/F157) + durable fitness (F158).

### Metric
- Offline fitness fixture f158_ok (gap demote → hit revive boost  -2→0.72)
- Live insecure-demo recall=1.0
- Modal pytorch#191831 BIT3_OK ~99s log_streaming

### SHA
`9e5ffce6591180db73f62edd3071a97e8c3de43f`

## 2026-08-01 — F159 F108 adaptive dual-recovery re-prompt slot

### Papers / posts
- Agent cost guides: shared re-prompt caps prevent multi-kind burn.
- Live F157: F106 memory util consumed max_extra=1 → hub-archival re-prompt never fired.
- Loop Engineering: budgeted recovery must still cover **independent** quality gaps.

### Insight
max_extra=1 is correct against runaway stacks, but memory util (f106) and hub-archival util (f157) are complementary recoveries. Highest ROI: grant **one** adaptive bonus slot when a complementary kind already used the base budget.

### Feature shipped (F159)
- `ensure_adaptive_slot` + complementary_kinds (memory ↔ recovery/hub-archival/recon)
- decide_allow reason=`adaptive_within_budget`; once-only expand
- hermes notices F159 when adaptive_expanded
- fixture f159_ok; skill_loop reprompt_adaptive_ok
- f49 still does not unlock adaptive

### Loop-engineering
Budget with selective dual-recovery — not unbounded multi-reprompt.

### Metric
- Offline fixture f159_ok (f106→f157 allow; adaptive once; off blocks)
- Live insecure-demo recall=1.0
- Modal pytorch#191829 BIT3_OK ~98s log_streaming

### SHA
`e470d39299d0e49c2abc9a87543d514fbc0187a4`

## 2026-08-01 — F160 skill-router synth for bench util measurement

### Papers / posts
- SkillsBench: measure genuine skill utilization requires knowing inject set.
- Assay: idle always skills invisible if inject set is empty.
- Live F155–F159: recovery_injected_n=0 on insecure-demo because skill-router.json missing.

### Insight
Bench live skips assemble-context. Without skill-router artifact, F121–F159 treat runs as "no recovery injected" and never measure hub-archival util. Highest ROI: synthesize always skills + inject progressive router before hermes.

### Feature shipped (F160)
- `ensure_skill_router_doc` — load or synthesize always_selected
- `score_recovery_util` uses synth when artifact missing
- inject writes skill-router next to prompt.md parent
- `bench_security_gate live` skill_router inject before hermes
- fixture f160_ok; skill_loop router_synth_ok

### Loop-engineering
Observe what you inject — measurement without inject artifact is theater.

### Metric
- Offline fixture f160_ok (synth recovery_injected_n≥2, hub_archival gap)
- Live: recovery_injected_n=3, hub_archival_injected, util_rate=1.0, recall=1.0
- Modal pytorch#191831 BIT3_OK ~90s

### SHA
`441d0b63380be6307c6d7b9ded1e079e6c6bf76f`

## 2026-08-01 — F161 multi-tenant hub-archival gap pressure

### Papers / posts
- FederatedSkill multi-tenant util themes (privacy-safe bins/tenant hashes).
- Torii F126 recovery hub gap_pressure pattern for always priority + re-prompt bias.
- F155–F160 local hub-archival util stack without multi-tenant compound.

### Insight
Local util/reprompt/demote existed but multi-tenant chronic hub-archival under-use did not raise always priority or re-prompt bias. Highest ROI: post_score hub-archival gap_pressure from federated signals + fitness chronic gaps.

### Feature shipped (F161)
- `post_score_hub_archival_hub` + load hub-archival-util-signals
- always priority compound for skill-prefer-hub-archival-early
- decide_recovery_reprompt F161 hub_archival_hub_pressure tags
- F156 critic deeper demote when multi-tenant high + local gap
- fitness federate chronic gap → hub-archival-util-signals.json
- fixture f161_ok

### Loop-engineering
Multi-tenant compound memory of skill under-use → local always budget + recovery.

### Metric
- Offline f161_ok gap_pressure=0.875 delta=40 re-prompt with hub pressure
- Live recovery_injected_n=3 util_rate=1.0 recall=1.0
- Modal pytorch#191829 BIT3_OK ~54s

### SHA
`8409b6e9b7aadac24365a792fb9b2239e61bec82`

## 2026-08-01 — F162 hub-archival hub pressure inject + demote-eval

### Papers / posts
- F125 recovery hub inject pattern (privacy-safe ids + bins).
- F161 multi-tenant hub-archival gap_pressure without prompt surface.
- Loop Engineering scorecard: paper demote metric for multi-tenant idle APPROVE.

### Insight
F161 computed pressure offline; agents never saw it. Highest ROI: inject F162 section into prompt + demote-eval case for hub_archival_hub_pressure_idle_approve.

### Feature shipped (F162)
- `render_hub_archival_hub_section` + `inject_hub_archival_hub_into_prompt`
- soft wire in `inject_into_prompt` after F125 recovery hub
- demote-eval `hub_archival_hub_pressure_idle_approve` paper metric
- fixture f162_ok; skill_loop hub_archival_hub_inject_ok

### Loop-engineering
Maker sees multi-tenant under-use before checker demotes — budgeted recovery with observability.

### Metric
- Offline f162_ok inject; demote-eval hub_archival_hub_pressure_idle_demoted
- Live: F162 marker + gap pressure in prompt; recovery_injected_n=3; recall=1.0
- Modal pytorch#191831 BIT3_OK ~91s

### SHA
`9f75c6c6ae6182b9556f210913fd218a49fa3293`

## 2026-08-01 — F163 hub-archival compound loop product surface

### Papers / posts
- Loop Engineering: measure what you ship (doctor/scorecard readiness).
- F155–F162 hub-archival intelligence stack without a single product bit.
- Product day-2 habit: `torii doctor` / `torii scorecard` package capabilities.

### Insight
The hub-archival loop was complete in scripts but fragmented across flags. Highest ROI: one `hub_archival_loop_ok` for doctor/scorecard + soft fitness cycle after util so chronic multi-tenant heat compounds every run.

### Feature shipped (F163)
- doctor surfaces F159–F162 + `hub_archival_loop_ok`
- product scorecard metrics + brand one_liner when loop ok
- hermes soft `ingest-hub-archival` + `cycle` after util
- skill_loop hub_archival_loop_ok + hermes fitness cycle wire

### Loop-engineering
Package measured compound loops as product readiness — not script archaeology.

### Metric
- doctor hub_archival_loop_ok + doctor_pass
- Live util_rate=1.0 recovery_injected_n=3; fitness last_hub_archival tool_hit
- Modal pytorch#191829 BIT3_OK ~74s

### SHA
`d70fea408e4767e44651bc4f3373a83f76c8902a`

## 2026-08-01 — F164 hub-archival brand + paper EVAL pack

### Papers / posts
- Loop Engineering: design the loop, get a score — package measured compound loops as product readiness.
- Mem0 discipline: inject ≠ utilization; tools must fire for memory/skills to count.
- F155–F163 hub-archival stack complete offline; brand/EVAL surfaces lagged doctor flags.

### Insight
Highest ROI after F163: surface `hub_archival_loop_ok` on PRODUCT/landing/scorecard-metrics and roll F155–F163 live Modal proofs into one paper EVAL pack — measured capabilities, not slogans.

### Feature shipped (F164)
- PRODUCT Mental model D (F155–F163 table + one-liners)
- TORII.md + landing.html hub-archival pipeline + scorecard callout
- torii.py scorecard brand md rows for all hub_archival_* + brand_lines
- docs/benchmarks/traces/f164-hub-archival-eval-pack/ (HUB-ARCHIVAL-EVAL.md + SUMMARY)
- INDEX + EVAL-REPORT entries

### Loop-engineering
Package measured readiness into the surfaces operators and papers actually read.

### Metric
- scorecard hub_archival_loop_ok=True · brand_ready=True · L3
- Live local recall=1.0 tp=4
- Modal pytorch#82997 BIT3_OK ~57s log streaming

### SHA
`TBD`

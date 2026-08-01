# Torii research → product log

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
_PENDING_

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

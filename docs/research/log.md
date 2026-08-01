# Torii research → product log

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
_(filled after push)_

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

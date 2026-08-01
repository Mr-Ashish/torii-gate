# Torii research → product log

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
`5f20f676917475ef17c342386eeaa7d9f79207bf`

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

# Torii research → product log

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

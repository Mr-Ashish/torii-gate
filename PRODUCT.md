# Torii Gate — product brief

## One sentence
Torii Gate is a PR/CI security gate that reviews AI-written and human code with agent tools, evidence, and merge protection.

## User
Platform / AppSec engineer who needs every PR checked for security without drowning in SAST noise.

## v1 scope
- GitHub comment trigger `@torii review this pr`
- Security pack default
- Comment + labels (`torii/*`)
- Local `.torii/` memory + FP patterns
- Redacted traces as Actions artifacts

## Non-goals (v1)
- Full ASPM dashboard
- Autonomous offensive red team
- Auto-merge patches without human

## Success metrics
- Time-to-first-signal on PR
- Measured FP rate (memory growth of suppressions)
- PRs blocked with path-evidenced findings

## Mental model (F78)

**Maker / Checker.** Hermes is the maker (agent review). A deterministic second-agent critic panel (path evidence, chain revalidation, trajectory fitness, scoped memory) re-scores every run and demotes weak APPROVE without path evidence — no extra LLM cost.

**Compound memory.** FP rules, TP signatures, and privacy-safe federated themes compound across PRs and tenants; scoped recall keeps prompt context budgeted.

**Measured gate.** Multi-corpus labeled benches (Python insecure-demo + Juice Shop synthetic) score recall before shipping harness changes.

## Self-evolution (F82)

Validated skill proposals (fitness-gated) only enter `agent/skills/active/` after offline regression gates (critic fixture + fitness fixture). Default off (`TORII_SKILL_AUTO_ADOPT=0`).

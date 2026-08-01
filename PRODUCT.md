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

## Per-skill attribution (F88)

Pack-level dual-rollout is necessary but not sufficient. Leave-one-out + unique keyword attribution identifies **free-rider** skills that never solo-hit; auto-adopt rejects them even when F74 validate says adopt.

## Adopt only if skills contribute (F87)

Skill auto-adopt (F82) now requires the F86 dual-rollout gate: `skill_contribution_pp > 0` (with-skills vs ablated). Zero-contribution libraries never enter `agent/skills/active/` even if F74 validate says adopt.

## Dual-rollout skills (F86)

SkillsBench-style **with vs ablated** contribution: skill hit_rate delta must stay positive while F70 recall holds. Multi-tenant promote of skill themes requires ≥2 tenants before hub promotion.

## Skill fitness (F85)

Post-run skill hit rates compound into `.torii/skill-fitness.json`. Chronically unused skills are **index-only** (not full-injected); high-hit skills get router boosts. Privacy-safe skill themes federate to the hub (ids + hits, no bodies/paths).

## Progressive skills (F84)

Active skills are **indexed** into the prompt; full skill bodies load only for path-relevant themes (extensions + triggers). Post-run **skill hit rate** measures which skills actually fire — fuel for F74/F82 evolution without context bloat.

## Self-evolution (F82)

Validated skill proposals (fitness-gated) only enter `agent/skills/active/` after offline regression gates (critic fixture + fitness fixture). Default off (`TORII_SKILL_AUTO_ADOPT=0`).

# Torii — brand lock (what we build)

**Decision date:** 2026-08-01  
**Source idea:** C1 — previously “Luffy-Security: PR/CI security gate agent”  
**Hub71 score:** 4.65 Grade A · #1 overall  

---

## Names

| Layer | Name | Use |
|-------|------|-----|
| **Company / brand** | **Torii** | Hub71 form, site, deck, domain |
| **Product (build now)** | **Torii Gate** | GitHub App, docs, CI check name |
| **Roadmap #2** | **Torii Trust** | was C2 hybrid SAST validator |
| **Roadmap #3** | **Torii Plane** | was C4 agent security control plane |
| **Internal eng** | Luffy control plane | repo / architecture only — not customer-facing |
| **Legal shell** | WY LLC (doola) | may differ from brand; brand = Torii |

---

## Why “Torii”

A **torii** is the gate at a threshold — ordinary ground on one side, what matters on the other.  
**Torii Gate** is the threshold between a pull request and production.

- Short (5 letters), pronounceable globally  
- Metaphor matches product job (J3 Gate)  
- Extends cleanly: Trust, Plane, later continuous modes  
- Distinct from CodeRabbit / Snyk / “Luffy” anime association  

**Pronunciation:** TOH-ree (not “tore-ee” as in fabric).

---

## One-liners

| Context | Line |
|---------|------|
| **Elevator** | Torii is the security gate for every pull request. |
| **Hub71** | Torii gates AI-written code in CI — evidence-backed findings, false-positive memory, merge authority. |
| **AppSec fatigue** | The gate gets stricter and quieter over time — not noisier. |
| **Eng** | Maker agent + checker panel + skill loop: route → hit → fitness → dual → attr → inject. |
| **Skills** | Skills that do not contribute do not ship in the next prompt. |
| **Memory** | Stale memory does not confirm findings or crowd the inject budget. |
| **Memory (AppSec)** | False positives die twice — and true positives stay sharp. |
| **Memory CLI** | One front door for memory tools — agents call `torii_memory`, not tribal scripts. |
| **Integrity** | Only path-evidenced findings compound; weak narrative never poisons the store. |
| **Cost control** | Soft re-prompts recover quality within a shared paid-attempt budget. |
| **Dual loops** | Skills that measure in; memory that pages in — both compound. |
| **Hub-archival** | Hub-archival skills that never page cold memory do not silently APPROVE. |
| **Hub-archival (AppSec)** | Cross-tenant retrieval heat becomes next-run always budget — without sharing paths or snippets. |
| **Hub-archival loop** | util → critic → re-prompt → fitness → hub inject — one measured `hub_archival_loop_ok` bit. |
| **GEPA refine (eng)** | Skills that fail tool util get refined, measured, multi-tenant promoted, decayed when dual_fail is chronic, and dual_pass-revived — or stay out of always budget. |
| **GEPA refine (AppSec)** | Idle recovery skills cannot silently APPROVE after GEPA refine inject or multi-tenant decay. |
| **GEPA refine loop** | refine → dual-gate → dual_pp → promote → hub critic → chronic decay → multi-tenant demote → dual_pass revive + free-rider MT + contribution_pp floor — one measured `refine_loop_ok` bit (F165–F185 / F184 pack / F178 pack). |
| **vs SAST** | Scanners generate findings; Torii is the merge authority that compounds. |
| **Tagline** | Nothing ships without crossing the gate. |

---

## ICP (lock)

| Buy | Do not sell first |
|-----|-------------------|
| Platform / DevEx owning required checks | Teams that only want PR style nits |
| AppSec drowning in SAST + AI PR volume | Full ASPM RFP day one |
| Eng leads shipping AI code without a security owner | Offensive red-team retainers |

**Job to be done:** *Give every PR a security merge authority that compounds (memory + skills), not another comment bot.*

---

## Skill compound loop (product story, F84–F89)

Customer-facing diagram (same as PRODUCT mental model B):

`route → hit → fitness → dual → attr → inject`

This is the differentiator vs static “agent skills.md” dumps: Torii **measures contribution**, demotes free-riders, and only full-injects skills that fire.

### Recovery skill loop (F119–F123)

Always-on recovery skills (memory CLI · product doctor · second-agent critic) get a **capped always budget**, **compact bodies**, post-run **tool utilization** scoring, and **one shared soft re-prompt** under F108. Traces archive `skill-router.json`, `recovery-skill-util.json`, and `recovery-skill-reprompt.env` for paper eval — inject without tools is not success.

### Measured product scorecard (F128–F129)

Install/ops surface — not marketing copy:

```bash
python3 scripts/torii.py doctor      # fails closed without recovery_hub_gap_ok
python3 scripts/torii.py scorecard   # doctor + loop L0–L3 + critic demote_rate
```

Reports **critic_approve_demote_rate** (offline weak + hub-gap idle APPROVE packs), recovery hub-gap critic readiness, and skill/memory loop levels. Landing and `docs/brand/scorecard-metrics.md` tell the same story: **evidence over slogans**.


## Memory compound loop (product story, F93–F108)

Customer-facing diagram (PRODUCT mental model C):

```text
compound → write → consolidate → effective → federate → recall → tiers → search
   │                                                                    │
   ├─ integrity gate (path only)          front door: torii_memory CLI ─┤
   ├─ utilization audit mid-review        soft re-prompt (budgeted) ────┤
   └─ privacy-safe multi-tenant export    shared max paid retries ──────┘
```

Differentiator vs “dump MEMORY.md forever”: Torii **events on write**, **integrity-gates compound**, **decays and evicts**, **strength-ranks** TP confirms, **tiers** core vs archival, **pages cold memory** on demand, **measures** whether the agent actually used memory tools, and **caps** paid re-prompts so recovery cannot double-spend by default.

Ops readiness: `python3 scripts/torii_memory.py doctor` + `memory_loop_status` L0–L3 — same discipline as the skill loop.

---

## Differentiator (2026 market)

Not another style/comment bot. Torii is a **security merge authority**: maker agent + deterministic checker panel + **two compound loops** (skills + memory) — runnable live on **Modal** with streamed Hermes logs. Competitors optimize for PR chatter; Torii optimizes for **path-evidenced block/approve** that gets quieter as skills measure in and memory pages in.

## What Torii Gate does (v1 scope)

1. Trigger on PR / required CI check  
2. Security-focused agent review (injection, authz, secrets, SSRF, unsafe crypto, …)  
3. Tool-backed path/line evidence  
4. Comment + optional merge block on high severity  
5. Org memory of FP / true positives with write events, tiers, archival search (`.torii/` or service-side)  
6. Measured skill loop (contribution before inject)  
7. Audit traces for enterprise later  

**Out of v1:** full ASPM dashboard, autonomous red team, auto-patch merge without human.

---

## Positioning

| We are | We are not |
|--------|------------|
| Security merge authority | Generic AI code review (CodeRabbit clone) |
| Pipeline-native AppSec | Day-one continuous pentest (XBOW / Sec1) |
| Evidence + measured FP | “Zero false positives” marketing |
| Gate that compounds into Trust + Plane | Scanner that only dumps SARIF |

---

## Visual (landing)

- Neo Kinpaku system already in `torii-landing.html`  
- Mark: minimal gate glyph (torii silhouette in gold on lacquer)  
- Wordmark: TORII · Alumni Sans · tracking  

---

## Domains / handles (check availability)

Priority: `torii.dev` · `gettorii.com` · `torii.security` · `@toriigate`  
Fallback: `usetorii.com` · `toriihq.com`

---

## Files

| File | Role |
|------|------|
| `torii-landing.html` | Customer / Hub71 landing |
| `torii-brand.md` | This brand lock |
| `luffy-security-landing.html` | Legacy (superseded by Torii) |
| Eng repo `luffy-pr-review-agent` | Implementation substrate — rename later if desired |

---

## Hub71 form answers (brand-aligned)

- **Company name:** Torii  
- **Product name:** Torii Gate  
- **One sentence:** Torii Gate is a PR/CI security gate that reviews AI-written and human code with agent tools, evidence, and merge protection.  
- **Roadmap:** Torii Trust (SAST validation) → Torii Plane (coding-agent policy).  

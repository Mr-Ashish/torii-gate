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
| **Primary (buyer)** | The gate gets stricter and quieter over time — not noisier. |
| **Hub71** | Torii gates AI-written code in CI — evidence-backed findings, false-positive memory, merge authority. |
| **AppSec fatigue** | The gate gets stricter and quieter over time — not noisier. |
| **Buyer diagram** | Review + check → compound (skills + memory) → merge signal `torii/gate`. |
| **Eng (Advanced)** | Maker + checker; skill loop route→hit→fitness→dual→attr→inject; memory pages cold truth. |
| **Skills** | Skills that do not contribute do not ship in the next prompt. |
| **Memory** | Stale memory does not confirm findings or crowd the inject budget. |
| **Memory (AppSec)** | False positives die twice — and true positives stay sharp. |
| **vs SAST** | Scanners generate findings; Torii is the merge authority that compounds. |
| **Tagline** | Nothing ships without crossing the gate. |

**Buyer diagram (canonical):** [`BUYER-DIAGRAM.md`](BUYER-DIAGRAM.md) · landing collapses A–E into three beats; F-IDs only under Advanced / `docs/research/`.

---

## ICP (lock)

| Buy | Do not sell first |
|-----|-------------------|
| Platform / DevEx owning required checks | Teams that only want PR style nits |
| AppSec drowning in SAST + AI PR volume | Full ASPM RFP day one |
| Eng leads shipping AI code without a security owner | Offensive red-team retainers |

**Job to be done:** *Give every PR a security merge authority that compounds (memory + skills), not another comment bot.*

---

## Buyer story (primary)

See [`BUYER-DIAGRAM.md`](BUYER-DIAGRAM.md). Three beats only on customer surfaces:

1. **Review + check** — tools on the diff; demote empty APPROVE  
2. **Compound** — skills measure in; memory pages in; quieter next PR  
3. **Merge signal** — required check **`torii/gate`**

## Advanced — skill & memory loops (engineers)

Customer-facing stage strings (not for hero copy):

`route → hit → fitness → dual → attr → inject`

```text
compound → write → consolidate → effective → federate → recall → tiers → search
```

Differentiator vs static skill dumps / forever MEMORY.md: measure contribution, demote free-riders, integrity-gate compound, tier core vs archival, budget soft re-prompts.

**Measured product scorecard (buyers first):** [`scorecard-metrics.md`](scorecard-metrics.md) — commercial overall_est + product surfaces, then Advanced loop metrics.

Ops (not marketing):

```bash
python3 scripts/torii.py doctor
python3 scripts/torii.py scorecard
python3 scripts/buyer_narrative_check.py fixture
```

Research IDs and hub-archival / GEPA refine depth: `PRODUCT.md` → **Advanced** · `docs/research/`.

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

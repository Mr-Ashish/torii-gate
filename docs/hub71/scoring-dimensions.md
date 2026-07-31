# Scoring dimensions — master inventory (revised)

**Purpose:** One canonical list of every axis we scored ideas on for Hub71 / Luffy / founder lock.  
**Scale:** 1–5 unless marked filter (pass/fail) or composite (derived).  
**Source of truth for full catalogue scores:** `idea-scores-full.csv` (20 atomic dims A–E).

---

## How many dimensions?

| Layer | Count | Role |
|-------|------:|------|
| **Atomic (scored 1–5)** | **20** | What goes in the CSV |
| **Programme filter** | **1** | MZN — binary OUT |
| **Pillar composites** | **3** | PMF · Hub · Ship |
| **Meta composites** | **2** | Joint · Triple (derived) |
| **Within-space market set** | **10** | Used only for AppSec idea re-rank |
| **Early v1 set (superseded)** | **10** | First recursive rank (A–J letters) |

**Canonical for “score any idea for Hub71” = Families A–E (20 dims) + MZN filter + 3 pillars.**

---

## Family A · First principles / PMF (5)

| ID | Name | High score (5) means | Low score (1) means |
|----|------|----------------------|---------------------|
| **A1** | Asymmetry / upside | Power-law outcome, software margins, platform path | Linear services, hard cap on scale |
| **A2** | Easy sell | Budgeted pain, short sales cycle, clear buyer, ROI ≤ ~30 days | Education sell, long enterprise only, no owner |
| **A3** | PMF iteration speed | Weekly ship/learn; high-frequency product usage | Annual sales cycles; no usage signal |
| **A4** | Metric clarity | North star + kill rules named before build | Vanity metrics only; no kill criteria |
| **A5** | Organic compound | Retention, expansion, network/data flywheel | One-shot projects; no compounding |

**Pillar PMF** ≈ mean(A1…A5) — *Can we get PMF?*

---

## Family B · UAE / Hub71 market fit (6)

| ID | Name | High score (5) means | Low score (1) means |
|----|------|----------------------|---------------------|
| **B1** | C18 / past pattern | Matches selected cohorts: AI×vertical, B2B, fintech, climate, health, deep tech | Pure consumer meme, no B2B, no sector story |
| **B2** | UAE policy fit | Aligns sovereign AI, cyber, Net Zero, health, fintech, logistics, digital gov | Irrelevant or antagonistic to AD priorities |
| **B3** | Abu Dhabi story | Credible why AD: HQ, pilots, ADGM, sovereign buyers, relocate narrative | Could be anywhere; AD is optional sticker |
| **B4** | Select odds realism | Honest probability vs ~1% Access bar (traction, team, fit) | Fantasy “we’re special” with no proof path |
| **B5** | India–UAE corridor | CEPA / immersion / India-build · Gulf-sell edge | No India or Gulf link |
| **B6** | Relocate fit | Founder can move AD for programme duration / long-term | Cannot or will not relocate |

**Pillar Hub (market half)** includes B1–B6 (with C doors below).

---

## Family C · Hub71 programme doors (6 scored + 1 filter)

| ID | Name | High score (5) means | Notes |
|----|------|----------------------|--------|
| **C1** | Access General | Strong fit for pre-seed→A, 12-mo scale track | Primary door for most ideas |
| **C2** | Initiate | Fits early idea + venture-builder path | Lower if product already mature |
| **C3** | Hub71+ AI | AI is core product (not marketing varnish) | Form checkbox / track |
| **C4** | Specialist | Life Sci / DA / Climate / SAVI / ECA fit | Most software scores low |
| **C5** | Sandbox | Regulator co-test path (fintech/health etc.) | Optional uplift |
| **C6** | India immersion | UAE–India CEPA immersion programme fit | Corridor dual-use |
| **—** | **MZN (filter)** | Emirati-only track | **OUT for non-Emirati founders** — do not score; hard fail |

**Pillar Hub** ≈ blend of B* + max/relevant C doors (Access + +AI weighted highest for our path).

---

## Family D · Ship (1)

| ID | Name | High score (5) means | Low score (1) means |
|----|------|----------------------|---------------------|
| **D1** | Build speed | Working demo in weeks; solo/small software founder | Years of hardware/reg before demo |

**Rule we used:** **Ship ≥ 4** required for “start building” list — else prestige trap.

**Pillar Ship** ≈ D1 (+ sometimes A2/A3 for “can prove before interviews”).

---

## Family E · Asset / research / competition (3)

| ID | Name | High score (5) means | Low score (1) means |
|----|------|----------------------|---------------------|
| **E1** | Architecture reuse | Luffy control plane maps 1:1 (gate → tools → memory → traces) | Greenfield; no reuse |
| **E2** | Paper / research support | Supported by SLR, RepoAudit, hybrid SAST, agent-security literature | Pure hype, no research spine |
| **E4** | Competition / defensibility | Room vs incumbents; moat via memory, gates, eval data | Red ocean clone day-1 |

**Note:** **E3 was never used in the CSV** (numbering skips E3 → E4). Treat E4 as “competition / defensibility.” Optional rename later: E3_competition.

---

## Family F · Legal / compliance risk (used in narrative re-ranks; not columns in CSV)

Scored informally when we said “all dims + legal.” Recommend adding explicitly next rescore:

| ID | Name | High score (5) means | Low score (1) means |
|----|------|----------------------|---------------------|
| **F1** | Legal / liability safety | Low product liability; assistive tooling; clear ToS | Offensive hacking, auto-exploit, financial advice, PHI without stack |
| **F2** | Regulatory burden | Ship without license/regulator day-1 | Needs banking license, medical device, dual-use export hell |
| **F3** | Entity / geo simplicity | Fits WY LLC + India ops + AD programme path | Conflicting residency / ODI blockers as product of idea itself |

---

## Composites (derived, not re-scored by hand)

| Name | Definition (as used) | Use |
|------|----------------------|-----|
| **pmf** | Mean of A1–A5 | PMF pillar |
| **hub** | Weighted blend of B1–B6 + C doors | Hub71 care? |
| **ship** | D1-centric (with A2/A3 influence in some runs) | Prove before interviews? |
| **joint** | Blend of pmf + hub | “Good business + AD” without ship |
| **triple** | Blend of pmf + hub + ship | Balanced decision score |
| **final** | Weighted sum of all atomic dims (A–E) | Primary rank in `idea-scores-full.csv` |

---

## Weights used for full catalogue `final` (canonical intent)

Approximate family weights after normalization (weights were fixed when sum exceeded 1.0):

| Family | Intent | Rough share of final |
|--------|--------|----------------------|
| A PMF | Can we win the market? | ~30–35% |
| B UAE market | Will AD care? | ~20–25% |
| C Programme doors | Which doors open? | ~15–20% |
| D Ship | Can we prove soon? | ~10–15% |
| E Asset / research | Unfair edge + moat | ~10–15% |
| F Legal (when used) | Don’t pick suicide product | small / hard filter |

**Hard rules (not weights):**
1. MZN → eliminate  
2. Ship (D1) < 4 → not on build list  
3. Prefer C3 (+AI) high for +AI track narrative  

Exact per-dim weights lived in the ranking scripts; if rescoring, normalize so Σw = 1.0.

---

## Within-space market set (AppSec re-rank only — 10 dims)

Used for `within-space-hub71-ranking.csv` / market analysis §9. **Does not replace A–E**; zooms inside cyber/Luffy space.

| ID | Name | Weight | High score means |
|----|------|-------:|------------------|
| M1 | Market fit (J1–J4 jobs) | 0.12 | Solves detect/trust/gate/govern jobs buyers pay for |
| M2 | Timing (2026–28) | 0.10 | Wave of AI code + ASPM + agent gov |
| M3 | White space vs incumbents | 0.14 | Not CodeRabbit/Snyk head-on day-1 |
| M4 | Ship from Luffy | 0.14 | Architecture reuse + weeks-to-demo |
| M5 | Hub71 fit | 0.14 | UAE/AI/doors narrative |
| M6 | Moat path | 0.12 | Year-3 defensibility (memory, eval, gate) |
| M7 | Buyer urgency | 0.10 | Budgeted pain now |
| M8 | ACV path | 0.06 | Credible path to $10k–100k ACV |
| M9 | Legal safe | 0.04 | Low liability |
| M10 | Platform compound | 0.04 | Wedge → control plane optionality |

---

## Early v1 set (superseded — first recursive rank)

Single-letter set before Hub71 catalogue explosion. Map → current:

| v1 | Meaning | Maps to |
|----|---------|---------|
| A_asymmetry | Upside | A1 |
| B_easy_sell | Easy sell | A2 |
| C_pmf_loop | PMF loop | A3 |
| D_metrics | Metrics | A4 |
| E_compound | Compound | A5 |
| F_hub71_past | Past pattern | B1 |
| G_uae_policy | UAE policy | B2 |
| H_ad_story | AD story | B3 |
| I_build_speed | Build speed | D1 |
| J_select_odds | Select odds | B4 |

Do not mix v1 letters with Family C programme doors (C1 Access ≠ v1 C_pmf_loop).

---

## Score rubric (universal 1–5)

| Score | Meaning |
|------:|---------|
| 5 | Exceptional / structural advantage |
| 4 | Strong / default yes |
| 3 | Acceptable / average |
| 2 | Weak / workaround needed |
| 1 | Structural fail on this axis |

---

## Quick checklist (copy for new ideas)

```
A1 asymmetry __  A2 easy_sell __  A3 pmf_loop __  A4 metrics __  A5 compound __
B1 c18_pattern __  B2 uae_policy __  B3 ad_story __  B4 select_odds __  B5 india_uae __  B6 relocate __
C1 access __  C2 initiate __  C3 plus_ai __  C4 specialist __  C5 sandbox __  C6 india_immersion __
D1 build_speed __
E1 arch_reuse __  E2 papers __  E4 competition __
F1 legal_safe __  F2 regulatory __  F3 entity_geo __   [optional]
MZN filter: OUT / N/A
Ship gate: D1 ≥ 4? Y/N
```

---

## Files

| File | Contents |
|------|----------|
| `idea-scores-full.csv` | 17 ideas × A–E atomic + composites |
| `within-space-hub71-ranking.csv` | AppSec-only M1–M10 ranking |
| `founder-collation.html` §02 | HTML tables for A–E |
| `appsec-market-hub71-analysis.md` §9 | Market weights M1–M10 |
| `scoring-dimensions.md` | **This master list** |

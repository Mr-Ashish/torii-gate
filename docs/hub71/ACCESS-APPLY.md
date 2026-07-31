# Hub71 Access — Torii application pack (paste-ready)

**Programme:** Access → **General Track** (sector-agnostic)  
**Also select:** **Hub71+ AI** = YES (on the same form)  
**Do not select:** MZN · ECA · SAVI · Life Sci · Climate · Digital Assets · Sandbox as primary  
**Optional later:** India Immersion (CEPA) if open — same product story  

**Official links**
- Programme: https://www.hub71.com/program/access-programme  
- Apply: https://www.hub71.com/program/access-programme/apply  
- Startup map: https://www.hub71.com/i-am-a-startup  

**Cohort 20 (confirm on site before submit)**
- Deadline: **21 August 2026**  
- Programme start: **February 2027**  
- Package (public): ~AED 250k in-kind + AED 250k SAFE; top-up path up to +AED 250k  
- Requirement: **≥1 founder relocates long-term to Abu Dhabi** and builds a team there  

**Product lock**
- Company brand: **Torii**  
- Product: **Torii Gate** (PR/CI security gate)  
- Roadmap: Torii Trust → Torii Plane  
- Repo: https://github.com/Mr-Ashish/torii-gate  

*Fill personal name / email / phone / LinkedIn yourself. Bracketed [ ] = your personal data.*

---

## 0. Programme selection (first choices)

| Field | Answer |
|-------|--------|
| Programme | **Access Programme** |
| Track | **General Track** (sector agnostic) |
| Specialist programmes (ECA / SAVI / Life Sci / DA / Climate) | **No / not applying** |
| MZN × Hub71 | **No** (not Emirati founder track) |
| Sandbox | **No** as primary (pipeline product, not regulator sandbox) |
| Hub71+ AI eligibility | **Yes** (see AI section below) |

---

## 1. Founder / contact

| Field | Paste |
|-------|--------|
| First name | [Your first name] |
| Last name | [Your last name] |
| Email | [Your email] |
| Phone / WhatsApp | [+country code…] |
| Country of residence | **India** (or current) |
| Nationality | [Your nationality] |
| LinkedIn | [URL] |
| Job title | **Founder & CEO** |
| Are you a founder? | **Yes** |
| Full-time on startup? | **Yes** (or: transitioning to full-time for Access / AD move) |
| Willing to relocate long-term to Abu Dhabi? | **Yes** — I commit to relocating if selected and building the team out of Abu Dhabi. |
| How did you hear about Hub71? | [Website / friend / community / India ecosystem / other] |

---

## 2. Company basics

| Field | Paste |
|-------|--------|
| Company / startup name | **Torii** |
| Product name | **Torii Gate** |
| Website | https://github.com/Mr-Ashish/torii-gate *(replace with product domain when live)* |
| One-liner (≤15 words) | **Security gate for every pull request — AI-written and human code.** |
| Tagline | **Nothing ships without crossing the gate.** |
| Founded | **2026** |
| HQ today | **India** (building); **target HQ / hub: Abu Dhabi** via Hub71 |
| Legal entity | **US Wyoming LLC** (formation in progress / formed via doola) · AD entity planned on selection |
| Stage | **Pre-seed** |
| Sector | **Cybersecurity / Developer tools / Enterprise software** |
| Sub-sector | **Application security (AppSec), DevSecOps, AI security** |
| B2B / B2C | **B2B** |
| Business model | **SaaS subscription** (per seat / per org + usage for agent runs) |

---

## 3. Hub71+ AI question (exact theme)

**Question (site):**  
*Is your startup utilizing or building AI solutions as part of its core product offering? Which category best describes your focus?*

**Answer — YES:**

> **Yes.** AI is core to Torii, not a feature bolt-on.  
> **Torii Gate** is an **agentic PR/CI security gate**: a control plane that assembles PR context, runs a tool-using AI agent (code/security analysis via workspace tools), validates findings with evidence, writes durable false-positive memory, and enforces merge authority (comments, labels, gate status).  
> **Category:** AI for **cybersecurity / software delivery security** (agentic AppSec / DevSecOps).  
> **Not:** generative content, pure chatbots, or “AI-washed” dashboards. The product fails without the agent loop, tools, and memory.

---

## 4. Problem (paste block)

**Short (≤500 chars):**

> Engineering teams ship AI-generated code every hour, but security still runs on annual pentests and noisy SAST scanners. False-positive rates of 60–90% train developers to ignore alerts. Real vulnerabilities merge in minutes. Security review does not scale to agent- and copilot-written code.

**Longer:**

> Three failures compound:  
> 1) **Volume** — AI coding multiplies PR velocity without multiplying security owners.  
> 2) **Noise** — Traditional SAST floods queues; teams mute tools; true risk hides in the backlog.  
> 3) **Timing** — Point-in-time pentests age out before the next sprint; the only place with continuous merge *authority* is the PR/CI gate — and that gate is still weakly secured for AI-era code.  
> Buyers need **evidence-backed security decisions at merge time**, not another quality chatbot or another scanner dashboard.

---

## 5. Solution / product

**Short:**

> **Torii Gate** sits on every pull request and CI check. An agent reviews changes with security-first lenses, cites path/line evidence, remembers false positives, and can block merge on high-severity findings. Same control plane expands to Torii Trust (SAST validation) and Torii Plane (policies for coding agents).

**How it works (steps):**

1. Trigger: `@torii review this pr` or workflow dispatch  
2. Assemble bounded PR context (sparse paths, capped diff, SOUL + memory)  
3. Hermes agent + tools via OpenRouter — security pack default  
4. Normalize verdict · labels · **torii/gate** status  
5. Distill FP memory under `.torii/` · redacted audit traces  

**Differentiation (one paragraph):**

> CodeRabbit optimizes quality comments. Snyk/Semgrep optimize detection volume. AI red-team platforms optimize after-the-fact offense (capital- and liability-heavy). **Torii owns the security merge gate**: evidence, measured FP memory, and authority at PR/CI — the control point developers already pass through.

**Repo / demo links:**
- Product repo: https://github.com/Mr-Ashish/torii-gate  
- Architecture substrate (control plane lineage): https://github.com/Mr-Ashish/luffy-pr-review-agent  
- Landing (local): `artifacts/torii-landing.html` → host when ready  

---

## 6. Value proposition / ICP

**ICP (ideal customer profile):**
- Series A–growth **product companies** shipping on GitHub  
- Platform / DevEx + AppSec jointly own CI  
- Already use (or tried) SAST and hate triage tax  
- Rolling out Copilot / Cursor / coding agents  

**Buyer personas:** Staff eng / platform lead (installs), AppSec engineer (trusts findings), Head of Eng (velocity + risk), later CISO (posture + agent governance).

**Value props:**
1. Security signal **in minutes on every PR**, not weeks after release  
2. **Lower triage tax** via evidence + FP memory (not “zero FP” slogans)  
3. Ready path to **govern coding agents** (Torii Plane) as AI engineering becomes the norm  

---

## 7. Market

**TAM / SAM / SOM (honest, pitch-ready):**

| Layer | Figure (working) | Rationale |
|-------|----------------|-----------|
| TAM | AppSec + agentic cyber ~**$15–25B** by late decade | Broad security spend; AppSec ~$12–16B growing ~11%+ |
| SAM | Pipeline-native security gates + trust layers ~**$2–4B** | PR/CI security, AI review security slice, mid-market |
| SOM (5y) | **$20–80M ARR** path if wedge wins mid-market DevSecOps | Not claiming year-1 unicorn |

**Trends you can cite without overclaiming:**
- AI-generated code as top AppSec concern  
- ASPM adoption ramping (Gartner direction: regulated orgs toward mainstream ASPM)  
- Capital and product heat in AI code review (e.g. CodeRabbit scale) and continuous AI pentest (e.g. XBOW) — proves budget; we enter at the **gate**, not as full red-team clone  

**MENA / AD angle:**
- Banks, energy, government digital programmes need **software supply-chain and pipeline security**  
- Sovereign AI adoption needs **agent governance**, not only model APIs  
- Abu Dhabi as **global HQ** for a security SaaS selling US/EU/India + GCC lighthouse accounts  

---

## 8. Business model & pricing (draft)

| Tier | Who | Indicative price |
|------|-----|------------------|
| Starter | Small teams | Free / low seat trial on public repos |
| Team | 10–100 eng | ~$15–40 / active developer / month |
| Business | Mid-market | ~$8–25k ACV (seats + agent run pool) |
| Enterprise | Policy, SSO, audit, agents | $40–100k+ ACV (Torii Plane) |

**Unit economics story:** Multi-model routing; cheap models for triage; expensive models only for hard validation; memory reduces repeated spend.

---

## 9. Traction (be honest — edit numbers to truth)

**Current (as of product lock):**

| Metric | Status |
|--------|--------|
| Product | Torii Gate repo public; security pack default; 400+ unit tests green |
| Control plane | Production-grade orchestrator (Hermes + OpenRouter + memory + traces) ported from prior PR-review agent work |
| Customers / paid | **[0 / early design partners — update]** |
| Waitlist / pilots | **[update]** |
| Revenue | **[0 / pre-revenue]** |
| Users | **[dogfood + target design partners]** |

**Near-term traction plan (90 days) — strong for Access even if early:**

1. 3–5 design-partner engineering orgs (GitHub App install)  
2. Public metrics: time-to-signal, FP suppressions learned, PRs gated  
3. One AD/GCC design partner exploration (bank / gov tech / large enterprise digital)  
4. Landing + demo video of insecure PR → Torii REQUEST CHANGES  

*Never invent customers. Empty traction + clear plan beats fake logos.*

---

## 10. Competition

| Competitor type | Examples | Why Torii wins wedge |
|-----------------|----------|----------------------|
| AI PR quality | CodeRabbit | They optimize quality; we optimize **security gate + evidence** |
| SAST / SCA | Snyk, Semgrep, Checkmarx | Detection volume; we add **trust + merge authority** |
| Platform free | GitHub Advanced Security | Good baseline; we go deeper on agent evidence + FP memory + multi-SCM path |
| AI red team | XBOW, continuous pentest vendors | Real market; wrong **first** product (capital, liability). Roadmap “proof mode” only |
| Services | Traditional pentest / Sec1-style | Continuous narrative OK; we stay **product + pipeline**, not services clone |

**Positioning sentence:**  
*Torii is the security gate and trust layer for AI-written code — not a quality review bot and not a day-one autonomous red team.*

---

## 11. Team

| Field | Paste |
|-------|--------|
| Founders | **[Your name]** — Founder & CEO |
| Background | **[2–4 bullets: engineering, AI agents, security, shipping systems — e.g. built production PR review agent control plane]** |
| Why this team wins | Deep ownership of the **agent control plane** (orchestrator, tools, memory, evals) that Torii productizes as security; can ship weekly |
| Advisors | **[if any]** |
| Full-time plan | Founder full-time; hire eng + GTM from AD after Access |

---

## 12. Fundraising

| Field | Paste |
|-------|--------|
| Funds raised to date | **$0 / bootstrapped** *(edit if otherwise)* |
| Looking to raise | Pre-seed / seed post-Access traction |
| Hub71 SAFE | Understood: cash incentive via SAFE per programme terms |
| Prior accelerators | **[none / list]** |

---

## 13. Why Hub71 / Why Abu Dhabi (critical section)

**Paste:**

> We are building a **global B2B AI security product** and want **Abu Dhabi as our long-term base**. Hub71 Access is the right door because we need:  
> 1) **Market access** — introductions to UAE banks, energy, government digital, and enterprise tech buyers who care about software risk and AI governance;  
> 2) **Capital network** — 40+ capital partners and a serious pre-seed→A path while we convert design partners to ACV;  
> 3) **Operating base** — housing, office, visas, ADGM-friendly environment so we can hire and host enterprise diligence from AD;  
> 4) **AI ecosystem** — Hub71+ AI fits our core: agentic systems securing the software supply chain.  
>  
> At least one founder will **relocate long-term to Abu Dhabi** if selected, set KPIs in the guided track, and build GTM from AD while engineering talent can remain hybrid (India build / AD sell + HQ narrative).  
>  
> **12-month AD plan:** design partners in GCC + global PLG; 1–2 lighthouse logos; Torii Trust beta; foundation for Torii Plane (coding-agent security control plane) as the enterprise platform story.

**What you want from Hub71 (ask):**
- Corporate / government pilot intros (AppSec, platform, CISO stakeholders)  
- Investor intros at pre-seed/seed  
- In-kind: office, housing, insurance, visa/licensing support  
- Mentors for enterprise security sales and MENA GTM  

---

## 14. India–UAE / corridor (if asked)

> Engineering and product iteration from **India** (cost-efficient agent eval loops); **customers and HQ gravity in Abu Dhabi / GCC + global SaaS**. CEPA / India immersion is a bonus distribution path, not a substitute for Access.

---

## 15. Risks / legal (if free text allows)

> Torii Gate is **pipeline-native and authorized-use**. We do not market autonomous unauthorized exploitation. Continuous offensive features (if any) require explicit rules of engagement. Product defaults: redacted traces, untrusted PR content treated as data, assistive security with optional blocking.

---

## 16. Pitch deck PDF checklist (required by Hub71)

Upload a **PDF** covering:

| # | Slide | Content for Torii |
|---|--------|-------------------|
| 1 | Title | Torii · Torii Gate · Security gate for every PR · Hub71 Access |
| 2 | Problem | AI code velocity · SAST noise · annual pentest obsolescence |
| 3 | Insight | Control plane at the gate > chatbots and scanner piles |
| 4 | Solution | Torii Gate product walkthrough |
| 5 | Product / demo | Architecture diagram + screenshot / metrics |
| 6 | How it works | Trigger → agent → evidence → memory → gate |
| 7 | Market | AppSec + AI security + agent gov waves |
| 8 | ICP & GTM | GitHub-first PLG → mid-market → enterprise Plane |
| 9 | Competition | Table vs CodeRabbit / Snyk / red-team AI |
| 10 | Business model | Seats + usage + enterprise ACV |
| 11 | Traction | Honest metrics + 90-day plan |
| 12 | Roadmap | Gate → Trust → Plane |
| 13 | Team | Founder + relocate commitment |
| 14 | The ask | Hub71 Access + AD plan + SAFE understanding |
| 15 | Appendix | Papers / security pack / repo links |

---

## 17. Short answers bank (character-limited fields)

**Elevator (30 sec):**  
Torii Gate is the security gate for pull requests. When AI and humans ship code, we run an agentic security review with real evidence, remember false positives, and can block risky merges — so teams move fast without shipping known-class vulnerabilities.

**Mission:**  
Make insecure code fail closed at the gate — especially code written by AI agents.

**Vision:**  
The default control plane that governs how humans and coding agents ship software safely.

**Moat:**  
Orchestration depth + tool evidence + org FP memory + eval traces; not a thin LLM wrapper.

**North-star metrics:**  
1) Confirmed findings with path evidence  
2) FP rate / suppressions learned  
3) PRs gated / time-to-signal  

---

## 18. Submit checklist

- [ ] Access **General** selected (not specialist, not MZN)  
- [ ] **AI = Yes** + category = cybersecurity / agentic AppSec  
- [ ] Relocate = **Yes** (if true)  
- [ ] Company name **Torii** · product **Torii Gate**  
- [ ] Links: GitHub torii-gate · website if any  
- [ ] Pitch deck PDF uploaded  
- [ ] Traction numbers **true**  
- [ ] Personal identity fields filled  
- [ ] Submit before **21 Aug 2026** (Cohort 20) — reconfirm date on site  

---

## 19. After submit

| Stage | What happens |
|-------|----------------|
| Review | Jun–Nov 2026 window for C20 (per site) |
| Round 2–3 | Pitches to Hub71 + partners |
| Round 4 | Final committee |
| Start | Feb 2027 |

Prepare: 5-min demo of Torii Gate on a real insecure PR; one-pager; founder relocate plan.

---

*Not legal/immigration/investment advice. Confirm equity/SAFE terms with Hub71 counsel before signing.*

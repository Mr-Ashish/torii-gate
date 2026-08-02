# Torii Gate — pricing & packaging

**Honest status:** open-source product (MIT) · **pre-revenue** · design partners welcome.  
This page is the **buyer packaging surface** — not a Hub71 application form.

**Model:** **open core + optional support / multi-org**. You always own the gate; you pay for help and fleet scale when you need them.

```text
self-host Gate (free)  →  Team support  →  Business multi-org  →  Enterprise (Plane)
```

## Tiers

| Tier | Who | What you get | Indicative price |
|------|-----|--------------|------------------|
| **Open (Gate)** | Any team that can install a GitHub Action | Full Torii Gate: `@torii review` · required check **`torii/gate`** · path-evidenced findings · local `.torii/` memory · gate certificates · quieter-over-time chart | **$0** — MIT · you bring OpenRouter (or compatible) keys · measured dogfood **~$0.01 / PR** p50 |
| **Team** | 10–100 eng · Platform / AppSec owner | Everything in Open + **priority response** on install / required-check / fail-closed ops · design-partner channel · help keeping cost/PR honest | **~$15–40 / active developer / month** *(indicative · not live billing)* |
| **Business** | Multi-repo / multi-org fleets | Team + **enterprise light** (`install --tenant`) · isolation + federation privacy (themes only) · optional support for hub-managed callers | **~$8–25k ACV** *(seats + agent-run guidance)* |
| **Enterprise** | Policy · SSO · agent fleet control | Business + roadmap **Torii Plane** (tool allowlists, spend policy, audit) · custom MSA | **$40–100k+ ACV** *(roadmap · not Gate v1)* |

> **Not sold as v1:** full ASPM dashboard · autonomous red team · auto-merge without humans · “zero false positives.”

## What “open core” means here

| Open (always free) | Paid when you need it |
|--------------------|------------------------|
| Gate agent + security pack | Human support / design partner |
| Required check **`torii/gate`** | Multi-org tenant fleet help |
| Compound memory & skills (self-host) | Custom deploy / policy workshops |
| Public labeled eval + cost vault docs | Future Plane control-plane features |

You never lose the merge authority if you stop paying — the pack stays on your repos.

## Path to value (before money)

```bash
./scripts/install-torii.sh --minimal /path/to/your-app
# secret OPENROUTER_API_KEY · require status check torii/gate
# @torii review this pr
python3 scripts/torii.py status --text
python3 scripts/torii.py quieter -- status   # after a few runs
```

Docs: [`INSTALL.md`](INSTALL.md) · [`GOLDEN-PATH.md`](GOLDEN-PATH.md) · [`QUIETER.md`](QUIETER.md) · measured cost: [`ops/cost-pr-dashboard.md`](ops/cost-pr-dashboard.md).

## Unit economics (why ~$0.01/PR is the story)

- Route cheap models for triage; escalate only when evidence is thin  
- Memory + dual gates cut repeat false positives (spend compounds down, not up)  
- Fail-closed tool-turns: no silent APPROVE burn  
- Soft budget: `TORII_MAX_COST_USD`  
- **Day-2 one screen:** `status --text` growth beat shows `open_core=$0 pre-revenue · unit=$X.XXX/PR` from the **local measured vault** (not list price · not federated)

Validate the workflow graph offline before any model spend:

```bash
python3 scripts/torii.py workflow -- validate   # free
python3 scripts/torii.py status --text          # unit=$…/PR when vault has cost samples
```

## Contact / design partners

**Design partner & paid pilot path (honest, pre-revenue):** [`PILOT.md`](PILOT.md)

- Apply: [Design partner issue template](https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml)  
- Repo: https://github.com/Mr-Ashish/torii-gate  
- Product brief: [`PRODUCT.md`](../PRODUCT.md)  
- Landing: https://mr-ashish.github.io/torii-gate/ · source [`docs/brand/landing.html`](brand/landing.html)  
- Programme notes (not pricing SoT): [`docs/hub71/ACCESS-APPLY.md`](hub71/ACCESS-APPLY.md)

*Paid billing not live. Never invent customers or closed deals. Traction table lives in PILOT.md.*

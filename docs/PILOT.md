# Torii Gate — design partner & paid pilot

**Honest status:** **pre-revenue** · **0 paid customers** · open core (MIT) ships free.  
This page is how serious teams become **design partners** or start a **paid pilot** — not a fake logo wall.

```text
install free Gate  →  dogfood on real PRs  →  design partner feedback  →  optional paid Team/Business pilot
```

## What we will never do here

- Invent customers, logos, ARR, or “in talks with FAANG”  
- Claim zero false positives  
- Auto-merge without a human  
- Charge for the open Gate pack itself (support / fleet help is optional)

## Design partner (default · free)

**Who:** Platform / DevEx / AppSec eng who can require **`torii/gate`** on one repo.

**You get**

| Item | Detail |
|------|--------|
| Full open Gate | Install pack · `@torii review` · certificates · quieter chart |
| Partner channel | Priority responses on install / fail-closed / required-check (best-effort) |
| Measured honesty | Cost/PR + public labeled eval tables you can audit |
| Influence | Feedback shapes defaults (not a custom fork) |

**You give**

1. Install on a **real** repo (not only a demo) within ~2 weeks  
2. Require **`torii/gate`** on the default branch (or document why not)  
3. 1–2 short feedback notes (what blocked, what surprised, cost/signal)  
4. Permission to say “design partner” **only if you opt in** (no public logo without yes)

**Apply:** open a GitHub issue with the **Design partner** template  
→ https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml  

Or email / DM linked from the repo if the template is unavailable — still no invented traction.

## Paid pilot (when you want a commercial trial)

Indicative only — **not live Stripe**. Pricing SoT: [`PRICING.md`](PRICING.md).

| Pilot | Duration | Indicative | Includes |
|-------|----------|------------|----------|
| **Team pilot** | 30–60 days | Team list price × seats (or fixed small SOW) | Design-partner channel + install workshop + cost/PR review |
| **Business pilot** | 60–90 days | Pro-rated Business ACV band | Multi-org `--tenant` · isolation review · hub-caller optional |

**Exit:** you keep the open pack on your repos either way.  
**Success criteria (shared):** time-to-signal, quieter trajectory, gate certificates on real PRs — not vanity comment volume.

## Path to value (before any money)

```bash
./scripts/install-torii.sh --minimal /path/to/your-app
# OPENROUTER_API_KEY · require torii/gate (job summary teaches this)
# @torii review this pr
python3 scripts/torii.py status --text
python3 scripts/torii.py quieter -- status
```

Landing: https://mr-ashish.github.io/torii-gate/ · Install: [`INSTALL.md`](INSTALL.md) · Pricing: [`PRICING.md`](PRICING.md).

## Traction (edit only with truth)

| Metric | Status |
|--------|--------|
| Paid customers | **0** |
| Design partners | **open — apply via issue template** |
| Revenue | **$0 / pre-revenue** |
| Public dogfood | Modal + Hermes on OSS PRs (`POST_COMMENT=0`) · cost p50 ~$0.01 |

*Never invent numbers. Empty traction + clear plan beats fake logos.*

## Operator checklist (us)

- [ ] Respond to design-partner issues within a few business days  
- [ ] Keep cost/PR vault + public-eval freshness honest  
- [ ] Do not list a logo without written opt-in  
- [ ] When first paid pilot closes, update this table and commercial cap narrative  

Refresh: `python3 scripts/pilot_surface.py fixture`

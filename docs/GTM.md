# Torii Gate — GTM outreach (honest · pre-revenue)

**Purpose:** give founders/operators **ready-to-send** copy to find design partners.  
**Not:** a fake logo wall, invented pipeline, or “in talks with FAANG.”

```text
open pack install  →  require torii/gate  →  design partner feedback  →  optional paid pilot
```

**Traction truth:** paid customers **0** · revenue **$0** · design partners **open (apply via issue)**.  
SoT: [`PILOT.md`](PILOT.md) · pricing: [`PRICING.md`](PRICING.md).

## Proof packet (paste into partner threads)

Auto-refreshed measured metrics (TTS · cost/PR · quieter · tool-use · public-eval) — **no fake logos**:

[`docs/PILOT-PROOF.md`](PILOT-PROOF.md) · regenerate: `python3 scripts/torii.py pilot -- packet`

## Who to message (ICP)

| Persona | Why they care | Ask |
|---------|---------------|-----|
| Platform / DevEx eng | Needs an honest required check for AI PR volume | Install on one repo · require `torii/gate` |
| AppSec eng | SAST noise + AI diffs | Path-evidenced block · quieter chart |
| Eng lead (security-minded) | AI code without an owner on every merge | Gate certificate + cost/PR honesty |

**Skip for v1:** full ASPM buyers, red-team agencies, teams that only want style nits.

## Rules (do not break)

1. Never invent customers, logos, ARR, or closed deals  
2. Never claim “zero false positives”  
3. Lead with **install free** — money only after path-to-value  
4. Prefer **one real repo** over a fleet pitch  
5. Log outcomes in PILOT.md traction table only with truth  

## Channel A — GitHub design-partner issue (default)

Send them the template (fills fields for you):

https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml

Short nudge if they already star/fork:

```text
Subject: Torii Gate design partner (free) — require torii/gate on one repo?

We ship an open-source PR security merge authority (MIT). Pre-revenue · 0 paid customers.

Ask: install the pack on one real repo, require status check `torii/gate`,
send 1–2 notes on what blocked / cost / quieter trajectory.

Apply: https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml
Install: https://github.com/Mr-Ashish/torii-gate/blob/main/docs/INSTALL.md
Landing: https://mr-ashish.github.io/torii-gate/
```

## Channel B — short DM / email (cold or warm)

```text
Hi {{name}} — quick ask, not a sales deck.

Torii Gate is open-source merge authority for AI/human PRs: agent tools on the
diff + deterministic checker + required check `torii/gate`. Measured dogfood
~90s / ~$0.01 per PR (OpenRouter). Pre-revenue · 0 paid · no fake logos.

Would you try a free design partner install on one repo this month?
Path: install pack → require torii/gate → @torii review → quieter chart.
Issue template: https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml
```

## Channel C — internal / community post

```text
Looking for design partners (free) for Torii Gate — PR/CI security merge authority.
Not another chatty bot: path-evidenced findings, gate certificates, quieter-over-time.
Open core MIT · pre-revenue · honest cost/PR tables.
Apply: design-partner issue on Mr-Ashish/torii-gate · INSTALL.md in five minutes.
```

## Path-to-value (paste into every thread)

```bash
./scripts/install-torii.sh --minimal /path/to/your-app
# secret OPENROUTER_API_KEY · require status check torii/gate
# @torii review this pr
python3 scripts/torii.py status --text
python3 scripts/torii.py quieter -- status
python3 scripts/torii.py pilot -- readiness
```

## Operator checklist (us)

- [ ] Prefer issue template over private promises  
- [ ] Respond within a few business days  
- [ ] After first partner: update PILOT.md traction **only with opt-in truth**  
- [ ] Keep public-eval freshness + cost vault honest (`public-eval -- status` · `ops -- status`)  
- [ ] Do not list logos without written opt-in  

## CLI

```bash
python3 scripts/torii.py pilot -- readiness
python3 scripts/torii.py pilot -- fixture
python3 scripts/diff_vs_sast.py fixture   # vs SAST one-pager for objections
```

Related: [`PILOT.md`](PILOT.md) · [`DIFF.md`](DIFF.md) · [`INSTALL.md`](INSTALL.md) · [`PRODUCT.md`](../PRODUCT.md).

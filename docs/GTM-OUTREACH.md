<!-- torii-gtm-outreach -->

# Torii Gate — GTM outreach (live metrics · ready to send)

_Generated: `2026-08-02T08:30:16Z` · metrics from local dogfood vault · **pre-revenue · 0 paid customers**_

> **Human sends these.** Never invent customers, logos, ARR, or closed deals. Numbers below are measured vault metrics — refresh before a campaign.

Outreach packs ready · channels=7 · TTS ~97s · cost ~$0.01/PR · labeled_tp=18 · 0 paid

## Live metrics (paste-ready)

| Metric | Value |
|--------|------:|
| Time-to-signal p50 | **~97s** |
| Cost/PR p50 | **~$0.01** |
| Tool-use rate | **91%** |
| Labeled TP (public eval) | **18** |
| Dogfood runs | 89 |
| Model pin | `deepseek/deepseek-v4-pro` |
| Paid customers | **0** |

**Readiness:** 8/8 · ok=`True`

Apply: https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml  
Landing: https://mr-ashish.github.io/torii-gate/  
Proof packet: [PILOT-PROOF.md](PILOT-PROOF.md) · static templates: [GTM.md](GTM.md)

---

## Channel A — GitHub issue nudge

```text
Subject: Torii Gate design partner (free) — require torii/gate on one repo?

We ship an open-source PR security merge authority (MIT). Pre-revenue · 0 paid customers.

Measured dogfood (own vault, not inventing logos): time-to-signal p50 ~97s ·
cost/PR p50 ~$0.01 · tool-use 91% · labeled TP vs SAST bench = 18.

Ask: install the pack on one real repo, require status check `torii/gate`,
send 1–2 notes on what blocked / cost / quieter trajectory.

Apply: https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml
Install: https://github.com/Mr-Ashish/torii-gate/blob/main/docs/INSTALL.md
Landing: https://mr-ashish.github.io/torii-gate/
Proof: https://github.com/Mr-Ashish/torii-gate/blob/main/docs/PILOT-PROOF.md
```

## Channel B — email / DM

```text
Hi {{name}} — quick ask, not a sales deck.

Torii Gate is open-source merge authority for AI/human PRs: agent tools on the
diff + deterministic checker + required check `torii/gate`. Measured dogfood
~97s / ~$0.01 per PR (OpenRouter · deepseek/deepseek-v4-pro). Pre-revenue · 0 paid · no fake logos.
Labeled public-eval TP=18 · tool-use rate 91% · dogfood runs=89.

Would you try a free design partner install on one repo this month?
Path: install pack → require torii/gate → @torii review → quieter chart.
Issue template: https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml
Landing: https://mr-ashish.github.io/torii-gate/
```

## Channel C — community post

```text
Looking for design partners (free) for Torii Gate — PR/CI security merge authority.
Not another chatty bot: path-evidenced findings, gate certificates, quieter-over-time.
Open core MIT · pre-revenue · honest cost/PR (~$0.01 p50) · TTS ~97s.
Apply: design-partner issue on Mr-Ashish/torii-gate · INSTALL.md in five minutes.
https://mr-ashish.github.io/torii-gate/
```

## Channel D — LinkedIn

```text
Building in public: Torii Gate — security merge authority for AI-written PRs.

Problem: copilots open PRs faster than AppSec can review; chatty AI reviewers add noise.
Approach: tools on the diff + deterministic checker + required GitHub check `torii/gate`.
Measured (own dogfood vault · 0 paid customers): TTS p50 ~97s · cost/PR ~$0.01 · tool-use 91%.

Free design partner: one real repo · require torii/gate · 1–2 feedback notes.
Apply → https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml
Landing → https://mr-ashish.github.io/torii-gate/

#AppSec #DevSecOps #AI #OpenSource
```

## Channel E — X / Twitter

```text
Torii Gate = PR security merge authority (not chatty review).

require `torii/gate` · path-evidenced findings · quieter over time
Dogfood: ~97s · ~$0.01/PR · tool-use 91% · 0 paid · MIT

Free design partner (one repo):
https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml
```

## Channel F — Show HN (honest · no hype)

```text
Show HN: Torii Gate – require torii/gate as a security merge authority for PRs

Torii is an open-source PR/CI gate: agent tools on the diff, a deterministic
checker that demotes weak APPROVE without path evidence, and a required status
check named `torii/gate`. Goal is merge authority that gets quieter over time
(FP memory + measured skill fitness), not another comment bot.

Honest metrics from our own Modal dogfood vault (pytorch PRs, POST_COMMENT=0):
- time-to-signal p50 ~97s
- cost/PR p50 ~$0.01 (OpenRouter · deepseek/deepseek-v4-pro)
- tool-use rate 91% · labeled TP on public eval = 18
- paid customers: 0 · pre-revenue · MIT open core

We are looking for free design partners on one real repo (require the check,
send 1–2 notes). No logo wall.

Landing: https://mr-ashish.github.io/torii-gate/
Apply: https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml
Repo: https://github.com/Mr-Ashish/torii-gate
```

## Channel G — objection (vs SAST / AI review)

```text
When someone says "we already have SAST / AI review":

SAST finds patterns; chatty AI review nags. Torii is **merge authority**:
required check `torii/gate` + path-evidenced findings + gate certificates.
Labeled public-eval: TP=18 · good_recall high · weak APPROVE FP proxy low
(see DIFF.md). Dogfood cost ~$0.01/PR · TTS ~97s. Install free before any pilot $.
https://mr-ashish.github.io/torii-gate/ · https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml
```

---

## Operator rules

1. Never invent customers, logos, ARR, or closed deals
2. Refresh metrics before sending: `python3 scripts/torii.py pilot -- outreach`
3. Prefer **one real repo** design partner over fleet pitch
4. After install: point them at `pilot -- week1`
5. Log traction in PILOT.md **only with opt-in truth**

## CLI

```bash
python3 scripts/torii.py pilot -- outreach   # refresh this file
python3 scripts/torii.py pilot -- packet     # proof one-pager
python3 scripts/torii.py pilot -- readiness
python3 scripts/torii.py pilot -- week1
```

Related: [GTM.md](GTM.md) · [PILOT.md](PILOT.md) · [DIFF.md](DIFF.md) · [INSTALL.md](INSTALL.md)

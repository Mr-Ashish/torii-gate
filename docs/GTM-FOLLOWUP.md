<!-- torii-gtm-followup -->

# Torii Gate — operator follow-up (live metrics · ready to reply)

_Generated: `2026-08-02T08:56:00Z` · metrics from local dogfood vault · **pre-revenue · 0 paid customers**_

> **Human sends these** after apply / star / install. Never invent customers, logos, ARR, or closed deals. Respond within a few business days.

Follow-up packs ready · templates=6 · TTS ~97s · cost ~$0.01/PR · 0 paid · human sends

## Cadence (us)

| When | Action | Template |
|------|--------|----------|
| <48h after apply issue | First response + install path | A |
| Day 3 no install signal | Soft nudge + blockers | B |
| After require-check live | Celebrate + week-1 feedback | F |
| Week 1 post-install | Ask 1–2 feedback notes | C |
| Star/fork warm lead | Short invite | D |
| Not ICP | Honest decline + open pack | E |

## Live metrics (paste-ready)

| Metric | Value |
|--------|------:|
| Time-to-signal p50 | **~97s** |
| Cost/PR p50 | **~$0.01** |
| Tool-use rate | **91%** |
| Labeled TP | **18** |
| Paid customers | **0** |

Apply: https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml  
Landing: https://mr-ashish.github.io/torii-gate/  
Outbound packs: [GTM-OUTREACH.md](GTM-OUTREACH.md) · static: [GTM.md](GTM.md)

---

## A — First response (apply issue)

```text
Thanks for applying — happy to design-partner with you (free · pre-revenue · 0 paid).

Path that works:
1. Install: https://github.com/Mr-Ashish/torii-gate/blob/main/docs/INSTALL.md
2. Secret: OPENROUTER_API_KEY (or your OpenRouter path)
3. Branch protection: require status check **torii/gate**
   · dry-run: `python3 scripts/torii.py quieter -- require-check`
   · enable (admin): `… quieter -- require-check -- --enable --yes`
4. On a PR: `@torii review this pr` (or pack workflow)
5. Week-1 checklist: `python3 scripts/torii.py pilot -- week1` → docs/PARTNER-WEEK1.md

Our dogfood (own vault, not inventing logos): TTS p50 ~97s · cost/PR ~$0.01 ·
tool-use 91% · labeled TP=18. Proof: docs/PILOT-PROOF.md · https://mr-ashish.github.io/torii-gate/

What we need back in week 1: 1–2 notes on what blocked / cost / quieter.
No public logo mention unless you opt in later.
```

## B — Day-3 nudge (no install yet)

```text
Quick nudge on the design-partner path — no pressure.

If install is stuck, the usual blockers are:
- missing OPENROUTER_API_KEY
- torii/gate not yet required on default branch
- pack workflow not on the PR event

Five-minute path: https://github.com/Mr-Ashish/torii-gate/blob/main/docs/INSTALL.md
Live check: `python3 scripts/torii.py quieter -- require-check` (want live_ok=true)
Week-1: `python3 scripts/torii.py pilot -- week1`

Happy to jump on a 15-min async thread if useful. Still free · 0 paid · MIT.
```

## C — Week-1 feedback ask

```text
If you got through install + require torii/gate — thank you.

When you have a minute, 1–2 short notes help more than a deck:
1. What blocked or surprised on first review?
2. Cost / time-to-signal vs expectation?
3. Did quieter / gate certificate feel useful?

Optional: paste `python3 scripts/torii.py status --text` (redact secrets).
We will not list you as a design partner publicly without opt-in.

Dogfood reference: TTS ~97s · ~$0.01/PR · TP=18 · https://mr-ashish.github.io/torii-gate/
```

## D — Star / fork warm reply

```text
Saw the star/fork — thanks.

If you want a free design partner install on one real repo (require `torii/gate`,
send 1–2 feedback notes), apply here:
https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml

Install: https://github.com/Mr-Ashish/torii-gate/blob/main/docs/INSTALL.md
Landing: https://mr-ashish.github.io/torii-gate/
Measured dogfood: ~97s · ~$0.01/PR · tool-use 91% · 0 paid customers.
```

## E — Not-ICP soft decline

```text
Thanks for the interest.

Honest take: Torii v1 is a **PR/CI security merge authority** (require `torii/gate`,
path-evidenced findings) for Platform/AppSec/eng leads — not full ASPM, not a
red-team agency product, and not a style-comment bot.

If that still fits one real repo, happy to design-partner free:
https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml · https://github.com/Mr-Ashish/torii-gate/blob/main/docs/INSTALL.md

If not, no hard feelings — the MIT pack stays open either way. Pre-revenue · 0 paid.
```

## F — After require-check live_ok

```text
Nice — `require-check` live_ok on your side is the real merge-authority step.

Next:
1. `python3 scripts/torii.py pilot -- week1` and confirm week1_ok
2. One organic `@torii review` on a real PR
3. 1–2 feedback notes (blocked / cost / quieter)

We measure quieter + certificates on *your* vault — not ours.
Reference dogfood: TTS ~97s · ~$0.01/PR · labeled TP=18.
Questions welcome. Still free · no logo without opt-in.
```

---

## Operator rules

1. Never invent customers, logos, ARR, or closed deals
2. Refresh before a reply wave: `python3 scripts/torii.py pilot -- followup`
3. Prefer one real repo over fleet pitch
4. Public “design partner” only with written opt-in
5. Update PILOT.md traction **only with truth**

## CLI

```bash
python3 scripts/torii.py pilot -- followup   # refresh this file
python3 scripts/torii.py pilot -- outreach   # outbound channel packs
python3 scripts/torii.py pilot -- week1
python3 scripts/torii.py pilot -- readiness
```

Related: [PILOT.md](PILOT.md) · [GTM.md](GTM.md) · [GTM-OUTREACH.md](GTM-OUTREACH.md) · [PARTNER-WEEK1.md](PARTNER-WEEK1.md)

<!-- torii-pilot-proof-packet -->

# Torii Gate — design partner proof packet

_Generated: `2026-08-02T08:30:17Z` · measured dogfood vault only · **pre-revenue · 0 paid customers**_

> **Never invent** customers, logos, ARR, or closed deals. This page is an auto-refresh of **local measured** metrics for outreach.

## One sentence

Torii Gate is a PR/CI **security merge authority**: agent tools on the diff, path-evidenced findings, required check **`torii/gate`**, quieter over time.

## Traction truth

| Fact | Value |
|------|------:|
| Paid customers | **0** |
| Revenue | **$0** |
| License | MIT open core |
| Commercial surface est. | **8.5/10** (cap until paid pilot) |

## Measured dogfood (local vault · not federated)

| Metric | Value |
|--------|------:|
| Time-to-signal p50 | **97s** |
| Cost/PR p50 | **$0.014** |
| Dogfood runs | 89 |
| Gate certificates (vault n) | 27 |
| Quieter | ok=True · getting_quieter=False · score=0.7274 |
| Local vault | organic=7 · demo=2 |
| Tool-use rate | **91%** · ok=True |
| Public eval | ok=True · fresh=True · model=`deepseek/deepseek-v4-pro` |
| vs SAST / AI review | labeled_tp=**18** · good_recall=1.0 · weak_fp=0.0 · [DIFF.md](DIFF.md) |

Audit: [cost/PR dashboard](ops/cost-pr-dashboard.md) · [golden-path metrics](benchmarks/golden-path-metrics.md) · [public eval](benchmarks/public-eval/SCORECARD.md) · [quieter](QUIETER.md).

## Shared success criteria (partner pilot)

| Criterion | Pass |
|-----------|:----:|
| `docs_honest` | yes |
| `golden_path_ready` | yes |
| `time_to_signal_measured` | yes |
| `cost_honesty` | yes |
| `gate_certs_in_vault` | yes |
| `quieter_surface` | yes |
| `public_eval_fresh` | yes |
| `commercial_surfaces` | yes |

**Readiness:** 8/8 · ok=`True` · full=`True`

## Path to value (5 minutes)

```bash
./scripts/install-torii.sh --minimal /path/to/your-app
# secret: OPENROUTER_API_KEY
# branch protection: require status check torii/gate
# on a PR: @torii review this pr
python3 scripts/torii.py status --text
python3 scripts/torii.py quieter -- status
python3 scripts/torii.py pilot -- readiness
```

## Apply (design partner · free)

https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml

Or: [docs/PILOT.md](PILOT.md) · [docs/GTM.md](GTM.md) · Pages: https://mr-ashish.github.io/torii-gate/

## Refresh this packet

```bash
python3 scripts/torii.py pilot -- packet
# → docs/PILOT-PROOF.md (+ .torii/pilot-proof.md when .torii/ exists)
```

---

_One-liner:_ Pilot readiness 8/8 · docs_honest=True · readiness_ok=True (pre-revenue · 0 paid)

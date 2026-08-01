<!-- torii-pilot-surface -->

# Pilot / design-partner surface

_Generated: `2026-08-01T19:42:19Z` · docs_pass=`True` · readiness_ok=`True`_

Pilot readiness 8/8 · docs_honest=True · readiness_ok=True (pre-revenue · 0 paid)

## Doc honesty checks

| Check | Pass |
|-------|:----:|
| `pilot_md` | yes |
| `design_partner_section` | yes |
| `paid_pilot_section` | yes |
| `path_to_value` | yes |
| `success_criteria` | yes |
| `issue_template` | yes |
| `template_requires_repo` | yes |
| `pricing_links_pilot` | yes |
| `readme_links_pilot` | yes |
| `product_links_pilot` | yes |
| `landing_links_pilot` | yes |
| `cli_group_wired` | yes |
| `honesty_pre_revenue` | yes |
| `honesty_zero_paid` | yes |
| `honesty_never_invent` | yes |
| `honesty_no_fake_arr` | yes |

## Measured readiness (shared success criteria)

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

### Vault snapshot (local only)

- time-to-signal p50: **93.0s** · dogfood_runs=77
- cost/PR p50: **$0.014** · cost_ok=True
- gate certificates: n=27 · vault cost p50=$0.016311252999999998
- quieter: ok=True · getting_quieter=True · score=0.7676
- public eval: ok=True · freshness=True · model=deepseek/deepseek-v4-pro
- commercial: ok=True · overall_est=8.5

Source: [`docs/PILOT.md`](../PILOT.md) · issue template: `.github/ISSUE_TEMPLATE/design-partner.yml`

```bash
python3 scripts/pilot_surface.py fixture
python3 scripts/pilot_surface.py readiness
python3 scripts/torii.py pilot -- status
```

Apply: https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml

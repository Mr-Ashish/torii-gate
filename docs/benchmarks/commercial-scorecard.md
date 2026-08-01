<!-- torii-commercial-scorecard -->

# Commercial product scorecard

_Generated: `2026-08-01T18:21:06Z` · schema **2** · **overall_est=8.5/10** (baseline 6.6) · commercial_ok=`True`_

Single commercial scorecard: golden path · buyer · public eval · install · ops · enterprise · gate cert · quieter · tool-use · workflow · measured cost/PR

Heuristic commercial score from hermetic surface fixtures — not a customer interview score. Cap 8.5 until live revenue proof.

## Trajectory

| Metric | Value |
|--------|------:|
| baseline overall | 6.6 |
| overall_est | **8.5** |
| lift | +1.9 |
| surfaces pass | 10/10 |
| post_queue_complete | True |

## Priority queue surfaces (1–6)

| Surface | Target | Dim | Pass |
|---------|--------|-----|:----:|
| `golden_path` | 7.5 | commercial / simplicity path | yes |
| `buyer_narrative` | 8.0 | simplicity (narrative) | yes |
| `public_eval` | 8.5 | technical trust | yes |
| `install_ux` | install | install UX (dim 7) | yes |
| `ops` | ops | reliability/ops (dim 8) | yes |
| `enterprise` | enterprise | enterprise light (dim 9) | yes |

## Post-queue surfaces (merge authority)

Gate certificate · quieter-over-time · agent tool-use — tools-as-code, not F-stack.

| Surface | Target | Dim | Pass |
|---------|--------|-----|:----:|
| `gate_certificate` | evidence | merge-authority certificate (dim 12) | yes |
| `quieter` | JTBD | own-repo quieter-over-time (dim 3) | yes |
| `tool_use` | tools | agent tool-use quality (dims 3+12) | yes |

## Core product (workflows-as-code)

Deterministic pipeline graph vs LLM prose — validate offline before paid runs.

| Surface | Target | Dim | Pass |
|---------|--------|-----|:----:|
| `workflow` | L3 | workflows-as-code (deterministic pipeline) | yes |

## Cost honesty (measured dogfood)

Measured dogfood cost/PR + time-to-signal (local vault only; not federated)

| Metric | Value |
|--------|------:|
| cost_honesty_ok | True |
| cost_ok (≥5 hermes-usage + p50) | True |
| cost samples | 34 |
| cost/PR p50 (USD) | 0.014 |
| time-to-signal p50 (s) | 93.0 |
| cost dashboard not stub | True |
| privacy: cost local (not federated) | True |
| landing measured dogfood | True |

Audit: [cost-pr-dashboard.md](../ops/cost-pr-dashboard.md) · [golden-path-metrics.md](golden-path-metrics.md) · [enterprise/PRIVACY.md](../enterprise/PRIVACY.md).

## Buyer artifacts

| Artifact | Present |
|----------|:-------:|
| `buyer_diagram` | True |
| `cost_pr_dashboard` | True |
| `enterprise_privacy` | True |
| `federation_md` | True |
| `gate_md` | True |
| `golden_path_md` | True |
| `install_md` | True |
| `landing_html` | True |
| `memory_md` | True |
| `ops_dashboard` | True |
| `pricing_md` | True |
| `public_eval_md` | True |
| `quieter_md` | True |
| `self_evolve_md` | True |
| `tool_use_md` | True |
| `workflow_yaml` | True |
| `workflows_md` | True |

## Refresh

```bash
python3 scripts/commercial_scorecard.py report
python3 scripts/commercial_scorecard.py fixture
python3 scripts/torii.py commercial -- status
python3 scripts/torii.py ops -- status
```

Related: [GOLDEN-PATH](../GOLDEN-PATH.md) · [WORKFLOWS](../WORKFLOWS.md) · [QUIETER](../QUIETER.md) · [TOOL-USE](../TOOL-USE.md) · [GATE](../GATE.md) · [public-eval](public-eval/SCORECARD.md) · [ops](../ops/DASHBOARD.md) · [cost/PR](../ops/cost-pr-dashboard.md) · [enterprise](../enterprise/)

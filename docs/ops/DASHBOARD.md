<!-- torii-ops-dashboard -->

# Torii ops dashboard

_Generated: `2026-08-01T16:27:49Z` · **ops_ok=True** · target **ops / dim 8**_

Fail-closed defaults · measured cost/PR · gate certificate · smoke CI · product surfaces · torii/gate

## Fail-closed defaults

Safe defaults active: **True**

| Env | Default | Effective | What |
|-----|---------|-----------|------|
| `TORII_TOOL_TURNS_GATE` | on | on | Zero-tool multi-file code PRs cannot APPROVE (fail-closed) |
| `TORII_TOOL_TURNS_REPROMPT` | on | on | Soft re-prompt once when tools were skipped (budgeted) |
| `TORII_WEBHOOK_ALLOW_OPEN` | off | off | Modal webhook refuse-open by default (must explicitly allow) |
| `TORII_COMMIT_STATUS` | on | on | Post torii/gate + torii/review commit statuses |
| `TORII_GATE_STRICT` | off | off | Optional hard job fail when gate closed (branch protection uses status) |
| `TORII_PR_LABELS` | on | on | Verdict labels on PRs (visible ops signal) |

## Required check

Context: **`torii/gate`** · docs_ok=**True**

Branch protection must require **`torii/gate`** (see `docs/INSTALL.md`, `docs/GATE.md`).

## Smoke

- Script: `True` · CI workflow: `True`
- Last run in this report: ran=False pass=None

```bash
./scripts/smoke-torii-gate.sh
python3 scripts/ops_dashboard.py report --smoke
```

## Cost / PR (dogfood vault)

| Stat | time-to-signal (s) | cost USD |
|------|-------------------:|---------:|
| n | 59 | 21 |
| mean | 98.936 | 0.018 |
| p50 | 91.7 | 0.013 |
| min | 39.2 | 0.008 |
| max | 262.0 | 0.058 |

Runs: **64** · cost_ok=**True** · source: `docs/benchmarks/traces vault`

Detail: [cost-pr-dashboard.md](cost-pr-dashboard.md) · Reliability one-pager: [RELIABILITY.md](RELIABILITY.md) · Golden path: [golden-path-metrics.md](../benchmarks/golden-path-metrics.md)

## Last gate certificate (merge authority)

Deterministic reason codes + path evidence for the latest dogfood gate decision (not a chat transcript). Soft-wired via `save-trace.sh` + reusable workflow.

**CLOSED — REQUEST_CHANGES (verdict_request_changes, strong_path_evidence, blocking_with_paths); path_evidence=1.00**

| Field | Value |
|-------|------:|
| certificate_id | `gc-c9f317b2365e7643` |
| block | True |
| verdict | REQUEST_CHANGES |
| path_evidence | 1.0 |
| reason_codes | `verdict_request_changes`, `strong_path_evidence`, `blocking_with_paths` |
| vault path | `docs/benchmarks/traces/20260801-1624-pytorch-pytorch-PR191840-modal-landing-cost/gate-certificate.json` |
| wire_ok | True |

```bash
python3 scripts/torii.py certificate -- fixture
python3 scripts/gate_certificate.py emit --review .torii-out/review-1.md --write .torii-out
```

## Product surfaces (day-2 ops map)

Docs + scripts ready: **10/10** · product_surfaces_ok=**True**

Operators should not hunt research logs — each surface has one CLI.

| Surface | Doc | Script | CLI | Ok |
|---------|-----|--------|-----|:--:|
| `install` | `docs/INSTALL.md` | `scripts/install_ux_check.py` | `torii.py doctor` | yes |
| `golden_path` | `docs/GOLDEN-PATH.md` | `scripts/golden_path_metrics.py` | `torii.py golden-path -- status` | yes |
| `certificate` | `docs/GATE.md` | `scripts/gate_certificate.py` | `torii.py certificate -- fixture` | yes |
| `quieter` | `docs/QUIETER.md` | `scripts/quieter_over_time.py` | `torii.py quieter -- status` | yes |
| `tool_use` | `docs/TOOL-USE.md` | `scripts/tool_use_quality.py` | `torii.py tool-use -- status` | yes |
| `workflows` | `docs/WORKFLOWS.md` | `scripts/workflow_as_code.py` | `torii.py workflow -- scorecard` | yes |
| `memory` | `docs/MEMORY.md` | `scripts/torii_memory.py` | `torii.py memory -- doctor` | yes |
| `federation` | `docs/FEDERATION.md` | `scripts/federated_hub_ingest.py` | `torii.py federation -- status` | yes |
| `self_evolve` | `docs/SELF-EVOLVE.md` | `scripts/self_evolve.py` | `torii.py self-evolve -- status` | yes |
| `commercial` | `docs/benchmarks/commercial-scorecard.md` | `scripts/commercial_scorecard.py` | `torii.py commercial -- status` | yes |

Hub map: [README product surfaces](../../README.md#product-surfaces-one-cli) · commercial: `python3 scripts/torii.py commercial -- status`

## Refresh

```bash
python3 scripts/ops_dashboard.py report --smoke
python3 scripts/torii.py ops -- report
python3 scripts/golden_path_metrics.py report
```

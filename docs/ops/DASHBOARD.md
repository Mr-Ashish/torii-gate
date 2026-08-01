<!-- torii-ops-dashboard -->

# Torii ops dashboard

_Generated: `2026-08-01T15:05:15Z` · **ops_ok=True** · target **ops / dim 8**_

Fail-closed defaults · cost/PR · gate certificate · smoke CI · torii/gate

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
| n | 47 | 9 |
| mean | 97.813 | 0.017 |
| p50 | 84.3 | 0.012 |
| min | 39.2 | 0.008 |
| max | 262.0 | 0.058 |

Runs: **52** · source: `docs/benchmarks/traces vault`

Detail: [cost-pr-dashboard.md](cost-pr-dashboard.md) · Reliability one-pager: [RELIABILITY.md](RELIABILITY.md)

## Last gate certificate (merge authority)

Deterministic reason codes + path evidence for the latest dogfood gate decision (not a chat transcript). Soft-wired via `save-trace.sh` + reusable workflow.

**CLOSED — REQUEST_CHANGES (verdict_request_changes, strong_path_evidence, blocking_with_paths); path_evidence=1.00**

| Field | Value |
|-------|------:|
| certificate_id | `gc-95888668ca0a313d` |
| block | True |
| verdict | REQUEST_CHANGES |
| path_evidence | 1.0 |
| reason_codes | `verdict_request_changes`, `strong_path_evidence`, `blocking_with_paths` |
| vault path | `docs/benchmarks/traces/20260801-1502-pytorch-pytorch-PR191840-modal-gate-cert-wire/gate-certificate.json` |
| wire_ok | True |

```bash
python3 scripts/torii.py certificate -- fixture
python3 scripts/gate_certificate.py emit --review .torii-out/review-1.md --write .torii-out
```

## Refresh

```bash
python3 scripts/ops_dashboard.py report --smoke
python3 scripts/torii.py ops -- report
```

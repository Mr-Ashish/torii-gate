<!-- torii-ops-dashboard -->

# Torii ops dashboard

_Generated: `2026-08-01T14:37:05Z` · **ops_ok=True** · target **ops / dim 8**_

Fail-closed defaults · cost/PR dashboard · smoke CI · required check torii/gate

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
| n | 43 | 7 |
| mean | 95.286 | 0.011 |
| p50 | 84.3 | 0.012 |
| min | 40.7 | 0.008 |
| max | 208.6 | 0.016 |

Runs: **48** · source: `docs/benchmarks/traces vault`

Detail: [cost-pr-dashboard.md](cost-pr-dashboard.md) · Reliability one-pager: [RELIABILITY.md](RELIABILITY.md)

## Refresh

```bash
python3 scripts/ops_dashboard.py report --smoke
python3 scripts/torii.py ops -- report
```

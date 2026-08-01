# Torii reliability & ops (one-pager)

**Dim 8 lift:** fail-closed defaults · cost/PR visibility · smoke CI · required check.

## Fail-closed (defaults)

| Control | Default | Effect |
|---------|---------|--------|
| Tool-turns gate | **on** | Multi-file code PRs with 0 tool turns cannot APPROVE |
| Tool-turns re-prompt | **on** | One budgeted soft re-prompt when tools were skipped |
| Modal webhook open | **off** | Refuse unauthenticated open webhook unless explicitly allowed |
| Commit statuses | **on** | Posts `torii/gate` + `torii/review` |
| `TORII_GATE_STRICT` | off | Optional hard job fail; branch protection uses **status** |

## Required check

Branch protection → require **`torii/gate`**. See `docs/INSTALL.md` and `docs/GATE.md`.

## Smoke CI

```bash
./scripts/smoke-torii-gate.sh
# CI: .github/workflows/smoke-offline.yml on push/PR to main
```

## Cost / PR

```bash
python3 scripts/ops_dashboard.py report --smoke
# → docs/ops/DASHBOARD.md · docs/ops/cost-pr-dashboard.md
```

Day-2: `python3 scripts/torii.py doctor` · `python3 scripts/torii.py ops -- status` · product map on `docs/ops/DASHBOARD.md`

## Links

| Doc | Role |
|-----|------|
| [DASHBOARD.md](DASHBOARD.md) | Live ops snapshot |
| [cost-pr-dashboard.md](cost-pr-dashboard.md) | Cost / time-to-signal stub |
| [../GATE.md](../GATE.md) | Gate contract |
| [../INSTALL.md](../INSTALL.md) | 5-minute install |
| [../OPERATIONS.md](../OPERATIONS.md) | Full ops runbook |

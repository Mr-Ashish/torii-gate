<!-- torii-enterprise-surface -->

# Enterprise surface inventory

_Generated: `2026-08-01T17:43:57Z` · **enterprise_ok=True**_

Org isolation + federation privacy as product docs and audit CLI — themes only, no paths/snippets/raw tenant IDs

## Guarantees

- no cross-tenant path inject via federation
- tenant hashes only in global aggregates
- promote requires min_tenants (default 2)
- repo-local .torii/ default; hub opt-in
- cost/PR dogfood vault stays local (never federated USD/tokens)

## Tenants (`memory/tenants/`) — n=6

| tenant_id | federation dir | files |
|-----------|:--------------:|------:|
| `demo-tenant` | True | 1 |
| `e2e-f155` | True | 1 |
| `e2e-pytorch` | True | 1 |
| `fixture-tenant-a` | True | 1 |
| `t-f155` | True | 1 |
| `tenant-z` | True | 1 |

## Federation privacy audit — 15/15 ok

| file | privacy_ok | issues |
|------|:----------:|--------|
| `federated-signals.json` | True | — |
| `hub-archival-util-signals.json` | True | — |
| `memory-util-signals.json` | True | — |
| `promoted-refine-dual-decay-themes.json` | True | — |
| `promoted-refine-dual-revive-themes.json` | True | — |
| `promoted-refine-dual-themes.json` | True | — |
| `recon-warm-signals.json` | True | — |
| `recovery-util-signals.json` | True | — |
| `scorecard-skill-signals.json` | True | — |
| `scorecard-util-signals.json` | True | — |
| `skill-fitness-signals.json` | True | — |
| `skill-refine-dual-decay-signals.json` | True | — |
| `skill-refine-dual-revive-signals.json` | True | — |
| `skill-refine-dual-signals.json` | True | — |
| `skill-refine-signals.json` | None | — |

## Docs

- [ORG-ISOLATION.md](ORG-ISOLATION.md) — org isolation story
- [PRIVACY.md](PRIVACY.md) — federation privacy one-pager + **cost/PR telemetry local**
- [../FEDERATION.md](../FEDERATION.md) — buyer JTBD (merge-authority federation)
- [../ops/cost-pr-dashboard.md](../ops/cost-pr-dashboard.md) — measured cost (not federated)

Cost telemetry documented as local vault only: **True**

## Refresh

```bash
python3 scripts/enterprise_surface.py report
python3 scripts/enterprise_surface.py fixture
```

# Pattern: enterprise light — isolation story + privacy one-pager

## Source
- Multi-tenant RAG isolation: never inject another tenant’s paths/snippets.
- IETF-style federated privacy: aggregate without raw tenant payloads.
- Scorecard dim **enterprise (4.5)** — tech exists as JSON; buyers need a product surface.

## Steal for Torii
1. `docs/enterprise/ORG-ISOLATION.md` — org diagram and guarantees.
2. `docs/enterprise/PRIVACY.md` — allowlist / denylist one-pager.
3. `enterprise_surface.py` audits `memory/federation/*.json` for home paths and `privacy_ok`.
4. CLI `torii.py enterprise` + hermetic fixture for CI.

## Anti-pattern
Shipping federated-signals JSON with `privacy_ok` while the only “enterprise docs” are F-number paragraphs in PRODUCT Advanced.

# F107 research note — Federate integrity-gated compound TPs

**Date:** 2026-08-01  
**Fire:** F107

## Sources

1. F77 hub federated ingest (privacy-safe theme/CWE/keywords/basenames).
2. F104 integrity-gated compound write (path evidence only).
3. F95 consolidate → federate effective scores (all durable TP).
4. IETF multi-tenant agent FL privacy: aggregate without raw tenant data.

## Gap

F104 grew local `tp-signatures` but multi-tenant hub only saw TPs after F94 consolidate (F95). Fresh integrity-gated findings from a review were not immediately shareable with provenance tags.

## Pattern

| Step | Rule |
|------|------|
| export | candidates with integrity=ok only |
| fields | theme, cwe, keywords, path_basenames, hits, tags |
| never | snippets, `/Users`, secrets, raw tenant name |
| ingest | F77 sanitize → tenant_hash + min-tenant promote later |

## Success

- fixture: fed_count≥1, privacy_ok, tags integrity_gated, basenames only
- compound `--federate` soft stage in run-torii-review

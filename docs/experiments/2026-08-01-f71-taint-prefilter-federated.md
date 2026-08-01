# F71 — Deterministic taint prefilter + federated sanitized signals

## Why

Papers (SemTaint, SAST-Genius) and OSS harnesses (deepsec) agree: **static-led
candidates before LLM reasoning** beat free-form agent hunts on cost and
precision. Torii had F70 local TP memory but no tools-as-code source/sink stage
and no privacy-safe cross-org aggregate.

## What shipped

| Piece | Path |
|-------|------|
| Prefilter + federate CLI | `scripts/taint_prefilter.py` |
| Tests | `tests/test_taint_prefilter.py` |
| Assemble wire | `scripts/assemble-context.sh` (F71 block) |
| Toggles | `TORII_TAINT_PREFILTER`, `TORII_FEDERATED_SIGNALS` |
| Adopted tool | `agent/tools/adopted/taint-prefilter.json` |

## Privacy contract (federation)

Exported signals may contain only:

- `theme`, `cwe`, abstract `keywords`, `path_basenames` (single segment)
- aggregate `hits` / `tenants`
- optional `tenant_hash` (SHA-256 prefix) — never raw tenant id

Never: absolute paths, `owner--repo` trees, code snippets, secrets.

## Metrics

- Offline: `python3 scripts/taint_prefilter.py fixture` → fixture_pass, recall=1.0
- Live: `python3 scripts/bench_security_gate.py live` → tp=4 recall=1.0

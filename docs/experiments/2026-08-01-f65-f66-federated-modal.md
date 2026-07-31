# F65 + F66 — Federated multi-tenant hub memory + Modal prod e2e defaults

**Date:** 2026-08-01  
**Status:** shipping  
**Tag:** PRODUCT_FEATURE | MEMORY | OPS | MODAL

## F65 — Multi-tenant federated hub memory

### Problem

Hub memory is a single flat tree `memory/repos/{slug}/`. Multiple orgs or
deployments sharing one hub risk cross-contaminating MEMORY / FP rules. F64
local self-learn stays per-repo; federation needed a **namespace** without
rewriting the single-tenant path.

### Fix

1. **`TORII_MEMORY_TENANT`** (optional string). Empty = classic
   `memory/repos/{slug}/` (back-compat).
2. When set (sanitized alnum/`._-`):
   `memory/tenants/{tenant}/repos/{slug}/` for MEMORY, runs, fp-rules, index.
3. **Ingest** (`hub-ingest-run.py`): tenant from env or payload `tenant`.
4. **Preload** (`preload-hub-memory.sh`): hub path respects tenant; also
   preloads hub `fp-rules.json` from the same tree.
5. **Payload** (`build-hub-payload.py`): embeds `tenant` for round-trip.
6. **Index** schema_version=2 lists both classic and tenant entries.

Judgment unchanged — pure storage layout.

## F66 — Modal as default prod live e2e host

### Problem

Modal worked for cheap e2e (bit 3) but did not explicitly set product defaults
shipped in F54–F64 (`TORII_LENS_PACK=auto`, tenant, hub knobs). Docs still
framed GHA as primary kitchen.

### Fix

1. Modal `review_pr` env: **`TORII_LENS_PACK=auto`**, lens packs on, F65
   tenant + hub repo pass-through from Modal secrets/env.
2. Version stamp **`0.7.0-f66`**.
3. Docs: Modal is the default **prod live e2e** path; GHA remains doorbell
   for installed targets.

## Tests

```bash
pytest tests/test_hub_ingest.py -q
```

## Verify

```bash
# F65 tenant ingest
TORII_MEMORY_TENANT=demo HUB_ROOT=/tmp/hub CLIENT_PAYLOAD='{"run":{...}}' \
  python3 scripts/hub-ingest-run.py
# → /tmp/hub/memory/tenants/demo/repos/…

# F66 Modal
./scripts/trigger-review.sh modal Mr-Ashish/milvus 1 --cheap --post
# result.version == 0.7.0-f66
```

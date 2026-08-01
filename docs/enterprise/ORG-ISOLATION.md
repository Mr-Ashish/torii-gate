# Org isolation story (multi-tenant product surface)

**One sentence:** Each customer org is a **tenant** with private memory on disk; the hub only learns **privacy-safe themes** that already passed a multi-tenant promote gate.

## What an “org” is in Torii v1

| Layer | What | Isolation |
|-------|------|-----------|
| **GitHub org / repo** | Where the required check `torii/gate` runs | Repo secrets, labels, branch protection stay in that org |
| **Tenant id** | Optional `TORII_MEMORY_TENANT` or `./scripts/install-torii.sh --tenant <id>` (stamp + `.torii/tenant.env`) | Sanitized id → `memory/tenants/<tenant>/` tree when hub mode is on |
| **Repo-local memory** | `.torii/` on the target default branch | Never copied to another customer’s tree |
| **Hub federation** | `memory/federation/*.json` on the hub | Themes + CWE + basenames + **tenant hashes** only |

```text
  Org A repo                    Org B repo
  ┌─────────────┐               ┌─────────────┐
  │ .torii/     │               │ .torii/     │  private FP/TP, paths, snippets
  │ runs/       │               │ runs/       │
  └──────┬──────┘               └──────┬──────┘
         │ privacy-safe export         │
         │ (theme/CWE/keywords/        │
         │  basenames + tenant hash)   │
         └───────────┬─────────────────┘
                     ▼
              Hub federation
         promote only if ≥ N tenants
         (default min_tenants=2)
```

## Guarantees (product contract)

1. **No cross-tenant path inject** — Org B’s review prompt never receives Org A’s file paths or code snippets from federation.  
2. **No raw tenant names in global aggregate fields** — hub stores **hashes** of tenant ids for counting, not `acme-corp`.  
3. **Promote gate** — single-tenant noise/poison does not become multi-tenant “truth” until enough independent tenants share the theme.  
4. **Repo-local remains default** — day-one install uses `.torii/` only; hub publish is opt-in (`TORII_MEMORY_MODE` / `TORII_HUB_PUBLISH`).  
5. **Fail-closed reviews still apply** — zero-tool APPROVE is blocked regardless of tenant (see `docs/ops/RELIABILITY.md`).  
6. **Cost / PR telemetry stays local** — hermes-usage USD estimates and dogfood vault rows never enter federation (see [PRIVACY.md](PRIVACY.md) · Cost / PR telemetry).

## Operator model

| Role | Day-one | Multi-org fleet |
|------|---------|-----------------|
| **Platform** | Install pack; require `torii/gate` | Optional hub + tenant id per org |
| **AppSec** | Read PR comments + labels | Federation themes only for shared patterns |
| **Compliance** | Read [PRIVACY.md](PRIVACY.md) | Audit `privacy_ok` on federation files |

## Hermetic isolation proof

`enterprise_surface.py fixture` builds a **temp dual-tenant tree**:

1. Tenant A gets a canary **absolute path** + **secret snippet** in `tp-signatures.json`.  
2. Tenant B runs scoped memory ingest + inject with `TORII_MEMORY_TENANT=tenant-iso-b`.  
3. **Pass only if** A’s path/snippet/raw tenant id never appear in B’s inject.  
4. Federation `sanitize_signal` must strip path/snippet and hash the tenant id.

```bash
python3 scripts/enterprise_surface.py fixture   # isolation_proof_ok must be true
python3 scripts/enterprise_surface.py status    # isolation_ok
```

## Commands

```bash
# List tenant trees + federation privacy posture
python3 scripts/enterprise_surface.py status

# Hermetic privacy audit + cross-tenant inject proof (no secrets in output)
python3 scripts/enterprise_surface.py fixture

# Two-tenant federate fixture (engine)
python3 scripts/federated_hub_ingest.py fixture
```

## What this is not (v1)

- Not a full multi-tenant SaaS control plane  
- Not row-level DB tenancy for a hosted product  
- Not “zero data leaves the repo” if you **opt in** to hub publish — but export is scrubbed  

See [PRIVACY.md](PRIVACY.md) for the exact field allowlist.

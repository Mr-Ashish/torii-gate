# Torii central memory

This directory is the **hub** for review memory across every target repository that runs Torii.

## Layout

```text
memory/
  repos/
    {owner}--{repo}/
      MEMORY.md                 # cumulative learned notes for that repo
      runs/
        {trace_id}/
          meta.json             # run identity + hashes
          review.md             # Torii Gate review body (may be truncated)
          summary.md            # short distill block
```

## How it gets updated

1. A **target repo** finishes a Torii Gate review and builds a redacted payload from the run trace.
2. It fires `repository_dispatch` (`torii-run`) on **this** repo using `TORII_HUB_TOKEN` (or `GITHUB_TOKEN` when Torii is reviewing itself).
3. Workflow **Ingest Torii Run** (`.github/workflows/ingest-torii-run.yml`) commits updates under `memory/repos/…`.

## Secrets (target repos)

| Secret | Purpose |
|--------|---------|
| `TORII_HUB_TOKEN` | PAT or fine-grained token with `contents: write` + ability to create `repository_dispatch` on `Mr-Ashish/torii-gate` |

Optional vars:

| Variable | Default | Purpose |
|----------|---------|---------|
| `TORII_HUB_REPO` | `Mr-Ashish/torii-gate` | Hub repository |

## Federated hub signals (F77)

Privacy-safe cross-tenant themes live under:

```text
memory/federation/federated-signals.json   # global aggregate
memory/federation/promoted-signals.json    # min_tenants / min_hits gate
memory/tenants/{tenant}/federation/        # tenant-local copy
```

Only theme / CWE / keywords / basenames / tenant_hash — never raw paths or snippets.

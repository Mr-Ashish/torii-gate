# F80 research note — Modal secrets bootstrap

**Date:** 2026-08-01  
**Fire:** F80

## Problem

Every live Modal e2e failed with `Secret 'torii-openrouter' not found` while the workspace already had `luffy-*` secrets and a local `.env`. Live Modal + Hermes log streaming (F67) was unreachable.

## Pattern

1. **Bootstrap CLI** creates filtered dotenv payloads (key-names only in logs).
2. **`modal secret create --from-dotenv --force`** for `torii-openrouter` / `torii-github`.
3. **Configurable names** via `TORII_MODAL_OPENROUTER_SECRET` / `TORII_MODAL_GITHUB_SECRET`.
4. Trigger path soft-applies secrets before `modal run`.

## Success metric

- fixture_pass; status ready after apply; Modal bit3 reaches Hermes stream

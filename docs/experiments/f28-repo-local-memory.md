# F28 — Repo-local `.torii/` memory

- Target repo owns MEMORY + slim runs under `.torii/`.
- Default `TORII_MEMORY_MODE=local`; hub only when `both|hub` or `TORII_HUB_PUBLISH=1`.
- Preload: local API contents first, hub fallback if opted in.
- Fat traces stay Actions artifacts.

# Insecure dogfood app

**DO NOT deploy.** Intentional vulnerabilities for Torii Gate demos and offline smoke.

| Route | Issue |
|-------|--------|
| `GET /search?q=` | SQL injection (`f-string` into `execute`) |
| `POST /load` | Unsafe `pickle.loads` on request body |
| `GET /run?cmd=` | Command injection (`shell=True`) |
| `GET /secret` | Secrets exposure (`OPENROUTER_API_KEY`) |

## How to use

1. Open a PR that adds or touches `demo/insecure/app.py`.
2. Comment `@torii review this pr` (security pack is default).
3. Expect **REQUEST CHANGES** / closed `torii/gate` when findings are path-evidenced.

Offline (no model, no PR):

```bash
./scripts/smoke-torii-gate.sh
```

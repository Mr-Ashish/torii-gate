# Fire — F33 webhook auth (2026-07-31)

## Problem

Modal `review_webhook` was an open spend URL once deployed (documented pitfall).

## Ship

- `scripts/webhook_auth.py` — pure HMAC + bearer authorize/sign CLI
- `review_webhook` reads raw body + headers, authorizes before parse/spawn
- Env: `TORII_WEBHOOK_SECRET`, `TORII_WEBHOOK_TOKEN` (open+warn if unset)
- Bit 4 dry plan self-checks auth; tests offline

## Verify

```bash
pytest tests/test_webhook_auth.py -q
modal run modal_app/app.py --bit 4 --repo Mr-Ashish/odoo --pr 3   # BIT4_OK includes auth_*_ok
```

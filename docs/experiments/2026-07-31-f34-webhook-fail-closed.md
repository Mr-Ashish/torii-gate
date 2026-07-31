# Fire — F34 webhook fail-closed (2026-07-31)

## Problem

F33 left `auth=open` when no secret/token — a deployed URL could still burn
OpenRouter if env was forgotten.

## Ship

- Default deny when neither SECRET nor TOKEN is set
- Escape hatch: `TORII_WEBHOOK_ALLOW_OPEN=1` / `allow_open=True` / CLI `--allow-open`
- Bit 4 dry plan asserts `auth_fail_closed_ok`
- Tests updated

## Verify

```bash
pytest tests/test_webhook_auth.py -q
modal run modal_app/app.py --bit 4 --repo Mr-Ashish/odoo --pr 3
```

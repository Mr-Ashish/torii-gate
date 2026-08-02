# HUB_REQUIRE_GATE_LIVE — Modal BIT3 dogfood

| Field | Value |
|-------|------:|
| fire | HUB_REQUIRE_GATE_LIVE |
| repo | pytorch/pytorch |
| pr | 191859 |
| model | deepseek/deepseek-v4-pro |
| POST_COMMENT | 0 |
| bit | 3 |
| result | **BIT3_OK** |
| verdict | **REQUEST_CHANGES** (test-gap calibration) |
| tool_call_turns | 9 |
| elapsed_s | 816.2 |
| modal app | ap-V523fSWpT1jO7coLVwOGXq |
| hermes | yes (Modal UI stream) |

Product: hub main requires torii/gate (live_ok=true) · require-check --enable for partners.

```bash
python3 scripts/torii.py quieter -- require-check
python3 scripts/torii.py quieter -- require-check -- --enable --yes
```

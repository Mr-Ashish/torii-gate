# REQUIRE_CHECK_LIVE — Modal BIT3 dogfood

| Field | Value |
|-------|------:|
| fire | REQUIRE_CHECK_LIVE |
| repo | pytorch/pytorch |
| pr | 191859 |
| model | deepseek/deepseek-v4-pro |
| POST_COMMENT | 0 |
| bit | 3 |
| result | **BIT3_OK** |
| verdict | **REQUEST_CHANGES** (test-gap calibration) |
| tool_call_turns | 16 |
| elapsed_s | 688.1 |
| modal app | ap-xvTjLAi5i6QsFqZf8rLO8C |
| hermes | yes (Modal UI stream) |

Product: `quieter -- require-check` live GitHub required-status probe; merge `require_check=off|live`.

```bash
python3 scripts/torii.py quieter -- require-check
python3 scripts/torii.py status --text
```

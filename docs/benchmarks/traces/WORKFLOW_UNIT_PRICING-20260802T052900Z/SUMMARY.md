# WORKFLOW_UNIT_PRICING — Modal BIT3 dogfood

| Field | Value |
|-------|------:|
| fire | WORKFLOW_UNIT_PRICING |
| repo | pytorch/pytorch |
| pr | 191854 |
| model | deepseek/deepseek-v4-pro |
| POST_COMMENT | 0 |
| bit | 3 |
| result | **BIT3_OK** |
| verdict | **REQUEST_CHANGES** (test-gap calibration) |
| tool_call_turns | 10 |
| elapsed_s | 868.8 |
| modal app | ap-nbii2ga0Kyslkl3erFiY73 |
| hermes | yes (Modal UI stream) |

Product: growth `workflow=L3 stages=20 triple_ready` · `unit=$0.014/PR` · week1 12/12.

```bash
python3 scripts/torii.py status --text
python3 scripts/torii.py workflow -- validate
```

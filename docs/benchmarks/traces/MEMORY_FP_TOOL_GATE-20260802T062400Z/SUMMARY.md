# MEMORY_FP_TOOL_GATE — Modal BIT3 dogfood

| Field | Value |
|-------|------:|
| fire | MEMORY_FP_TOOL_GATE |
| repo | pytorch/pytorch |
| pr | 191857 |
| model | deepseek/deepseek-v4-pro |
| POST_COMMENT | 0 |
| bit | 3 |
| result | **BIT3_OK** |
| verdict | **REQUEST_CHANGES** (test-gap calibration) |
| tool_call_turns | 5 |
| elapsed_s | 781.9 |
| modal app | ap-Q7plD0MmdH9vWz4cGxw7vm |
| hermes | yes (Modal UI stream) |

Product: install-demo FP rules (fp=2) · tool_gate=on on day-2.

```bash
python3 scripts/torii.py memory -- compound -- bootstrap-demo
python3 scripts/torii.py status --text
```

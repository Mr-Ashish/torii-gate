<!-- torii-gate-certificate -->

# Torii gate certificate

_id `gc-bbbbbb72db7f8678` · `2026-08-01T17:23:24Z`_

**CLOSED — REQUEST_CHANGES (verdict_request_changes, strong_path_evidence, blocking_with_paths); path_evidence=0.75**

| Field | Value |
|-------|------:|
| context | `torii/gate` |
| state | failure |
| block | True |
| verdict | REQUEST_CHANGES |
| path_evidence | 0.75 (n=1) |
| content_sha | `bbbbbb72db7f8678` |

## Reason codes (deterministic)

- `verdict_request_changes`
- `strong_path_evidence`
- `blocking_with_paths`

## Path cites

- `demo/insecure/app.py`

## Reproduce

```bash
python3 scripts/gate_certificate.py emit --review insecure-demo-good-review.md
python3 scripts/torii.py certificate -- fixture
```


<!-- torii-gate-certificate -->

# Torii gate certificate

_id `gc-3f3b2e2951a12451` · `2026-08-01T14:57:39Z`_

**CLOSED — REQUEST_CHANGES (verdict_request_changes, strong_path_evidence, blocking_with_paths); path_evidence=1.00**

| Field | Value |
|-------|------:|
| context | `torii/gate` |
| state | failure |
| block | True |
| verdict | REQUEST_CHANGES |
| path_evidence | 1.0 (n=8) |
| content_sha | `3f3b2e2951a12451` |

## Reason codes (deterministic)

- `verdict_request_changes`
- `strong_path_evidence`
- `blocking_with_paths`

## Path cites

- `c10/metal/utils.h`
- `test_mps.py`
- `common_mps.py`
- `linalg.py`
- `torch/testing/_internal/common_mps.py`
- `torch/testing/_internal/opinfo/definitions/linalg.py`
- `utils.h`
- `test/test_mps.py`

## Reproduce

```bash
python3 scripts/gate_certificate.py emit --review review.md
python3 scripts/torii.py certificate -- fixture
```


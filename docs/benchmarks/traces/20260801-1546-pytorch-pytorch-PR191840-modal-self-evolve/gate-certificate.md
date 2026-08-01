<!-- torii-gate-certificate -->

# Torii gate certificate

_id `gc-82065e74ed27795d` · `2026-08-01T15:48:45Z`_

**CLOSED — REQUEST_CHANGES (verdict_request_changes, strong_path_evidence, blocking_with_paths); path_evidence=1.00**

| Field | Value |
|-------|------:|
| context | `torii/gate` |
| state | failure |
| block | True |
| verdict | REQUEST_CHANGES |
| path_evidence | 1.0 (n=4) |
| content_sha | `82065e74ed27795d` |

## Reason codes (deterministic)

- `verdict_request_changes`
- `strong_path_evidence`
- `blocking_with_paths`

## Path cites

- `torch/package/analyze/trace_dependencies.py`
- `test/package/test_analyze.py`
- `test_analyze.py`
- `trace_dependencies.py`

## Reproduce

```bash
python3 scripts/gate_certificate.py emit --review review.md
python3 scripts/torii.py certificate -- fixture
```


<!-- torii-gate-certificate -->

# Torii gate certificate

_id `gc-95888668ca0a313d` · `2026-08-01T15:05:15Z`_

**CLOSED — REQUEST_CHANGES (verdict_request_changes, strong_path_evidence, blocking_with_paths); path_evidence=1.00**

| Field | Value |
|-------|------:|
| context | `torii/gate` |
| state | failure |
| block | True |
| verdict | REQUEST_CHANGES |
| path_evidence | 1.0 (n=6) |
| content_sha | `95888668ca0a313d` |

## Reason codes (deterministic)

- `verdict_request_changes`
- `strong_path_evidence`
- `blocking_with_paths`

## Path cites

- `torch/package/analyze/trace_dependencies.py`
- `test/package/test_analyze.py`
- `test_analyze.py`
- `trace_dependencies.py`
- `torch/utils/viz/_cycles.py`
- `torch/package/analyze/__init__.py`

## Reproduce

```bash
python3 scripts/gate_certificate.py emit --review review.md
python3 scripts/torii.py certificate -- fixture
```


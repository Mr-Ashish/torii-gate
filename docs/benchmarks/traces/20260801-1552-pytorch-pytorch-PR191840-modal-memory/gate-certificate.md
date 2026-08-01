<!-- torii-gate-certificate -->

# Torii gate certificate

_id `gc-1bf7e01455b0a74d` · `2026-08-01T15:54:42Z`_

**OPEN — APPROVE (verdict_approve_open, strong_path_evidence, blocking_with_paths); path_evidence=1.00**

| Field | Value |
|-------|------:|
| context | `torii/gate` |
| state | success |
| block | False |
| verdict | APPROVE |
| path_evidence | 1.0 (n=4) |
| content_sha | `1bf7e01455b0a74d` |

## Reason codes (deterministic)

- `verdict_approve_open`
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


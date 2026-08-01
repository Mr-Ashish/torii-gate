<!-- torii-gate-certificate -->

# Torii gate certificate

_id `gc-620fd969d4470e58` · `2026-08-01T17:49:50Z`_

**OPEN — APPROVE (verdict_approve_open, low_path_evidence, blocking_with_paths); path_evidence=0.30**

| Field | Value |
|-------|------:|
| context | `torii/gate` |
| state | success |
| block | False |
| verdict | APPROVE |
| path_evidence | 0.3 (n=1) |
| content_sha | `620fd969d4470e58` |

## Reason codes (deterministic)

- `verdict_approve_open`
- `low_path_evidence`
- `blocking_with_paths`
- `critic_demoted_maker`
- `critic:path_evidence_below_0_4_0_3`
- `critic:recon_warm_hub_heat_idle_1_0_0_34_recon_warm_hub`

## Path cites

- `app.py`

## Critic demote

- maker → recommended: **APPROVE** → **COMMENT**
- path_evidence_below_0.4 (0.3)
- recon_warm_hub_heat_idle (1.0>=0.34;recon_warm_hub_high_local_idle:no_archival_search_artifact)

## Reproduce

```bash
python3 scripts/gate_certificate.py emit --review insecure-demo-weak-review.md
python3 scripts/torii.py certificate -- fixture
```


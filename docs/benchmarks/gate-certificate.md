<!-- torii-gate-certificate -->

# Gate certificate surface

_Generated: `2026-08-01T14:50:55Z` · **fixture_pass=True** · target **evidence / dim 12**_

Deterministic merge-authority certificate: reason codes + path evidence, not chat.

## Hermetic checks

| Check | Pass |
|-------|:----:|
| `good_blocks` | yes |
| `good_request_changes` | yes |
| `good_strong_or_partial_path` | yes |
| `good_has_reason_codes` | yes |
| `good_has_cert_id` | yes |
| `weak_opens` | yes |
| `weak_low_path` | yes |
| `weak_critic_attached` | yes |
| `weak_critic_demoted_code` | yes |
| `wrote_sample_certs` | yes |
| `gate_md_mentions_certificate` | yes |

## Sample certificates

| Review | block | verdict | path_score | cert id |
|--------|:-----:|---------|----------:|---------|
| insecure-demo good | True | REQUEST_CHANGES | 0.75 | `gc-bbbbbb72db7f8678` |
| insecure-demo weak | False | APPROVE | 0.3 | `gc-620fd969d4470e58` |

Fixtures: `docs/benchmarks/fixtures/gate-certificate-{good,weak}/`.

## Buyer use

```bash
python3 scripts/gate_certificate.py emit --review .torii-out/review-1.md --write .torii-out
python3 scripts/torii.py certificate -- fixture
python3 scripts/torii.py certificate -- report
```

Branch protection still requires **`torii/gate`**. The certificate explains *why* without opening the chat log.

Related: [GATE.md](../GATE.md) · [GOLDEN-PATH.md](../GOLDEN-PATH.md)

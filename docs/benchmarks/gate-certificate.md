<!-- torii-gate-certificate -->

# Gate certificate surface

_Generated: `2026-08-01T17:23:22Z` · schema **2** · **fixture_pass=True** · target **evidence / dim 12**_

Deterministic merge-authority certificate: reason codes + path evidence, not chat — dogfood vault pairs cert × cost on one surface.

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
| `gate_md_cert_cost_pair` | yes |
| `vault_scan_callable` | yes |
| `vault_has_cost_pairs` | yes |

## Sample certificates

| Review | block | verdict | path_score | cert id |
|--------|:-----:|---------|----------:|---------|
| insecure-demo good | True | REQUEST_CHANGES | 0.75 | `gc-bbbbbb72db7f8678` |
| insecure-demo weak | False | APPROVE | 0.3 | `gc-620fd969d4470e58` |

Fixtures: `docs/benchmarks/fixtures/gate-certificate-{good,weak}/`.

## Dogfood vault (cert × cost)

Live Modal/local dogfood rows that already minted a gate certificate. **Local vault only** — cost never federates ([enterprise/PRIVACY.md](../enterprise/PRIVACY.md)).

| Metric | Value |
|--------|------:|
| certificates in vault | 23 |
| with cost (hermes-usage) | 23 |
| cost/PR p50 (USD) | 0.0183 |
| privacy | local vault only |

| trace | pr | verdict | block | path | t_s | cost_usd | certificate | reason codes (head) |
|-------|---:|---------|:-----:|-----:|----:|---------:|-------------|---------------------|
| `20260801-1719-pytorch-pytorch-PR191840-modal-cer` | 191840 | APPROVE | False | 1.0 | 130 | 0.0131 | `gc-5010f8293ba0375a` | `verdict_approve_open`, `strong_path_evidence`, `blocking_with_paths` |
| `20260801-1712-pytorch-pytorch-PR191840-modal-gat` | 191840 | APPROVE | False | 1.0 | 68 | 0.0112 | `gc-e9a820f99efec661` | `verdict_approve_open`, `strong_path_evidence`, `blocking_with_paths` |
| `20260801-1706-pytorch-pytorch-PR191840-modal-day` | 191840 | APPROVE | False | 1.0 | 89 | 0.0185 | `gc-58da0b7175c81ccd` | `verdict_approve_open`, `strong_path_evidence`, `blocking_with_paths` |
| `20260801-1700-pytorch-pytorch-PR191840-modal-ins` | 191840 | REQUEST_CHANGES | True | 1.0 | 93 | 0.0132 | `gc-e7fe92916d5c3e59` | `verdict_request_changes`, `strong_path_evidence`, `blocking_with_paths` |
| `20260801-1654-pytorch-pytorch-PR191840-modal-bra` | 191840 | REQUEST_CHANGES | True | 1.0 | 97 | 0.0249 | `gc-332eb8180a333c36` | `verdict_request_changes`, `strong_path_evidence`, `blocking_with_paths` |
| `20260801-1649-pytorch-pytorch-PR191840-modal-com` | 191840 | APPROVE | False | 1.0 | 93 | 0.0156 | `gc-23ee89e53f33b7d9` | `verdict_approve_open`, `strong_path_evidence`, `blocking_with_paths` |
| `20260801-1642-pytorch-pytorch-PR191840-modal-ent` | 191840 | APPROVE | False | 1.0 | 97 | 0.0218 | `gc-7d4a3cd3ec21d7e6` | `verdict_approve_open`, `strong_path_evidence`, `blocking_with_paths` |
| `20260801-1636-pytorch-pytorch-PR191840-modal-rea` | 191840 | APPROVE | False | 1.0 | 112 | 0.0173 | `gc-c44356ac39c273bc` | `verdict_approve_open`, `strong_path_evidence`, `blocking_with_paths` |
| `20260801-1630-pytorch-pytorch-PR191840-modal-pro` | 191840 | APPROVE | False | 1.0 | 122 | 0.0196 | `gc-c1d8088ce9649d7a` | `verdict_approve_open`, `strong_path_evidence`, `blocking_with_paths` |
| `20260801-1624-pytorch-pytorch-PR191840-modal-lan` | 191840 | REQUEST_CHANGES | True | 1.0 | 117 | 0.0238 | `gc-c9f317b2365e7643` | `verdict_request_changes`, `strong_path_evidence`, `blocking_with_paths` |

Ops rollup (same vault): [ops/cost-pr-dashboard.md](../ops/cost-pr-dashboard.md) · `python3 scripts/torii.py ops -- status`

## Buyer use

```bash
python3 scripts/gate_certificate.py emit --review .torii-out/review-1.md --write .torii-out
python3 scripts/torii.py certificate -- fixture
python3 scripts/torii.py certificate -- report
python3 scripts/torii.py ops -- status   # cost × cert recent table
```

Branch protection still requires **`torii/gate`**. The certificate explains *why* without opening the chat log; vault pairs that id with measured spend.

Related: [GATE.md](../GATE.md) · [GOLDEN-PATH.md](../GOLDEN-PATH.md) · [cost/PR](../ops/cost-pr-dashboard.md)

# F75 research note — Mem0 multi-scope recall over TP/FP

**Date:** 2026-08-01  
**Fire:** F75  
**Memory OSS:** `oss-memory-mem0` (Apache-2.0) — patterns only, no vendored runtime

## Sources

1. **Mem0** (arXiv 2504.19413, Apache-2.0): multi-scope API (`user_id` / `agent_id` / `run_id` / `app_id`); selective retrieval; conflict detection on write.
2. **Memory security** (arXiv 2604.16548 mnemonic sovereignty; longitudinal safety 2026): segment memory, provenance labels, resist cross-scope poisoning.
3. **Torii prior:** F64 fp-rules, F70 tp-signatures, F71 federated (path-free), F65 tenant — inject was unscoped dump.

## Pattern ported (not copied code)

| Mem0 idea | Torii F75 |
|-----------|-----------|
| user/agent/run scopes | run > repo > tenant > agent > global |
| selective retrieval | path_match + scope rank + hits budget |
| conflict detection | path-anchored FP vs theme TP policy |
| token efficiency | TORII_SCOPED_TP_MAX / FP_MAX; optional replace F70 bulk |

## Privacy

- Federated scope never carries absolute paths (`/Users/` stripped).
- Tenant isolation via `TORII_MEMORY_TENANT` path namespace.
- No vector DB dependency.

## Success metric

- Offline: path-relevant TP ranks above high-hit wrong-path; FP conflict; inject marker; privacy_ok
- Live: SCOPED_MEMORY=1 in meta; recall JSON in out_dir

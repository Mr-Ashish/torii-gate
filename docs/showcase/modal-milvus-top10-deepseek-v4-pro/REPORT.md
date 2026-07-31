# Modal e2e — top-10 milvus complex PRs · DeepSeek V4 Pro

**Model:** `deepseek/deepseek-v4-pro` (OpenRouter) · Hermes agent · Modal `0.8.0-f67`  
**Host:** Modal bit-3 · F67 log streaming  
**Corpus:** [Mr-Ashish/milvus](https://github.com/Mr-Ashish/milvus) PRs **#4–#13** (ports of milvus-io top-10 cognitive set)  
**Wall clock:** ~50 min sequential (19:25Z → 20:15Z)

| Fork | Upstream | Title | Verdict | Score | Tools | Time | Review |
|-----:|---------:|-------|---------|------:|------:|-----:|--------|
| [#4](https://github.com/Mr-Ashish/milvus/pull/4) | [#51785](https://github.com/milvus-io/milvus/pull/51785) | schema.Version for QueryNode | **COMMENT** | 78 | 31 | 383s | [comment](https://github.com/Mr-Ashish/milvus/pull/4#issuecomment-5146724799) |
| [#5](https://github.com/Mr-Ashish/milvus/pull/5) | [#51393](https://github.com/milvus-io/milvus/pull/51393) | nested element-level array indexes | **APPROVE** | 85 | 39 | 346s | [comment](https://github.com/Mr-Ashish/milvus/pull/5#issuecomment-5146772574) |
| [#6](https://github.com/Mr-Ashish/milvus/pull/6) | [#51886](https://github.com/milvus-io/milvus/pull/51886) | delegator schema load gate | **APPROVE** | 78 | 24 | 327s | [comment](https://github.com/Mr-Ashish/milvus/pull/6#issuecomment-5146814422) |
| [#7](https://github.com/Mr-Ashish/milvus/pull/7) | [#51246](https://github.com/milvus-io/milvus/pull/51246) | async storage v2 field load | **APPROVE** | 82 | 20 | 328s | [comment](https://github.com/Mr-Ashish/milvus/pull/7#issuecomment-5146858609) |
| [#8](https://github.com/Mr-Ashish/milvus/pull/8) | [#51431](https://github.com/milvus-io/milvus/pull/51431) | RG balance epochs | **APPROVE** | 82 | 35 | 291s | [comment](https://github.com/Mr-Ashish/milvus/pull/8#issuecomment-5146899583) |
| [#9](https://github.com/Mr-Ashish/milvus/pull/9) | [#51874](https://github.com/milvus-io/milvus/pull/51874) | manifest CAS base==current | **APPROVE** | 92 | 10 | 168s | [comment](https://github.com/Mr-Ashish/milvus/pull/9#issuecomment-5146929158) |
| [#10](https://github.com/Mr-Ashish/milvus/pull/10) | [#51845](https://github.com/milvus-io/milvus/pull/51845) | optimistic CAS partial updates | **REQUEST CHANGES** | 69 | 29 | 347s | [comment](https://github.com/Mr-Ashish/milvus/pull/10#issuecomment-5146974756) |
| [#11](https://github.com/Mr-Ashish/milvus/pull/11) | [#51694](https://github.com/milvus-io/milvus/pull/51694) | segment resources → published state | **APPROVE** | 92 | 11 | 262s | [comment](https://github.com/Mr-Ashish/milvus/pull/11#issuecomment-5147009178) |
| [#12](https://github.com/Mr-Ashish/milvus/pull/12) | [#51641](https://github.com/milvus-io/milvus/pull/51641) | copy-segment stale snapshot guards | **APPROVE** | 87 | 20 | 181s | [comment](https://github.com/Mr-Ashish/milvus/pull/12#issuecomment-5147034062) |
| [#13](https://github.com/Mr-Ashish/milvus/pull/13) | [#51441](https://github.com/milvus-io/milvus/pull/51441) | stats skip index row-group/cell | **APPROVE** | 92 | 21 | 274s | [comment](https://github.com/Mr-Ashish/milvus/pull/13#issuecomment-5147069647) |

## Stats

- **10/10** success (`ok=true`, `orch_rc=0`, `BIT3_OK`, comments posted)
- Mean score: **83.7/100** (range 69–92)
- Mean tools: **24.0** (range 10–39)
- Mean elapsed: **291s** (range 168–383s)
- Verdicts: **8 APPROVE · 1 REQUEST CHANGES · 1 COMMENT**

## Command

```bash
for pr in 4 5 6 7 8 9 10 11 12 13; do
  ./scripts/trigger-review.sh modal Mr-Ashish/milvus $pr \
    --model deepseek/deepseek-v4-pro --post
done
```

Artifacts: `.torii-out-e2e-modal-milvus-top10-deepseek-v4-pro/pr{N}/modal-run.log`


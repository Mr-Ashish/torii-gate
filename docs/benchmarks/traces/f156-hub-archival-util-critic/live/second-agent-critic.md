# Second-agent critic (F78)

- at: `2026-08-01T10:04:38Z`
- maker: **REQUEST_CHANGES**
- recommended: **REQUEST_CHANGES**
- composite: **0.8013** level **L2** (13/14 checkers ok)

| Checker | OK | Score | Notes |
|---------|:--:|------:|-------|
| structure | yes | 1.0 | {"verdict": "REQUEST_CHANGES", "has_summary": true, "has_blocking": true, "has_c |
| f70_dual_critic | no | 0.3333 | {"precision_proxy": 0.3333, "effective_precision": 0.2696, "effective_aware": tr |
| f72_chain | yes | 0.8571 | {"full_chain_rate": 0.8571, "scorecard_pct": 60.7, "verdict_checker": "REQUEST_C |
| f73_fitness | yes | 0.7829 | {"composite": 0.7829, "path_evidence": 0.75, "procedure": 0.9675, "tool_use": 0. |
| f75_memory | yes | 1.0 | {"conflict_count": 0, "suppress_count": 0, "item_count": 8} |
| f121_recovery_util | yes | 1.0 | {"utilization_gap": false, "util_rate": 1.0, "recovery_injected": [], "tool_hit_ |
| f136_scorecard_util | yes | 1.0 | {"utilization_gap": false, "util_rate": 1.0, "scorecard_injected": [], "scorecar |
| f127_hub_gap | yes | 0.7 | {"gap_pressure": 0.4756, "thr": 0.34, "high": true, "reason": "no_recovery_injec |
| f139_scorecard_hub_gap | yes | 1.0 | {"gap_pressure": 0.0, "thr": 0.34, "high": false, "reason": "no_scorecard_inject |
| f141_memory_util | yes | 1.0 | {"feature": "F141", "utilization_gap": false, "util_score": 1.0, "hit_count": 23 |
| f143_memory_hub_gap | yes | 1.0 | {"feature": "F143", "gap_pressure": 0.0, "thr": 0.34, "high": false, "util_score |
| f150_recon_warm_hub | yes | 0.85 | {"feature": "F150", "heat": 0.0, "thr": 0.34, "high": false, "theme_n": 0, "max_ |
| f156_hub_archival_util | yes | 1.0 | {"enabled": true, "hub_archival_injected": false, "hub_archival_util_gap": false |
| f81_llm | yes | 0.5 | {"skipped": true, "reason": "TORII_LLM_CRITIC disabled"} |


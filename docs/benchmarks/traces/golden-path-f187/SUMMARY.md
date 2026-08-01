# Golden path (F187) — live dogfood proof

## Offline
- golden_path_metrics fixture_pass (12/12 readiness)
- labeled TP cases: 9 (insecure-demo 4 + juice-shop-synthetic 5)
- good_recall=1.0 · weak_recall=0.0 · delta=1.0
- docs: GOLDEN-PATH.md + golden-path-metrics.md

## Live Modal
- pytorch/pytorch PR #191840
- BIT3_OK · ~48.0s · POST_COMMENT=0 · log_streaming=true
- model: deepseek/deepseek-chat-v4-pro
- verdict: COMMENT (fail-closed F45: 0 tool turns on multi-file PR — not APPROVE)

## Commercial
- Required check documented: `torii/gate`
- Install one-pager: docs/GOLDEN-PATH.md
- Metrics chart: docs/benchmarks/golden-path-metrics.md

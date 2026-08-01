# PUBLIC_EVAL (F189) — labeled multi-pack scorecard

## Offline
- 4 packs all_pass: insecure-demo, juice-shop, nodegoat, django-vuln
- labeled_tp_cases=18 · good_recall=1.0 · weak=0.0 · seed=42
- docs/benchmarks/public-eval/SCORECARD.md

## Live Modal
- pytorch/pytorch PR #191840
- BIT3_OK · ~52.8s · POST_COMMENT=0 · log_streaming=true
- model: deepseek/deepseek-chat-v4-pro
- verdict: COMMENT (fail-closed zero tools)

## Commercial
- scorecard_target: 8.5
- dim_lift: technical trust / public labeled eval

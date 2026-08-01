# SUMMARY — GATE_CERT_WIRE live Modal dogfood

- feature: **GATE_CERT_WIRE** (save-trace + workflow + ops last certificate)
- repo: pytorch/pytorch PR #191840
- bit: 3 · POST_COMMENT=0 · model deepseek/deepseek-v4-pro
- outcome: BIT3_OK · elapsed ~173.5s · log_streaming=true · tools=7
- verdict: **REQUEST_CHANGES** · block=True
- certificate: `gc-95888668ca0a313d` · path_evidence=1.0
- reason_codes: verdict_request_changes, strong_path_evidence, blocking_with_paths
- modal: https://modal.com/apps/mr-ashish/main/ap-4ghVM4pbAMLAIlBbyHhzHn
- note: soft wire ships this fire; live Modal image certifies offline emit until next deploy

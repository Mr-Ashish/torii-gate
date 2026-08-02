# Torii Gate — first-principles product scorecard

_Scored: `2026-08-02T01:39:00Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | merge authority · torii/gate |
| 2 | Diff vs SAST | 8.2 | DIFF.md · labeled_tp=18 |
| 3 | JTBD | 9.2 | quieter organic + TTS + proof packet |
| 4 | Agent tools | **8.3** | Modal DEFAULT_MODEL=deepseek-v4-pro tool-use SoT |
| 5 | Memory | 8.0 | L3 |
| 6 | Self-evolution | 7.8 | dual_gate · pending=1 |
| 7 | Install | 8.9 | bootstrap --demo |
| 8 | Ops | **9.1** | LIVE_LEAN · model SoT on status · public-eval age 0h |
| 9 | Enterprise | 8.0 | isolation |
| 10 | Pricing | 8.0 | open core |
| 11 | GTM | 8.4 | PILOT-PROOF + landing link |
| 12 | Simplicity | **8.8** | status cost/trust shows model=deepseek/deepseek-v4-pro |

**Overall ~8.5 raw** (cap **8.0** until first design partner / paid pilot).

## This fire

**MODEL_SOT_DEEPSEEK:** Modal `DEFAULT_MODEL` → `deepseek/deepseek-v4-pro`; model_alias fixture gates modal default; status cost/trust shows preferred model; public-eval refreshed; landing links PILOT-PROOF.

## Remaining

| Rank | Gap | Status | ROI |
|-----:|-----|--------|-----|
| 1 | First closed design partner | human GTM (packet ready) | high / non-code |
| 2 | No F185+ without customer win | standing | — |

```bash
python3 scripts/model_alias.py fixture
python3 scripts/torii.py status --text
```

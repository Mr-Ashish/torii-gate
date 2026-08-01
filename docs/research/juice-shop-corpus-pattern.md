# F76 research note — multi-corpus labeled security bench

**Date:** 2026-08-01  
**Fire:** F76

## Sources

1. OWASP Juice Shop challenge taxonomy (SQLi, XSS, CMDi, secrets, IDOR) — themes only.
2. Prior Torii F70 insecure-demo pack — dual-pass critic + TP promote.
3. Product competitive context (2026 AI PR review): security-focused gates vs general code-quality bots (CodeRabbit alternatives emphasize evidence + low noise).

## Pattern

| Idea | Port |
|------|------|
| Multi-pack labeled ground truth | `bench_corpus.py` packs registry |
| License-safe synthetic app | `demo/juice-shop-synthetic/` original JS |
| Offline good/weak delta | F70 fixture per pack + aggregate `all_pass` |
| Static-led JS | F71 rules: express sources, XSS, hardcoded secrets |

## Success metric

- `bench_corpus.py all` → packs_passed=2, avg_delta_recall≈1.0
- Taint candidates ≥2 on juice routes

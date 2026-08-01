# Pattern: public labeled eval (fixed seed + OSS themes)

## Source
- Eval / paper hygiene: fixed seed + model id on published scorecards.
- Torii priority →8.5 technical trust: Juice Shop synthetic + **2 additional OSS-theme packs**.
- Mem0/SkillsBench discipline: good vs weak harness; weak recall ≈ FP proxy.

## Steal for Torii
1. License-safe synthetic demos themed after NodeGoat + Django/Flask training apps (not forks).
2. Register packs in `bench_corpus.PACKS` with good/weak fixtures.
3. `public_eval.py report` writes `docs/benchmarks/public-eval/SCORECARD.md` with seed, model_id, FP/TP, cost/PR.
4. CLI: `torii.py public-eval -- fixture|report`.

## Anti-pattern
Claiming TP/FP on unlabelled live pytorch dogfood without a fixed labeled corpus.

# Torii Gate vs SAST vs AI review

**Buyer one-pager** · dim 2 (differentiation) · honest positioning, not a bake-off claim.

Torii is a **security merge authority** on the PR. It does not replace scanners or general AI review — it answers a different job: *can this change merge?*

```text
SAST / SCA     →  find possible vulns (often noisy backlog)
AI code review →  style, nits, general quality comments
Torii Gate     →  path-evidenced security gate + quieter over time
```

## Capability matrix

| Capability | SAST / SCA (e.g. Semgrep, Snyk, CodeQL) | AI PR review (e.g. CodeRabbit-class) | Torii Gate |
|------------|:---------------------------------------:|:------------------------------------:|:----------:|
| Primary job | Detect patterns / deps | Code quality comments | **Security merge authority** |
| Every PR merge signal | Often advisory | Comments | **Required check `torii/gate`** |
| Path evidence on findings | Rules / SARIF | Sometimes | **Required for strong APPROVE** |
| False-positive memory | Rare / project config | N/A | **Local FP/TP compound memory** |
| Quieter over time | Usually noisier | Chatty | **Measured quieter chart** |
| Gate certificate (reason codes) | No | No | **Yes · tools-as-code** |
| Agent tools on the diff | No | Limited | **Hermes tools · measured tool-use rate** |
| Cost model | Seat / scan volume | Seat | **~\$0.01/PR p50 dogfood** (OpenRouter) |
| Offense / exploit proof | No | No | Not v1 (not our ICP) |

## What the labeled public eval shows (not marketing)

Fixed seed **42** · model pin · license-safe synthetic packs (Juice Shop theme, NodeGoat theme, Django/Flask theme, insecure-demo).

| Metric | Value | Why it matters |
|--------|------:|----------------|
| Labeled TP cases | **18** | Ground-truth security cases on good harness |
| Good harness recall (mean) | **1.0** | Required cases matched when review is strong |
| Weak harness recall (FP proxy) | **0.0** | Empty/weak APPROVE does not fake recall |
| Packs passed | **4 / 4** | Multi-theme corpus, not one demo |
| Cost/PR p50 (live dogfood vault) | **~\$0.014** | Honest unit economics (local vault only) |
| Time-to-signal p50 | **~93s** | First merge signal latency |

Refresh / audit:

```bash
python3 scripts/torii.py public-eval -- status
python3 scripts/torii.py public-eval -- report   # regenerates scorecard when stale
cat docs/benchmarks/public-eval/SCORECARD.md
```

Source of truth: [`docs/benchmarks/public-eval/SCORECARD.md`](benchmarks/public-eval/SCORECARD.md) · badge: [`BADGE.md`](benchmarks/public-eval/BADGE.md).

## When to use what (buyer decision)

| You need… | Prefer |
|-----------|--------|
| Broad CVE/dep coverage on the monorepo | **SAST / SCA** (keep it) |
| Style / maintainability comments | **AI review bot** |
| A required check that blocks weak AI-generated security merges | **Torii Gate** |
| Hybrid later | SAST SARIF → human triage *or* future Torii validator path (roadmap, not v1 claim) |

**Do not** turn off SAST because Torii exists. **Do** require `torii/gate` so path-empty APPROVE cannot merge.

## Path to value (prove the diff in 5 minutes)

```bash
./scripts/install-torii.sh --minimal /path/to/your-app
# secret OPENROUTER_API_KEY · require status check torii/gate
# @torii review this pr
python3 scripts/torii.py status --text
python3 scripts/torii.py quieter -- status
python3 scripts/torii.py certificate -- fixture
```

Install: [`INSTALL.md`](INSTALL.md) · Golden path: [`GOLDEN-PATH.md`](GOLDEN-PATH.md) · Pilot: [`PILOT.md`](PILOT.md).

## Honesty constraints

- Live OSS dogfood PRs are **unlabelled** — not counted as TP/FP.
- Public eval is **synthetic packs with ground truth**, fixed seed, model pin — reproducible.
- We do **not** claim “zero false positives” or “replaces Semgrep.”
- Traction stays truthful: pre-revenue · 0 paid — [`PILOT.md`](PILOT.md).

```bash
python3 scripts/diff_vs_sast.py fixture
python3 scripts/torii.py buyer -- status   # narrative still one diagram
```

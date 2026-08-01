# Torii Gate — golden path (commercial)

**Target:** scorecard **7.5** — install → required check → real PR dogfood → FP/TP chart.

One buyer story: *the gate gets stricter and quieter.* Advanced compound-loop F-numbers live under `docs/research/` — not here.

```text
install pack  →  secret  →  require torii/gate  →  @torii review  →  signal + metrics
```

## 5-minute install (target repo)

```bash
# from a torii-gate checkout
./scripts/install-torii.sh /path/to/your-app
# hub-managed thin caller only (free upgrades from hub main):
# ./scripts/install-torii.sh --caller /path/to/your-app

cd /path/to/your-app
git add -A && git commit -m "ci: install Torii Gate" && git push
```

### Wire secrets & vars

| Item | Where | Value |
|------|--------|--------|
| `OPENROUTER_API_KEY` | repo **secret** | required |
| `TORII_MODEL` | repo var (optional) | `deepseek/deepseek-v4-pro` |
| `TORII_COMMIT_STATUS` | repo var | leave unset (default on). Set `0` only to disable statuses |

### Required check (the merge authority)

1. GitHub → **Settings → Branches → Branch protection** on the default branch.
2. Enable **Require status checks to pass before merging**.
3. Add required context: **`torii/gate`** (not only `torii/review`).
4. First run may need to complete once before the context appears in the picker — trigger a review on any open PR (below).

| Context | Role |
|---------|------|
| **`torii/gate`** | Security-aware open/closed — **prefer for branch protection** |
| `torii/review` | Classic verdict signal (optional companion) |

Contract detail: [`docs/GATE.md`](GATE.md) · pack notes: [`pack/README.md`](../pack/README.md).

### First signal on a PR

```text
@torii review this pr
```

Or: **Actions → Torii Gate → Run workflow** (PR number).

Expect within minutes: PR comment + labels + commit status **`torii/gate`**.

Offline proof (hub checkout, no API key):

```bash
./scripts/smoke-torii-gate.sh
python3 scripts/golden_path_metrics.py fixture
```

## Dogfood (real PRs)

| Surface | How | Comment on PR? |
|---------|-----|----------------|
| **Modal live** (hub operator) | `modal run modal_app/app.py --bit 3 --repo OWNER/NAME --pr N --model deepseek/deepseek-v4-pro --no-post-comment` | no (`POST_COMMENT=0`) |
| **Local** | `POST_COMMENT=0 ./scripts/review-local.sh owner/repo N` | no unless `POST_COMMENT=1` |
| **Installed Actions** | `@torii review this pr` on a real PR | yes (customer path) |

Intentional insecure dogfood tree: [`demo/insecure/`](../demo/insecure/).

### Own repo + pytorch

- **pytorch/pytorch** — Modal bit-3 dogfood, redacted traces under `docs/benchmarks/traces/`.
- **This hub** — smoke + labeled packs + optional self-PR via Actions after install.

## Metrics chart

Refresh published numbers:

```bash
python3 scripts/golden_path_metrics.py report
# → docs/benchmarks/golden-path-metrics.md
python3 scripts/torii.py golden-path -- status
```

| Metric | Meaning |
|--------|---------|
| **time-to-signal** | wall seconds to verdict (Hermes + gate stages) |
| **cost/PR** | estimated USD when `hermes-usage.json` present |
| **TP rate** | good-harness recall on labeled packs |
| **FP proxy** | weak-harness recall (should stay ~0) |
| **verdicts** | unlabelled live distribution (not claimed TP/FP) |

Published table: [`docs/benchmarks/golden-path-metrics.md`](benchmarks/golden-path-metrics.md).

Labeled packs today: `insecure-demo` (4) + `juice-shop-synthetic` (5). Public multi-repo eval expansion is queue item **#3**.

## CLI front door

```bash
python3 scripts/torii.py help
python3 scripts/torii.py doctor
python3 scripts/torii.py golden-path -- fixture
python3 scripts/torii.py golden-path -- report
python3 scripts/torii.py gate -- --review path/to/review.md
```

## What we deliberately hide here

- Multi-stage loop diagrams and research feature IDs → `PRODUCT.md` **Advanced** / `docs/research/`.
- Landing headline stays: **gate gets stricter and quieter** — not internal loop codenames.
- Buyer diagram: [`docs/brand/BUYER-DIAGRAM.md`](brand/BUYER-DIAGRAM.md).

## Next commercial lifts

1. This golden path (install + `torii/gate` + metrics) — **this doc**.
2. Buyer narrative collapse (one diagram) — queue #2.
3. Public labeled eval (+2 OSS repos) — queue #3.
4. Install UX polish / reliability / enterprise light — queue #4–6.

# Torii Gate — 5-minute install

**Goal:** first PR signal under five minutes of operator time.  
**Required merge check:** `torii/gate`  
**One CLI:** `python3 scripts/torii.py` (do not juggle peer scripts on day one)

```text
install → secret → require torii/gate → @torii review this pr
```

## 1. Install pack (≈1 min)

```bash
# from a torii-gate checkout
./scripts/install-torii.sh /path/to/your-app

# 5-minute surface only (gate + review runtime; no bench/eval/modal scripts):
./scripts/install-torii.sh --minimal /path/to/your-app

# hub-managed thin workflow (upgrades follow hub main):
./scripts/install-torii.sh --caller /path/to/your-app

# optional enterprise light: stamp multi-org tenant id (repo-local memory still default)
./scripts/install-torii.sh --tenant acme-platform /path/to/your-app
```

```bash
cd /path/to/your-app
git add -A && git commit -m "ci: install Torii Gate" && git push
```

## 2. Secret (≈1 min)

GitHub → **Settings → Secrets and variables → Actions**

| Name | Required |
|------|----------|
| `OPENROUTER_API_KEY` | **yes** |
| `TORII_MODEL` (variable) | optional · `deepseek/deepseek-chat-v4-pro` |

## 3. Required check (≈1 min)

**Settings → Branches → Branch protection** on the default branch:

1. Require status checks to pass before merging  
2. Required context: **`torii/gate`**  
3. Trigger one review first if the check name is not yet listed  

**First Actions run:** the job summary includes a **Required check — make the gate merge authority** checklist (same steps). You do not need to dig docs mid-install — open the workflow run → Summary.

## 4. First review (≈1–2 min)

On any open PR comment:

```text
@torii review this pr
```

Or: **Actions → Torii Gate → Run workflow** (PR number).

Expect: PR comment + labels + commit status **`torii/gate`**.

## 5. Doctor + status (day-2 habit)

```bash
python3 scripts/torii.py status --text   # one-screen: commercial · cost · cert · quieter
python3 scripts/torii.py doctor          # human summary (default on TTY)
python3 scripts/torii.py doctor --json   # machine JSON
python3 scripts/torii.py help
```

`status --text` is the buyer day-2 one-screen (no research feature IDs).  
`doctor_pass: true` means product surfaces are wired. Failures print the failing check names.

## CLI confusion — use one front door

`python3 scripts/torii.py help` is **tiered** (Day-1 · Day-2 · Advanced). Day-1 only needs:

```bash
python3 scripts/torii.py status --text
python3 scripts/torii.py doctor
python3 scripts/torii.py smoke              # offline, no API key
python3 scripts/torii.py golden-path -- status
# require branch-protection check: torii/gate
```

Day-2 (after a few reviews): `quieter -- status` · `ops -- status` · `certificate -- fixture` · `enterprise -- status`.  
Advanced groups (memory loops, federation, self-evolve) stay on the same CLI — they are not the install path.

| Use this | Not this (day one) |
|----------|--------------------|
| `python3 scripts/torii.py …` | raw `torii_memory.py`, `skill_loop_status.py`, … |
| `torii.py memory -- search -- -q "…"` | inventing paths into `scripts/` |
| `torii.py gate -- --review review.md` | hand-editing status checks |

`scripts/torii_memory.py` remains supported for agents that already pin it; humans and install docs standardize on **`torii.py`**.

## Verify install (offline)

```bash
# on hub or pack-mode target
./scripts/smoke-torii-gate.sh
python3 scripts/install_ux_check.py fixture
python3 scripts/torii.py doctor
```

## Deeper docs

| Doc | When |
|-----|------|
| [`GOLDEN-PATH.md`](GOLDEN-PATH.md) | commercial loop + metrics |
| [`GATE.md`](GATE.md) | gate policy contract |
| [`ops/RELIABILITY.md`](ops/RELIABILITY.md) | fail-closed defaults · smoke CI · cost/PR |
| [`WORKFLOWS.md`](WORKFLOWS.md) | pipelines-as-code (validate offline) |
| [`QUIETER.md`](QUIETER.md) · [`TOOL-USE.md`](TOOL-USE.md) | quieter + tool-use charts |
| [`enterprise/`](enterprise/) · [`FEDERATION.md`](FEDERATION.md) | enterprise light + multi-tenant privacy |
| [`MEMORY.md`](MEMORY.md) | compound memory — FP die twice |
| [`SELF-EVOLVE.md`](SELF-EVOLVE.md) | day-2 skill self-evolution (dual-gated) |
| [`workflows/INSTALL-GUIDE.md`](workflows/INSTALL-GUIDE.md) | full capability matrix |
| [`brand/BUYER-DIAGRAM.md`](brand/BUYER-DIAGRAM.md) | buyer story |
| `docs/research/` | Advanced / F-IDs |

## Day-2 (optional)

After the first green `torii/gate` runs:

```bash
python3 scripts/torii.py doctor
python3 scripts/torii.py memory -- doctor
python3 scripts/torii.py quieter -- status
python3 scripts/torii.py self-evolve -- status
python3 scripts/torii.py ops -- status
python3 scripts/torii.py golden-path -- status
python3 scripts/torii.py enterprise -- status
```

### Own-repo quieter checklist

Customer vault (after install): runs accumulate under **`.torii/runs/`**.  
Measure without cloning the Torii hub dogfood tree:

```bash
python3 scripts/torii.py quieter -- report   # → .torii/quieter-over-time.md
python3 scripts/torii.py quieter -- status
```

See [`QUIETER.md`](QUIETER.md) · required check remains **`torii/gate`**.

### Own-repo quieter checklist (branch protection)

1. Required check **`torii/gate`** is on (step 3 above).  
2. Review a few real PRs (`@torii review this pr`) — slim packs land in **`.torii/runs/`**.  
3. Measure: `python3 scripts/torii.py quieter -- report` → `.torii/quieter-over-time.md` ([`QUIETER.md`](QUIETER.md)).  

Buyer story: *the gate gets stricter and quieter over time — not noisier.*

### Cost / PR visibility (day-2)

Operators should not open Modal run pages to answer “what does a PR cost?”:

```bash
python3 scripts/ops_dashboard.py report
# → docs/ops/cost-pr-dashboard.md  (p50 cost + time-to-signal + cert ids)
python3 scripts/golden_path_metrics.py report
# → docs/benchmarks/golden-path-metrics.md
```

Dogfood vault (Modal + Hermes, `POST_COMMENT=0`) feeds measured p50 cost/PR and time-to-signal. Soft budget: repo var `TORII_MAX_COST_USD` warns without failing by default. See [`ops/cost-pr-dashboard.md`](ops/cost-pr-dashboard.md) · [`ops/RELIABILITY.md`](ops/RELIABILITY.md).

### Enterprise light (optional fleet)

Day-one stays **repo-local** (`.torii/`). Multi-org fleets can stamp a tenant id:

| Knob | What |
|------|------|
| `./scripts/install-torii.sh --tenant <id> DEST` | Writes `tenant_id=` on `.torii-install-stamp` + `.torii/tenant.env` (`TORII_MEMORY_TENANT`) |
| Repo var / secret `TORII_MEMORY_TENANT` | Same id without re-install |
| Hub publish | **Opt-in** (`TORII_HUB_PUBLISH=1`) — themes only, never paths/snippets/USD |

```bash
python3 scripts/torii.py enterprise -- status
python3 scripts/torii.py enterprise -- fixture
```

Privacy: cost/PR dogfood stays **local vault only** — never federated. Docs: [`enterprise/ORG-ISOLATION.md`](enterprise/ORG-ISOLATION.md) · [`enterprise/PRIVACY.md`](enterprise/PRIVACY.md) · [`FEDERATION.md`](FEDERATION.md).

Memory keeps the next PR quieter (path-evidenced FP/TP store). Self-evolution proposes skills from measured gaps; adopt stays dual-gated. Details: [`MEMORY.md`](MEMORY.md) · [`SELF-EVOLVE.md`](SELF-EVOLVE.md).

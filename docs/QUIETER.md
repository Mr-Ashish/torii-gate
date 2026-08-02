# Torii Gate — quieter over time (own-repo path)

**Buyer story:** *The gate gets stricter and quieter over time — not noisier.*

This is the post-install habit for a **real repo** (yours), not a research harness.

```text
install pack → require status check torii/gate → review PRs → quieter chart
```

## 0. Customer vault bootstrap

Install stamps **`.torii/runs/README.md`** and **two labeled demo packs** (`demo-early-001` · `demo-late-001`, `demo: true`) so `quieter -- status` works **offline** before the first PR. After real reviews, slim organic packs land under `.torii/runs/{trace_id}/` via **FS workspace write** (`TORII_LOCAL_FS_PUBLISH=1`, default) even when git push of `.torii` is off (`TORII_LOCAL_PUBLISH=0`). Hub dogfood is optional.

| State | What status shows |
|-------|-------------------|
| Empty vault | `local_runs_n=0` · `bootstrap_needed` · run `quieter -- bootstrap --demo` |
| Demo only | `local_demo_n≥1` · chart works · `organic_needed` · require **`torii/gate`** or `land-dogfood` |
| Organic | `local_organic_n≥1` · quieter chart from real reviews / landed dogfood |

Honesty: demo packs prove the vault path; trajectory prefers organic/hub rows when present (`trajectory_source=measured|demo`). Landed packs use `source=land-dogfood` · `demo=false` (not install-demo).

```bash
python3 scripts/torii.py quieter -- bootstrap --demo   # README + labeled demos
python3 scripts/torii.py quieter -- land-dogfood       # organic from hub Modal dogfood
python3 scripts/torii.py quieter -- status             # local_runs_n · demo · organic
```
## 1. Install on your repo

```bash
# from a torii-gate checkout
./scripts/install-torii.sh /path/to/your-app
# or 5-minute surface:
# ./scripts/install-torii.sh --minimal /path/to/your-app
```

Wire `OPENROUTER_API_KEY` (repo secret). Details: [`GOLDEN-PATH.md`](GOLDEN-PATH.md) · [`INSTALL.md`](INSTALL.md).

## 2. Required check (merge authority)

1. GitHub → **Settings → Branches → Branch protection** on the default branch.
2. Enable **Require status checks to pass before merging**.
3. Add required context: **`torii/gate`** (prefer over `torii/review` alone).
4. Trigger one review so the context appears in the picker if needed.

| Context | Role |
|---------|------|
| **`torii/gate`** | Security-aware open/closed — **use for branch protection** |
| `torii/review` | Optional companion verdict signal |

Contract: [`GATE.md`](GATE.md). Every open/close can ship a **gate certificate** (reason codes + path evidence) — not a chat dump.

## 3. First reviews

```text
@torii review this pr
```

Or: **Actions → Torii Gate → Run workflow**.

Expect: PR comment + labels + commit status **`torii/gate`**.  
False positives die twice (memory suppressions); true positives stay path-evidenced.

## 4. Measure “quieter” (own repo — no hub archaeology)

After pack install, each review can land a slim pack under **`.torii/runs/{trace_id}/`** (meta + summary + review). That is your **customer vault**.

```bash
# from the installed target repo (or hub checkout)
python3 scripts/torii.py quieter -- report
python3 scripts/torii.py quieter -- status
# writes:
#   .torii/quieter-over-time.md      ← customer path (always when .torii/ exists)
#   docs/benchmarks/quieter-over-time.md  ← hub path when present
```

| Vault | Where | Who |
|-------|--------|-----|
| **Local runs** | `.torii/runs/` | **Your repo after install** (default measure path) |
| Hub dogfood | `docs/benchmarks/traces/` | Torii hub maintainers only |

Override: `TORII_TRACE_VAULT_ROOT=/path/to/runs`.

| Signal | Quieter means |
|--------|----------------|
| **path evidence** | blocks/opens cite files, not vibes |
| **tool use** | agent used workspace/diff tools (not pure prose) |
| **certificates** | every run has merge-authority evidence (rate should rise after gate-cert wire) |
| **weak APPROVE** | empty/no-tool approvals go down |
| **quiet_score** | composite early → late (late should hold or rise) |
| **cost / time** | optional honesty: mean cost/PR + time-to-signal on the same chart |

Hub maintainers also run Modal on public PRs (`POST_COMMENT=0`) — optional second vault. Cost tables: [`ops/cost-pr-dashboard.md`](ops/cost-pr-dashboard.md) · product brief: [`PRODUCT.md`](../PRODUCT.md).

## 5. What “stricter and quieter” is *not*

- Not more comment bots.
- Not a new compound-loop feature ID for every PR.
- Not auto-merge without a human.

It is: **required check + path-evidenced signal + measured noise drop over time.**

## CLI

```bash
python3 scripts/torii.py quieter -- fixture
python3 scripts/torii.py quieter -- status
python3 scripts/torii.py quieter -- report
python3 scripts/torii.py tool-use -- status
python3 scripts/torii.py golden-path -- status
python3 scripts/torii.py certificate -- fixture
```

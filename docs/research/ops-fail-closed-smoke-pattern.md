# Pattern: reliability ops — fail-closed + smoke CI + cost stub

## Source
- Loop Engineering: measure the loop operators feel (smoke green, cost visible).
- AppSec merge gates: silent APPROVE without tools is worse than a closed gate.
- Scorecard dim **reliability/ops (5.0)**.

## Steal for Torii
1. Inventory fail-closed defaults (tool-turns on, webhook open off, statuses on).
2. `.github/workflows/smoke-offline.yml` — no API key, runs `smoke-torii-gate.sh` + focused pytest.
3. `ops_dashboard.py` publishes cost/PR + dashboard under `docs/ops/`.
4. Required check docs stay linked from GATE/INSTALL.

## Anti-pattern
Deep compound loops while smoke only runs on a laptop and cost lives in Modal UI only.

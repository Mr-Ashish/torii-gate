# Torii Gate — self-evolution (day-2)

**Buyer story:** *The gate teaches itself measured skills — dual-gated adopt, not free-form prompt drift.*

```text
run evidence → proposals → offline eval → dual-gate adopt → next PR skills
```

## Why this is product (not research theater)

| Promise | Reality |
|---------|---------|
| Skills improve over time | Only when **tool hits** and dual gates pass |
| Close the loop on ops gaps | `propose-scorecard` turns scorecard gaps into skill proposals |
| Safe by default | Human/default REJECT until eval + attribution pass; no auto-chaos |

Self-evolution is **optional day-2**. Day-one is still: install → require **`torii/gate`** → review.

## Operator path

```bash
# Status of trajectories / proposals / active skills
python3 scripts/torii.py self-evolve -- status

# Offline hermetic fixture (CI-friendly)
python3 scripts/torii.py self-evolve -- fixture

# From product scorecard gaps (ops close-the-loop)
python3 scripts/self_evolve.py propose-scorecard

# Dual-gate adopt cycle for scorecard skills (default: gates must pass)
python3 scripts/skill_auto_adopt.py cycle-scorecard
```

| Command | Use when |
|---------|----------|
| `status` | See ledger + active skills after dogfood |
| `fixture` | Prove mine/score wiring offline |
| `propose-scorecard` | Brand/ops metrics show a gap |
| `refine-from-util` | Advanced: GEPA-lite body tweak from util traces (optional) |

## Guardrails (buyer language)

1. **Allowlisted tools** — probes come from known CLI patterns, not arbitrary log regex.  
2. **Dual-gate adopt** — contribution + attribution; free-riders stay proposals.  
3. **Inject budget** — recovery/product skills compete for always slots (no context dump).  
4. **Measure utilization** — inject ≠ tools fired (see [`TOOL-USE.md`](TOOL-USE.md)).

## Related

- Install day-one: [`INSTALL.md`](INSTALL.md)  
- Quieter over time: [`QUIETER.md`](QUIETER.md)  
- Workflows-as-code: [`WORKFLOWS.md`](WORKFLOWS.md)  
- Product scorecard: `python3 scripts/torii.py scorecard`  
- Engine: `scripts/self_evolve.py` · `scripts/skill_auto_adopt.py`

# Torii Gate — one buyer diagram

**Primary story:** *The gate gets stricter and quieter over time — not noisier.*

Feature IDs (F78, F186, …) are **not** the product story. They live under **Advanced** / `docs/research/`.

## The diagram

```text
                    ┌─────────────────────────────────────────┐
   PR / CI ───────► │           TORII GATE                    │
   @torii review    │                                         │
                    │   1. REVIEW          maker tools on diff │
                    │      + CHECK         demote weak APPROVE │
                    │                                         │
                    │   2. COMPOUND        skills that measure │
                    │      (two loops)     memory that pages   │
                    │         │                               │
                    │         ▼                               │
                    │   quieter next PR · sharper blocks      │
                    │                                         │
                    │   3. MERGE SIGNAL    required check     │
                    │                      torii/gate         │
                    └─────────────────────────────────────────┘
                                      │
                                      ▼
                         open / closed · labels · comment
```

### Three beats (what to say on a call)

| Beat | Buyer language | What engineers implement |
|------|----------------|--------------------------|
| **1. Review + check** | Agent looks at the diff with tools; a second pass kills empty APPROVEs | Maker agent + deterministic checker panel |
| **2. Compound** | Every run teaches the next: skills that help stay loud; noise dies | Skill loop + memory loop (see Advanced) |
| **3. Merge signal** | Branch protection requires **`torii/gate`** — honest open/closed | Commit status + labels |

### Why not five mental models on the landing page?

A–E (maker/checker, skill loop, memory loop, recovery, hub-archival/GEPA) are **one product behavior** from the buyer’s seat: **review → learn → gate**. Splitting them into five F-numbered diagrams raises cognitive load and hides the install path.

| Old label | Folded into beat |
|-----------|------------------|
| Mental model A (maker/checker) | **1. Review + check** |
| Mental model B (skill loop) | **2. Compound** |
| Mental model C (memory loop) | **2. Compound** |
| Mental model D (recovery / hub-archival) | **2. Compound** (quality under budget) |
| Mental model E (GEPA refine) | **2. Compound** (skills improve or leave always budget) |

## Primary surfaces (must stay simple)

| Surface | Rule |
|---------|------|
| `docs/brand/landing.html` | One diagram; F-IDs only in Advanced `<details>` |
| `README.md` | Buyer diagram + golden path; link Advanced in PRODUCT |
| `PRODUCT.md` | Buyer section first; F-stack under **Advanced** |
| `docs/GOLDEN-PATH.md` | Install → `torii/gate` → metrics (no F-tour) |

## Advanced (engineers & research)

- Full loop stage tables: `PRODUCT.md` → **Advanced**
- Research fire log / patterns: `docs/research/`
- Measured scorecard ops: `python3 scripts/torii.py scorecard` (ops, not marketing)

## Check

```bash
python3 scripts/buyer_narrative_check.py fixture
```

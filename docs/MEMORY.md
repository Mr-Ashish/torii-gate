# Torii Gate — compound memory

**Buyer story:** *False positives die twice — true positives stay sharp.*

```text
path-evidenced finding → write (integrity) → consolidate → scoped recall
                              ↓
                    core (hot) vs archival (cold) · graph supersession
```

## JTBD (merge authority)

| Pain | Torii memory |
|------|----------------|
| SAST / bot noise returns after dismiss | **FP rules + events** — resolved noise does not resurrect |
| Stale “confirmed” TPs inflate confidence | **Effective critic** — only strong, non-stale memory confirms |
| Prompt dump of every past finding | **Scoped recall + tiers** — path-matched core first; cold pages on demand |
| Multi-tenant leak risk | **Federate themes only** — see [`FEDERATION.md`](FEDERATION.md) |

Memory does **not** replace **`torii/gate`**. It makes the next PR **quieter** while blocks stay path-evidenced.

## Operator path

```bash
# Product front door
python3 scripts/torii.py memory -- help
python3 scripts/torii.py memory -- status
python3 scripts/torii.py memory -- doctor

# Search / graph (Hermes day-2 habit)
python3 scripts/torii.py memory -- search -- -q "sql OR pickle OR secret"
python3 scripts/torii.py memory -- graph -- query --path <file> --hops 2

# Compound loop readiness (L0–L3)
python3 scripts/torii.py memory-loop -- scorecard --shallow
python3 scripts/torii.py memory-loop -- fixture
```

| Surface | Meaning |
|---------|---------|
| **Local `.torii/`** | Default — FP/TP store, graph, tiers on the repo |
| **Integrity write** | Only path-evidenced findings become durable TP signatures |
| **Archival search** | Cold hits promote when paths/themes match |
| **Hub federate** | Optional privacy-safe themes across tenants |

## What memory is *not*

- Not a full ASPM dashboard  
- Not “share full findings across orgs”  
- Not auto-merge  
- Not the cost/PR ledger — measured dogfood spend lives in ops (`python3 scripts/torii.py ops -- status` · [`ops/cost-pr-dashboard.md`](ops/cost-pr-dashboard.md)); memory federates **themes only** ([`FEDERATION.md`](FEDERATION.md))

Related: [`QUIETER.md`](QUIETER.md) · [`FEDERATION.md`](FEDERATION.md) · [`TOOL-USE.md`](TOOL-USE.md) · [`GATE.md`](GATE.md) · install [`INSTALL.md`](INSTALL.md).

## Day-2 habit

```bash
python3 scripts/torii.py doctor
python3 scripts/torii.py memory -- doctor
python3 scripts/torii.py quieter -- status
python3 scripts/torii.py status --text   # growth: memory=L3 tp=N fp=M doctor=…
```

Scoped store counts (`tp` / `fp`) on the growth beat make “FP die twice · TP stay sharp” auditable without opening `.torii/scoped-memory.json`.

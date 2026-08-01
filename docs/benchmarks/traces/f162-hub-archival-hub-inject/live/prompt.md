<!-- torii-f142-memory-util-hub -->
## Federated memory util (F142 hub compound)

Cross-tenant memory tool outcomes (skill/tool themes + util bins only; no paths):
- (no hub memory util themes yet — local memory CLI always budget applies)
<!-- /torii-f142-memory-util-hub -->

# Task
You are Torii Gate security reviewer. Review the following file for vulnerabilities.
Produce Markdown with **Verdict:**, **Score:**, ### Summary, ### Blocking,
### Security audit, ### Key findings, ### Tests & risk, ### What I checked.
Every finding MUST cite a path (use `demo/insecure/app.py`). Prefer high-severity issues.

**Repo:** local-bench
**File under review:** `demo/insecure/app.py`

<!-- torii-f70-tp-signatures -->
## Known true-positive signatures (F70 compound memory)

These patterns were confirmed on labeled benches or prior TP promotions.
Prefer raising path-evidenced findings that match; do not skip them as noise.

- `sqli-search` theme=sql_injection cwe=CWE-89 hits=5 keywords=[sql injection, sqli, f-string, f"select, string-formatted, execute(f, cur.execute(f, cwe-89]
- `pickle-load` theme=insecure_deserialization cwe=CWE-502 hits=5 keywords=[pickle, deserialize, deserialization, unsafe load, cwe-502, pickle.loads]
- `cmdi-run` theme=command_injection cwe=CWE-78 hits=5 keywords=[command injection, shell=true, os command, rce, subprocess, cwe-78, shell injection]
- `secret-exposure` theme=secrets_exposure cwe=CWE-200,CWE-798 hits=5 keywords=[secret, api key, api_key, openrouter, credential, exposes, exposure]


```python
"""Demo insecure snippet for Torii Gate dogfood — DO NOT deploy."""

from flask import Flask, request
import sqlite3
import os
import pickle
import subprocess

app = Flask(__name__)


@app.get("/search")
def search():
    # intentional SQL injection for gate demo
    q = request.args.get("q", "")
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    cur.execute(f"SELECT * FROM items WHERE name = '{q}'")
    return {"rows": cur.fetchall()}


@app.post("/load")
def load():
    # intentional unsafe deserialize
    data = request.data
    return {"obj": str(pickle.loads(data))}


@app.get("/run")
def run_cmd():
    # intentional command injection
    cmd = request.args.get("cmd", "echo hi")
    return {"out": subprocess.check_output(cmd, shell=True).decode()}


@app.get("/secret")
def secret():
    return {"key": os.environ.get("OPENROUTER_API_KEY", "missing")}

```

<!-- torii-f84-skill-router -->
## Skill router (F84/F119/F120 — progressive disclosure + compact)

Use the **index** for awareness; follow **selected full skills** as reviewer discipline.
Routed themes: chain, cmdi, pickle, python, review, secrets, sqli, taint, tools.

### Skill index (all active)

- `skill-archival-memory-search` — Archival memory search when cold facts may apply [general]
- `skill-f74-exploit-scenario` ★ — skill-f74-exploit-scenario [exploit,attacker,sqli,cmdi]
- `skill-f74-prefer-chain-json` — skill-f74-prefer-chain-json [taint,chain,python,javascript]
- `skill-prefer-critic-early` — skill-prefer-critic-early [critic,checker,path,evidence]
- `skill-prefer-hub-archival-early` ★ — skill-prefer-hub-archival-early [archival,hub,recon_warm,memory]
- `skill-prefer-memory-cli-early` ★ — skill-prefer-memory-cli-early [memory,cli,search,graph]
- `skill-prefer-product-cli` ★ — skill-prefer-product-cli [product,cli,doctor,status]
- `skill-preserve-deep-tools` — Preserve deep tool patterns that worked [review,tools,depth,deep_tools]
- `skill-soft-tool-nudge` — Soft mid-review tool nudge [review,tools,h10_soft_nudge]
- `skill-tool-depth-hunks` — Tool depth: prefer diff hunks over file heads [review,diff,tools,zero_tools]

### Selected full skills

#### skill-prefer-hub-archival-early

---
---

## Skill: prefer-hub-archival-early (F153/F154)

1. **Before** finishing findings, run hub-aware archival paging:
   `python3 scripts/archival_memory_search.py auto --files changed.py`
   `python3 scripts/torii.py memory -- search -- -q "hub warm themes"`
   Keep `TORII_RECON_WARM_HUB_QUERY=1` (F149 expands auto-query).
2. Prefer hits with **hub_boost** / multi-tenant warm themes; still require path:line.
3. Do **not** re-raise F145-superseded
…(F120 compacted)

#### skill-prefer-memory-cli-early

---
---

## Skill: prefer-memory-cli-early

1. Before finishing findings, call:
   `python3 scripts/torii.py memory -- search -- -q "auth OR sql OR pickle OR secret"`
   or `python3 scripts/torii_memory.py search -- -q "theme keywords"`
2. Prefer search/graph on changed basenames before re-raising old themes.
3. Treat hits as hints only — still require path:line evidence to block.
4. Do not wait for F106 re-prompt — early use saves the F108 recovery budget.

#### skill-prefer-product-cli

---
---

## Skill: prefer-product-cli

1. Early mid-review call once:
   `python3 scripts/torii.py doctor` or `python3 scripts/torii.py status`
   `python3 scripts/torii.py budget -- status` when soft re-prompts are possible.
2. Treat doctor/status as readiness hints only — still require path:line evidence.
3. Prefer product CLI over ad-hoc script hunting for memory/gate/budget surfaces.

#### skill-f74-exploit-scenario

<!-- F74 adopted 2026-08-01T01:28:42Z -->
---
id: skill-f74-exploit-scenario
feature: F74
status: adopted
source: feedback:no trigger/exploit scenario language
weak_dims: feedback
created_at: 2026-08-01T01:00:38Z
title: Exploit scenario language (fitness feedback)
---

## Skill: exploit-scenario (F74 fitness-gated)

When REQUEST CHANGES on a confirmed sink:
1. Add one **attacker trigger** sentence (how input reaches the sink).
2. Keep it concrete (endpoint, CLI flag, pickle load path) — no generic "could be bad".
3. If no realistic trigger exists, lower severity or mark residual risk honestly.
<!-- /torii-f84-skill-router -->

<!-- torii-f125-recovery-hub -->
## Federated recovery util (F125 hub compound)

Cross-tenant recovery tool outcomes (skill ids + util bins only; no paths):
- `skill-prefer-memory-cli-early`: hits=47 tenants=3 tool_hits=0 Δprio=+40 bin=hit
- `skill-prefer-hub-archival-early`: hits=11 tenants=1 tool_hits=1 Δprio=+32 bin=hit
- `skill-prefer-product-cli`: hits=3 tenants=1 tool_hits=0 Δprio=+19 bin=hit
- **Hub gap pressure=0.42** — prefer early recovery CLI tool calls (memory/doctor/critic) before finalizing.
<!-- /torii-f125-recovery-hub -->

<!-- torii-f162-hub-archival-hub -->
## Federated hub-archival util (F161/F162 hub pressure)

Cross-tenant hub-archival tool outcomes (skill ids + util bins only; no paths):
- `skill-prefer-hub-archival-early`: hits=2 tenants=1 tool_hits=1 gap_hits=1 Δprio=+22 bin=hit
- **Hub-archival gap pressure=0.50** (thr=0.34) — call `archival_memory_search` with hub warm themes so `hub_boost` evidence appears before finalizing (generic memory CLI is not enough).
<!-- /torii-f162-hub-archival-hub -->


<!-- torii-f138-scorecard-hub -->
## Federated scorecard util (F138 hub compound)

Cross-tenant scorecard-gap ops tool outcomes (skill ids + util bins only; no paths):
- (no hub scorecard skill themes yet — local scorecard adopt applies)
<!-- /torii-f138-scorecard-hub -->



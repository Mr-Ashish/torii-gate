**Verdict:** REQUEST CHANGES

**Score:** 0 / 100

**Review effort:** 1 (four trivial, path-evidenced, intentionally planted vulnerabilities — no deep tracing needed)

---

### Summary

Every route in this file contains a critical security flaw. The file is marked as a demo/dogfood snippet, but it should never be merged into a deployable codebase. All four findings match known true-positive signatures.

### Blocking

All four findings below block merge. Each has a concrete trigger via unauthenticated HTTP.

---

### Security audit

**Not clean.** Four high-severity, no-authentication-required vulnerabilities:

| # | CWE | Route | Impact |
|---|-----|-------|--------|
| 1 | CWE-89 (SQLi) | `/search` | Data exfiltration, table drop |
| 2 | CWE-502 (Deserialize) | `/load` | Remote code execution |
| 3 | CWE-78 (Cmd injection) | `/run` | Remote code execution |
| 4 | CWE-200 (Secrets) | `/secret` | Credential leakage |

---

### Key findings

1. **SQL Injection — `demo/insecure/app.py:18`**
   - **Trigger:** `GET /search?q='; DROP TABLE items; --`
   - `cur.execute(f"SELECT * FROM items WHERE name = '{q}'")` interpolates attacker-controlled `q` directly into SQL via f-string.
   - No parameterization, no escaping, no input validation.

2. **Insecure deserialization (RCE) — `demo/insecure/app.py:26`**
   - **Trigger:** `POST /load` with a crafted pickle payload (e.g. `cos\nsystem\n(S'id'\ntR.`)
   - `pickle.loads(data)` on raw untrusted request body. Pickle can execute arbitrary code during deserialization.
   - No signature verification, no safe loader, no allowlist.

3. **Command injection (RCE) — `demo/insecure/app.py:33`**
   - **Trigger:** `GET /run?cmd=cat /etc/passwd; rm -rf /`
   - `subprocess.check_output(cmd, shell=True)` passes attacker-controlled string to a shell. Any shell metacharacter (`;`, `|`, `&&`, backtick, `$()`) enables arbitrary command execution.
   - No input sanitization, no `shlex.quote`, no argument-list form.

4. **Secret exposure — `demo/insecure/app.py:38`**
   - **Trigger:** `GET /secret` — returns `OPENROUTER_API_KEY` from the environment in the response body.
   - No authentication gate. Anyone who can reach the endpoint gets the API key.
   - Key is likely billed; leakage enables credential stuffing and financial abuse.

### Multi-lens checklist (security pack)

| Lens | Verdict | Note |
|------|---------|------|
| Injection | **concern** | SQLi (line 18), CMDi (line 33) |
| AuthN / AuthZ | **concern** | No auth on any endpoint; `/secret` leaks credentials |
| Secrets / config | **concern** | `OPENROUTER_API_KEY` exposed (line 38) |
| Deserialize | **concern** | `pickle.loads` on untrusted input (line 26) |
| SSRF | n/a | No outbound requests in diff |
| XSS / CSRF | n/a | JSON responses only; no HTML rendering |
| Path traversal | n/a | No file-system path construction |
| Crypto misuse | n/a | No crypto operations |
| Supply chain | n/a | No new dependencies |

### Tests & risk

- **No tests present.** This is a demo file, not a production module, but if this were a real PR, absence of negative tests for all four security paths would be blocking.
- **Risk:** If deployed to any reachable host, all four endpoints provide unauthenticated attack surface: two direct RCE vectors, one full-database compromise, and one credential leak.

### What I checked

- Full file content (`demo/insecure/app.py`, 38 lines)
- All four routes matched against known true-positive signatures from F70 compound memory:
  - `sqli-search` → confirmed on line 18
  - `pickle-load` → confirmed on line 26
  - `cmdi-run` → confirmed on line 33
  - `secret-exposure` → confirmed on line 38
- No other files in scope — this is a single-file review

**— Torii Gate**

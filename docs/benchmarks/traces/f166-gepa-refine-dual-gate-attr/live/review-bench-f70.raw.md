All tool signals confirm the four TP signatures with hub boost. Here is the review:

---

**Verdict:** REQUEST CHANGES

**Score:** 5 / 100

**Review effort:** 1

---

### Summary

`demo/insecure/app.py` contains four critical, independently exploitable vulnerabilities across every exposed endpoint. All four match confirmed true-positive signatures with multi-tenant archival/hub corroboration (`sqli-search`, `pickle-load`, `cmdi-run`, `secret-exposure`). The file carries a `DO NOT deploy` docstring, but reviewed as-is the diff is production-unfit.

### Blocking

All four findings below are blocking. Each has a concrete trigger path and no mitigating control.

---

### Security audit

**No — 4 HIGH findings.**

| ID | CWE | Severity | Endpoint | Line |
|----|-----|----------|----------|------|
| SQL injection | CWE-89 | HIGH | `GET /search` | 18 |
| Insecure deserialization | CWE-502 | HIGH | `POST /load` | 26 |
| Command injection | CWE-78 | HIGH | `GET /run` | 33 |
| Secret exposure | CWE-200/CWE-798 | HIGH | `GET /secret` | 38 |

---

### Key findings

**1. SQL injection — `demo/insecure/app.py:18`**
- **Trigger:** `GET /search?q=' OR 1=1 --`
- User-supplied `q` query parameter flows via f-string directly into `cur.execute(f"SELECT * FROM items WHERE name = '{q}'")` with no parameterization, escaping, or allow-list.
- **Attacker scenario:** An unauthenticated remote attacker sends a crafted `q` value to read arbitrary tables, exfiltrate data, or drop the database (SQLite permits multiple statements in some configurations).

**2. Insecure deserialization — `demo/insecure/app.py:26`**
- **Trigger:** `POST /load` with a pickle payload crafted via `pickle.dumps(os.system("..."))`.
- `pickle.loads(request.data)` deserializes the raw untrusted POST body. Pickle can execute arbitrary code during deserialization — no signature verification, sandbox, or safe loader.
- **Attacker scenario:** An unauthenticated remote attacker sends a malicious pickle payload to achieve remote code execution on the server.

**3. Command injection — `demo/insecure/app.py:33`**
- **Trigger:** `GET /run?cmd=cat /etc/passwd; id`
- `subprocess.check_output(cmd, shell=True)` passes attacker-controlled `cmd` directly to a shell. No input sanitization, allow-listing, or `shlex.quote`.
- **Attacker scenario:** An unauthenticated remote attacker injects shell metacharacters to execute arbitrary OS commands with the privileges of the Flask process.

**4. Secret exposure — `demo/insecure/app.py:38`**
- **Trigger:** `GET /secret` returns `{"key": os.environ.get("OPENROUTER_API_KEY", "missing")}` — the live API key from the server environment is exposed in the response body to any caller.
- **Attacker scenario:** An unauthenticated remote attacker calls the unprotected endpoint to harvest the `OPENROUTER_API_KEY` and consume quota or pivot to other services.

---

### Multi-lens checklist

| Lens | Verdict | Note |
|------|---------|------|
| Injection (SQL/LDAP/OS) | **concern** | SQLi at line 18, command injection at line 33 |
| AuthZ / authN bypass | n/a | No auth surface present to bypass |
| Secrets / credentials | **concern** | `OPENROUTER_API_KEY` exposed at line 38 |
| XSS / CSRF | n/a | JSON responses only; no HTML rendering |
| SSRF | n/a | No outbound fetch from user input |
| Path traversal | n/a | No file-path input vectors |
| Unsafe deserialize | **concern** | `pickle.loads` on untrusted body at line 26 |
| Crypto misuse | n/a | No crypto operations in diff |
| Supply-chain / deps | ok | Standard-library-only imports |

---

### Tests & risk

- **No tests in diff.** The file is a standalone demo with no test coverage.
- Risk of deploying any of these four endpoints to a live network is immediate full compromise (RCE + data exfiltration + credential theft).

---

### What I checked

- Full file read with line numbers (`demo/insecure/app.py`, 38 lines).
- Memory search via `torii.py memory search` — all four TP signatures hit with scores 0.94–0.98.
- Hub archival search via `archival_memory_search.py auto` — all four themes reconsolidated with hub boost across 29 global tenants.
- Product doctor (`torii.py doctor`) — doctor_pass=true, no recovery gaps.
- Budget status — 1 extra re-prompt remaining, no exhaustion.
- Graph neighbor hop confirmed no supersede edges for these four themes.

No false-positive patterns exist in memory for this repo — all four findings are first-raise.

— **Torii Gate**

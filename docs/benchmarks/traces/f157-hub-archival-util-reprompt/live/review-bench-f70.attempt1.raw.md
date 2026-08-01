**Verdict:** REQUEST CHANGES
**Score:** 0/100 — four critical vulnerabilities; this code must never reach production.

---

### Summary
Every endpoint in `demo/insecure/app.py` contains a severe, independently exploitable vulnerability. The file is labelled as a demo, but that does not change the verdict — if merged, any of these paths creates a full compromise vector.

### Blocking
All four findings below are blocking. Each provides a concrete exploit path requiring no authentication or preconditions.

---

### Security audit

| Finding | CWE | Trigger | Impact |
|---|---|---|---|
| SQL injection | CWE-89 | `GET /search?q=...` | Full DB read/write |
| Unsafe deserialization | CWE-502 | `POST /load` with pickle payload | Remote code execution |
| Command injection | CWE-78 | `GET /run?cmd=...` | Remote code execution |
| Secret exposure | CWE-200 | `GET /secret` | API key leak |

---

### Key findings

1. **SQL Injection — `demo/insecure/app.py:18`**
   `cur.execute(f"SELECT * FROM items WHERE name = '{q}'")` interpolates raw query-string input into SQL via an f-string. An attacker can supply `q='; DROP TABLE items; --` or extract arbitrary data with UNION-based payloads. Use parameterized queries (`cur.execute("SELECT ... WHERE name = ?", (q,))`).

2. **Unsafe Deserialization — `demo/insecure/app.py:26`**
   `pickle.loads(data)` deserializes untrusted request body bytes. Pickle can execute arbitrary Python during deserialization (e.g., `__reduce__` gadgets). This yields full RCE. Replace with a safe serialization format (JSON, msgpack) or never deserialize untrusted pickle.

3. **Command Injection — `demo/insecure/app.py:33`**
   `subprocess.check_output(cmd, shell=True)` passes user-controlled `cmd` directly to a shell. `?cmd=cat /etc/passwd; rm -rf /` or backtick injection both work. Use `shell=False` with an argument list, and avoid passing raw user input to subprocess entirely.

4. **Secret Exposure — `demo/insecure/app.py:38`**
   `os.environ.get("OPENROUTER_API_KEY")` is returned verbatim in the HTTP response body. Any caller can retrieve the live API key with `GET /secret`. Never expose environment secrets through application endpoints.

---

### Tests & risk
- **No tests present.** All four endpoints lack input validation, authorization, and negative test coverage. This diff would pass a naive unit-test suite (it returns 200) while being trivially exploitable.
- **Risk:** critical. Unauthenticated RCE on two paths (`/load`, `/run`), data exfiltration on `/search`, credential theft on `/secret`.

---

### What I checked
- `demo/insecure/app.py` — all 38 lines reviewed
- All four endpoints (`/search`, `/load`, `/run`, `/secret`) traced end-to-end
- Matched against F70 true-positive signatures (sqli-search, pickle-load, cmdi-run, secret-exposure — all four hit)

---

**— Torii Gate**

**Verdict:** REQUEST CHANGES
**Score:** 5/100 — four critical, path-evidenced, easily triggerable vulnerabilities; every endpoint is a confirmed sink.
**Review effort:** 1/5 — 32-line single file with textbook vulnerabilities; all sinks obvious on first read.

### Summary
Every endpoint in `demo/insecure/app.py` exposes a distinct, independently triggerable remote-code-execution or data-exfiltration vulnerability. The file is intentionally insecure (self-described "DO NOT deploy"), but the gate treats all diffs equally: none of these should merge to a production branch without explicit suppression.

### Blocking
All four findings below are blocking.

---

### Security audit: **No** — four concerns

| # | Concern | CWE |
|---|---------|-----|
| 1 | SQL injection via f-string query interpolation | CWE-89 |
| 2 | Unsafe pickle deserialization from request body | CWE-502 |
| 3 | OS command injection via shell=True with raw query param | CWE-78 |
| 4 | API key returned verbatim to any caller | CWE-200 |

---

### Key findings

**1. SQL Injection — `/search` (CRITICAL)**
- **Path:** `demo/insecure/app.py:15`
- **Sink:** `cur.execute(f"SELECT * FROM items WHERE name = '{q}'")`
- **Source:** `q = request.args.get("q", "")` (line 13)
- **Attacker trigger:** `GET /search?q=' OR 1=1 --` enumerates all rows; `GET /search?q='; DROP TABLE items --` destroys data. The f-string places unsanitized user input directly into the SQL statement body with no parameterization.
- **Fix:** Use parameterized queries: `cur.execute("SELECT * FROM items WHERE name = ?", (q,))`

**2. Insecure Deserialization — `/load` (CRITICAL)**
- **Path:** `demo/insecure/app.py:21`
- **Sink:** `pickle.loads(data)`
- **Source:** `data = request.data` (line 20)
- **Attacker trigger:** `POST /load` with a crafted pickle payload (`cos\nsystem\n(S'rm -rf /'\ntR.`) achieves arbitrary code execution on the server. `pickle.loads` executes attacker-controlled bytecode during deserialization.
- **Fix:** Never deserialize untrusted pickle. Use a safe serialization format (JSON, MessagePack) or restrict with `pickle.Unpickler` + a strict `find_class` allowlist.

**3. Command Injection — `/run` (CRITICAL)**
- **Path:** `demo/insecure/app.py:27`
- **Sink:** `subprocess.check_output(cmd, shell=True)`
- **Source:** `cmd = request.args.get("cmd", "echo hi")` (line 26)
- **Attacker trigger:** `GET /run?cmd=cat /etc/passwd` or `GET /run?cmd=; rm -rf /` — the shell=True passes the raw string to `/bin/sh -c`, allowing command chaining, subshells, and redirection.
- **Fix:** Use `subprocess.check_output([cmd])` with shell=False, or better, avoid passing user input to subprocess entirely.

**4. Secret Exposure — `/secret` (HIGH)**
- **Path:** `demo/insecure/app.py:32`
- **Sink:** `return {"key": os.environ.get("OPENROUTER_API_KEY", "missing")}`
- **Attacker trigger:** Any unauthenticated `GET /secret` returns the live `OPENROUTER_API_KEY` (or "missing" if unset). If the env var is populated, the key is exfiltrated with zero authentication, zero rate-limiting, and zero audit trail.
- **Fix:** Remove the endpoint entirely. If the key is needed internally, access it only server-side; never serialize it into an HTTP response.

---

### Tests & risk
- **No tests present** in the reviewed diff. All four endpoints are untested.
- **Risk:** If this file is reachable in any deployment environment (dev, staging, CI), all four vulnerabilities are trivially exploitable without authentication.

---

### What I checked
- Full 32-line diff of `demo/insecure/app.py`
- All four `@app` route handlers: `/search`, `/load`, `/run`, `/secret`
- Source-to-sink taint for each endpoint (query param → SQL, request body → pickle, query param → shell, env var → response body)
- Archival memory search confirmed all four true-positive signatures (`sqli-search`, `pickle-load`, `cmdi-run`, `secret-exposure`) with file-glob matches
- No auth, no rate limiting, no input validation present on any endpoint

---

### Multi-lens checklist

| Lens | Status | Note |
|------|--------|------|
| Injection | **concern** | SQL injection (`/search`) + command injection (`/run`) — both CRITICAL |
| AuthN/AuthZ | **concern** | No auth on any endpoint; `/secret` exposes API key with no gate |
| Secrets | **concern** | `OPENROUTER_API_KEY` returned in plaintext HTTP response |
| Deserialization | **concern** | `pickle.loads` on untrusted request body — RCE |
| XSS/CSRF | n/a | No HTML rendering surface in diff |
| SSRF | n/a | No outbound URL fetch in diff |
| Path traversal | n/a | No filesystem path construction in diff |
| Crypto | n/a | No cryptographic operations in diff |
| Supply chain | ok | Standard library + Flask + sqlite3; no novel third-party deps |
| Fail-open | **concern** | `/secret` returns `"missing"` when key is unset — benign but confirms fail-open pattern; all other endpoints fail-open to exploitability |
| DoS | ok | No unbounded loops or resource exhaustion paths visible |
| Error handling | **concern** | `subprocess.check_output` raises `CalledProcessError` on non-zero exit — likely unhandled 500; `pickle.loads` raises on malformed input — also unhandled 500 |

---

**— Torii Gate**

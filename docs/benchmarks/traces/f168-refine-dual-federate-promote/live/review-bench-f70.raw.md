All tool checks confirm the four TP signatures at max confidence. Here is the review.

---

**Verdict:** REQUEST CHANGES
**Score:** 5/100

### Summary

This file is a deliberately insecure Flask demo containing four critical vulnerabilities on four separate endpoints — each independently would block merge. Zero mitigations, zero input validation, zero safe defaults. Not production-viable in any sense; the `"""DO NOT deploy"""` docstring is the only defense and it is not a control.

### Blocking

All four findings below are independently blocking. Each has a concrete, trivially exploitable trigger path.

### Security audit

**No.** Four confirmed criticals, no safe endpoints.

### Key findings

1.  **SQL Injection — `demo/insecure/app.py:16`**
    `cur.execute(f"SELECT * FROM items WHERE name = '{q}'")`
    CWE-89. User-controlled `q` (query param, line 13) interpolated via f-string directly into SQL. No parameterization.
    *Attacker trigger:* `GET /search?q=' UNION SELECT 1,2,3 --` exfiltrates arbitrary table data; `GET /search?q='; DROP TABLE items; --` destroys data.
    **Severity: CRITICAL.**

2.  **Insecure Deserialization — `demo/insecure/app.py:23`**
    `pickle.loads(data)` where `data = request.data` (line 22, raw POST body).
    CWE-502. Untrusted pickle input yields arbitrary code execution via `__reduce__` gadget chains.
    *Attacker trigger:* `POST /load` with a crafted pickle payload — attacker achieves RCE on the server process.
    **Severity: CRITICAL.**

3.  **Command Injection — `demo/insecure/app.py:28`**
    `subprocess.check_output(cmd, shell=True)` where `cmd = request.args.get("cmd", "echo hi")` (line 27).
    CWE-78. `shell=True` passes the string through `/bin/sh`, enabling shell metacharacter injection.
    *Attacker trigger:* `GET /run?cmd=cat /etc/passwd` reads files; `GET /run?cmd=; rm -rf /` (or reverse shell payload) achieves full host compromise.
    **Severity: CRITICAL.**

4.  **Secret Exposure — `demo/insecure/app.py:32`**
    `os.environ.get("OPENROUTER_API_KEY")` returned directly in the JSON response body.
    CWE-200 / CWE-798. Any unauthenticated caller retrieves the active API key.
    *Attacker trigger:* `GET /secret` returns `{"key": "sk-or-..."}` — key usable for billable API calls under the victim's account.
    **Severity: HIGH** (downgraded from critical only because the env var may be unset; when set, impact is credential theft + financial loss).

### Tests and risk

- No tests present for the file under review. Risk is maximum — every endpoint is exploitable via unauthenticated HTTP requests.
- Even if this is a demo/bench file never deployed, the presence of a secret-exposing endpoint creates risk of accidental deployment with a live key.

### Multi-lens checklist

| Lens | Verdict | Note |
|------|---------|------|
| Injection (SQL/NoSQL/OS) | **concern** | SQLi + CMDi both confirmed (lines 16, 28) |
| AuthZ / access control | **concern** | No auth on any endpoint; secret endpoint (line 32) exposes credentials to unauthenticated callers |
| Secrets / credential handling | **concern** | `OPENROUTER_API_KEY` exposed in plaintext response (line 32) |
| XSS / output encoding | n/a | JSON responses, no HTML rendering path |
| CSRF | n/a | No state-changing GET that would benefit (state changes already trivially accessible) |
| SSRF | n/a | No outbound requests from server |
| Path traversal | n/a | No file-path construction from user input |
| Unsafe deserialization | **concern** | `pickle.loads` on untrusted `request.data` (line 23) |
| Crypto misuse | n/a | No crypto operations |
| Supply-chain / dependency | n/a | Standard library + Flask + sqlite3 — no version-pinning concerns visible in this diff |
| Fail-open defaults | **concern** | All endpoints default to exposed; `shell=True` is opt-in dangerous |
| DoS / unbounded work | ok | No unbounded loops or resource exhaustion visible |

### What I checked

- Read full file (32 lines, 4 endpoints).
- Ran memory search (`torii.py memory`) — all four F70 TP signatures (`sqli-search`, `cmdi-run`, `pickle-load`, `secret-exposure`) matched with path globs targeting `demo/insecure/app.py` and scores 0.97–1.0.
- Ran hub archival auto-search — reconsolidated all four TP signatures at score 1.0; federation reconfirmed all four themes across 9 cross-tenant hits each.
- Ran `torii.py doctor` — all checks pass, no recovery gaps.
- No FP patterns to exclude; no prior dismissals on this file.

**— Torii Gate**

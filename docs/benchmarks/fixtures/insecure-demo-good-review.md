<!-- torii-review -->
# Torii Gate review — demo/insecure

**Verdict:** REQUEST CHANGES
**Score:** 2/10
**Confidence:** high

### Summary
Intentional insecure Flask demo: multiple critical injection and secrets issues in `demo/insecure/app.py`.

### Blocking
1. **SQL injection** in `demo/insecure/app.py` `/search` — `cur.execute(f"SELECT ... '{q}'")` interpolates user input (CWE-89). Trigger: `GET /search?q=' OR 1=1--`.
2. **Insecure deserialization** — `pickle.loads(request.data)` on `/load` (CWE-502). Trigger: POST crafted pickle RCE.
3. **Command injection** — `subprocess.check_output(cmd, shell=True)` on `/run` (CWE-78). Trigger: `GET /run?cmd=id`.
4. **Secrets exposure** — `/secret` returns `OPENROUTER_API_KEY` from the environment.

### Security audit
- SQL injection via f-string into sqlite execute.
- pickle.loads on untrusted body.
- shell=True command injection.
- API key leak endpoint.

### Key findings
- Path-evidenced SQLi, pickle, shell, secrets all in `demo/insecure/app.py`.

### Tests & risk
No tests; production deploy of this module would be catastrophic.

### What I checked
Full file `demo/insecure/app.py` via workspace tools.

## 🏴‍☠️ Torii Review — PR #demo-django-vuln

**Verdict:** REQUEST CHANGES
**Confidence:** high
**Score:** 26/100
**Review effort:** 4/5

### Summary
Synthetic Django/Flask-theme views in `demo/django-vuln-synthetic/views.py` introduce SSRF, path traversal, open redirect, SSTI, and secret exposure. Merge blocked.

### Multi-lens checklist
1. **security** — concern: SSRF, LFI, open redirect, SSTI, secrets
2. **correctness** — concern: redirect without allowlist
3. **api_contracts** — concern: public fetch endpoint
4. **tests** — concern: no negative tests
5. **concurrency** — n/a
6. **performance** — n/a
7. **maintainability** — ok

### Blocking
1. **SSRF** — `demo/django-vuln-synthetic/views.py` `urlopen(url)` on `request.args.get("url")` (CWE-918). Trigger: `?url=http://169.254.169.254/latest/meta-data/`.
2. **Path traversal** — `BASE / "files" / name` then `read_text` without resolving under root (CWE-22). Trigger: `?name=../../etc/passwd`.
3. **Open redirect** — `redirect(next_url)` with unvalidated `next` query (CWE-601). Trigger: `?next=https://evil.example/`.
4. **SSTI / template injection** — `render_template_string` with user `title` interpolated into template string (CWE-1336 / CWE-94). Trigger: `?title={{7*7}}`.
5. **Secrets exposure** — `/config` returns hardcoded/demo `SECRET_KEY` (`django-insecure-...`) and DEBUG=True (CWE-798).

### Key findings
- Source→sink: query.url → urlopen; query.name → file read; query.next → redirect; query.title → template; config endpoint leaks secret_key.
- Prefer URL allowlists, safe path join+resolve, redirect allowlist, static templates, secrets from env/KMS.

### Security audit
- Injection: **fail** (SSTI)
- SSRF/path: **fail**
- Secrets: **fail**
- Redirect: **fail**

### Residual risk
High if views are mounted publicly.

### Nits
None

### Suggested test plan
| Pri | Kind | Target | Scenario |
|-----|------|--------|----------|
| P0 | unit | fetch | block private ranges |
| P0 | unit | download | deny `..` |
| P0 | unit | go | only relative allowlist |
| P0 | unit | page | no user-controlled template |

### Tests & risk
- Relevant tests added/updated: no
- Risk: high
- Rollback: easy (demo only)

### What I checked
- `demo/django-vuln-synthetic/views.py` (fetch, download, go, page, config)

---
*Torii · public-eval django-vuln-synthetic good fixture*

## 🏴‍☠️ Torii Review — PR #demo-nodegoat

**Verdict:** REQUEST CHANGES
**Confidence:** high
**Score:** 30/100
**Review effort:** 4/5

### Summary
Synthetic NodeGoat-theme routes in `demo/nodegoat-synthetic/app.js` introduce NoSQL injection, path traversal, SSRF, and IDOR. Merge blocked until source→sink issues are fixed.

### Multi-lens checklist
1. **security** — concern: NoSQL inject, LFI, SSRF, IDOR
2. **correctness** — concern: authz fail-open on allocations
3. **api_contracts** — concern: public APIs without ownership
4. **tests** — concern: no negative tests
5. **concurrency** — n/a
6. **performance** — n/a
7. **maintainability** — ok

### Blocking
1. **NoSQL injection** — `demo/nodegoat-synthetic/app.js` builds Mongo-style `filter = { userName, password }` from `req.body` without type checks; operator injection via `"$gt"` (CWE-943). Trigger: `password: {"$gt":""}`.
2. **Path traversal** — `path.join(__dirname, "uploads", name)` + `fs.readFileSync` on `req.query.file` (CWE-22). Trigger: `?file=../../etc/passwd`.
3. **SSRF** — `http.get(url)` with `req.query.url` on `/api/stock` (CWE-918). Trigger: `?url=http://169.254.169.254/`.
4. **IDOR / broken access control** — `/api/allocations/:userId` returns any user's allocations without session ownership check (CWE-639).

### Key findings
- Source→sink: body password → find filter; query.file → readFileSync; query.url → http.get; params.userId → data without authz.
- Prefer typed password strings, path resolve under uploads root, URL allowlists, and session-bound userId.

### Security audit
- Injection: **fail** (NoSQL)
- Path/SSRF: **fail**
- Authz: **fail** (IDOR on allocations)

### Residual risk
High if routes are reachable.

### Nits
None

### Suggested test plan
| Pri | Kind | Target | Scenario |
|-----|------|--------|----------|
| P0 | unit | login | reject operator objects in password |
| P0 | unit | avatar | deny `..` segments |
| P0 | unit | stock | block link-local SSRF |
| P0 | unit | allocations | deny cross-user id |

### Tests & risk
- Relevant tests added/updated: no
- Coverage: missing negative tests
- Risk: high
- Rollback: easy (demo only)

### What I checked
- `demo/nodegoat-synthetic/app.js` (login, avatar, stock, allocations)

---
*Torii · public-eval nodegoat-synthetic good fixture*

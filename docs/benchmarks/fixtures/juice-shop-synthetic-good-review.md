## 🏴‍☠️ Torii Review — PR #demo-juice

**Verdict:** REQUEST CHANGES
**Confidence:** high
**Score:** 28/100
**Review effort:** 4/5

### Summary
Synthetic Juice Shop–theme routes introduce multiple high-severity injection and authz defects in `demo/juice-shop-synthetic/routes.js`. Merge blocked until source→sink issues are fixed or proven unreachable.

### Multi-lens checklist
1. **security** — concern: SQLi, XSS, CMDi, secrets, IDOR
2. **correctness** — concern: authz fail-open on basket
3. **api_contracts** — concern: public REST without ownership checks
4. **tests** — concern: no negative tests
5. **concurrency** — n/a
6. **performance** — n/a
7. **maintainability** — ok

### Blocking
1. **SQL injection** in product search — `demo/juice-shop-synthetic/routes.js` builds `SELECT ... LIKE '%${q}%'` from `req.query.q` (CWE-89). Trigger: `GET /rest/products/search?q='%20OR%201=1--`.
2. **Reflected XSS** — `demo/juice-shop-synthetic/routes.js` returns unsanitized `comment` HTML in `/api/Feedbacks` (CWE-79). Trigger: `?comment=<script>alert(1)</script>`.
3. **Command injection** — `child_process.exec(\`ping -c 1 ${host}\`)` on admin route (CWE-78). Trigger: `?host=127.0.0.1;id`.
4. **Hardcoded secrets** — `JWT_SECRET` and `INTERNAL_API_KEY` (`sk-demo-...`) in `demo/juice-shop-synthetic/routes.js` (CWE-798).
5. **IDOR / broken access control** — `/rest/basket/:id` loads any basket without ownership check (CWE-639). Trigger: enumerate `id=1..N` as another user.

### Key findings
- Source→sink: `req.query.q` → SQL template; `req.query.host` → `exec`; `req.query.comment` → HTML response.
- Prefer parameterized queries, output encoding, `execFile` without shell, secrets from env/KMS, and authz on basket ownership.

### Security audit
- Injection: **fail** (SQLi + XSS + CMDi)
- Secrets: **fail** (hardcoded JWT/API key)
- Authz: **fail** (IDOR on basket)

### Residual risk
High if any of these routes are reachable in a real deployment.

### Nits
None

### Suggested test plan
| Pri | Kind | Target | Scenario |
|-----|------|--------|----------|
| P0 | unit | `routes.js` search | reject SQLi payloads |
| P0 | unit | `routes.js` feedback | encode HTML |
| P0 | unit | basket | deny cross-user id |

### Tests & risk
- Relevant tests added/updated: no
- Coverage: missing negative tests for all five themes
- Risk: high — multiple RCE/injection/authz classes
- Rollback: easy (demo only)

### What I checked
- `demo/juice-shop-synthetic/routes.js` (search, feedback, admin ping, login secret, basket)
- `demo/juice-shop-synthetic/db-stub.js`

---
*Torii · F76 juice-shop-synthetic good fixture*

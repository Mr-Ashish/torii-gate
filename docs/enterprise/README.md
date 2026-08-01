# Torii enterprise light

**Dim 9 lift:** multi-tenant as a **product surface** (not only JSON under `memory/`).

| Doc | Audience |
|-----|----------|
| [ORG-ISOLATION.md](ORG-ISOLATION.md) | Platform / security eng — how orgs stay isolated |
| [PRIVACY.md](PRIVACY.md) | AppSec / compliance — what federation shares (and never shares) |
| [SURFACE.md](SURFACE.md) | Live inventory (generated) |

```bash
python3 scripts/enterprise_surface.py status
python3 scripts/enterprise_surface.py fixture
python3 scripts/enterprise_surface.py report
python3 scripts/torii.py enterprise -- status
```

**Buyer line:** *Cross-tenant learning without paths, snippets, or raw org IDs.*

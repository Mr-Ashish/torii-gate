# Showcase · OpenUI × Torii (Phase 1 fixture)

Deterministic conversion of the live Odoo PR #3 Torii review into **OpenUI Lang**.

| File | Role |
|------|------|
| `review.openui` | OpenUI Lang program for `@openuidev/react-lang` Renderer |
| Source review | `../e2e-odoo-pr3-opus5-agentic-loop/review.md` |

Regenerate:

```bash
python3 scripts/review-to-openui.py \
  --review docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/review.md \
  --usage docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/hermes-usage.json \
  --timings docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/timings.json \
  --title "Torii Review — Odoo PR #3" \
  -o docs/showcase/openui-torii/review.openui
```

Render in Phase 2 console: `ui/review-console/`.

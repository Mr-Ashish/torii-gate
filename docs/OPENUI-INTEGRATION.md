# Torii × OpenUI integration plan

**Status:** planned + phased implementation  
**OpenUI source (local clone):** `/tmp/openui` ← `https://github.com/thesysdev/openui`  
**Docs:** [openui.com](https://www.openui.com/) · packages under `@openuidev/*`

---

## 1. What OpenUI is (plain words)

OpenUI is **not** a dashboard framework. It is a **generative UI stack**:

```text
Your allowed components  →  system prompt for the LLM
LLM streams "OpenUI Lang"  →  compact structured UI language
Renderer (React/Vue/Svelte) →  live charts, tables, cards, forms
```

Key pieces (from upstream monorepo):

| Package | Role |
|---------|------|
| `@openuidev/lang-core` | Parse / prompt gen (framework-agnostic) |
| `@openuidev/react-lang` | React `Renderer`, `createLibrary`, `defineComponent` |
| `@openuidev/react-ui` | Prebuilt chat UI + `openuiChatLibrary` components |
| `@openuidev/react-headless` | Chat state + streaming adapters |
| `@openuidev/browser-bundle` | CDN/iframe no-build embed |
| `@openuidev/cli` | Scaffold apps, generate prompts |

Reference examples we mirror:

- `examples/fastapi-backend` — **Python backend + Vite React** (closest to Torii’s shell/Python world)
- `examples/openui-chat` — full `AgentInterface` chat
- `examples/openui-dashboard` — multi-surface dashboard patterns

**OpenUI Cloud** (Thesys managed) is optional later; v1 uses **open-source OpenUI only** (no `THESYS_API_KEY` required).

---

## 2. What Torii is today (UI surface)

Torii is a **CI control plane**. Human-facing outputs are mostly:

| Surface | Format today |
|---------|----------------|
| PR comment | Markdown contract (`Verdict`, `Score`, `Summary`, `Blocking`, …) |
| Commit status / reactions | GitHub API |
| Job summary | Markdown tables (cost F21/F29, memory F30) |
| Traces | `.torii-out/traces/` artifacts |
| Memory | `.torii/` slim pack |
| Modal | emerging run host (`modal_app/`) |

**Gap:** Reviews are **text walls on GitHub**. There is no interactive console for verdicts, findings, cost, memory health, or traces.

GitHub comments **cannot** render OpenUI Lang natively → interactive UI must live in a **hosted viewer** (link from comment optional later).

---

## 3. Product goal (Torii OpenUI)

Ship a **Torii Review Console** that:

1. Takes a Torii run (review Markdown + optional `timings.json` / `hermes-usage.json` / memory-health)  
2. Renders it as **interactive OpenUI** (verdict badge, score, findings table, cost card, steps)  
3. Later: trigger a review and stream progress  
4. Stays optional — core CLI/GHA/Modal pipeline unchanged  

```text
  Torii pipeline (scripts / GHA / Modal)
           │
           ▼
  review.md + meta JSON  ──converter──►  OpenUI Lang string
           │
           ▼
  Review Console (Vite/React + @openuidev/react-lang Renderer)
           │
           ▼
  Operator sees interactive review (not only Markdown)
```

---

## 4. Design decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Stack | **Vite + React** frontend + **Python converter** (stdlib) | Matches Torii (Python scripts); FastAPI example pattern |
| GenUI mode v1 | **Deterministic convert** Markdown→OpenUI Lang | No second LLM call; cheap; reproducible for CI fixtures |
| GenUI mode v2 (later) | Optional LLM polish with Torii component library prompt | Richer charts; needs OpenRouter |
| Component library | Custom **Torii library** on top of `@openuidev/react-ui` primitives | Domain language: Verdict, Finding, Cost, TraceStage |
| Hosting | Local `ui/` in Torii repo first; Modal static later | Keep monorepo simple |
| GitHub | Optional “Open interactive review” link in comment | Phase 4+ |
| OpenUI Cloud | Out of scope v1 | Avoid Thesys key dependency |

### Torii → OpenUI component map (v1)

| Review field | OpenUI presentation |
|--------------|---------------------|
| Verdict | Tag / Callout (color by APPROVE / REQUEST CHANGES / COMMENT) |
| Score | Card + metric text |
| Summary | Markdown / TextContent |
| Blocking | Table or ListBlock of findings |
| Key findings / suggestions | Table rows (severity, path, note) |
| Cost / usage (F21/F29) | Card (model, $, tokens, budget status) |
| Memory health (F30) | Card (source, local publish, hub) |
| Trace stages | Steps component |
| Truncation banner (F27) | Callout warning |

---

## 5. Phased implementation

### Phase 0 — Research & plan ✅

- Clone OpenUI to `/tmp/openui`
- Document packages, examples, Torii mapping
- This document

**Verify:** plan reviewed; clone present; mapping table complete.

### Phase 1 — Converter (Python, no UI server)

- `scripts/review-to-openui.py` — parse Torii Gate review Markdown (+ optional JSON sidecars) → OpenUI Lang text  
- Fixture under `docs/showcase/openui-torii/` from a sample review  
- Unit tests  

**Verify:** `pytest` + CLI produces valid-looking OpenUI Lang; no network.

### Phase 2 — Review Console shell (static)

- `ui/review-console/` Vite + React app  
- `@openuidev/react-lang` + `@openuidev/react-ui`  
- Load fixture OpenUI Lang file and render with `<Renderer />`  
- Torii-themed layout (read-only)  

**Verify:** `npm run build` succeeds; local `npm run dev` shows fixture review UI.

### Phase 3 — Wire real run artifacts

- API or file picker: load `review-*.md` + `timings.json` + `hermes-usage.json` + `memory-health.env`  
- Optional: serve from FastAPI `ui/api` or Modal endpoint  
- “Paste review Markdown” mode for dogfood  

**Verify:** load e2e showcase review (Odoo PR3 package) into console.

### Phase 4 — Trigger + stream (optional control plane)

- Button “Review PR” → call Modal `review_pr` or local `review-local.sh`  
- Stream status / final OpenUI  
- Deep-link from PR comment  

**Verify:** end-to-end on `Mr-Ashish/odoo` PR (cheap model).

### Phase 5 — Docs & packaging

- README / ARCHITECTURE / USAGE / OPERATIONS / MODAL updated  
- Install note for console  
- Showcase screenshots / fixture README  

**Verify:** docs cross-link; `docs/OPENUI-INTEGRATION.md` status = shipped phases marked.

---

## 6. Non-goals (v1)

- Replacing GitHub PR comment Markdown entirely  
- OpenUI Cloud / Thesys billing  
- Full agentic chat copilot rewriting SOUL  
- Mobile React Native console  

---

## 7. Repo layout (target)

```text
pr-review-agent/
  scripts/review-to-openui.py      # Phase 1
  ui/review-console/               # Phase 2+
    package.json
    src/
      App.tsx
      library.tsx                  # Torii component library
      fixtures/
  docs/OPENUI-INTEGRATION.md       # this plan
  docs/showcase/openui-torii/      # fixtures + sample openui lang
  tests/test_review_to_openui.py
```

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| OpenUI Lang schema drift | Pin `@openuidev/*` versions; fixture tests |
| Monorepo Odoo UI too heavy | Console only views **review artifacts**, not full Odoo |
| Double LLM cost | Phase 1 converter is deterministic (no LLM) |
| GitHub can’t render OpenUI | Hosted console + link |

---

## 9. Phase status tracker

| Phase | Status |
|-------|--------|
| 0 Research & plan | **done** |
| 1 Converter + tests + fixture | **done** (`scripts/review-to-openui.py`, showcase fixture) |
| 2 Review console shell | **superseded** by full **Run Console** (Impeccable Operate / kinpaku) |
| 2b Full run UI | **done** — PR · result · findings · diff · trace · loop · cost · memory · artifacts |
| 3 Real artifacts | **done** (`pack-run-for-ui.py` → `run-bundle.json`, Load bundle) |
| 3b Auto-pack every run (F31) | **done** — orchestrator soft-writes `.torii-out/run-bundle.json` (+ trace copy); Modal returns `run_bundle` |
| 4 Trigger from console (F32) | **done** — Run tab + `trigger-review.sh` + Modal bit4 webhook/spawn (no in-browser Hermes) |
| 4b Deep-link from PR comment (F35) | **done** — `ops_footer.py` Actions run + run-bundle tip (+ optional `TORII_CONSOLE_URL`) |
| 4c Stream progress | pending (live status stream while review runs) |
| 4d Ops signals in console (F40) | **done** — pack `signals` + Overview chips (timeout/path-skip/budget/truncation) |
| 5 Docs complete | **done** for Phases 0–4b + F31/F32/F35/F40 |

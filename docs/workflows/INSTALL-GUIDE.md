# Torii Gate — install guide (F79 workflows-as-code)

Generated: `2026-08-01T02:21:39Z` · readiness **L3** (100.0%)

## One-liner

Torii is the **security merge authority** for every PR: maker agent + checker panel + compound memory.

## Install (target repo)

```bash
# from torii-gate checkout
./scripts/install-torii.sh /path/to/your-app
# or hub-managed thin caller:
./scripts/install-torii.sh --caller /path/to/your-app
```

### Next steps

1. Commit installed workflows + agent/scripts; push default branch.
2. Secret: `OPENROUTER_API_KEY` (and optional `TORII_HUB_TOKEN`).
3. Optional vars: `TORII_MODEL=deepseek/deepseek-v4-pro`, `TORII_SECOND_CRITIC=1`, `TORII_SCOPED_MEMORY=1`.
4. Branch protection: require status context **`torii/gate`**.
5. On a PR: `@torii review this pr`

## Pipeline (workflows-as-code)

```text
  [pre] preload_memory → scripts/preload-hub-memory.sh (soft)
  [pre] assemble → scripts/assemble-context.sh (hard)
  [maker] hermes → scripts/run-hermes-review.sh (hard)
  [post] distill → scripts/distill-memory.sh (soft)
  [post] fp_resolve_update → scripts/fp_resolve_memory.py (soft)
  [post] save_trace → scripts/save-trace.sh (soft)
  [checker] traj_fitness → scripts/trajectory_fitness.py (soft)
  [checker] second_agent_critic → scripts/second_agent_critic.py (soft)
  [memory] evolve_ingest → scripts/self_evolve.py (soft)
  [memory] fitness_gate_evolve → scripts/fitness_gate_evolve.py (soft)
  [memory] skill_auto_adopt → scripts/skill_auto_adopt.py (soft)
  [checker] skill_router_score → scripts/skill_router.py (soft)
  [memory] skill_attribution_cycle → scripts/skill_attribution.py (soft)
  [memory] skill_fitness → scripts/skill_fitness.py (soft)
  [memory] skill_theme_promote → scripts/skill_dual_rollout.py (soft)
  [memory] federated_hub → scripts/federated_hub_ingest.py (soft)
  [publish] publish_local → scripts/publish-run-local.sh (soft)
  [publish] publish_hub → scripts/publish-run-to-hub.sh (soft)
  [publish] pack_ui_bundle → scripts/pack-run-for-ui.py (soft)
  [publish] post_comment → scripts/post-review-comment.sh (hard)
```

Validate anytime:

```bash
python3 scripts/workflow_as_code.py validate
python3 scripts/workflow_as_code.py status
./scripts/smoke-torii-gate.sh
```

## Capability matrix (what you get)

| Feature | Capability | Script |
|---------|------------|--------|
| F22 | Map verdict → torii/gate merge signal | `scripts/torii_gate_status.py` (yes) |
| F64 | Durable FP rules so false positives die twice | `scripts/fp_resolve_memory.py` (yes) |
| F70 | Labeled vuln bench + dual-pass critic + TP signatures | `scripts/bench_security_gate.py` (yes) |
| F71 | Deterministic source→sink prefilter | `scripts/taint_prefilter.py` (yes) |
| F72 | Full-chain maker/checker revalidation | `scripts/chain_revalidate.py` (yes) |
| F73 | Multi-dim fitness + paper-safe trace vault | `scripts/trajectory_fitness.py` (yes) |
| F74 | Fitness-gated skill evolution | `scripts/fitness_gate_evolve.py` (yes) |
| F75 | Mem0-style scoped TP/FP recall | `scripts/scoped_memory_recall.py` (yes) |
| F76 | Multi-corpus PY+JS labeled benches | `scripts/bench_corpus.py` (yes) |
| F77 | Cross-tenant privacy-safe federated signals | `scripts/federated_hub_ingest.py` (yes) |
| F78 | Multi-checker second-agent critic panel | `scripts/second_agent_critic.py` (yes) |
| F79 | Declarative gate workflow validate/plan/install-guide | `scripts/workflow_as_code.py` (yes) |
| F80 | Bootstrap Modal secrets torii-* from .env for live e2e | `scripts/modal_secrets_bootstrap.py` (yes) |
| F81 | Optional OpenRouter LLM checker atop F78 panel | `scripts/llm_critic.py` (yes) |
| F82 | Safe auto-adopt of validated F74 skills with regression gates | `scripts/skill_auto_adopt.py` (yes) |
| F87 | Dual-rollout contribution_pp>0 required before skill adopt (gate) | `scripts/skill_auto_adopt.py` (yes) |
| F88 | Per-skill LOO attribution; reject free-riders before adopt | `scripts/skill_attribution.py` (yes) |
| F89 | Attribution ledger ranks inject; free-riders index-only | `scripts/skill_router.py` (yes) |
| F91 | Skill compound loop readiness scorecard L0–L3 | `scripts/skill_loop_status.py` (yes) |
| F83 | Paper-ready aggregate metrics from redacted trace vault | `scripts/eval_trace_report.py` (yes) |
| F84 | Progressive skill disclosure by path themes + post-run hit scoring | `scripts/skill_router.py` (yes) |
| F85 | Skill hit-rate ledger demotes zombies and federates skill themes | `scripts/skill_fitness.py` (yes) |
| F86 | Dual-rollout skill contribution delta + multi-tenant skill promote | `scripts/skill_dual_rollout.py` (yes) |

## Mental model

- **Maker** — Hermes agent writes the security review.
- **Checker** — F78 multi-checker panel (path/chain/fitness/memory) demotes weak APPROVE.
- **Memory** — FP rules, TP signatures, scoped recall, federated hub themes compound.
- **Skill loop** — `route → hit → fitness → dual → attr → inject` (skills that do not contribute do not re-inflate prompts).
- **Gate** — `torii/gate` commit status is the merge signal.

## Skill compound loop readiness (F91)

**Loop:** `route → hit → fitness → dual → attr → inject`  ·  **Level:** L3  ·  **100.0%**

Skills that do not contribute do not ship in the next prompt.

| Stage | Feature | Script | Pack | OK |
|-------|---------|--------|:----:|:--:|
| route | F84 | `skill_router.py` | ✓ | ✓ |
| hit | F84 | `skill_router.py` | ✓ | ✓ |
| fitness | F85 | `skill_fitness.py` | ✓ | ✓ |
| dual | F86 | `skill_dual_rollout.py` | ✓ | ✓ |
| attr | F88 | `skill_attribution.py` | ✓ | ✓ |
| inject | F89 | `skill_router.py` | ✓ | ✓ |
| adopt_gate | F87 | `skill_auto_adopt.py` | ✓ | ✓ |

- Active skills: **5** (skill-f74-exploit-scenario, skill-f74-prefer-chain-json, skill-preserve-deep-tools, skill-soft-tool-nudge, skill-tool-depth-hunks)
- Wiring (assemble/run): **ok**
- Deep fixtures: **skipped/fail**
- Ready: **True**

Deep skill-loop proof: `python3 scripts/skill_loop_status.py fixture`

## Offline proof (no API key)

```bash
./scripts/smoke-torii-gate.sh
python3 scripts/bench_corpus.py all
python3 scripts/second_agent_critic.py fixture
python3 scripts/skill_loop_status.py scorecard
```


#!/usr/bin/env python3
"""F110: Unified Torii product CLI front door (loop-eng style umbrella).

Research / product drivers:
  - Loop Engineering `@cobusgreyling/loop`: one binary, pass-through to tools,
    doctor/status for day-2 habit — old scripts stay supported.
  - Torii F103: memory front door; product still has many peer entrypoints
    (gate status, skill loop, re-prompt budget, smoke).
  - Hermes agents invent paths; one product CLI is the discoverable surface.

Product thesis:
  Highest ROI packaging+agentic slice: **python3 scripts/torii.py** as thin
  umbrella over memory / gate / budget / skill-loop / memory-loop with help,
  status, doctor.

Usage:
  python3 scripts/torii.py help
  python3 scripts/torii.py status
  python3 scripts/torii.py doctor
  python3 scripts/torii.py scorecard
  python3 scripts/torii.py memory -- help
  python3 scripts/torii.py memory -- search -- -q "sql injection"
  python3 scripts/torii.py memory -- doctor
  python3 scripts/torii.py gate -- --review review.md
  python3 scripts/torii.py budget -- status
  python3 scripts/torii.py skill-loop -- scorecard --shallow
  python3 scripts/torii.py memory-loop -- scorecard --shallow
  python3 scripts/torii.py golden-path -- fixture
  python3 scripts/torii.py golden-path -- report

Env:
  TORII_ROOT
  TORII_CLI   1 (default) | 0
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F110"
SCHEMA = 1
MARKER = "<!-- torii-f110-product-cli -->"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

# Tier for cognitive-load collapse (HELP_CLI_COLLAPSE):
#   day1     — install → first signal (buyer must see first)
#   day2     — quieter / cost / enterprise habit
#   advanced — engineers / research (still one CLI, not front-door)
# top-level group → script
GROUPS: dict[str, dict[str, Any]] = {
    "memory": {
        "script": "torii_memory.py",
        "help": "Compound memory (FP die twice · path-evidenced TP)",
        "tier": "advanced",
        "examples": [
            "memory -- help",
            "memory -- doctor",
            'memory -- search -- -q "sql injection"',
            "memory -- compound -- fixture",
        ],
    },
    "gate": {
        "script": "torii_gate_status.py",
        "help": "Map review verdict → CI gate / merge policy",
        "tier": "day1",
        "examples": ["gate -- --review review.md", "gate -- --help"],
    },
    "budget": {
        "script": "reprompt_budget.py",
        "help": "Shared soft re-prompt budget (advanced recovery)",
        "tier": "advanced",
        "examples": ["budget -- status", "budget -- fixture"],
    },
    "skill-loop": {
        "script": "skill_loop_status.py",
        "help": "Skill compound loop readiness (L0–L3)",
        "tier": "advanced",
        "examples": ["skill-loop -- scorecard --shallow", "skill-loop -- fixture"],
    },
    "memory-loop": {
        "script": "memory_loop_status.py",
        "help": "Memory compound loop readiness (L0–L3)",
        "tier": "advanced",
        "examples": ["memory-loop -- scorecard --shallow", "memory-loop -- fixture"],
    },
    "smoke": {
        "script": "smoke-torii-gate.sh",
        "help": "Offline smoke (no API key)",
        "tier": "day1",
        "examples": ["smoke"],
        "shell": True,
    },
    "workflow": {
        "script": "workflow_as_code.py",
        "help": "Workflows-as-code validate + scorecard",
        "tier": "advanced",
        "examples": [
            "workflow -- scorecard",
            "workflow -- validate",
            "workflow -- fixture",
        ],
    },
    "golden-path": {
        "script": "golden_path_metrics.py",
        "help": "Install → torii/gate → dogfood metrics",
        "tier": "day1",
        "examples": [
            "golden-path -- fixture",
            "golden-path -- status",
            "golden-path -- report",
        ],
    },
    "buyer": {
        "script": "buyer_narrative_check.py",
        "help": "Buyer narrative checks (one diagram, hide research IDs)",
        "tier": "advanced",
        "examples": [
            "buyer -- fixture",
            "buyer -- status",
            "buyer -- report",
        ],
    },
    "public-eval": {
        "script": "public_eval.py",
        "help": "Public labeled eval + cost/PR honesty",
        "tier": "day2",
        "examples": [
            "public-eval -- fixture",
            "public-eval -- report",
            "public-eval -- status",
        ],
    },
    "install-ux": {
        "script": "install_ux_check.py",
        "help": "Install UX surface checks (5-min path)",
        "tier": "advanced",
        "examples": [
            "install-ux -- fixture",
            "install-ux -- report",
        ],
    },
    "ops": {
        "script": "ops_dashboard.py",
        "help": "Ops: fail-closed defaults · cost/PR · smoke",
        "tier": "day2",
        "examples": [
            "ops -- fixture",
            "ops -- report --smoke",
            "ops -- status",
        ],
    },
    "enterprise": {
        "script": "enterprise_surface.py",
        "help": "Enterprise light: org isolation + federation privacy",
        "tier": "day2",
        "examples": [
            "enterprise -- status",
            "enterprise -- fixture",
            "enterprise -- report",
        ],
    },
    "federation": {
        "script": "federated_hub_ingest.py",
        "help": "Privacy-safe multi-tenant hub signals (themes only)",
        "tier": "advanced",
        "examples": [
            "federation -- status",
            "federation -- fixture",
            "federation -- promote",
        ],
    },
    "self-evolve": {
        "script": "self_evolve.py",
        "help": "Self-evolution: dual-gated skill adopt (not free-form drift)",
        "tier": "day2",
        "examples": [
            "self-evolve -- status",
            "self-evolve -- resolve-productized",
            "self-evolve -- fixture",
            "self-evolve -- propose-scorecard",
        ],
    },
    "commercial": {
        "script": "commercial_scorecard.py",
        "help": "Commercial rollup (surfaces + cost honesty)",
        "tier": "day2",
        "examples": [
            "commercial -- fixture",
            "commercial -- report",
            "commercial -- status",
        ],
    },
    "certificate": {
        "script": "gate_certificate.py",
        "help": "Merge-authority certificate (reason codes + path evidence)",
        "tier": "day2",
        "examples": [
            "certificate -- fixture",
            "certificate -- emit -- --review docs/benchmarks/fixtures/insecure-demo-good-review.md",
            "certificate -- report",
        ],
    },
    "quieter": {
        "script": "quieter_over_time.py",
        "help": "Quieter-over-time chart (customer .torii/runs vault)",
        "tier": "day2",
        "examples": [
            "quieter -- bootstrap",
            "quieter -- status",
            "quieter -- report",
            "quieter -- fixture",
        ],
    },
    "tool-use": {
        "script": "tool_use_quality.py",
        "help": "Agent tool-use quality (tools-as-code)",
        "tier": "day2",
        "examples": [
            "tool-use -- fixture",
            "tool-use -- status",
            "tool-use -- report",
        ],
    },
    "pilot": {
        "script": "pilot_surface.py",
        "help": "Design partner / paid pilot path + measured readiness",
        "tier": "day2",
        "examples": [
            "pilot -- status",
            "pilot -- readiness",
            "pilot -- fixture",
            "pilot -- report",
        ],
    },
    "diff": {
        "script": "diff_vs_sast.py",
        "help": "Torii vs SAST vs AI review (buyer differentiation)",
        "tier": "day2",
        "examples": [
            "diff -- status",
            "diff -- fixture",
            "diff -- report",
        ],
    },
}

_TIER_ORDER = ("day1", "day2", "advanced")
_TIER_LABELS = {
    "day1": "Day-1 — install → first signal",
    "day2": "Day-2 — quieter · cost · enterprise · pilot · self-evolve",
    "advanced": "Advanced — engineers (still one CLI)",
}


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_CLI") or "1").strip().lower()
    return raw not in _FALSEY


def _scripts_dir(root: Path | None = None) -> Path:
    return (root or _root()) / "scripts"


def help_payload() -> dict[str, Any]:
    groups = []
    tiers: dict[str, list[str]] = {t: [] for t in _TIER_ORDER}
    for name, meta in GROUPS.items():
        tier = str(meta.get("tier") or "advanced")
        if tier not in tiers:
            tier = "advanced"
        groups.append(
            {
                "group": name,
                "script": meta["script"],
                "help": meta["help"],
                "tier": tier,
                "examples": meta.get("examples") or [],
            }
        )
        tiers[tier].append(name)
    day1_n = len(tiers.get("day1") or [])
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "entrypoint": "python3 scripts/torii.py",
        "one_liner": (
            "One product front door for Torii Gate — Day-1 install path first; "
            "Day-2 quieter/cost/enterprise/pilot/self-evolve; Advanced for engineers."
        ),
        "usage": "python3 scripts/torii.py <group|help|status|doctor> [-- <args>]",
        "groups": groups,
        "tiers": tiers,
        "day1_groups_n": day1_n,
        "help_collapse_ok": day1_n <= 6 and day1_n >= 2 and "gate" in (tiers.get("day1") or []),
        "builtins": ["help", "status", "doctor", "scorecard", "inject-hint"],
        "scored_at": _now(),
    }


def render_help_text() -> str:
    p = help_payload()
    by_tier: dict[str, list[dict[str, Any]]] = {t: [] for t in _TIER_ORDER}
    for g in p["groups"]:
        t = str(g.get("tier") or "advanced")
        if t not in by_tier:
            t = "advanced"
        by_tier[t].append(g)

    lines = [
        "# Torii product CLI",
        "",
        p["one_liner"],
        "",
        f"Usage: `{p['usage']}`",
        "",
        "Builtins (always): `help` · `status --text` · `doctor` · `scorecard`",
        "",
        "Install (5 minutes): `docs/INSTALL.md` · `./scripts/install-torii.sh [--minimal] DEST`",
        "",
    ]
    for tier in _TIER_ORDER:
        label = _TIER_LABELS.get(tier, tier)
        lines.append(f"## {label}")
        lines.append("")
        if tier == "day2":
            # Cognitive collapse: primary table + secondary one-liner
            primary = [g for g in (by_tier.get(tier) or []) if g["group"] in _DAY2_PRIMARY]
            secondary = [
                g for g in (by_tier.get(tier) or []) if g["group"] not in _DAY2_PRIMARY
            ]
            # preserve declared primary order
            primary_sorted = []
            by_name = {g["group"]: g for g in primary}
            for name in _DAY2_PRIMARY:
                if name in by_name:
                    primary_sorted.append(by_name[name])
            for g in primary:
                if g not in primary_sorted:
                    primary_sorted.append(g)
            lines.append("| Group | Purpose |")
            lines.append("|-------|---------|")
            for g in primary_sorted:
                lines.append(f"| `{g['group']}` | {g['help']} |")
            if secondary:
                also = " · ".join(f"`{g['group']}`" for g in secondary)
                lines.append("")
                lines.append(f"Also day-2 (same CLI): {also}")
            lines.append("")
        else:
            lines.append("| Group | Purpose |")
            lines.append("|-------|---------|")
            for g in by_tier.get(tier) or []:
                lines.append(f"| `{g['group']}` | {g['help']} |")
            lines.append("")

    lines += [
        "Day-1 only needs: `status --text` · `doctor` · `smoke` · `golden-path -- status` · require **`torii/gate`**.",
        "Day-2 one screen is **four beats** (merge · cost/trust · org · growth) — `status --verbose` for full surface list.",
        "Advanced groups stay on the same CLI — they are not the install path.",
        "",
        "Examples:",
        "```bash",
        "python3 scripts/torii.py help",
        "python3 scripts/torii.py status --text   # day-2 four beats",
        "python3 scripts/torii.py doctor",
        "python3 scripts/torii.py golden-path -- status",
        "python3 scripts/torii.py quieter -- status",
        "python3 scripts/torii.py ops -- status",
        "```",
        "",
    ]
    return "\n".join(lines)


def render_inject_hint() -> str:
    return (
        f"{MARKER}\n"
        "## Torii product CLI (umbrella front door)\n\n"
        "Prefer the **product** entrypoint — Day-1 first, Advanced only when needed:\n\n"
        "```bash\n"
        "python3 scripts/torii.py help\n"
        "python3 scripts/torii.py status --text\n"
        "python3 scripts/torii.py doctor\n"
        "python3 scripts/torii.py golden-path -- status\n"
        "python3 scripts/torii.py quieter -- status\n"
        "python3 scripts/torii.py memory -- search -- -q \"theme keywords\"\n"
        "```\n\n"
        "Still require path:line evidence to block. Peer scripts remain for agents that pin them.\n"
        "<!-- /torii-f110-product-cli -->\n"
    )


def run_group(group: str, passthrough: list[str], *, root: Path | None = None) -> int:
    root = root or _root()
    meta = GROUPS.get(group)
    if not meta:
        print(json.dumps({"error": "unknown_group", "group": group, "feature": FEATURE}), file=sys.stderr)
        return 2
    script = _scripts_dir(root) / meta["script"]
    if not script.is_file():
        print(
            json.dumps({"error": "missing_script", "script": str(script), "feature": FEATURE}),
            file=sys.stderr,
        )
        return 2
    env = {**os.environ, "TORII_ROOT": str(root)}
    if meta.get("shell"):
        args = ["bash", str(script), *passthrough]
    else:
        args = [sys.executable, str(script), *passthrough]
        if not passthrough:
            # default help for python tools that support it
            if group == "gate":
                args = [sys.executable, str(script), "--help"]
            elif group == "budget":
                args = [sys.executable, str(script), "status"]
            elif group in ("skill-loop", "memory-loop"):
                args = [sys.executable, str(script), "scorecard", "--shallow"]
            elif group == "memory":
                args = [sys.executable, str(script), "help"]
    try:
        r = subprocess.run(args, cwd=str(root), env=env)
        return int(r.returncode)
    except OSError as exc:
        print(json.dumps({"error": str(exc), "feature": FEATURE}), file=sys.stderr)
        return 2


def _soft_script_json(
    root: Path, script: str, argv: list[str], *, timeout: int = 45
) -> dict[str, Any] | None:
    """Best-effort peer script JSON (never fails status/doctor)."""
    path = _scripts_dir(root) / script
    if not path.is_file():
        return None
    try:
        r = subprocess.run(
            [sys.executable, str(path), *argv],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "TORII_ROOT": str(root)},
        )
        if r.returncode != 0 or not (r.stdout or "").strip():
            return None
        data = json.loads(r.stdout)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def build_status_payload(root: Path | None = None) -> dict[str, Any]:
    """Day-2 product status payload (machine + buyer day-2 panel fields)."""
    root = root or _root()
    present = {}
    for name, meta in GROUPS.items():
        present[name] = (_scripts_dir(root) / meta["script"]).is_file()
    extras: dict[str, Any] = {}
    ml = _soft_script_json(
        root, "memory_loop_status.py", ["scorecard", "--shallow"], timeout=60
    )
    if ml:
        extras["memory_loop"] = {
            "level": ml.get("level"),
            "ready": ml.get("ready"),
            "stages_ok": ml.get("stages_ok"),
        }
    budget = _soft_script_json(root, "reprompt_budget.py", ["status"], timeout=30)
    if budget:
        st = budget.get("state") if isinstance(budget.get("state"), dict) else {}
        extras["reprompt_budget"] = {
            "enabled": budget.get("enabled"),
            "remaining": st.get("remaining"),
            "max_extra": st.get("max_extra") or budget.get("env_max_extra"),
        }

    # Buyer day-2 panel (soft — never blocks status)
    day2: dict[str, Any] = {}
    commercial = _soft_script_json(
        root, "commercial_scorecard.py", ["status"], timeout=60
    )
    if commercial:
        day2["commercial_ok"] = commercial.get("commercial_ok")
        day2["overall_est"] = commercial.get("overall_est")
        day2["cost_honesty_ok"] = commercial.get("cost_honesty_ok")
        day2["cost_p50_usd"] = commercial.get("cost_p50_usd")
        day2["surfaces_pass"] = commercial.get("surfaces_pass")
    cert = _soft_script_json(root, "gate_certificate.py", ["status"], timeout=45)
    if cert:
        day2["cert_vault_n"] = cert.get("vault_n")
        day2["cert_vault_cost_p50"] = cert.get("vault_cost_p50_usd")
        day2["cert_vault_ok"] = cert.get("vault_ok")
    quieter = _soft_script_json(root, "quieter_over_time.py", ["status"], timeout=45)
    if quieter:
        day2["quieter_ok"] = quieter.get("quieter_ok")
        day2["getting_quieter"] = quieter.get("getting_quieter")
        day2["quiet_score_all"] = quieter.get("quiet_score_all")
        day2["quieter_local_runs_n"] = quieter.get("local_runs_n")
        day2["quieter_local_demo_n"] = quieter.get("local_demo_n")
        day2["quieter_local_organic_n"] = quieter.get("local_organic_n")
        day2["quieter_bootstrap_needed"] = quieter.get("bootstrap_needed")
        day2["quieter_organic_needed"] = quieter.get("organic_needed")
        day2["quieter_trajectory_source"] = quieter.get("trajectory_source")
    ops = _soft_script_json(root, "ops_dashboard.py", ["status"], timeout=45)
    if ops:
        day2["ops_ok"] = ops.get("ops_ok")
        day2["cost_ok"] = ops.get("cost_ok")
        day2["fail_closed_safe_defaults"] = ops.get("fail_closed_safe_defaults")
        day2["smoke_ci"] = ops.get("smoke_ci")
        if day2.get("cost_p50_usd") is None:
            day2["cost_p50_usd"] = ops.get("cost_p50")
    ent = _soft_script_json(root, "enterprise_surface.py", ["status"], timeout=45)
    if ent:
        day2["enterprise_ok"] = ent.get("enterprise_ok")
        day2["tenant_n"] = ent.get("tenant_n")
        day2["isolation_ok"] = ent.get("isolation_ok")
        day2["federation_privacy_ok"] = ent.get("federation_privacy_ok") or ent.get(
            "federation_all_ok"
        )
        day2["privacy_themes_only"] = ent.get("privacy_themes_only")
    # Federation multi-tenant heat (themes only — privacy-safe hub)
    fed = _soft_script_json(root, "federated_hub_ingest.py", ["status"], timeout=30)
    if fed:
        day2["fed_multi_tenant_themes"] = fed.get("multi_tenant_themes")
        day2["fed_signal_count"] = fed.get("count")
    # Tool-use quality (tools-as-code JTBD)
    tools = _soft_script_json(root, "tool_use_quality.py", ["status"], timeout=45)
    if tools:
        day2["tool_use_ok"] = (
            tools.get("tool_use_ok")
            or tools.get("tool_use_quality_ok")
            or tools.get("quality_ok")
        )
        day2["tool_use_rate"] = tools.get("tool_use_rate")
        day2["tool_use_n"] = (
            tools.get("measured_n") or tools.get("n") or tools.get("dogfood_n")
        )
        day2["zero_tool_rate"] = tools.get("zero_tool_rate")
    # Pilot path honesty + measured readiness (pre-revenue design partner)
    pilot = _soft_script_json(root, "pilot_surface.py", ["status"], timeout=120)
    if pilot:
        day2["pilot_ok"] = pilot.get("pilot_ok")
        day2["pilot_readiness_ok"] = pilot.get("readiness_ok")
        day2["pilot_ready_n"] = pilot.get("ready_n")
        day2["pilot_ready_total"] = pilot.get("ready_total")
        day2["pilot_proof_packet_ok"] = pilot.get("proof_packet_ok")
        day2["pilot_apply_url"] = pilot.get("apply_url")
    # Self-evolution day-2 (dual-gate adopt — buyer language, no F-IDs)
    sev = _soft_script_json(root, "self_evolve.py", ["status"], timeout=30)
    if sev:
        day2["self_evolve_ok"] = sev.get("self_evolve_ok")
        day2["self_evolve_active_n"] = sev.get("active_skills_n")
        day2["self_evolve_pending_n"] = sev.get("pending_proposals_n")
        day2["self_evolve_pending_ids"] = sev.get("pending_ids")
        day2["self_evolve_dual_gate_safe"] = sev.get("dual_gate_default_safe")
        day2["self_evolve_dual_gate_hint"] = sev.get("dual_gate_hint")
        day2["self_evolve_one_liner"] = sev.get("one_liner")
    # Diff vs SAST / AI review (buyer differentiation)
    dvs = _soft_script_json(root, "diff_vs_sast.py", ["status"], timeout=20)
    if dvs:
        day2["diff_vs_sast_ok"] = dvs.get("diff_vs_sast_ok")
        day2["diff_labeled_tp"] = (dvs.get("measured") or {}).get("labeled_tp")
    # Model alias SoT present + preferred product model (DeepSeek V4 Pro tool-use)
    day2["model_alias_script"] = (_scripts_dir(root) / "model_alias.py").is_file()
    try:
        sys.path.insert(0, str(_scripts_dir(root)))
        from model_alias import PREFERRED_DEEPSEEK, from_env  # type: ignore

        day2["preferred_model"] = PREFERRED_DEEPSEEK
        day2["model_from_env"] = from_env()
    except Exception:
        day2["preferred_model"] = "deepseek/deepseek-v4-pro"
        day2["model_from_env"] = day2["preferred_model"]
    # Public eval freshness (soft) — normalize model id for display honesty
    pe = _soft_script_json(root, "public_eval.py", ["status"], timeout=30)
    if pe:
        day2["public_eval_ok"] = pe.get("public_eval_ok")
        day2["public_eval_freshness_ok"] = pe.get("freshness_ok")
        mid = pe.get("model_id") or ""
        try:
            sys.path.insert(0, str(_scripts_dir(root)))
            from model_alias import normalize_model  # type: ignore

            mid = normalize_model(str(mid))
        except Exception:
            if mid in {
                "deepseek/deepseek-chat-v4-pro",
                "deepseek-chat-v4-pro",
            }:
                mid = "deepseek/deepseek-v4-pro"
        day2["public_eval_model"] = mid
    # Golden path: time-to-signal p50 (buyer path-to-value honesty)
    golden = _soft_script_json(root, "golden_path_metrics.py", ["status"], timeout=40)
    if golden:
        day2["golden_ready"] = golden.get("ready")
        day2["time_to_signal_p50_s"] = golden.get("time_to_signal_p50_s")
        day2["golden_dogfood_runs"] = golden.get("dogfood_runs")
    # Workflows-as-code (deterministic pipeline vs LLM prose)
    wf = _soft_script_json(root, "workflow_as_code.py", ["scorecard"], timeout=45)
    if wf:
        day2["workflow_level"] = wf.get("level")
        day2["workflow_valid"] = wf.get("valid")
        day2["workflow_ok"] = bool(wf.get("valid") and wf.get("level") in ("L2", "L3"))
    # Live lean: product default ON for merge-signal path (Modal/GHA dogfood).
    # Env override only when TORII_LIVE_LEAN is explicitly set.
    day2["live_lean_default"] = True
    _ll_env = (os.environ.get("TORII_LIVE_LEAN") or "").strip().lower()
    if _ll_env in {"1", "true", "yes", "on"}:
        day2["live_lean"] = True
        day2["live_lean_source"] = "env"
    elif _ll_env in {"0", "false", "no", "off"}:
        day2["live_lean"] = False
        day2["live_lean_source"] = "env"
    else:
        # Unset → report product default (not "False" which misleads day-2 buyers)
        day2["live_lean"] = True
        day2["live_lean_source"] = "product_default"

    groups_n = sum(1 for v in present.values() if v)
    return {
        "feature": FEATURE,
        "enabled": enabled(),
        "root": str(root),
        "groups_present": present,
        "groups_n": groups_n,
        "groups_total": len(present),
        "all_present": all(present.values()) if present else False,
        "memory_cli": (_scripts_dir(root) / "torii_memory.py").is_file(),
        "extras": extras,
        "day2": day2,
        "one_liner": (
            "Day-2 four beats: merge authority · cost/trust (TTS+cost) · org · growth — "
            "require torii/gate."
        ),
        "status_compact": True,
        "scored_at": _now(),
    }


# Day-2 CLI groups shown in full help table vs one-line "also"
_DAY2_PRIMARY = (
    "quieter",
    "ops",
    "commercial",
    "certificate",
    "enterprise",
    "pilot",
)
_DAY2_SECONDARY = (
    "public-eval",
    "tool-use",
    "self-evolve",
    "diff",
)


def render_status_text(payload: dict[str, Any], *, verbose: bool = False) -> str:
    """Human day-2 one-screen status — four buyer beats (cognitive collapse).

    Default: 4 bullets (merge · cost/trust · org · growth).
    ``verbose=True`` or ``status --verbose``: legacy per-surface lines.
    """
    day2 = payload.get("day2") if isinstance(payload.get("day2"), dict) else {}
    ok = bool(payload.get("all_present"))
    lines = [
        f"# Torii status · {'READY' if ok else 'GAPS'}",
        f"scored_at: {payload.get('scored_at')}",
        f"CLI groups: {payload.get('groups_n')}/{payload.get('groups_total')} present",
        "",
        "## Day-2 readiness (buyer · 4 beats)",
    ]
    if not day2:
        lines.append("- _(soft day-2 peeks unavailable — run doctor / commercial -- fixture)_")
    elif verbose:
        # Legacy expanded surface list (operators / CI dumps)
        if day2.get("overall_est") is not None:
            lines.append(
                f"- commercial: overall_est={day2.get('overall_est')} · "
                f"ok={day2.get('commercial_ok')} · surfaces={day2.get('surfaces_pass')}"
            )
        if day2.get("cost_p50_usd") is not None or day2.get("cost_ok") is not None:
            p50 = day2.get("cost_p50_usd")
            p50_s = f"${float(p50):.3f}" if isinstance(p50, (int, float)) else "—"
            lines.append(
                f"- cost honesty: p50={p50_s}/PR · cost_ok={day2.get('cost_ok')} · "
                f"honesty={day2.get('cost_honesty_ok')} (local vault only)"
            )
        if day2.get("cert_vault_n") is not None:
            cp = day2.get("cert_vault_cost_p50")
            cp_s = f"${float(cp):.3f}" if isinstance(cp, (int, float)) else "—"
            lines.append(
                f"- gate certificates: n={day2.get('cert_vault_n')} · "
                f"cost p50={cp_s} · ok={day2.get('cert_vault_ok')}"
            )
        if day2.get("quieter_ok") is not None:
            lines.append(
                f"- quieter: ok={day2.get('quieter_ok')} · "
                f"getting_quieter={day2.get('getting_quieter')} · "
                f"score={day2.get('quiet_score_all')}"
            )
        if day2.get("ops_ok") is not None or day2.get("fail_closed_safe_defaults") is not None:
            lines.append(
                f"- ops: ok={day2.get('ops_ok')} · "
                f"fail_closed={day2.get('fail_closed_safe_defaults')} · "
                f"smoke_ci={day2.get('smoke_ci')}"
            )
        if day2.get("enterprise_ok") is not None:
            lines.append(
                f"- enterprise: ok={day2.get('enterprise_ok')} · "
                f"tenants={day2.get('tenant_n')} · isolation={day2.get('isolation_ok')}"
            )
        if day2.get("tool_use_ok") is not None or day2.get("tool_use_rate") is not None:
            lines.append(
                f"- tool-use: ok={day2.get('tool_use_ok')} · "
                f"rate={day2.get('tool_use_rate')} · n={day2.get('tool_use_n')}"
            )
        if day2.get("public_eval_ok") is not None:
            lines.append(
                f"- public eval: ok={day2.get('public_eval_ok')} · "
                f"freshness={day2.get('public_eval_freshness_ok')} · "
                f"model={day2.get('public_eval_model')}"
            )
        if day2.get("pilot_ok") is not None:
            lines.append(
                f"- pilot: ok={day2.get('pilot_ok')} · "
                f"readiness={day2.get('pilot_readiness_ok')} "
                f"({day2.get('pilot_ready_n')}/{day2.get('pilot_ready_total')})"
            )
        if day2.get("self_evolve_ok") is not None:
            lines.append(
                f"- self-evolve: ok={day2.get('self_evolve_ok')} · "
                f"active={day2.get('self_evolve_active_n')} · "
                f"dual_gate_safe={day2.get('self_evolve_dual_gate_safe')}"
            )
        if day2.get("diff_vs_sast_ok") is not None:
            lines.append(
                f"- vs SAST: ok={day2.get('diff_vs_sast_ok')} · "
                f"labeled_tp={day2.get('diff_labeled_tp')}"
            )
    else:
        # --- four buyer beats (default) ---
        p50 = day2.get("cost_p50_usd")
        p50_s = f"${float(p50):.3f}" if isinstance(p50, (int, float)) else "—"
        cp = day2.get("cert_vault_cost_p50")
        cp_s = f"${float(cp):.3f}" if isinstance(cp, (int, float)) else "—"
        rn, rt = day2.get("pilot_ready_n"), day2.get("pilot_ready_total")
        pilot_r = f"{rn}/{rt}" if rn is not None and rt is not None else "—"
        ml = (payload.get("extras") or {}).get("memory_loop") or {}
        mem_s = ""
        if ml:
            mem_s = f" · memory={ml.get('level')}"

        qloc = day2.get("quieter_local_runs_n")
        qdemo = day2.get("quieter_local_demo_n")
        qorg = day2.get("quieter_local_organic_n")
        qboot = day2.get("quieter_bootstrap_needed")
        qorg_need = day2.get("quieter_organic_needed")
        qboot_s = ""
        if qloc is not None:
            extra = f"local_runs={qloc}"
            if qdemo is not None:
                extra += f" demo={qdemo}"
            if qorg is not None:
                extra += f" organic={qorg}"
            if qboot:
                extra += " bootstrap=True"
            elif qorg_need:
                extra += " organic_needed=True"
            qboot_s = f" · {extra}"
        lines.append(
            f"- **Merge authority:** quieter={day2.get('quieter_ok')} "
            f"(getting_quieter={day2.get('getting_quieter')} score={day2.get('quiet_score_all')}"
            f"{qboot_s}) · "
            f"certs n={day2.get('cert_vault_n')} ({cp_s}/PR) · "
            f"require **torii/gate**"
        )
        tts = day2.get("time_to_signal_p50_s")
        tts_s = f"{float(tts):.0f}s" if isinstance(tts, (int, float)) else "—"
        lean = day2.get("live_lean")
        lean_src = day2.get("live_lean_source")
        lean_s = ""
        if lean is not None:
            lean_s = f" · live_lean={lean}"
            if lean_src and lean_src != "env":
                lean_s += f"({lean_src})"
        pref = day2.get("preferred_model") or day2.get("public_eval_model")
        pref_s = f" · model={pref}" if pref else ""
        ztr = day2.get("zero_tool_rate")
        ztr_s = (
            f" · zero_tool={float(ztr):.0%}"
            if isinstance(ztr, (int, float))
            else ""
        )
        lines.append(
            f"- **Cost & trust:** commercial={day2.get('overall_est')}/10 "
            f"ok={day2.get('commercial_ok')} · cost p50={p50_s}/PR "
            f"honesty={day2.get('cost_honesty_ok')} · "
            f"time-to-signal p50={tts_s} · "
            f"public-eval freshness={day2.get('public_eval_freshness_ok')} · "
            f"tool-use rate={day2.get('tool_use_rate')}{ztr_s} · "
            f"fail_closed={day2.get('fail_closed_safe_defaults')}{lean_s}{pref_s}"
        )
        fed_ok = day2.get("federation_privacy_ok")
        themes_only = day2.get("privacy_themes_only")
        mt = day2.get("fed_multi_tenant_themes")
        fed_s = ""
        if fed_ok is not None or themes_only or mt is not None:
            parts = []
            if themes_only:
                parts.append("themes-only")
            if fed_ok is not None:
                parts.append(f"privacy_ok={fed_ok}")
            if mt is not None:
                parts.append(f"mt_themes={mt}")
            fed_s = " · fed " + " ".join(parts) if parts else ""
        lines.append(
            f"- **Org:** enterprise={day2.get('enterprise_ok')} · "
            f"tenants={day2.get('tenant_n')} · isolation={day2.get('isolation_ok')}"
            f"{fed_s} · "
            f"install --tenant (optional fleet)"
        )
        wf_lv = day2.get("workflow_level")
        wf_s = f" · workflow={wf_lv}" if wf_lv is not None else ""
        proof_ok = day2.get("pilot_proof_packet_ok")
        proof_s = " · proof=docs/PILOT-PROOF.md" if proof_ok else ""
        sev_pend = day2.get("self_evolve_pending_n")
        sev_ids = day2.get("self_evolve_pending_ids") or []
        sev_pend_s = ""
        if sev_pend is not None:
            sev_pend_s = f" pending={sev_pend}"
            if sev_ids and int(sev_pend or 0) > 0:
                sev_pend_s += f"({','.join(str(x) for x in sev_ids[:2])})"
        lines.append(
            f"- **Growth:** pilot readiness={day2.get('pilot_readiness_ok')} ({pilot_r})"
            f"{proof_s} · "
            f"self-evolve active={day2.get('self_evolve_active_n')}"
            f"{sev_pend_s} "
            f"dual_gate_safe={day2.get('self_evolve_dual_gate_safe')} · "
            f"vs SAST labeled_tp={day2.get('diff_labeled_tp')} "
            f"(docs/DIFF.md){mem_s}{wf_s}"
        )

    if verbose:
        ml = (payload.get("extras") or {}).get("memory_loop") or {}
        if ml:
            lines.append(
                f"- memory loop: level={ml.get('level')} ready={ml.get('ready')}"
            )

    lines += [
        "",
        "## Next",
        "1. Require status check **torii/gate** (merge authority)",
        "2. `python3 scripts/torii.py doctor` · `quieter -- status` · `pilot -- readiness`",
        "3. Prefer model `deepseek/deepseek-v4-pro` · GTM templates: docs/GTM.md · Pages: https://mr-ashish.github.io/torii-gate/",
        "",
        "Detail: `status --verbose` · JSON: `status --json` · help: `python3 scripts/torii.py help`",
        "",
        str(payload.get("one_liner") or ""),
        "",
    ]
    return "\n".join(lines)


def cmd_status(args: argparse.Namespace) -> int:
    payload = build_status_payload()
    want_json = bool(getattr(args, "json", False))
    want_text = bool(getattr(args, "text", False))
    want_verbose = bool(getattr(args, "verbose", False))
    env_json = (os.environ.get("TORII_STATUS_JSON") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    env_text = (os.environ.get("TORII_STATUS_TEXT") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    # Default human text on TTY; JSON when piped, --json, or TORII_STATUS_JSON=1
    # Force text with --text / TORII_STATUS_TEXT even when non-TTY (install check).
    use_text = want_text or env_text or (
        not want_json and not env_json and sys.stdout.isatty()
    )
    if use_text and not want_json and not env_json:
        print(render_status_text(payload, verbose=want_verbose))
    else:
        print(json.dumps(payload, indent=2))
    return 0 if payload.get("all_present") else 1


def _scorecard_ops_panel(root: Path) -> dict[str, Any]:
    """F135: privacy-safe scorecard skill fitness readiness (soft panel)."""
    panel: dict[str, Any] = {
        "feature": "F135",
        "active_n": 0,
        "active": [],
        "fed_n": 0,
        "fitness_ingested_n": 0,
        "scorecard_ops_ok": False,
        "privacy_ok": True,
    }
    try:
        sys.path.insert(0, str(_scripts_dir(root)))
        from skill_auto_adopt import list_active_scorecard_skills  # type: ignore

        active = list_active_scorecard_skills(root)
        panel["active"] = active[:16]
        panel["active_n"] = len(active)
    except Exception as exc:
        panel["active_soft_error"] = str(exc)[:80]
    fed = root / "memory" / "federation" / "scorecard-skill-signals.json"
    if fed.is_file():
        try:
            doc = json.loads(fed.read_text(encoding="utf-8"))
            panel["fed_n"] = int(doc.get("count") or len(doc.get("signals") or []))
            panel["fed_skill_n"] = len(doc.get("skill_ids") or [])
            panel["privacy_ok"] = bool(doc.get("privacy_ok", True)) and (
                "/Users/" not in fed.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    # fitness ledger scorecard ops entries
    fit = root / ".torii" / "skill-fitness.json"
    if fit.is_file():
        try:
            led = json.loads(fit.read_text(encoding="utf-8"))
            sc_ids = [
                sid
                for sid, e in (led.get("skills") or {}).items()
                if isinstance(e, dict)
                and (
                    e.get("scorecard_ops")
                    or int(e.get("scorecard_ingested_n") or 0) >= 1
                )
            ]
            panel["fitness_ingested_n"] = len(sc_ids)
            panel["fitness_skills"] = sc_ids[:16]
            last = led.get("last_scorecard_ingest") or {}
            if last:
                panel["last_scorecard_ingest_n"] = last.get("n")
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    # ok when any scorecard skill is active OR federated OR fitness-ingested
    panel["scorecard_ops_ok"] = bool(
        panel["active_n"] >= 1
        or panel.get("fed_skill_n", 0) >= 1
        or panel["fitness_ingested_n"] >= 1
        or panel["fed_n"] >= 1
    )
    return panel


def cmd_doctor(args: argparse.Namespace) -> int:
    """Cheap product doctor: memory + loops + budget + recovery skill readiness."""
    root = _root()
    results = []
    all_ok = True
    recovery_ok: bool | None = None
    recovery_active: list[str] = []
    recovery_hub_gap_ok: bool | None = None
    recon_warm_hub_ok: bool | None = None
    hub_archival_util_ok: bool | None = None
    hub_archival_util_critic_ok: bool | None = None
    # F163: compound hub-archival loop surfaces (F159–F162)
    hub_archival_hub_ok: bool | None = None
    hub_archival_hub_inject_ok: bool | None = None
    router_synth_ok: bool | None = None
    reprompt_adaptive_ok: bool | None = None
    hub_archival_fitness_ok: bool | None = None

    checks: list[tuple[str, list[str]]] = [
        ("memory", [sys.executable, str(_scripts_dir(root) / "torii_memory.py"), "status"]),
        (
            "memory_loop",
            [
                sys.executable,
                str(_scripts_dir(root) / "memory_loop_status.py"),
                "scorecard",
                "--shallow",
            ],
        ),
        (
            "budget",
            [sys.executable, str(_scripts_dir(root) / "reprompt_budget.py"), "fixture"],
        ),
        (
            "skill_loop",
            [
                sys.executable,
                str(_scripts_dir(root) / "skill_loop_status.py"),
                "scorecard",
                "--shallow",
            ],
        ),
    ]
    for name, cmd in checks:
        script_path = Path(cmd[1] if cmd[0] == sys.executable else cmd[0])
        # for python: cmd[1] is script
        if cmd[0] == sys.executable and not Path(cmd[1]).is_file():
            results.append({"check": name, "ok": False, "error": "missing"})
            all_ok = False
            continue
        try:
            r = subprocess.run(
                cmd,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "TORII_ROOT": str(root)},
            )
            ok = r.returncode == 0
            try:
                data = json.loads(r.stdout)
                if "fixture_pass" in data:
                    ok = ok and bool(data["fixture_pass"])
                if "all_present" in data:
                    ok = ok and bool(data["all_present"])
                if name.endswith("loop") and "level" in data:
                    ok = ok and data.get("level") in ("L2", "L3")
                # F124: skill loop must report recovery_ok (memory/product/critic active)
                # F128: recovery_hub_gap_ok (f127 critic + demote-eval paper path)
                if name == "skill_loop":
                    if "recovery_ok" in data:
                        recovery_ok = bool(data.get("recovery_ok"))
                        recovery_active = list(data.get("recovery_active") or [])
                        ok = ok and recovery_ok
                    else:
                        recovery_ok = False
                        ok = False
                    recovery_hub_gap_ok = data.get("recovery_hub_gap_ok")
                    if recovery_hub_gap_ok is not None:
                        ok = ok and bool(recovery_hub_gap_ok)
                    else:
                        # fail closed if scorecard too old for F128
                        recovery_hub_gap_ok = False
                        ok = False
                    # F151: recon_warm_hub_ok soft on doctor (surfaces; demote-eval is hard gate)
                    recon_warm_hub_ok = data.get("recon_warm_hub_ok")
                    # F155: hub-archival recovery util soft surface (inject ≠ hub_boost tools)
                    hub_archival_util_ok = data.get("hub_archival_util_ok")
                    # F156: critic demote path soft surface
                    hub_archival_util_critic_ok = data.get("hub_archival_util_critic_ok")
                    # F163: compound hub-archival loop (F159–F162) soft surfaces
                    hub_archival_hub_ok = data.get("hub_archival_hub_ok")
                    hub_archival_hub_inject_ok = data.get("hub_archival_hub_inject_ok")
                    router_synth_ok = data.get("router_synth_ok")
                    reprompt_adaptive_ok = data.get("reprompt_adaptive_ok")
                    hub_archival_fitness_ok = data.get("hub_archival_fitness_ok")
                    # F165–F170 GEPA refine compound loop soft surfaces
                    skill_refine_ok = data.get("skill_refine_ok")
                    skill_refine_attr_ok = data.get("skill_refine_attr_ok")
                    refine_dual_ok = data.get("refine_dual_ok")
                    refine_promote_ok = data.get("refine_promote_ok")
                    refine_dual_hub_ok = data.get("refine_dual_hub_ok")
                    refine_loop_ok = data.get("refine_loop_ok")
            except (json.JSONDecodeError, TypeError):
                recovery_hub_gap_ok = None
                recon_warm_hub_ok = None
                hub_archival_util_ok = None
                hub_archival_util_critic_ok = None
                hub_archival_hub_ok = None
                hub_archival_hub_inject_ok = None
                router_synth_ok = None
                reprompt_adaptive_ok = None
                hub_archival_fitness_ok = None
                skill_refine_ok = None
                skill_refine_attr_ok = None
                refine_dual_ok = None
                refine_promote_ok = None
                refine_dual_hub_ok = None
                refine_loop_ok = None
            entry: dict[str, Any] = {"check": name, "ok": ok, "rc": r.returncode}
            if name == "skill_loop":
                entry["recovery_ok"] = recovery_ok
                entry["recovery_active"] = recovery_active
                entry["recovery_hub_gap_ok"] = recovery_hub_gap_ok
                entry["recon_warm_hub_ok"] = recon_warm_hub_ok
                entry["hub_archival_util_ok"] = hub_archival_util_ok
                entry["hub_archival_util_critic_ok"] = hub_archival_util_critic_ok
                entry["hub_archival_hub_ok"] = hub_archival_hub_ok
                entry["hub_archival_hub_inject_ok"] = hub_archival_hub_inject_ok
                entry["router_synth_ok"] = router_synth_ok
                entry["reprompt_adaptive_ok"] = reprompt_adaptive_ok
                entry["hub_archival_fitness_ok"] = hub_archival_fitness_ok
                entry["skill_refine_ok"] = skill_refine_ok
                entry["skill_refine_attr_ok"] = skill_refine_attr_ok
                entry["refine_dual_ok"] = refine_dual_ok
                entry["refine_promote_ok"] = refine_promote_ok
                entry["refine_dual_hub_ok"] = refine_dual_hub_ok
                entry["refine_loop_ok"] = refine_loop_ok
            results.append(entry)
            if not ok:
                all_ok = False
        except Exception as exc:
            results.append({"check": name, "ok": False, "error": str(exc)[:120]})
            all_ok = False

    # surface last recovery_hub_gap_ok / recon_warm_hub_ok / hub_archival_* / refine_* loop
    hub_gap = None
    recon_warm = None
    hub_arch = None
    hub_arch_critic = None
    hub_arch_hub = None
    hub_arch_inject = None
    router_synth = None
    reprompt_adapt = None
    hub_arch_fit = None
    skill_refine = None
    skill_refine_attr = None
    refine_dual = None
    refine_promote = None
    refine_dual_hub = None
    refine_loop = None
    for e in results:
        if e.get("check") == "skill_loop" and "recovery_hub_gap_ok" in e:
            hub_gap = e.get("recovery_hub_gap_ok")
        if e.get("check") == "skill_loop" and "recon_warm_hub_ok" in e:
            recon_warm = e.get("recon_warm_hub_ok")
        if e.get("check") == "skill_loop" and "hub_archival_util_ok" in e:
            hub_arch = e.get("hub_archival_util_ok")
        if e.get("check") == "skill_loop" and "hub_archival_util_critic_ok" in e:
            hub_arch_critic = e.get("hub_archival_util_critic_ok")
        if e.get("check") == "skill_loop" and "hub_archival_hub_ok" in e:
            hub_arch_hub = e.get("hub_archival_hub_ok")
        if e.get("check") == "skill_loop" and "hub_archival_hub_inject_ok" in e:
            hub_arch_inject = e.get("hub_archival_hub_inject_ok")
        if e.get("check") == "skill_loop" and "router_synth_ok" in e:
            router_synth = e.get("router_synth_ok")
        if e.get("check") == "skill_loop" and "reprompt_adaptive_ok" in e:
            reprompt_adapt = e.get("reprompt_adaptive_ok")
        if e.get("check") == "skill_loop" and "hub_archival_fitness_ok" in e:
            hub_arch_fit = e.get("hub_archival_fitness_ok")
        if e.get("check") == "skill_loop" and "skill_refine_ok" in e:
            skill_refine = e.get("skill_refine_ok")
        if e.get("check") == "skill_loop" and "skill_refine_attr_ok" in e:
            skill_refine_attr = e.get("skill_refine_attr_ok")
        if e.get("check") == "skill_loop" and "refine_dual_ok" in e:
            refine_dual = e.get("refine_dual_ok")
        if e.get("check") == "skill_loop" and "refine_promote_ok" in e:
            refine_promote = e.get("refine_promote_ok")
        if e.get("check") == "skill_loop" and "refine_dual_hub_ok" in e:
            refine_dual_hub = e.get("refine_dual_hub_ok")
        if e.get("check") == "skill_loop" and "refine_loop_ok" in e:
            refine_loop = e.get("refine_loop_ok")
    # F135: scorecard ops fitness panel (informational — does not fail doctor)
    sc_panel = _scorecard_ops_panel(root)
    # F163: hub-archival compound loop readiness (soft product surface)
    ha_loop_ok = bool(
        hub_arch
        and hub_arch_critic
        and hub_arch_hub
        and hub_arch_inject
        and router_synth
        and reprompt_adapt
        and hub_arch_fit
    )
    # F170: GEPA refine compound loop (F165–F169) — soft product surface
    refine_loop_ok = bool(
        refine_loop
        if refine_loop is not None
        else (
            skill_refine
            and skill_refine_attr
            and refine_dual
            and refine_promote
            and refine_dual_hub
        )
    )
    # Soft day-2 buyer panel (commercial / cert vault / quieter) — no hard fail
    day2: dict[str, Any] = {}
    try:
        st = build_status_payload(root)
        day2 = st.get("day2") if isinstance(st.get("day2"), dict) else {}
    except Exception:
        day2 = {}

    payload: dict[str, Any] = {
        "feature": FEATURE,
        "feature_recovery": "F128",
        "feature_recon_warm_hub": "F151",
        "feature_hub_archival_util": "F155",
        "feature_hub_archival_util_critic": "F156",
        "feature_hub_archival_loop": "F163",
        "feature_refine_loop": "F170/F186",
        "feature_scorecard_ops": "F135",
        "doctor_pass": all_ok,
        "recovery_ok": recovery_ok,
        "recovery_active": recovery_active,
        "recovery_hub_gap_ok": hub_gap,
        "recon_warm_hub_ok": recon_warm,
        "hub_archival_util_ok": hub_arch,
        "hub_archival_util_critic_ok": hub_arch_critic,
        "hub_archival_hub_ok": hub_arch_hub,
        "hub_archival_hub_inject_ok": hub_arch_inject,
        "router_synth_ok": router_synth,
        "reprompt_adaptive_ok": reprompt_adapt,
        "hub_archival_fitness_ok": hub_arch_fit,
        "hub_archival_loop_ok": ha_loop_ok,
        "skill_refine_ok": skill_refine,
        "skill_refine_attr_ok": skill_refine_attr,
        "refine_dual_ok": refine_dual,
        "refine_promote_ok": refine_promote,
        "refine_dual_hub_ok": refine_dual_hub,
        "refine_loop_ok": refine_loop_ok,
        "scorecard_ops": sc_panel,
        "scorecard_ops_ok": sc_panel.get("scorecard_ops_ok"),
        "day2": day2,
        "results": results,
        "scored_at": _now(),
        "cli": "python3 scripts/torii.py",
        "install_doc": "docs/INSTALL.md",
    }
    want_json = bool(getattr(args, "json", False))
    want_text = bool(getattr(args, "text", False))
    env_json = (os.environ.get("TORII_DOCTOR_JSON") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    env_text = (os.environ.get("TORII_DOCTOR_TEXT") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    # Default human text on TTY; JSON when piped, --json, or TORII_DOCTOR_JSON=1
    use_text = want_text or env_text or (
        not want_json and not env_json and sys.stdout.isatty()
    )
    if use_text and not want_json and not env_json:
        print(render_doctor_text(payload))
    else:
        print(json.dumps(payload, indent=2))
    return 0 if all_ok else 1


def render_doctor_text(payload: dict[str, Any]) -> str:
    """Human day-2 doctor summary (install UX — hide F-stack by default)."""
    ok = bool(payload.get("doctor_pass"))
    day2 = payload.get("day2") if isinstance(payload.get("day2"), dict) else {}
    lines = [
        f"# Torii doctor · {'PASS' if ok else 'FAIL'}",
        f"scored_at: {payload.get('scored_at')}",
        f"doctor_pass: {ok}",
        "",
        "## Checks",
    ]
    for r in payload.get("results") or []:
        if not isinstance(r, dict):
            continue
        mark = "ok" if r.get("ok") else "FAIL"
        lines.append(f"- [{mark}] {r.get('check')}")
    lines += [
        "",
        "## Product readiness (short)",
        f"- recovery skills active: {payload.get('recovery_ok')} "
        f"({', '.join(payload.get('recovery_active') or []) or 'none'})",
        f"- recovery hub-gap: {payload.get('recovery_hub_gap_ok')}",
        f"- hub-archival loop: {payload.get('hub_archival_loop_ok')}",
        f"- refine loop: {payload.get('refine_loop_ok')}",
        "",
        "## Day-2 scoreboard (measured)",
    ]
    if day2:
        if day2.get("overall_est") is not None:
            lines.append(
                f"- commercial overall_est={day2.get('overall_est')} · "
                f"ok={day2.get('commercial_ok')}"
            )
        p50 = day2.get("cost_p50_usd")
        if p50 is not None or day2.get("cost_honesty_ok") is not None:
            p50_s = f"${float(p50):.3f}" if isinstance(p50, (int, float)) else "—"
            lines.append(
                f"- cost/PR p50={p50_s} · honesty={day2.get('cost_honesty_ok')} "
                f"(local vault only)"
            )
        if day2.get("cert_vault_n") is not None:
            lines.append(
                f"- gate cert vault n={day2.get('cert_vault_n')} · "
                f"ok={day2.get('cert_vault_ok')}"
            )
        if day2.get("getting_quieter") is not None:
            lines.append(
                f"- quieter-over-time getting_quieter={day2.get('getting_quieter')} · "
                f"ok={day2.get('quieter_ok')}"
            )
    else:
        lines.append(
            "- Run `python3 scripts/torii.py status --text` for commercial · "
            "cost · cert · quieter one-screen"
        )
    lines += [
        "",
        "## Cost honesty (day-2)",
        "- Measured dogfood cost/PR + time-to-signal: "
        "`python3 scripts/torii.py ops -- status` · "
        "`python3 scripts/torii.py commercial -- status`",
        "- Tables: docs/ops/cost-pr-dashboard.md · "
        "docs/benchmarks/commercial-scorecard.md (Cost honesty section)",
        "- Telemetry is **local vault only** (not federated) — docs/enterprise/PRIVACY.md",
        "",
        "## Next",
        "- Install: docs/INSTALL.md · require status **torii/gate**",
        "- One CLI: python3 scripts/torii.py help|status|doctor|memory|gate|ops",
        "- One-screen: python3 scripts/torii.py status --text",
        "- JSON: python3 scripts/torii.py doctor --json",
        "",
    ]
    if not ok:
        fails = [
            str(r.get("check"))
            for r in (payload.get("results") or [])
            if isinstance(r, dict) and not r.get("ok")
        ]
        lines.append(f"Failing checks: {', '.join(fails) or 'see JSON'}")
        lines.append("")
    return "\n".join(lines)


def product_scorecard(
    *,
    root: Path | None = None,
    run_demote: bool = True,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """F129/F130: brand/ops scorecard — doctor + loops + demote + memory util.

    Packages measured capabilities (not slogans) for landing, install day-2,
    and EVAL vault: recovery_hub_gap_ok, critic_approve_demote_rate,
    memory_tool_util_delta (Mem0/Letta: tools must be called).
    """
    root = root or _root()
    sd = _scripts_dir(root)
    doctor: dict[str, Any] = {}
    skill: dict[str, Any] = {}
    memory: dict[str, Any] = {}
    demote: dict[str, Any] = {}
    mem_util: dict[str, Any] = {}
    workflow: dict[str, Any] = {}

    def _run_json(cmd: list[str], timeout: int = 180) -> dict[str, Any]:
        try:
            r = subprocess.run(
                cmd,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "TORII_ROOT": str(root)},
            )
            if r.stdout.strip():
                return json.loads(r.stdout)
        except Exception as exc:
            return {"error": str(exc)[:160], "ok": False}
        return {"error": "empty", "ok": False}

    doctor = _run_json([sys.executable, str(Path(__file__).resolve()), "doctor"])
    skill = _run_json(
        [sys.executable, str(sd / "skill_loop_status.py"), "scorecard", "--shallow"]
    )
    memory = _run_json(
        [sys.executable, str(sd / "memory_loop_status.py"), "scorecard", "--shallow"]
    )
    # F131: workflows-as-code readiness (loop-eng style pipeline graph)
    if (sd / "workflow_as_code.py").is_file():
        workflow = _run_json(
            [sys.executable, str(sd / "workflow_as_code.py"), "scorecard"],
            timeout=120,
        )
    # Prefer prior demote-eval artifact (live pipeline already ran critic_demote_eval
    # stage). Avoid double demote-eval which burned 5–15+ min on Modal and hit 1500s caps.
    if out_dir:
        prior_demote = Path(out_dir) / "critic-demote-eval.json"
        if prior_demote.is_file():
            try:
                demote = json.loads(prior_demote.read_text(encoding="utf-8"))
                if not isinstance(demote, dict):
                    demote = {}
                else:
                    demote = {**demote, "from_prior_artifact": True}
            except (OSError, json.JSONDecodeError):
                demote = {}
        prior_mu = Path(out_dir) / "memory-util-eval.json"
        if prior_mu.is_file():
            try:
                mem_util = json.loads(prior_mu.read_text(encoding="utf-8"))
                if not isinstance(mem_util, dict):
                    mem_util = {}
            except (OSError, json.JSONDecodeError):
                mem_util = {}

    if run_demote and not demote and (sd / "second_agent_critic.py").is_file():
        demote_cmd = [
            sys.executable,
            str(sd / "second_agent_critic.py"),
            "demote-eval",
        ]
        if out_dir:
            demote_cmd += ["--out-dir", str(out_dir)]
        demote = _run_json(demote_cmd, timeout=300)
    # F130: memory tool utilization paper pack (Mem0/Letta tool-call discipline)
    if run_demote and not mem_util and (sd / "memory_tool_audit.py").is_file():
        mu_cmd = [
            sys.executable,
            str(sd / "memory_tool_audit.py"),
            "util-eval",
        ]
        if out_dir:
            mu_cmd += ["--out-dir", str(out_dir)]
        mem_util = _run_json(mu_cmd, timeout=120)

    doctor_pass = bool(doctor.get("doctor_pass"))
    recovery_ok = bool(doctor.get("recovery_ok") or skill.get("recovery_ok"))
    hub_gap_ok = bool(
        doctor.get("recovery_hub_gap_ok")
        if doctor.get("recovery_hub_gap_ok") is not None
        else skill.get("recovery_hub_gap_ok")
    )
    demote_rate = demote.get("demote_rate")
    demote_pass = bool(demote.get("eval_pass")) if demote else False
    mem_util_delta = mem_util.get("delta") if mem_util else None
    mem_util_pass = bool(mem_util.get("eval_pass")) if mem_util else False
    skill_level = skill.get("level")
    mem_level = memory.get("level")
    wf_level = workflow.get("level") if workflow else None
    wf_valid = bool(workflow.get("valid")) if workflow else False
    wf_ok = wf_valid and wf_level in ("L2", "L3")

    # F131 dual compound brand panel: skill + memory + workflow levels
    dual_compound = {
        "skill_loop_level": skill_level,
        "memory_loop_level": mem_level,
        "workflow_level": wf_level,
        "workflow_valid": wf_valid,
        "workflow_pct": workflow.get("pct") if workflow else None,
        "both_loops_l3": skill_level == "L3" and mem_level == "L3",
        "triple_ready": skill_level == "L3" and mem_level == "L3" and wf_ok,
    }

    # F135: scorecard skill fitness readiness (soft metric; not brand gate)
    sc_ops = _scorecard_ops_panel(root)
    # soft: try fitness ingest so scorecard themes compound into ledger
    sc_fit_report: dict[str, Any] = {}
    try:
        sys.path.insert(0, str(sd))
        from skill_fitness import (  # type: ignore
            ingest_scorecard_skills,
            scorecard_fitness_enabled,
        )

        if scorecard_fitness_enabled():
            sc_fit_report = ingest_scorecard_skills(None, root=root, save=True)
            # refresh panel after ingest
            sc_ops = _scorecard_ops_panel(root)
    except Exception as exc:
        sc_fit_report = {"soft_error": str(exc)[:120]}

    # brand headline metrics (privacy-safe floats/bools only)
    metrics = {
        "doctor_pass": doctor_pass,
        "recovery_ok": recovery_ok,
        "recovery_hub_gap_ok": hub_gap_ok,
        "skill_loop_level": skill_level,
        "memory_loop_level": mem_level,
        "workflow_level": wf_level,
        "workflow_valid": wf_valid,
        "workflow_ok": wf_ok,
        "dual_compound_triple_ready": dual_compound["triple_ready"],
        "critic_approve_demote_rate": demote_rate,
        "weak_approve_demoted": demote.get("weak_demote_ok"),
        "hub_gap_idle_demoted": demote.get("hub_gap_demote_ok"),
        "recon_warm_hub_idle_demoted": demote.get("recon_warm_hub_demote_ok")
        if demote
        else None,
        "recon_warm_hub_ok": bool(
            doctor.get("recon_warm_hub_ok")
            if doctor.get("recon_warm_hub_ok") is not None
            else skill.get("recon_warm_hub_ok")
        ),
        # F155: hub-archival recovery util (always inject → hub_boost tools)
        "hub_archival_util_ok": bool(
            doctor.get("hub_archival_util_ok")
            if doctor.get("hub_archival_util_ok") is not None
            else skill.get("hub_archival_util_ok")
        ),
        # F156: hub-archival util critic demote path
        "hub_archival_util_critic_ok": bool(
            skill.get("hub_archival_util_critic_ok")
            if skill.get("hub_archival_util_critic_ok") is not None
            else doctor.get("hub_archival_util_critic_ok")
        ),
        # F163: compound hub-archival loop (util→reprompt→fitness→hub→inject)
        "hub_archival_hub_ok": bool(
            skill.get("hub_archival_hub_ok")
            if skill.get("hub_archival_hub_ok") is not None
            else doctor.get("hub_archival_hub_ok")
        ),
        "hub_archival_hub_inject_ok": bool(
            skill.get("hub_archival_hub_inject_ok")
            if skill.get("hub_archival_hub_inject_ok") is not None
            else doctor.get("hub_archival_hub_inject_ok")
        ),
        "router_synth_ok": bool(
            skill.get("router_synth_ok")
            if skill.get("router_synth_ok") is not None
            else doctor.get("router_synth_ok")
        ),
        "reprompt_adaptive_ok": bool(
            skill.get("reprompt_adaptive_ok")
            if skill.get("reprompt_adaptive_ok") is not None
            else doctor.get("reprompt_adaptive_ok")
        ),
        "hub_archival_fitness_ok": bool(
            skill.get("hub_archival_fitness_ok")
            if skill.get("hub_archival_fitness_ok") is not None
            else doctor.get("hub_archival_fitness_ok")
        ),
        "hub_archival_loop_ok": bool(
            doctor.get("hub_archival_loop_ok")
            if doctor.get("hub_archival_loop_ok") is not None
            else (
                skill.get("hub_archival_util_ok")
                and skill.get("hub_archival_util_critic_ok")
                and skill.get("hub_archival_hub_ok")
                and skill.get("hub_archival_hub_inject_ok")
                and skill.get("router_synth_ok")
                and skill.get("reprompt_adaptive_ok")
                and skill.get("hub_archival_fitness_ok")
            )
        ),
        # F170: GEPA refine compound loop (F165–F169)
        "skill_refine_ok": bool(
            skill.get("skill_refine_ok")
            if skill.get("skill_refine_ok") is not None
            else doctor.get("skill_refine_ok")
        ),
        "skill_refine_attr_ok": bool(
            skill.get("skill_refine_attr_ok")
            if skill.get("skill_refine_attr_ok") is not None
            else doctor.get("skill_refine_attr_ok")
        ),
        "refine_dual_ok": bool(
            skill.get("refine_dual_ok")
            if skill.get("refine_dual_ok") is not None
            else doctor.get("refine_dual_ok")
        ),
        "refine_promote_ok": bool(
            skill.get("refine_promote_ok")
            if skill.get("refine_promote_ok") is not None
            else doctor.get("refine_promote_ok")
        ),
        "refine_dual_hub_ok": bool(
            skill.get("refine_dual_hub_ok")
            if skill.get("refine_dual_hub_ok") is not None
            else doctor.get("refine_dual_hub_ok")
        ),
        "refine_loop_ok": bool(
            doctor.get("refine_loop_ok")
            if doctor.get("refine_loop_ok") is not None
            else (
                skill.get("refine_loop_ok")
                if skill.get("refine_loop_ok") is not None
                else (
                    skill.get("skill_refine_ok")
                    and skill.get("skill_refine_attr_ok")
                    and skill.get("refine_dual_ok")
                    and skill.get("refine_promote_ok")
                    and skill.get("refine_dual_hub_ok")
                )
            )
        ),
        "refine_dual_fail_idle_demoted": demote.get("refine_dual_fail_demote_ok")
        if demote
        else None,
        "refine_decay_hub_idle_demoted": demote.get("refine_decay_hub_demote_ok")
        if demote
        else None,
        "refine_dual_decay_ok": bool(
            skill.get("refine_dual_decay_ok")
            if skill.get("refine_dual_decay_ok") is not None
            else doctor.get("refine_dual_decay_ok")
        ),
        "refine_decay_fed_ok": bool(
            skill.get("refine_decay_fed_ok")
            if skill.get("refine_decay_fed_ok") is not None
            else doctor.get("refine_decay_fed_ok")
        ),
        # F175–F177: dual_pass revive + free-rider MT + contribution_pp floor
        "refine_dual_revive_ok": bool(
            skill.get("refine_dual_revive_ok")
            if skill.get("refine_dual_revive_ok") is not None
            else doctor.get("refine_dual_revive_ok")
        ),
        "free_rider_revive_ok": bool(
            skill.get("free_rider_revive_ok")
            if skill.get("free_rider_revive_ok") is not None
            else doctor.get("free_rider_revive_ok")
        ),
        "revive_pp_gate_ok": bool(
            skill.get("revive_pp_gate_ok")
            if skill.get("revive_pp_gate_ok") is not None
            else doctor.get("revive_pp_gate_ok")
        ),
        "free_rider_revive_idle_demoted": demote.get("free_rider_revive_demote_ok")
        if demote
        else None,
        "low_pp_revive_idle_demoted": demote.get("revive_pp_gate_demote_ok")
        if demote
        else None,
        "revive_loo_gate_ok": bool(
            skill.get("revive_loo_gate_ok")
            if skill.get("revive_loo_gate_ok") is not None
            else doctor.get("revive_loo_gate_ok")
        ),
        "loo_revive_idle_demoted": demote.get("revive_loo_gate_demote_ok")
        if demote
        else None,
        "hub_gepa_compound_ok": bool(
            skill.get("hub_gepa_compound_ok")
            if skill.get("hub_gepa_compound_ok") is not None
            else doctor.get("hub_gepa_compound_ok")
        ),
        "hub_gepa_compound_idle_demoted": demote.get("hub_gepa_compound_demote_ok")
        if demote
        else None,
        "hub_gepa_compound_inject_ok": bool(
            skill.get("hub_gepa_compound_inject_ok")
            if skill.get("hub_gepa_compound_inject_ok") is not None
            else doctor.get("hub_gepa_compound_inject_ok")
        ),
        "hub_gepa_compound_always_ok": bool(
            skill.get("hub_gepa_compound_always_ok")
            if skill.get("hub_gepa_compound_always_ok") is not None
            else doctor.get("hub_gepa_compound_always_ok")
        ),
        "reprompt_compound_ok": bool(
            skill.get("reprompt_compound_ok")
            if skill.get("reprompt_compound_ok") is not None
            else doctor.get("reprompt_compound_ok")
        ),
        "compound_reprompt_fitness_ok": bool(
            skill.get("compound_reprompt_fitness_ok")
            if skill.get("compound_reprompt_fitness_ok") is not None
            else doctor.get("compound_reprompt_fitness_ok")
        ),
        "compound_reprompt_pressure_ok": bool(
            skill.get("compound_reprompt_pressure_ok")
            if skill.get("compound_reprompt_pressure_ok") is not None
            else doctor.get("compound_reprompt_pressure_ok")
        ),
        "hub_archival_hub_pressure_idle_demoted": demote.get(
            "hub_archival_hub_pressure_demote_ok"
        )
        if demote
        else None,
        "demote_eval_pass": demote_pass,
        "memory_tool_util_delta": mem_util_delta,
        "memory_tool_util_good": mem_util.get("good_score") if mem_util else None,
        "memory_tool_util_weak": mem_util.get("weak_score") if mem_util else None,
        "memory_util_eval_pass": mem_util_pass,
        # F135
        "scorecard_ops_ok": bool(sc_ops.get("scorecard_ops_ok")),
        "scorecard_skills_n": int(sc_ops.get("active_n") or 0),
        "scorecard_fed_n": int(sc_ops.get("fed_n") or 0),
        "scorecard_fitness_ingested_n": int(sc_ops.get("fitness_ingested_n") or 0),
    }
    brand_ready = bool(
        doctor_pass
        and recovery_ok
        and hub_gap_ok
        and skill_level in ("L2", "L3")
        and wf_ok
        and (not run_demote or demote_pass)
        and (not run_demote or mem_util_pass)
    )
    # Loop-Ready style level for product surface
    if (
        brand_ready
        and skill_level == "L3"
        and mem_level == "L3"
        and wf_level == "L3"
        and demote_pass
        and mem_util_pass
    ):
        level = "L3"
    elif doctor_pass and recovery_ok and wf_ok:
        level = "L2"
    elif recovery_ok or doctor_pass:
        level = "L1"
    else:
        level = "L0"

    report: dict[str, Any] = {
        "feature": "F131",
        "feature_cli": FEATURE,
        "feature_scorecard": "F129",
        "feature_memory_util": "F130",
        "feature_scorecard_ops": "F135",
        "feature_hub_archival_loop": "F163",
        "feature_refine_loop": "F170/F186",
        "schema": SCHEMA,
        "scored_at": _now(),
        "level": level,
        "brand_ready": brand_ready,
        "metrics": metrics,
        "dual_compound": dual_compound,
        "one_liner": (
            "Measured gate readiness: dual compound (skill+memory) + workflow graph + "
            f"demote_rate={demote_rate} + memory_util_delta={mem_util_delta}"
            + (
                " + hub-archival loop (util→reprompt→fitness→hub inject)."
                if metrics.get("hub_archival_loop_ok")
                else "."
            )
        ),
        "brand_lines": [
            f"Doctor pass: **{doctor_pass}** · recovery skills **{'ok' if recovery_ok else 'gap'}**",
            f"Hub gap critic path: **{'ok' if hub_gap_ok else 'gap'}** (F127/F128)",
            f"Critic APPROVE demote rate (offline pack): **{demote_rate}**",
            f"Memory tool util delta (good−weak): **{mem_util_delta}** (F130)",
            f"Dual compound: skill **{skill_level}** · memory **{mem_level}** · workflow **{wf_level}** (F131)",
            (
                f"Scorecard ops fitness: **{'ok' if sc_ops.get('scorecard_ops_ok') else 'idle'}** "
                f"(active={sc_ops.get('active_n', 0)} fed={sc_ops.get('fed_n', 0)} "
                f"fitness={sc_ops.get('fitness_ingested_n', 0)}) (F135)"
            ),
            # F164: package measured hub-archival compound loop into brand surface
            (
                f"Hub-archival loop: **{'ok' if metrics.get('hub_archival_loop_ok') else 'gap'}** "
                f"(util→critic→reprompt→fitness→hub inject · F155–F163)"
            ),
            # F170/F184: GEPA + hub×GEPA compound loop (F165–F183)
            (
                f"GEPA refine loop: **{'ok' if metrics.get('refine_loop_ok') else 'gap'}** "
                f"(refine→dual→promote→decay→revive→compound · F165–F183 / F184)"
            ),
            (
                f"Dual_pass revive gates: revive **{'ok' if metrics.get('refine_dual_revive_ok') else 'gap'}** · "
                f"free-rider MT **{'ok' if metrics.get('free_rider_revive_ok') else 'gap'}** · "
                f"pp-floor **{'ok' if metrics.get('revive_pp_gate_ok') else 'gap'}** · "
                f"LOO **{'ok' if metrics.get('revive_loo_gate_ok') else 'gap'}** · "
                f"hub×GEPA **{'ok' if metrics.get('hub_gepa_compound_ok') else 'gap'}** · "
                f"inject **{'ok' if metrics.get('hub_gepa_compound_inject_ok') else 'gap'}** · "
                f"always **{'ok' if metrics.get('hub_gepa_compound_always_ok') else 'gap'}** · "
                f"reprompt **{'ok' if metrics.get('reprompt_compound_ok') else 'gap'}** · "
                f"fitness **{'ok' if metrics.get('compound_reprompt_fitness_ok') else 'gap'}** · "
                f"pressure **{'ok' if metrics.get('compound_reprompt_pressure_ok') else 'gap'}** (F175–F186)"
            ),
        ],
        "doctor": {
            "doctor_pass": doctor.get("doctor_pass"),
            "recovery_ok": doctor.get("recovery_ok"),
            "recovery_hub_gap_ok": doctor.get("recovery_hub_gap_ok"),
            "recovery_active": doctor.get("recovery_active"),
            "scorecard_ops_ok": doctor.get("scorecard_ops_ok"),
        },
        "scorecard_ops": sc_ops,
        "scorecard_fitness": {
            "ingested_n": sc_fit_report.get("ingested_n"),
            "privacy_ok": sc_fit_report.get("privacy_ok"),
            "scorecard_ops_ok": sc_fit_report.get("scorecard_ops_ok"),
            "skills": sc_fit_report.get("skills"),
        }
        if sc_fit_report
        else None,
        "skill_loop": skill,
        "memory_loop": memory,
        "workflow": {
            "level": wf_level,
            "valid": wf_valid,
            "pct": workflow.get("pct"),
            "pack_install_lists_all": workflow.get("pack_install_lists_all"),
        }
        if workflow
        else None,
        "demote_eval": {
            "eval_pass": demote.get("eval_pass"),
            "demote_rate": demote.get("demote_rate"),
            "weak_demote_ok": demote.get("weak_demote_ok"),
            "hub_gap_demote_ok": demote.get("hub_gap_demote_ok"),
            "paper": demote.get("paper"),
        }
        if demote
        else None,
        "memory_util_eval": {
            "eval_pass": mem_util.get("eval_pass"),
            "delta": mem_util.get("delta"),
            "good_score": mem_util.get("good_score"),
            "weak_score": mem_util.get("weak_score"),
            "paper": mem_util.get("paper"),
        }
        if mem_util
        else None,
        "cmds": {
            "doctor": "python3 scripts/torii.py doctor",
            "scorecard": "python3 scripts/torii.py scorecard",
            "workflow": "python3 scripts/torii.py workflow -- scorecard",
            "demote_eval": "python3 scripts/second_agent_critic.py demote-eval",
            "memory_util_eval": "python3 scripts/memory_tool_audit.py util-eval",
        },
    }
    # write artifact
    dests: list[Path] = []
    if out_dir:
        dests.append(Path(out_dir) / "product-scorecard.json")
    # always soft-write under .torii for ops
    dests.append(root / ".torii" / "product-scorecard.json")
    def _rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(root.resolve()))
        except Exception:
            # never leak home paths into artifacts
            name = p.name
            return name

    for dest in dests:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            # write without absolute paths first
            slim = dict(report)
            slim.pop("artifacts", None)
            dest.write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
            report.setdefault("artifacts", []).append(_rel(dest))
        except OSError:
            pass
    # Soft commercial + product-surface panel for buyers (no hard dependency)
    commercial_panel: dict[str, Any] = {}
    product_panel: dict[str, Any] = {}
    try:
        cpath = root / "scripts" / "commercial_scorecard.py"
        if cpath.is_file():
            cr = subprocess.run(
                [sys.executable, str(cpath), "status"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "TORII_ROOT": str(root)},
            )
            if cr.stdout.strip().startswith("{"):
                commercial_panel = json.loads(cr.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        commercial_panel = {}
    try:
        opath = root / "scripts" / "ops_dashboard.py"
        if opath.is_file():
            # import inventory without full smoke
            sys.path.insert(0, str(root / "scripts"))
            import ops_dashboard as _ops  # type: ignore

            product_panel = _ops.product_surfaces_inventory(root)
    except Exception:
        product_panel = {}

    # BRAND_COST: cost honesty from commercial status (local vault p50s)
    cost_honesty_ok = commercial_panel.get("cost_honesty_ok")
    cost_p50 = commercial_panel.get("cost_p50_usd")
    tts_p50 = None
    try:
        dpath = root / "docs" / "ops" / "dashboard.json"
        if dpath.is_file():
            dj = json.loads(dpath.read_text(encoding="utf-8"))
            cpr = dj.get("cost_per_pr") or {}
            if cost_honesty_ok is None:
                cost_honesty_ok = cpr.get("cost_ok")
            if cost_p50 is None:
                cost_p50 = (cpr.get("cost_usd") or {}).get("p50")
            tts_p50 = (cpr.get("time_to_signal_s") or {}).get("p50")
    except (OSError, json.JSONDecodeError, TypeError):
        pass

    report["commercial"] = {
        "commercial_ok": commercial_panel.get("commercial_ok"),
        "overall_est": commercial_panel.get("overall_est"),
        "surfaces_pass": commercial_panel.get("surfaces_pass"),
        "cost_honesty_ok": cost_honesty_ok,
        "cost_p50_usd": cost_p50,
        "tts_p50_s": tts_p50,
    }
    report["product_surfaces"] = {
        "ok": product_panel.get("ok"),
        "ok_n": product_panel.get("ok_n"),
        "total": product_panel.get("total"),
    }

    # brand markdown snippet (no secrets / no home paths)
    brand_md = root / "docs" / "brand" / "scorecard-metrics.md"
    try:
        lines = [
            "# Torii Gate — product scorecard",
            "",
            f"_Generated: `{report['scored_at']}` · level **{level}** · brand_ready=**{brand_ready}**_",
            "",
            "Buyers start here. Advanced loop metrics (engineers) are below the fold.",
            "",
            "## Commercial readiness (queue + post-queue)",
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| overall_est | **{commercial_panel.get('overall_est')}** / 10 |",
            f"| commercial_ok | {commercial_panel.get('commercial_ok')} |",
            f"| surfaces_pass | {commercial_panel.get('surfaces_pass')} |",
            f"| dual_compound L3 | skill {metrics['skill_loop_level']} · memory {metrics['memory_loop_level']} · workflow {metrics['workflow_level']} |",
            f"| doctor_pass | {metrics['doctor_pass']} |",
            f"| product_surfaces | {product_panel.get('ok_n')}/{product_panel.get('total')} |",
            f"| cost_honesty_ok | {cost_honesty_ok} |",
            f"| cost/PR p50 (USD) | {cost_p50} |",
            f"| time-to-signal p50 (s) | {tts_p50} |",
            "",
            "Measured dogfood cost/latency is **local vault only** (not federated). "
            "Audit: [cost-pr-dashboard](../ops/cost-pr-dashboard.md) · "
            "[commercial Cost honesty](../benchmarks/commercial-scorecard.md) · "
            "[enterprise/PRIVACY](../enterprise/PRIVACY.md).",
            "",
            "Commands: `python3 scripts/torii.py commercial -- status` · "
            "`python3 scripts/torii.py doctor` · "
            "`python3 scripts/torii.py ops -- status`",
            "",
            "Docs: [INSTALL](../INSTALL.md) · [GOLDEN-PATH](../GOLDEN-PATH.md) · "
            "[QUIETER](../QUIETER.md) · [MEMORY](../MEMORY.md) · "
            "[WORKFLOWS](../WORKFLOWS.md) · [commercial-scorecard](../benchmarks/commercial-scorecard.md) · "
            "[FEDERATION](../FEDERATION.md)",
            "",
            "---",
            "",
            "## Advanced — measured loop metrics",
            "",
            report["one_liner"],
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| doctor_pass | {metrics['doctor_pass']} |",
            f"| recovery_ok | {metrics['recovery_ok']} |",
            f"| recovery_hub_gap_ok | {metrics['recovery_hub_gap_ok']} |",
            f"| skill_loop_level | {metrics['skill_loop_level']} |",
            f"| memory_loop_level | {metrics['memory_loop_level']} |",
            f"| workflow_level | {metrics['workflow_level']} |",
            f"| workflow_valid | {metrics['workflow_valid']} |",
            f"| dual_compound_triple_ready | {metrics['dual_compound_triple_ready']} |",
            f"| critic_approve_demote_rate | {metrics['critic_approve_demote_rate']} |",
            f"| weak_approve_demoted | {metrics['weak_approve_demoted']} |",
            f"| hub_gap_idle_demoted | {metrics['hub_gap_idle_demoted']} |",
            f"| recon_warm_hub_idle_demoted | {metrics.get('recon_warm_hub_idle_demoted')} |",
            f"| recon_warm_hub_ok | {metrics.get('recon_warm_hub_ok')} |",
            f"| memory_tool_util_delta | {metrics['memory_tool_util_delta']} |",
            f"| memory_tool_util_good | {metrics['memory_tool_util_good']} |",
            f"| memory_tool_util_weak | {metrics['memory_tool_util_weak']} |",
            # F164: hub-archival compound loop (F155–F163) measured brand surface
            f"| hub_archival_util_ok | {metrics.get('hub_archival_util_ok')} |",
            f"| hub_archival_util_critic_ok | {metrics.get('hub_archival_util_critic_ok')} |",
            f"| hub_archival_hub_ok | {metrics.get('hub_archival_hub_ok')} |",
            f"| hub_archival_hub_inject_ok | {metrics.get('hub_archival_hub_inject_ok')} |",
            f"| hub_archival_fitness_ok | {metrics.get('hub_archival_fitness_ok')} |",
            f"| reprompt_adaptive_ok | {metrics.get('reprompt_adaptive_ok')} |",
            f"| router_synth_ok | {metrics.get('router_synth_ok')} |",
            f"| hub_archival_loop_ok | {metrics.get('hub_archival_loop_ok')} |",
            f"| hub_archival_hub_pressure_idle_demoted | {metrics.get('hub_archival_hub_pressure_idle_demoted')} |",
            # F170: GEPA refine compound loop (F165–F169) brand surface
            f"| skill_refine_ok | {metrics.get('skill_refine_ok')} |",
            f"| skill_refine_attr_ok | {metrics.get('skill_refine_attr_ok')} |",
            f"| refine_dual_ok | {metrics.get('refine_dual_ok')} |",
            f"| refine_promote_ok | {metrics.get('refine_promote_ok')} |",
            f"| refine_dual_hub_ok | {metrics.get('refine_dual_hub_ok')} |",
            f"| refine_loop_ok | {metrics.get('refine_loop_ok')} |",
            f"| refine_dual_decay_ok | {metrics.get('refine_dual_decay_ok')} |",            f"| refine_decay_fed_ok | {metrics.get('refine_decay_fed_ok')} |",
            f"| refine_dual_fail_idle_demoted | {metrics.get('refine_dual_fail_idle_demoted')} |",
            f"| refine_decay_hub_idle_demoted | {metrics.get('refine_decay_hub_idle_demoted')} |",
            f"| refine_dual_revive_ok | {metrics.get('refine_dual_revive_ok')} |",
            f"| free_rider_revive_ok | {metrics.get('free_rider_revive_ok')} |",
            f"| revive_pp_gate_ok | {metrics.get('revive_pp_gate_ok')} |",
            f"| free_rider_revive_idle_demoted | {metrics.get('free_rider_revive_idle_demoted')} |",
            f"| low_pp_revive_idle_demoted | {metrics.get('low_pp_revive_idle_demoted')} |",
            f"| revive_loo_gate_ok | {metrics.get('revive_loo_gate_ok')} |",
            f"| loo_revive_idle_demoted | {metrics.get('loo_revive_idle_demoted')} |",
            f"| hub_gepa_compound_ok | {metrics.get('hub_gepa_compound_ok')} |",
            f"| hub_gepa_compound_idle_demoted | {metrics.get('hub_gepa_compound_idle_demoted')} |",
            f"| hub_gepa_compound_inject_ok | {metrics.get('hub_gepa_compound_inject_ok')} |",
            f"| hub_gepa_compound_always_ok | {metrics.get('hub_gepa_compound_always_ok')} |",
            f"| reprompt_compound_ok | {metrics.get('reprompt_compound_ok')} |",
            f"| compound_reprompt_fitness_ok | {metrics.get('compound_reprompt_fitness_ok')} |",
            f"| compound_reprompt_pressure_ok | {metrics.get('compound_reprompt_pressure_ok')} |",
            "",
            "Source: `python3 scripts/torii.py scorecard` · workflow F131 · demote F128/F151 · util F130 · hub-archival F155–F163 (F164) · GEPA refine F165–F180 (F170/F180).",
            "",
            "These are **measured** offline/ops metrics — not marketing pass rates.",
            "",
        ]
        brand_md.parent.mkdir(parents=True, exist_ok=True)
        brand_md.write_text("\n".join(lines), encoding="utf-8")
        report["brand_md"] = _rel(brand_md)
        # rewrite primary .torii artifact with relative paths
        for dest in dests:
            try:
                dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            except OSError:
                pass
    except OSError:
        pass
    return report


def cmd_scorecard(args: argparse.Namespace) -> int:
    """F129: product brand/ops scorecard with demote-eval metrics."""
    od = None
    if getattr(args, "out_dir", None) and args.out_dir:
        od = Path(args.out_dir)
    elif (os.environ.get("OUT_DIR") or "").strip():
        od = Path(os.environ["OUT_DIR"])
    skip_demote = bool(getattr(args, "shallow", False))
    report = product_scorecard(
        root=_root(),
        run_demote=not skip_demote,
        out_dir=od,
    )
    print(json.dumps(report, indent=2))
    return 0 if report.get("brand_ready") else 1


def cmd_inject_hint(args: argparse.Namespace) -> int:
    section = render_inject_hint()
    if args.prompt:
        p = Path(args.prompt)
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        if MARKER in text:
            import re

            text = re.sub(
                r"<!-- torii-f110-product-cli -->.*?<!-- /torii-f110-product-cli -->\n?",
                section,
                text,
                count=1,
                flags=re.S,
            )
        else:
            text = text.rstrip() + "\n\n" + section
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(json.dumps({"feature": FEATURE, "injected": True, "prompt": args.prompt}))
        return 0
    print(section)
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    h = help_payload()
    help_ok = len(h.get("groups") or []) >= 5 and "memory" in {
        g["group"] for g in h["groups"]
    }
    help_collapse_ok = bool(h.get("help_collapse_ok"))
    help_text = render_help_text()
    help_tiered = (
        "Day-1" in help_text
        and "Day-2" in help_text
        and "Advanced" in help_text
        and "F103" not in help_text
        and "F108" not in help_text
        and "F79" not in help_text
    )
    st = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "status"],
        cwd=str(_root()),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(_root())},
    )
    status_ok = st.returncode == 0
    try:
        status_ok = status_ok and bool(json.loads(st.stdout).get("all_present"))
    except json.JSONDecodeError:
        status_ok = False
    dr = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "doctor"],
        cwd=str(_root()),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(_root())},
        timeout=180,
    )
    doctor_ok = False
    try:
        doctor_ok = bool(json.loads(dr.stdout).get("doctor_pass"))
    except json.JSONDecodeError:
        doctor_ok = False
    hint = render_inject_hint()
    hint_ok = MARKER in hint and "torii.py" in hint
    # dispatch memory help (capture so help text does not pollute fixture JSON)
    disp_r = subprocess.run(
        [sys.executable, str(_scripts_dir(_root()) / "torii_memory.py"), "help"],
        cwd=str(_root()),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(_root())},
        timeout=60,
    )
    dispatch_ok = disp_r.returncode == 0 and "torii_memory" in (disp_r.stdout or "")
    # F129: product scorecard shallow (skip demote for speed) must brand-ready doctor path
    sc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "scorecard", "--shallow"],
        cwd=str(_root()),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(_root())},
        timeout=180,
    )
    scorecard_ok = False
    try:
        scd = json.loads(sc.stdout)
        scorecard_ok = bool(scd.get("brand_ready") or scd.get("metrics", {}).get("doctor_pass"))
    except json.JSONDecodeError:
        scorecard_ok = False
    fixture_pass = all(
        [
            help_ok,
            help_collapse_ok,
            help_tiered,
            status_ok,
            doctor_ok,
            hint_ok,
            dispatch_ok,
            scorecard_ok,
        ]
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_scorecard": "F129",
                "feature_help_collapse": "HELP_CLI_COLLAPSE",
                "fixture_pass": fixture_pass,
                "help_ok": help_ok,
                "help_collapse_ok": help_collapse_ok,
                "help_tiered": help_tiered,
                "day1_groups_n": h.get("day1_groups_n"),
                "status_ok": status_ok,
                "doctor_ok": doctor_ok,
                "hint_ok": hint_ok,
                "dispatch_ok": dispatch_ok,
                "scorecard_ok": scorecard_ok,
                "groups_n": len(h.get("groups") or []),
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv or argv[0] in ("-h", "--help", "help"):
        if "--json" in argv:
            print(json.dumps(help_payload(), indent=2))
        else:
            print(render_help_text())
        return 0

    cmd = argv[0]
    rest = argv[1:]
    if "--" in rest:
        i = rest.index("--")
        passthrough = rest[i + 1 :]
        pre = rest[:i]
    else:
        passthrough = rest
        pre = []

    if cmd == "status":
        p = argparse.ArgumentParser(prog="torii.py status")
        p.add_argument(
            "--json",
            action="store_true",
            help="Print full JSON (default: human text on TTY)",
        )
        p.add_argument(
            "--text",
            action="store_true",
            help="Force human day-2 one-screen (even when piped)",
        )
        p.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Expanded per-surface day-2 lines (default: four buyer beats)",
        )
        ns, _ = p.parse_known_args(pre + passthrough)
        return cmd_status(ns)
    if cmd == "doctor":
        p = argparse.ArgumentParser(prog="torii.py doctor")
        p.add_argument(
            "--json",
            action="store_true",
            help="Print full JSON (default: human text on TTY)",
        )
        p.add_argument(
            "--text",
            action="store_true",
            help="Force human day-2 summary (even when piped)",
        )
        ns, _ = p.parse_known_args(pre + passthrough)
        return cmd_doctor(ns)
    if cmd == "scorecard":
        p = argparse.ArgumentParser()
        p.add_argument("--out-dir", default="")
        p.add_argument(
            "--shallow",
            action="store_true",
            help="Skip demote-eval (doctor+loops only)",
        )
        ns, _ = p.parse_known_args(pre + passthrough)
        return cmd_scorecard(ns)
    if cmd == "inject-hint":
        p = argparse.ArgumentParser()
        p.add_argument("--prompt", default="")
        ns, _ = p.parse_known_args(pre + passthrough)
        return cmd_inject_hint(ns)
    if cmd == "fixture":
        return cmd_fixture(argparse.Namespace())
    if cmd == "help":
        print(render_help_text())
        return 0

    if not enabled() and cmd not in ("help", "status"):
        print(json.dumps({"feature": FEATURE, "enabled": False, "skipped": True}))
        return 0

    if cmd not in GROUPS:
        print(f"Unknown command: {cmd}\n", file=sys.stderr)
        print(render_help_text(), file=sys.stderr)
        return 2

    return run_group(cmd, passthrough)


if __name__ == "__main__":
    raise SystemExit(main())

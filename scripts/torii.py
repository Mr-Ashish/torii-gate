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

# top-level group → script
GROUPS: dict[str, dict[str, Any]] = {
    "memory": {
        "script": "torii_memory.py",
        "help": "Compound memory stack front door (F103–F107)",
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
        "examples": ["gate -- --review review.md", "gate -- --help"],
    },
    "budget": {
        "script": "reprompt_budget.py",
        "help": "Shared soft-re-prompt budget F49+F106+F122 (F108)",
        "examples": ["budget -- status", "budget -- fixture"],
    },
    "skill-loop": {
        "script": "skill_loop_status.py",
        "help": "Skill compound loop L0–L3 readiness",
        "examples": ["skill-loop -- scorecard --shallow", "skill-loop -- fixture"],
    },
    "memory-loop": {
        "script": "memory_loop_status.py",
        "help": "Memory compound loop L0–L3 readiness",
        "examples": ["memory-loop -- scorecard --shallow", "memory-loop -- fixture"],
    },
    "smoke": {
        "script": "smoke-torii-gate.sh",
        "help": "Offline smoke (bash)",
        "examples": ["smoke"],
        "shell": True,
    },
    "workflow": {
        "script": "workflow_as_code.py",
        "help": "Workflows-as-code validate + scorecard (F79/F131)",
        "examples": [
            "workflow -- scorecard",
            "workflow -- validate",
            "workflow -- fixture",
        ],
    },
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
    for name, meta in GROUPS.items():
        groups.append(
            {
                "group": name,
                "script": meta["script"],
                "help": meta["help"],
                "examples": meta.get("examples") or [],
            }
        )
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "entrypoint": "python3 scripts/torii.py",
        "one_liner": "One product front door for Torii Gate (memory · gate · budget · loops).",
        "usage": "python3 scripts/torii.py <group|help|status|doctor> [-- <args>]",
        "groups": groups,
        "builtins": ["help", "status", "doctor", "scorecard", "inject-hint"],
        "scored_at": _now(),
    }


def render_help_text() -> str:
    p = help_payload()
    lines = [
        f"# Torii product CLI ({FEATURE})",
        "",
        p["one_liner"],
        "",
        f"Usage: `{p['usage']}`",
        "",
        "| Group | Script | Purpose |",
        "|-------|--------|---------|",
    ]
    for g in p["groups"]:
        lines.append(f"| `{g['group']}` | `{g['script']}` | {g['help']} |")
    lines += [
        "",
        "Builtins: `help` · `status` · `doctor` · `scorecard` · `inject-hint`",
        "",
        "Examples:",
        "```bash",
        "python3 scripts/torii.py help",
        "python3 scripts/torii.py status",
        "python3 scripts/torii.py doctor",
        "python3 scripts/torii.py scorecard",
        "python3 scripts/torii.py memory -- help",
        'python3 scripts/torii.py memory -- search -- -q "sql injection"',
        "python3 scripts/torii.py budget -- status",
        "python3 scripts/torii.py memory-loop -- scorecard --shallow",
        "```",
        "",
        "Memory-only agents may still use `scripts/torii_memory.py` directly (F103).",
        "",
    ]
    return "\n".join(lines)


def render_inject_hint() -> str:
    return (
        f"{MARKER}\n"
        "## Torii product CLI (F110 — umbrella front door)\n\n"
        "Prefer the **product** entrypoint for discoverability:\n\n"
        "```bash\n"
        "python3 scripts/torii.py help\n"
        "python3 scripts/torii.py memory -- help\n"
        "python3 scripts/torii.py memory -- search -- -q \"theme keywords\"\n"
        "python3 scripts/torii.py memory -- graph -- query --path <file> --hops 2\n"
        "python3 scripts/torii.py budget -- status\n"
        "```\n\n"
        "Memory stack still has `torii_memory.py` (F103). Soft re-prompts share a budget (F108).\n"
        "Still require path:line evidence to block.\n"
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


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    present = {}
    for name, meta in GROUPS.items():
        present[name] = (_scripts_dir(root) / meta["script"]).is_file()
    extras: dict[str, Any] = {}
    # soft memory loop peek
    try:
        r = subprocess.run(
            [
                sys.executable,
                str(_scripts_dir(root) / "memory_loop_status.py"),
                "scorecard",
                "--shallow",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "TORII_ROOT": str(root)},
        )
        if r.returncode == 0 and r.stdout.strip():
            extras["memory_loop"] = json.loads(r.stdout)
    except Exception as exc:
        extras["memory_loop_error"] = str(exc)[:120]
    try:
        r = subprocess.run(
            [sys.executable, str(_scripts_dir(root) / "reprompt_budget.py"), "status"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "TORII_ROOT": str(root)},
        )
        if r.returncode == 0 and r.stdout.strip():
            extras["reprompt_budget"] = json.loads(r.stdout)
    except Exception as exc:
        extras["budget_error"] = str(exc)[:120]
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "root": str(root),
                "groups_present": present,
                "all_present": all(present.values()),
                "memory_cli": (_scripts_dir(root) / "torii_memory.py").is_file(),
                "extras": extras,
                "scored_at": _now(),
            },
            indent=2,
        )
    )
    return 0 if all(present.values()) else 1


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
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_recovery": "F128",
                "feature_recon_warm_hub": "F151",
                "feature_hub_archival_util": "F155",
                "feature_hub_archival_util_critic": "F156",
                "feature_hub_archival_loop": "F163",
                "feature_refine_loop": "F170/F183",
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
                "results": results,
                "scored_at": _now(),
            },
            indent=2,
        )
    )
    return 0 if all_ok else 1


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
    if run_demote and (sd / "second_agent_critic.py").is_file():
        demote_cmd = [
            sys.executable,
            str(sd / "second_agent_critic.py"),
            "demote-eval",
        ]
        if out_dir:
            demote_cmd += ["--out-dir", str(out_dir)]
        demote = _run_json(demote_cmd, timeout=300)
    # F130: memory tool utilization paper pack (Mem0/Letta tool-call discipline)
    if run_demote and (sd / "memory_tool_audit.py").is_file():
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
        "feature_refine_loop": "F170",
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
            # F170/F174/F178: GEPA refine compound loop (F165–F177)
            (
                f"GEPA refine loop: **{'ok' if metrics.get('refine_loop_ok') else 'gap'}** "
                f"(refine→dual→promote→decay→revive→free-rider→pp-floor · F165–F177)"
            ),
            (
                f"Dual_pass revive gates: revive **{'ok' if metrics.get('refine_dual_revive_ok') else 'gap'}** · "
                f"free-rider MT **{'ok' if metrics.get('free_rider_revive_ok') else 'gap'}** · "
                f"pp-floor **{'ok' if metrics.get('revive_pp_gate_ok') else 'gap'}** · "
                f"LOO **{'ok' if metrics.get('revive_loo_gate_ok') else 'gap'}** · "
                f"hub×GEPA **{'ok' if metrics.get('hub_gepa_compound_ok') else 'gap'}** · "
                f"inject **{'ok' if metrics.get('hub_gepa_compound_inject_ok') else 'gap'}** · "
                f"always **{'ok' if metrics.get('hub_gepa_compound_always_ok') else 'gap'}** · "
                f"reprompt **{'ok' if metrics.get('reprompt_compound_ok') else 'gap'}** (F175–F183)"
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
    # brand markdown snippet (no secrets / no home paths)
    brand_md = root / "docs" / "brand" / "scorecard-metrics.md"
    try:
        lines = [
            "# Torii Gate — measured scorecard (F129/F130/F164/F170/F178)",
            "",
            f"_Generated: `{report['scored_at']}` · level **{level}** · brand_ready={brand_ready}_",
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
            f"| refine_dual_decay_ok | {metrics.get('refine_dual_decay_ok')} |",
            f"| refine_decay_fed_ok | {metrics.get('refine_decay_fed_ok')} |",
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
    fixture_pass = all([help_ok, status_ok, doctor_ok, hint_ok, dispatch_ok, scorecard_ok])
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_scorecard": "F129",
                "fixture_pass": fixture_pass,
                "help_ok": help_ok,
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
        return cmd_status(argparse.Namespace())
    if cmd == "doctor":
        return cmd_doctor(argparse.Namespace())
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

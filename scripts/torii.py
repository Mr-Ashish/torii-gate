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


def cmd_doctor(args: argparse.Namespace) -> int:
    """Cheap product doctor: memory + loops + budget + recovery skill readiness."""
    root = _root()
    results = []
    all_ok = True
    recovery_ok: bool | None = None
    recovery_active: list[str] = []
    recovery_hub_gap_ok: bool | None = None

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
            except (json.JSONDecodeError, TypeError):
                recovery_hub_gap_ok = None
            entry: dict[str, Any] = {"check": name, "ok": ok, "rc": r.returncode}
            if name == "skill_loop":
                entry["recovery_ok"] = recovery_ok
                entry["recovery_active"] = recovery_active
                entry["recovery_hub_gap_ok"] = recovery_hub_gap_ok
            results.append(entry)
            if not ok:
                all_ok = False
        except Exception as exc:
            results.append({"check": name, "ok": False, "error": str(exc)[:120]})
            all_ok = False

    # surface last recovery_hub_gap_ok if set on skill_loop entry
    hub_gap = None
    for e in results:
        if e.get("check") == "skill_loop" and "recovery_hub_gap_ok" in e:
            hub_gap = e.get("recovery_hub_gap_ok")
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_recovery": "F128",
                "doctor_pass": all_ok,
                "recovery_ok": recovery_ok,
                "recovery_active": recovery_active,
                "recovery_hub_gap_ok": hub_gap,
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

    # brand headline metrics (privacy-safe floats/bools only)
    metrics = {
        "doctor_pass": doctor_pass,
        "recovery_ok": recovery_ok,
        "recovery_hub_gap_ok": hub_gap_ok,
        "skill_loop_level": skill_level,
        "memory_loop_level": mem_level,
        "critic_approve_demote_rate": demote_rate,
        "weak_approve_demoted": demote.get("weak_demote_ok"),
        "hub_gap_idle_demoted": demote.get("hub_gap_demote_ok"),
        "demote_eval_pass": demote_pass,
        "memory_tool_util_delta": mem_util_delta,
        "memory_tool_util_good": mem_util.get("good_score") if mem_util else None,
        "memory_tool_util_weak": mem_util.get("weak_score") if mem_util else None,
        "memory_util_eval_pass": mem_util_pass,
    }
    brand_ready = bool(
        doctor_pass
        and recovery_ok
        and hub_gap_ok
        and skill_level in ("L2", "L3")
        and (not run_demote or demote_pass)
        and (not run_demote or mem_util_pass)
    )
    # Loop-Ready style level for product surface
    if brand_ready and skill_level == "L3" and demote_pass and mem_util_pass:
        level = "L3"
    elif doctor_pass and recovery_ok:
        level = "L2"
    elif recovery_ok or doctor_pass:
        level = "L1"
    else:
        level = "L0"

    report: dict[str, Any] = {
        "feature": "F130",
        "feature_cli": FEATURE,
        "feature_scorecard": "F129",
        "schema": SCHEMA,
        "scored_at": _now(),
        "level": level,
        "brand_ready": brand_ready,
        "metrics": metrics,
        "one_liner": (
            "Measured gate readiness: doctor + hub-gap critic + "
            f"demote_rate={demote_rate} + memory_util_delta={mem_util_delta}."
        ),
        "brand_lines": [
            f"Doctor pass: **{doctor_pass}** · recovery skills **{'ok' if recovery_ok else 'gap'}**",
            f"Hub gap critic path: **{'ok' if hub_gap_ok else 'gap'}** (F127/F128)",
            f"Critic APPROVE demote rate (offline pack): **{demote_rate}**",
            f"Memory tool util delta (good−weak): **{mem_util_delta}** (F130)",
            f"Skill loop **{skill_level}** · Memory loop **{mem_level}**",
        ],
        "doctor": {
            "doctor_pass": doctor.get("doctor_pass"),
            "recovery_ok": doctor.get("recovery_ok"),
            "recovery_hub_gap_ok": doctor.get("recovery_hub_gap_ok"),
            "recovery_active": doctor.get("recovery_active"),
        },
        "skill_loop": skill,
        "memory_loop": memory,
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
            "# Torii Gate — measured scorecard (F129/F130)",
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
            f"| critic_approve_demote_rate | {metrics['critic_approve_demote_rate']} |",
            f"| weak_approve_demoted | {metrics['weak_approve_demoted']} |",
            f"| hub_gap_idle_demoted | {metrics['hub_gap_idle_demoted']} |",
            f"| memory_tool_util_delta | {metrics['memory_tool_util_delta']} |",
            f"| memory_tool_util_good | {metrics['memory_tool_util_good']} |",
            f"| memory_tool_util_weak | {metrics['memory_tool_util_weak']} |",
            "",
            "Source: `python3 scripts/torii.py scorecard` · demote F128 · memory util F130.",
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

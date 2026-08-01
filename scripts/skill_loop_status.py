#!/usr/bin/env python3
"""F91: Skill compound loop readiness scorecard (route→hit→fitness→dual→attr→inject).

Research / product drivers:
  - Loop Engineering readiness scorecards: explicit stages, L0–L3
  - F90 brand packaged the skill loop; install/ops still could not answer
    "is the skill path ready on this checkout?"
  - Prior F79 scorecard covered pack scripts but not skill-loop health

Product thesis:
  Highest ROI packaging/ops slice: **one deterministic status** that checks
  scripts, active skills, dual contribution, attribution ledger hooks, and
  install pack presence — so Hub71 demos and target installs prove the loop.

Commands:
  status    — full JSON readiness
  scorecard — compact level + stage flags
  fixture   — hermetic offline pass on product tree
  markdown  — short MD block for install-guide

Env:
  TORII_ROOT
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F91"
SCHEMA = 1

# Skill compound loop stages (F84–F89 + F114–F122 recovery loop)
LOOP_STAGES: list[dict[str, Any]] = [
    {
        "id": "route",
        "feature": "F84",
        "script": "skill_router.py",
        "one_liner": "Progressive skill inject by path themes",
    },
    {
        "id": "hit",
        "feature": "F84/F114",
        "script": "skill_router.py",
        "cmd": ["score", "--help"],
        "one_liner": "Post-run prose + tool-outcome hit scoring",
        "soft_cmd": True,
    },
    {
        "id": "fitness",
        "feature": "F85/F116",
        "script": "skill_fitness.py",
        "one_liner": "Hit-rate ledger; tool-hit demote shield + federate",
    },
    {
        "id": "dual",
        "feature": "F86/F115",
        "script": "skill_dual_rollout.py",
        "one_liner": "With vs ablated contribution_pp + tool contrib",
    },
    {
        "id": "attr",
        "feature": "F88/F115",
        "script": "skill_attribution.py",
        "one_liner": "LOO free-rider + tool_hit attribution + adopt gate",
    },
    {
        "id": "inject",
        "feature": "F89/F119/F120",
        "script": "skill_router.py",
        "one_liner": "Always budget + compact full-body inject",
        "needs_attr_router": True,
    },
    {
        "id": "adopt_gate",
        "feature": "F87/F118",
        "script": "skill_auto_adopt.py",
        "one_liner": "Dual+tool-attr gates before auto-adopt",
    },
    {
        "id": "recovery_util",
        "feature": "F121",
        "script": "skill_router.py",
        "cmd": ["util", "--help"],
        "one_liner": "Recovery skill tool utilization (inject ≠ tools)",
        "soft_cmd": True,
    },
    {
        "id": "recovery_reprompt",
        "feature": "F122",
        "script": "reprompt_budget.py",
        "one_liner": "Shared budget includes f122 recovery re-prompt kind",
    },
    {
        "id": "recovery_hub",
        "feature": "F125",
        "script": "skill_router.py",
        "cmd": ["hub-score", "--help"],
        "one_liner": "Hub recovery-util post-score → always priority compound",
        "soft_cmd": True,
    },
    {
        "id": "recovery_hub_gap",
        "feature": "F127/F128",
        "script": "second_agent_critic.py",
        "cmd": ["demote-eval", "--help"],
        "one_liner": "Hub gap critic + paper demote-rate eval",
        "soft_cmd": True,
    },
]


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scripts(root: Path) -> Path:
    return root / "scripts"


def check_script(root: Path, name: str) -> bool:
    return (_scripts(root) / name).is_file()


def active_skills(root: Path) -> list[str]:
    d = root / "agent" / "skills" / "active"
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.md") if p.name != "README.md")


def pack_lists_script(root: Path, name: str) -> bool:
    install = root / "scripts" / "install-torii.sh"
    if not install.is_file():
        return False
    text = install.read_text(encoding="utf-8", errors="replace")
    return name in text


def run_soft_fixture(root: Path, script: str, args: list[str]) -> dict[str, Any]:
    path = _scripts(root) / script
    if not path.is_file():
        return {"ok": False, "error": "missing_script"}
    try:
        r = subprocess.run(
            [sys.executable, str(path), *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "TORII_ROOT": str(root)},
        )
        entry: dict[str, Any] = {
            "ok": r.returncode == 0,
            "rc": r.returncode,
        }
        try:
            data = json.loads(r.stdout)
            entry["data_keys"] = list(data.keys())[:12]
            if "fixture_pass" in data:
                entry["fixture_pass"] = data["fixture_pass"]
                entry["ok"] = entry["ok"] and bool(data["fixture_pass"])
            if "dual_pass" in data:
                entry["dual_pass"] = data["dual_pass"]
                entry["ok"] = entry["ok"] and bool(data["dual_pass"])
            if "skill_contribution_pp" in data:
                entry["skill_contribution_pp"] = data["skill_contribution_pp"]
                if float(data["skill_contribution_pp"] or 0) <= 0:
                    entry["ok"] = False
            if "passed" in data and "gates" in data:
                entry["passed"] = data["passed"]
                entry["ok"] = entry["ok"] and bool(data["passed"])
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return entry
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def assess(root: Path | None = None, *, deep: bool = True) -> dict[str, Any]:
    root = root or _root()
    stages_out: list[dict[str, Any]] = []
    for st in LOOP_STAGES:
        script = st["script"]
        present = check_script(root, script)
        in_pack = pack_lists_script(root, script)
        entry: dict[str, Any] = {
            "id": st["id"],
            "feature": st["feature"],
            "script": script,
            "one_liner": st["one_liner"],
            "script_ok": present,
            "pack_ok": in_pack,
            "ok": present and in_pack,
        }
        stages_out.append(entry)

    skills = active_skills(root)
    skills_ok = len(skills) >= 1
    # F123/F155: dual-gate recovery skills that teach tool CLIs
    # F155: hub-archival joins recovery stack after F154 always adopt
    recovery_active = [
        s
        for s in (
            "skill-prefer-memory-cli-early",
            "skill-prefer-product-cli",
            "skill-prefer-critic-early",
            "skill-prefer-hub-archival-early",  # F155
        )
        if s in skills
    ]
    # L3 still requires classic 3; hub-archival is additive surface
    recovery_classic_n = sum(
        1
        for s in recovery_active
        if s
        in (
            "skill-prefer-memory-cli-early",
            "skill-prefer-product-cli",
            "skill-prefer-critic-early",
        )
    )
    recovery_ok = recovery_classic_n >= 3
    hub_archival_util_ok = "skill-prefer-hub-archival-early" in recovery_active
    # F135: scorecard-gap ops skills (soft; not required for L3)
    scorecard_active = [
        s
        for s in skills
        if any(
            x in s
            for x in (
                "scorecard",
                "demote-eval",
                "memory-util",
                "hub-gap",
                "dual-compound",
                "workflow-scorecard",
            )
        )
    ]
    # fitness ledger scorecard ingest presence
    scorecard_fitness_n = 0
    fit_path = root / ".torii" / "skill-fitness.json"
    if fit_path.is_file():
        try:
            import json as _json

            led = _json.loads(fit_path.read_text(encoding="utf-8"))
            scorecard_fitness_n = sum(
                1
                for e in (led.get("skills") or {}).values()
                if isinstance(e, dict)
                and (
                    e.get("scorecard_ops")
                    or int(e.get("scorecard_ingested_n") or 0) >= 1
                )
            )
        except Exception:
            scorecard_fitness_n = 0
    fed_sc = root / "memory" / "federation" / "scorecard-skill-signals.json"
    scorecard_fed_ok = fed_sc.is_file()
    scorecard_ops_ok = (
        len(scorecard_active) >= 1 or scorecard_fitness_n >= 1 or scorecard_fed_ok
    )

    # assemble-context / run-torii-review / hermes / save-trace wiring
    assemble = (root / "scripts" / "assemble-context.sh").read_text(
        encoding="utf-8", errors="replace"
    ) if (root / "scripts" / "assemble-context.sh").is_file() else ""
    run_sh = (root / "scripts" / "run-torii-review.sh").read_text(
        encoding="utf-8", errors="replace"
    ) if (root / "scripts" / "run-torii-review.sh").is_file() else ""
    hermes_sh = (root / "scripts" / "run-hermes-review.sh").read_text(
        encoding="utf-8", errors="replace"
    ) if (root / "scripts" / "run-hermes-review.sh").is_file() else ""
    save_tr = (root / "scripts" / "save-trace.sh").read_text(
        encoding="utf-8", errors="replace"
    ) if (root / "scripts" / "save-trace.sh").is_file() else ""
    wire = {
        "assemble_skill_router": "skill_router" in assemble or "SKILL_ROUTER" in assemble,
        "run_skill_router_score": "skill_router.py" in run_sh and "score" in run_sh,
        "run_skill_fitness": "skill_fitness.py" in run_sh,
        "run_skill_attribution": "skill_attribution.py" in run_sh,
        "run_skill_dual_promote": "skill_dual_rollout.py" in run_sh,
        "run_recovery_util": "recovery_skill_util" in run_sh or "util --out-dir" in run_sh,
        # F136: scorecard skill util mid-run
        "run_scorecard_util": "scorecard-util" in run_sh or "scorecard_skill_util" in run_sh,
        "save_trace_scorecard_util": "scorecard-skill-util.json" in save_tr,
        "run_scorecard_hub": "scorecard-hub-score" in run_sh or "scorecard_hub" in run_sh,
        "save_trace_scorecard_hub": "scorecard-hub-score.json" in save_tr,
        "hermes_f122_reprompt": "F122" in hermes_sh or "recovery-skill-reprompt" in hermes_sh,
        # F157: hub-archival util soft re-prompt under F108
        "hermes_f157_reprompt": "F157" in hermes_sh or "hub_archival_util_gap" in hermes_sh
        or "f157" in hermes_sh,
        "save_trace_recovery": "recovery-skill-util.json" in save_tr,
        # F125: hub recovery post-score compound (router inject path + trace archive)
        "save_trace_recovery_hub": "recovery-hub-score.json" in save_tr,
        "router_hub_score_cmd": "hub-score" in (
            (root / "scripts" / "skill_router.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_router.py").is_file()
            else ""
        ),
        # F127/F128: hub gap critic wired in second-agent panel + demote-eval
        "critic_hub_gap": "f127_hub_gap" in (
            (root / "scripts" / "second_agent_critic.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "second_agent_critic.py").is_file()
            else ""
        ),
        "critic_demote_eval": "demote-eval" in (
            (root / "scripts" / "second_agent_critic.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "second_agent_critic.py").is_file()
            else ""
        ),
        "critic_scorecard_hub_gap": "f139_scorecard_hub_gap" in (
            (root / "scripts" / "second_agent_critic.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "second_agent_critic.py").is_file()
            else ""
        ),
        # F151: recon-warm hub critic + demote-eval paper path
        "critic_recon_warm_hub": "f150_recon_warm_hub" in (
            (root / "scripts" / "second_agent_critic.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "second_agent_critic.py").is_file()
            else ""
        ),
        "demote_eval_recon_warm": "recon_warm_hub_idle_approve" in (
            (root / "scripts" / "second_agent_critic.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "second_agent_critic.py").is_file()
            else ""
        ),
        # F156: hub-archival util gap critic + demote-eval paper path
        "critic_hub_archival_util": "f156_hub_archival_util" in (
            (root / "scripts" / "second_agent_critic.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "second_agent_critic.py").is_file()
            else ""
        ),
        "demote_eval_hub_archival": "hub_archival_util_idle_approve" in (
            (root / "scripts" / "second_agent_critic.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "second_agent_critic.py").is_file()
            else ""
        ),
    }
    wire_ok = all(wire.values())

    deep_results: dict[str, Any] = {}
    if deep:
        deep_results["dual"] = run_soft_fixture(
            root, "skill_dual_rollout.py", ["dual"]
        )
        deep_results["attr_fixture"] = run_soft_fixture(
            root, "skill_attribution.py", ["fixture"]
        )
        deep_results["router_fixture"] = run_soft_fixture(
            root, "skill_router.py", ["fixture"]
        )
        # fitness fixture is heavier but quick
        deep_results["fitness_fixture"] = run_soft_fixture(
            root, "skill_fitness.py", ["fixture"]
        )
        deep_results["budget_fixture"] = run_soft_fixture(
            root, "reprompt_budget.py", ["fixture"]
        )

    deep_ok = True
    if deep:
        deep_ok = all(v.get("ok") for v in deep_results.values()) if deep_results else False

    stage_ok_n = sum(1 for s in stages_out if s["ok"])
    stage_total = len(stages_out)
    # readiness scoring
    points = 0
    points += stage_ok_n
    points += 1 if skills_ok else 0
    points += 1 if recovery_ok else 0  # F123
    points += 1 if wire_ok else 0
    points += 2 if deep_ok else 0
    max_points = stage_total + 1 + 1 + 1 + 2
    pct = round(100.0 * points / max_points, 1) if max_points else 0.0
    if pct >= 95 and deep_ok and skills_ok and wire_ok and recovery_ok:
        level = "L3"
    elif pct >= 75:
        level = "L2"
    elif pct >= 50:
        level = "L1"
    else:
        level = "L0"

    return {
        "feature": FEATURE,
        "feature_recovery": "F128",
        "schema": SCHEMA,
        "loop": "route → hit → fitness → dual → attr → inject → util → re-prompt → hub → critic demote",
        "scored_at": _now(),
        "level": level,
        "recovery_active": recovery_active,
        "recovery_ok": recovery_ok,
        "recovery_hub_ok": bool(wire.get("save_trace_recovery_hub"))
        and bool(wire.get("router_hub_score_cmd")),
        "recovery_hub_gap_ok": bool(wire.get("critic_hub_gap"))
        and bool(wire.get("critic_demote_eval")),
        "recon_warm_hub_ok": bool(wire.get("critic_recon_warm_hub"))
        and bool(wire.get("demote_eval_recon_warm")),
        "feature_recon_warm_hub": "F151",
        # F155: hub-archival recovery util membership (inject ≠ hub_boost tools)
        "hub_archival_util_ok": hub_archival_util_ok,
        "feature_hub_archival_util": "F155",
        # F156: critic demote when hub-archival inject ≠ hub_boost
        "hub_archival_util_critic_ok": bool(wire.get("critic_hub_archival_util"))
        and bool(wire.get("demote_eval_hub_archival")),
        "feature_hub_archival_util_critic": "F156",
        "hub_archival_reprompt_ok": bool(wire.get("hermes_f157_reprompt")),
        "feature_hub_archival_reprompt": "F157",
        # F159: adaptive F108 dual-recovery slot (f106↔f157)
        "reprompt_adaptive_ok": "ensure_adaptive_slot" in (
            (root / "scripts" / "reprompt_budget.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "reprompt_budget.py").is_file()
            else ""
        )
        and "F159" in (
            (root / "scripts" / "reprompt_budget.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "reprompt_budget.py").is_file()
            else ""
        ),
        "feature_reprompt_adaptive": "F159",
        # F160: synthesize skill-router when bench skips assemble
        "router_synth_ok": "ensure_skill_router_doc" in (
            (root / "scripts" / "skill_router.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_router.py").is_file()
            else ""
        )
        and "F160" in (
            (root / "scripts" / "skill_router.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_router.py").is_file()
            else ""
        )
        and "f160_skill_router" in (
            (root / "scripts" / "bench_security_gate.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "bench_security_gate.py").is_file()
            else ""
        ),
        "feature_router_synth": "F160",
        # F161: multi-tenant hub-archival gap pressure
        "hub_archival_hub_ok": "post_score_hub_archival_hub" in (
            (root / "scripts" / "skill_router.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_router.py").is_file()
            else ""
        )
        and "F161" in (
            (root / "scripts" / "skill_router.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_router.py").is_file()
            else ""
        ),
        "feature_hub_archival_hub": "F161",
        # F162: inject hub-archival hub pressure into prompt
        "hub_archival_hub_inject_ok": "inject_hub_archival_hub_into_prompt" in (
            (root / "scripts" / "skill_router.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_router.py").is_file()
            else ""
        )
        and "torii-f162-hub-archival-hub" in (
            (root / "scripts" / "skill_router.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_router.py").is_file()
            else ""
        )
        and "hub_archival_hub_pressure_idle_approve" in (
            (root / "scripts" / "second_agent_critic.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "second_agent_critic.py").is_file()
            else ""
        ),
        "feature_hub_archival_hub_inject": "F162",
        # F163: hermes soft fitness cycle after util
        "hermes_hub_archival_fitness_cycle": "ingest-hub-archival" in hermes_sh
        and "skill_fitness.py" in hermes_sh
        and "F163" in hermes_sh,
        "feature_hub_archival_loop": "F163",
        # F165: GEPA-lite skill body refine from util traces (Hermes self-evolution)
        "hermes_skill_refine": "refine-from-util" in hermes_sh
        and "F165" in hermes_sh
        and "self_evolve.py" in hermes_sh,
        "skill_refine_ok": "refine_from_util" in (
            (root / "scripts" / "self_evolve.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "self_evolve.py").is_file()
            else ""
        )
        and "constraint_validate_skill" in (
            (root / "scripts" / "self_evolve.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "self_evolve.py").is_file()
            else ""
        )
        and "refine-from-util" in hermes_sh,
        "feature_skill_refine": "F165",
        # F166: refine dual-gate LOO floor + fitness shield
        "skill_refine_attr_ok": "refine_attr_enabled" in (
            (root / "scripts" / "skill_attribution.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_attribution.py").is_file()
            else ""
        )
        and "_load_refined_skills" in (
            (root / "scripts" / "skill_attribution.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_attribution.py").is_file()
            else ""
        )
        and "ingest_refine" in (
            (root / "scripts" / "skill_fitness.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_fitness.py").is_file()
            else ""
        )
        and "ingest-refine" in hermes_sh
        and "F166" in hermes_sh,
        "feature_skill_refine_attr": "F166",
        # F158: fitness ledger ingest/demote for hub-archival util
        "hub_archival_fitness_ok": "ingest_hub_archival_util" in (
            (root / "scripts" / "skill_fitness.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_fitness.py").is_file()
            else ""
        )
        and "F158" in (
            (root / "scripts" / "skill_fitness.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "skill_fitness.py").is_file()
            else ""
        ),
        "feature_hub_archival_fitness": "F158",
        # F163 compound: full hub-archival loop wired (soft product/doctor surface)
        "hub_archival_loop_ok": bool(
            hub_archival_util_ok
            and bool(wire.get("critic_hub_archival_util"))
            and bool(wire.get("demote_eval_hub_archival"))
            and "post_score_hub_archival_hub"
            in (
                (root / "scripts" / "skill_router.py").read_text(
                    encoding="utf-8", errors="replace"
                )
                if (root / "scripts" / "skill_router.py").is_file()
                else ""
            )
            and "inject_hub_archival_hub_into_prompt"
            in (
                (root / "scripts" / "skill_router.py").read_text(
                    encoding="utf-8", errors="replace"
                )
                if (root / "scripts" / "skill_router.py").is_file()
                else ""
            )
            and "ensure_skill_router_doc"
            in (
                (root / "scripts" / "skill_router.py").read_text(
                    encoding="utf-8", errors="replace"
                )
                if (root / "scripts" / "skill_router.py").is_file()
                else ""
            )
            and "ensure_adaptive_slot"
            in (
                (root / "scripts" / "reprompt_budget.py").read_text(
                    encoding="utf-8", errors="replace"
                )
                if (root / "scripts" / "reprompt_budget.py").is_file()
                else ""
            )
            and "ingest_hub_archival_util"
            in (
                (root / "scripts" / "skill_fitness.py").read_text(
                    encoding="utf-8", errors="replace"
                )
                if (root / "scripts" / "skill_fitness.py").is_file()
                else ""
            )
            and "ingest-hub-archival" in hermes_sh
        ),
        "feature_scorecard_ops": "F135",
        "scorecard_active": scorecard_active,
        "scorecard_ops_ok": scorecard_ops_ok,
        "scorecard_fitness_n": scorecard_fitness_n,
        "scorecard_fed_ok": scorecard_fed_ok,
        "pct": pct,
        "points": points,
        "max_points": max_points,
        "ready": level in ("L2", "L3") and stage_ok_n == stage_total,
        "stages": stages_out,
        "stages_ok": stage_ok_n,
        "stages_total": stage_total,
        "active_skills": skills,
        "active_skills_n": len(skills),
        "skills_ok": skills_ok,
        "wiring": wire,
        "wiring_ok": wire_ok,
        "deep": deep_results if deep else None,
        "deep_ok": deep_ok if deep else None,
        "one_liner": "Skills that do not contribute do not ship in the next prompt.",
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"## Skill compound loop readiness ({FEATURE})",
        "",
        f"**Loop:** `{report.get('loop')}`  ·  **Level:** {report.get('level')}  ·  **{report.get('pct')}%**",
        "",
        report.get("one_liner") or "",
        "",
        "| Stage | Feature | Script | Pack | OK |",
        "|-------|---------|--------|:----:|:--:|",
    ]
    for s in report.get("stages") or []:
        lines.append(
            f"| {s.get('id')} | {s.get('feature')} | `{s.get('script')}` | "
            f"{'✓' if s.get('pack_ok') else '·'} | {'✓' if s.get('ok') else '✗'} |"
        )
    lines.extend(
        [
            "",
            f"- Active skills: **{report.get('active_skills_n')}** "
            f"({', '.join((report.get('active_skills') or [])[:6]) or 'none'})",
            f"- Recovery skills (memory/product/critic[+hub-archival]): **{'ok' if report.get('recovery_ok') else 'gap'}** "
            f"({', '.join(report.get('recovery_active') or []) or 'none'})",
            f"- Hub-archival recovery util (F155): **{'ok' if report.get('hub_archival_util_ok') else 'gap'}**",
            f"- Hub-archival util critic/demote-eval (F156): **{'ok' if report.get('hub_archival_util_critic_ok') else 'gap'}**",
            f"- Hub-archival util soft re-prompt (F157): **{'ok' if report.get('hub_archival_reprompt_ok') else 'gap'}**",
            f"- F108 adaptive dual-recovery slot (F159): **{'ok' if report.get('reprompt_adaptive_ok') else 'gap'}**",
            f"- Skill-router synth for bench util (F160): **{'ok' if report.get('router_synth_ok') else 'gap'}**",
            f"- Hub-archival multi-tenant hub pressure (F161): **{'ok' if report.get('hub_archival_hub_ok') else 'gap'}**",
            f"- Hub-archival hub inject + demote-eval (F162): **{'ok' if report.get('hub_archival_hub_inject_ok') else 'gap'}**",
            f"- Hub-archival fitness demote/boost (F158): **{'ok' if report.get('hub_archival_fitness_ok') else 'gap'}**",
            f"- Hub-archival compound loop (F163): **{'ok' if report.get('hub_archival_loop_ok') else 'gap'}** "
            f"(fitness cycle hermes: **{'ok' if report.get('hermes_hub_archival_fitness_cycle') else 'gap'}**)",
            f"- GEPA-lite skill refine-from-util (F165): **{'ok' if report.get('skill_refine_ok') else 'gap'}** "
            f"(hermes: **{'ok' if report.get('hermes_skill_refine') else 'gap'}**)",
            f"- Refine dual-gate LOO floor + fitness shield (F166): **{'ok' if report.get('skill_refine_attr_ok') else 'gap'}**",
            f"- Recovery hub gap critic/demote-eval (F128): **{'ok' if report.get('recovery_hub_gap_ok') else 'gap'}**",
            f"- Recon-warm hub critic/demote-eval (F151): **{'ok' if report.get('recon_warm_hub_ok') else 'gap'}**",
            f"- Wiring (assemble/run/hermes/save-trace): **{'ok' if report.get('wiring_ok') else 'gap'}**",
            f"- Deep fixtures: **{'ok' if report.get('deep_ok') else 'skipped/fail'}**",
            f"- Ready: **{report.get('ready')}**",
            "",
        ]
    )
    return "\n".join(lines)


def cmd_status(args: argparse.Namespace) -> int:
    deep = not args.shallow
    report = assess(_root(), deep=deep)
    print(json.dumps(report, indent=2))
    return 0 if report.get("ready") else 1


def cmd_scorecard(args: argparse.Namespace) -> int:
    report = assess(_root(), deep=not args.shallow)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_recovery": report.get("feature_recovery") or "F123",
                "level": report["level"],
                "pct": report["pct"],
                "ready": report["ready"],
                "stages_ok": f"{report['stages_ok']}/{report['stages_total']}",
                "skills_n": report["active_skills_n"],
                "recovery_ok": report.get("recovery_ok"),
                "recovery_active": report.get("recovery_active"),
                "recovery_hub_ok": report.get("recovery_hub_ok"),
                "recovery_hub_gap_ok": report.get("recovery_hub_gap_ok"),
                "recon_warm_hub_ok": report.get("recon_warm_hub_ok"),
                "feature_recon_warm_hub": report.get("feature_recon_warm_hub"),
                "hub_archival_util_ok": report.get("hub_archival_util_ok"),
                "feature_hub_archival_util": report.get("feature_hub_archival_util"),
                "hub_archival_util_critic_ok": report.get("hub_archival_util_critic_ok"),
                "feature_hub_archival_util_critic": report.get(
                    "feature_hub_archival_util_critic"
                ),
                "hub_archival_reprompt_ok": report.get("hub_archival_reprompt_ok"),
                "feature_hub_archival_reprompt": report.get(
                    "feature_hub_archival_reprompt"
                ),
                "reprompt_adaptive_ok": report.get("reprompt_adaptive_ok"),
                "feature_reprompt_adaptive": report.get("feature_reprompt_adaptive"),
                "router_synth_ok": report.get("router_synth_ok"),
                "feature_router_synth": report.get("feature_router_synth"),
                "hub_archival_hub_ok": report.get("hub_archival_hub_ok"),
                "feature_hub_archival_hub": report.get("feature_hub_archival_hub"),
                "hub_archival_hub_inject_ok": report.get("hub_archival_hub_inject_ok"),
                "feature_hub_archival_hub_inject": report.get(
                    "feature_hub_archival_hub_inject"
                ),
                "hub_archival_fitness_ok": report.get("hub_archival_fitness_ok"),
                "feature_hub_archival_fitness": report.get(
                    "feature_hub_archival_fitness"
                ),
                "hub_archival_loop_ok": report.get("hub_archival_loop_ok"),
                "hermes_hub_archival_fitness_cycle": report.get(
                    "hermes_hub_archival_fitness_cycle"
                ),
                "feature_hub_archival_loop": report.get("feature_hub_archival_loop"),
                "skill_refine_ok": report.get("skill_refine_ok"),
                "hermes_skill_refine": report.get("hermes_skill_refine"),
                "feature_skill_refine": report.get("feature_skill_refine") or "F165",
                "skill_refine_attr_ok": report.get("skill_refine_attr_ok"),
                "feature_skill_refine_attr": report.get("feature_skill_refine_attr")
                or "F166",
                "feature_scorecard_ops": report.get("feature_scorecard_ops"),
                "scorecard_ops_ok": report.get("scorecard_ops_ok"),
                "scorecard_active": report.get("scorecard_active"),
                "wiring_ok": report["wiring_ok"],
                "deep_ok": report.get("deep_ok"),
                "loop": report["loop"],
            },
            indent=2,
        )
    )
    return 0 if report.get("ready") else 1


def cmd_markdown(args: argparse.Namespace) -> int:
    report = assess(_root(), deep=not args.shallow)
    md = to_markdown(report)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(json.dumps({"feature": FEATURE, "wrote": args.out, "level": report["level"]}))
    else:
        sys.stdout.write(md)
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    report = assess(_root(), deep=True)
    # product tree must be L2+ with all stage scripts
    fixture_pass = bool(
        report.get("stages_ok") == report.get("stages_total")
        and report.get("skills_ok")
        and report.get("wiring_ok")
        and report.get("deep_ok")
        and report.get("recovery_ok")
        and report.get("recovery_hub_gap_ok")
        and report.get("recon_warm_hub_ok")
        and report.get("level") in ("L2", "L3")
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_recovery": "F128",
                "fixture_pass": fixture_pass,
                "level": report["level"],
                "pct": report["pct"],
                "stages_ok": report["stages_ok"],
                "stages_total": report["stages_total"],
                "skills_n": report["active_skills_n"],
                "recovery_ok": report.get("recovery_ok"),
                "recovery_active": report.get("recovery_active"),
                "recovery_hub_ok": report.get("recovery_hub_ok"),
                "recovery_hub_gap_ok": report.get("recovery_hub_gap_ok"),
                "recon_warm_hub_ok": report.get("recon_warm_hub_ok"),
                "feature_recon_warm_hub": report.get("feature_recon_warm_hub"),
                "hub_archival_util_ok": report.get("hub_archival_util_ok"),
                "feature_hub_archival_util": "F155",
                "hub_archival_util_critic_ok": report.get("hub_archival_util_critic_ok"),
                "feature_hub_archival_util_critic": "F156",
                "hub_archival_reprompt_ok": report.get("hub_archival_reprompt_ok"),
                "feature_hub_archival_reprompt": "F157",
                "reprompt_adaptive_ok": report.get("reprompt_adaptive_ok"),
                "feature_reprompt_adaptive": "F159",
                "router_synth_ok": report.get("router_synth_ok"),
                "feature_router_synth": "F160",
                "hub_archival_hub_ok": report.get("hub_archival_hub_ok"),
                "feature_hub_archival_hub": "F161",
                "hub_archival_hub_inject_ok": report.get("hub_archival_hub_inject_ok"),
                "feature_hub_archival_hub_inject": "F162",
                "hub_archival_fitness_ok": report.get("hub_archival_fitness_ok"),
                "feature_hub_archival_fitness": "F158",
                "hub_archival_loop_ok": report.get("hub_archival_loop_ok"),
                "hermes_hub_archival_fitness_cycle": report.get(
                    "hermes_hub_archival_fitness_cycle"
                ),
                "feature_hub_archival_loop": "F163",
                "skill_refine_ok": report.get("skill_refine_ok"),
                "hermes_skill_refine": report.get("hermes_skill_refine"),
                "feature_skill_refine": "F165",
                "skill_refine_attr_ok": report.get("skill_refine_attr_ok"),
                "feature_skill_refine_attr": "F166",
                "wiring_ok": report["wiring_ok"],
                "deep_ok": report["deep_ok"],
                "ready": report["ready"],
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F91 skill compound loop readiness")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, func, help_ in (
        ("status", cmd_status, "Full readiness JSON"),
        ("scorecard", cmd_scorecard, "Compact scorecard"),
        ("fixture", cmd_fixture, "Hermetic product-tree fixture"),
        ("markdown", cmd_markdown, "Markdown for install-guide"),
    ):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument(
            "--shallow",
            action="store_true",
            help="Skip deep dual/attr/router fixtures",
        )
        if name == "markdown":
            sp.add_argument("--out", default="")
        sp.set_defaults(func=func)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

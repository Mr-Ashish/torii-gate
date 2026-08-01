#!/usr/bin/env python3
"""F85/F116/F126/F135: Skill fitness ledger — demote zombies + tool/scorecard shields.

Research drivers (2026):
  - FederatedSkill (arXiv 2606.03143): skill library as federation unit; share
    privacy-safe patches/themes, not raw trajectories — up to +44% success.
  - Agent Skill Evaluation & Evolution (arXiv 2606.11435): longitudinal skill
    quality tracking; dual-rollout with/without skills; drop skills that never
    contribute (dead library entries).
  - Trajectory eval 2026 / Mem2Act: tool trajectory is a first-class quality
    signal — F114 tool_hit_n must compound into demote/boost/federate, not
    sit as an inert counter.
  - SigLeak / contrastive skill signatures: tool-outcome themes are portable
    skill evidence without raw trajectories.
  - MUSE-Autoskill: skill lifecycle create → evaluate → refine/demote.
  - CoEvoSkills / EvoSkills: adopted skills need fitness feedback or they rot.
  - Prior Torii F84: skill-hits.json per run — no durable ledger, no demote,
    no hub federation of skill themes.
  - F134: scorecard skills federate themes but never entered the fitness ledger
    (recovery hub had F126; scorecard ops did not).

Product thesis:
  Measure (F84) without action is theater. Highest ROI: compound hit rates into
  a local fitness ledger, **soft-demote** chronically low-hit skills from full
  progressive inject (index-only), **shield tool-effective recovery skills**
  (F116), **ingest F134 scorecard skill themes into fitness** (F135), boost
  high-hit + tool-hit skills in the router, and emit F77-compatible federated
  skill themes (id + hits + tool_outcome tags only).

Commands:
  ingest   — fold skill-hits.json into .torii/skill-fitness.json
  status   — ledger summary
  demote   — mark low hit_rate skills after min samples (tool-shielded)
  boosts   — per-skill score deltas for skill_router (+ tool bonus)
  federate — write privacy-safe skill theme signals → hub ingest path
  cycle    — ingest → hub recovery → scorecard skills → demote → federate
  ingest-scorecard — F135 fold scorecard-skill-signals into ledger
  fixture  — hermetic: hit skill boosts; zombie demotes; tool+scorecard shield
  apply    — print demoted + boosts JSON for assemble/router

Env:
  TORII_ROOT
  TORII_SKILL_FITNESS           1 (default) | 0/off
  TORII_SKILL_FITNESS_FILE      override ledger path
  TORII_SKILL_FITNESS_MIN_N     default 3 samples before demote
  TORII_SKILL_FITNESS_DEMOTE    default 0.25 hit_rate threshold
  TORII_SKILL_FITNESS_BOOST     default 2.0 max path-score bonus
  TORII_SKILL_FITNESS_TOOL      1 (default) | 0 — F116 tool_hit shield/boost/federate
  TORII_SKILL_FITNESS_HUB       1 (default) | 0 — F126 ingest hub recovery-util deltas
  TORII_SKILL_FITNESS_SCORECARD 1 (default) | 0 — F135 ingest scorecard skill themes
  TORII_SKILL_FITNESS_HUB_ARCHIVAL 1 (default) | 0 — F158 ingest hub-archival util gap/hit
  TORII_MEMORY_TENANT           optional for federate tenant hash
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F85"
FEATURE_TOOL = "F116"
FEATURE_HUB = "F126"
FEATURE_SCORECARD = "F135"
FEATURE_HUB_ARCHIVAL = "F158"
SCHEMA = 1
LEDGER_NAME = "skill-fitness.json"
SCORECARD_FED_REL = "memory/federation/scorecard-skill-signals.json"
HUB_ARCHIVAL_SKILL_ID = "skill-prefer-hub-archival-early"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})
_PATH_RX = re.compile(r"(?:/Users/|/home/|C:\\\\Users\\\\)", re.I)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SKILL_FITNESS") or "1").strip().lower()
    return raw not in _FALSEY


def tool_fitness_enabled() -> bool:
    """F116: tool_hit_n shields demote, boosts router, federates tool themes."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_TOOL") or "1").strip().lower()
    return raw not in _FALSEY


def hub_archival_fitness_enabled() -> bool:
    """F158: fold hub-archival util gap/hit into fitness demote/boost."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_HUB_ARCHIVAL") or "1").strip().lower()
    return raw not in _FALSEY


def refine_fitness_enabled() -> bool:
    """F166: GEPA-lite refine events shield demote + soft tool boost."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_REFINE") or "1").strip().lower()
    return raw not in _FALSEY


def refine_dual_decay_enabled() -> bool:
    """F171: chronic dual_fail decays always priority + lifts refine shield."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_REFINE_DUAL_DECAY") or "1").strip().lower()
    return raw not in _FALSEY


def refine_dual_revive_enabled() -> bool:
    """F175: dual_pass after decay → local revive + multi-tenant federate re-boost."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_REFINE_DUAL_REVIVE") or "1").strip().lower()
    return raw not in _FALSEY


def refine_dual_revive_mt_gate_enabled() -> bool:
    """F176: multi-tenant free-rider gate — local dual_pass cannot clear multi_tenant_decay."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_REVIVE_MT_GATE") or "1").strip().lower()
    return raw not in _FALSEY


def refine_dual_revive_pp_gate_enabled() -> bool:
    """F177: SkillOpt-style contribution_pp floor for dual_pass revive re-entry."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_REVIVE_PP_GATE") or "1").strip().lower()
    return raw not in _FALSEY


def refine_dual_revive_min_pp() -> float:
    """F177: min refine_tool_contribution_pp to revive (default 10)."""
    try:
        return float(os.environ.get("TORII_REFINE_REVIVE_MIN_PP") or "10")
    except (TypeError, ValueError):
        return 10.0


def refine_dual_revive_loo_gate_enabled() -> bool:
    """F179: LOO attribution free-rider / avg_contribution floor for dual_pass revive."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_REVIVE_LOO_GATE") or "1").strip().lower()
    return raw not in _FALSEY


def refine_dual_revive_min_loo() -> float:
    """F179: min skill-attribution avg_contribution to revive (default 0.5)."""
    try:
        return float(os.environ.get("TORII_REFINE_REVIVE_MIN_LOO") or "0.5")
    except (TypeError, ValueError):
        return 0.5


def refine_dual_revive_loo_min_n() -> int:
    """F179: min attribution samples before LOO free-rider gate applies."""
    try:
        return int(os.environ.get("TORII_REFINE_REVIVE_LOO_MIN_N") or "2")
    except (TypeError, ValueError):
        return 2


def _load_attr_skill(root: Path, sid: str) -> dict[str, Any]:
    """Load privacy-safe skill-attribution ledger entry for sid (F89/F166/F179)."""
    paths = [
        root / ".torii" / "skill-attribution.json",
        root / "memory" / "evolution" / "skill-attribution.json",
    ]
    envp = (os.environ.get("TORII_SKILL_ATTR_FILE") or "").strip()
    if envp:
        paths.insert(0, Path(envp))
    od = (os.environ.get("OUT_DIR") or "").strip()
    if od:
        paths.insert(0, Path(od) / "skill-attribution.json")
    for path in paths:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        frs = set(str(x) for x in (data.get("free_riders") or []) if x)
        skills = data.get("skills") or {}
        ent: dict[str, Any] | None = None
        if isinstance(skills, dict):
            raw = skills.get(sid)
            if isinstance(raw, dict):
                ent = raw
        elif isinstance(skills, list):
            for row in skills:
                if isinstance(row, dict) and str(row.get("id") or row.get("skill_id") or "") == sid:
                    ent = row
                    break
        if ent is None and sid in frs:
            return {
                "free_rider": True,
                "avg_contribution": 0.0,
                "n": 1,
                "source": str(path.name),
            }
        if ent is None:
            continue
        return {
            "free_rider": bool(ent.get("free_rider") or sid in frs),
            "avg_contribution": float(
                ent.get("avg_contribution") or ent.get("contribution") or 0
            ),
            "n": int(ent.get("n") or ent.get("selected_n") or 1),
            "source": str(path.name),
        }
    return {}


def refine_dual_fail_thr() -> float:
    """F171: dual_fail_rate ≥ thr after min samples → decay (default 0.67)."""
    try:
        return float(os.environ.get("TORII_SKILL_FITNESS_REFINE_DUAL_FAIL_THR") or "0.67")
    except (TypeError, ValueError):
        return 0.67


def hub_fitness_enabled() -> bool:
    """F126: fold hub recovery-util post-score into local fitness ledger."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_HUB") or "1").strip().lower()
    return raw not in _FALSEY


def scorecard_fitness_enabled() -> bool:
    """F135: fold F134 scorecard-skill-signals into local fitness ledger."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_SCORECARD") or "1").strip().lower()
    return raw not in _FALSEY


def _load_scorecard_fed_doc(root: Path) -> dict[str, Any] | None:
    """Load privacy-safe scorecard skill federation doc (F134)."""
    path = root / SCORECARD_FED_REL
    if not path.is_file():
        # also accept out_dir-style copy under .torii
        alt = root / ".torii" / "scorecard-skill-signals.json"
        path = alt if alt.is_file() else path
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def ingest_scorecard_skills(
    doc: dict[str, Any] | None = None,
    ledger: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """F135: F134 scorecard skill themes → soft tool_hit / shield on ledger.

    Consumes scorecard-skill-signals.json (skill_ids + scorecard_ops tags only).
    Never stores paths, raw tenant names, or commands.
    Active ops skills get tool-hit shield so they are not demoted as zombies
    before live hits accumulate (CoEvoSkills: adopt without fitness = rot).
    """
    root = root or _root()
    if not scorecard_fitness_enabled():
        return {
            "feature": FEATURE_SCORECARD,
            "ingested_n": 0,
            "reason": "scorecard_fitness_off",
            "privacy_ok": True,
            "scorecard_ops_ok": False,
        }
    if doc is None:
        doc = _load_scorecard_fed_doc(root)
    if not isinstance(doc, dict):
        return {
            "feature": FEATURE_SCORECARD,
            "ingested_n": 0,
            "reason": "no_scorecard_signals",
            "privacy_ok": True,
            "scorecard_ops_ok": False,
        }

    ledger = ledger if ledger is not None else load_ledger(ledger_path(root))
    skill_ids: list[str] = []
    for sid in doc.get("skill_ids") or []:
        sid_s = str(sid).strip()
        if sid_s and sid_s not in skill_ids:
            skill_ids.append(sid_s)
    for sig in doc.get("signals") or []:
        if not isinstance(sig, dict):
            continue
        tags = sig.get("tags") or []
        if "scorecard_ops" not in tags and "f134" not in tags:
            # still accept theme that maps to skill-prefer-*
            pass
        theme = str(sig.get("theme") or sig.get("id") or "")
        # reconstruct skill id from theme slug when possible
        if theme.startswith("skill-prefer-") or theme.startswith("skill-"):
            sid_s = theme[:96]
            if sid_s not in skill_ids:
                skill_ids.append(sid_s)
        # keywords may carry skill stem
        for kw in sig.get("keywords") or []:
            k = str(kw).strip()
            if k.startswith("skill-prefer-") and k not in skill_ids:
                skill_ids.append(k[:96])

    # also soft-load active scorecard skills from disk (ids only)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from skill_auto_adopt import list_active_scorecard_skills  # type: ignore

        for sid in list_active_scorecard_skills(root):
            if sid not in skill_ids:
                skill_ids.append(sid)
    except Exception:
        pass

    ingested: list[str] = []
    for sid in skill_ids:
        sid_s = str(sid).strip()
        if not sid_s or _PATH_RX.search(sid_s) or "/" in sid_s or ".." in sid_s:
            continue
        sid_s = re.sub(r"[^A-Za-z0-9._-]+", "-", sid_s)[:96]
        if not sid_s.startswith("skill-"):
            # map bare stems
            if sid_s.startswith("prefer-"):
                sid_s = f"skill-{sid_s}"
            else:
                continue
        # soft sample weight: scorecard ops are tool CLIs (doctor/scorecard)
        weight = 2
        ent = _skill_entry(ledger, sid_s)
        ent["selected_n"] = int(ent.get("selected_n") or 0) + weight
        ent["tool_hit_n"] = int(ent.get("tool_hit_n") or 0) + weight
        ent["hit_n"] = int(ent.get("hit_n") or 0) + weight
        sel = int(ent["selected_n"])
        ent["hit_rate"] = round(int(ent["hit_n"]) / sel, 4) if sel else 0.0
        ent["tool_hit_rate"] = (
            round(int(ent.get("tool_hit_n") or 0) / sel, 4) if sel else 0.0
        )
        ent["scorecard_ingested_n"] = int(ent.get("scorecard_ingested_n") or 0) + 1
        ent["scorecard_ops"] = True
        ent["last_seen"] = _now()
        ent["last_scorecard_at"] = _now()
        # never demote scorecard ops while tool fitness on
        if tool_fitness_enabled():
            ent["demoted"] = False
        ingested.append(sid_s)

    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "run_id": "scorecard_skills",
            "feature": FEATURE_SCORECARD,
            "ingested_n": len(ingested),
            "skills": ingested[:16],
        }
    )
    ledger["history"] = hist[-100:]
    ledger["last_scorecard_ingest"] = {
        "at": _now(),
        "feature": FEATURE_SCORECARD,
        "skills": ingested[:16],
        "n": len(ingested),
        "privacy_ok": bool(doc.get("privacy_ok", True)),
    }
    if save:
        save_ledger(ledger, ledger_path(root))
    privacy_blob = json.dumps(ledger.get("last_scorecard_ingest") or {})
    privacy_ok = (
        "/Users/" not in privacy_blob
        and "/home/" not in privacy_blob
        and bool(doc.get("privacy_ok", True))
    )
    return {
        "feature": FEATURE_SCORECARD,
        "ingested_n": len(ingested),
        "skills": ingested[:16],
        "privacy_ok": privacy_ok,
        "scorecard_ops_ok": len(ingested) >= 1,
        "fed_skill_n": len(doc.get("skill_ids") or []),
    }


def ingest_hub_archival_util(
    util: dict[str, Any] | None = None,
    ledger: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    out_dir: Path | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """F158: fold hub-archival util slice into fitness ledger (hit shield / gap demote).

    Consumes F155 score_recovery_util fields:
      hub_archival_injected, hub_archival_tool_hit, hub_archival_util_gap

    Privacy: skill id + counters only — no paths, prompts, or tenant strings.
    SkillsBench / Assay: chronic inject≠hub_boost must compound into demote;
    tool_hit shields revive.
    """
    root = root or _root()
    if not hub_archival_fitness_enabled():
        return {
            "feature": FEATURE_HUB_ARCHIVAL,
            "ingested": 0,
            "reason": "hub_archival_fitness_off",
            "privacy_ok": True,
        }
    if util is None and out_dir is not None:
        up = Path(out_dir) / "recovery-skill-util.json"
        if up.is_file():
            try:
                util = json.loads(up.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                util = None
    if util is None:
        # soft score from out_dir router artifacts
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from skill_router import score_recovery_util  # type: ignore

            util = score_recovery_util(
                Path(out_dir) if out_dir else None, root=root
            )
        except Exception as exc:
            return {
                "feature": FEATURE_HUB_ARCHIVAL,
                "ingested": 0,
                "error": str(exc)[:120],
                "privacy_ok": True,
            }
    if not isinstance(util, dict):
        return {
            "feature": FEATURE_HUB_ARCHIVAL,
            "ingested": 0,
            "reason": "no_util",
            "privacy_ok": True,
        }

    injected = bool(util.get("hub_archival_injected"))
    tool_hit = bool(util.get("hub_archival_tool_hit"))
    gap = bool(util.get("hub_archival_util_gap"))
    if not injected:
        return {
            "feature": FEATURE_HUB_ARCHIVAL,
            "ingested": 0,
            "reason": "hub_archival_not_injected",
            "privacy_ok": True,
            "skill_id": HUB_ARCHIVAL_SKILL_ID,
        }

    ledger = ledger if ledger is not None else load_ledger(ledger_path(root))
    sid = HUB_ARCHIVAL_SKILL_ID
    ent = _skill_entry(ledger, sid)
    ent["selected_n"] = int(ent.get("selected_n") or 0) + 1
    ent["hub_archival_selected_n"] = int(ent.get("hub_archival_selected_n") or 0) + 1
    if tool_hit:
        ent["hit_n"] = int(ent.get("hit_n") or 0) + 1
        ent["tool_hit_n"] = int(ent.get("tool_hit_n") or 0) + 1
        ent["hub_archival_hit_n"] = int(ent.get("hub_archival_hit_n") or 0) + 1
        ent["demoted"] = False  # revive on hub_boost evidence
    else:
        ent["miss_n"] = int(ent.get("miss_n") or 0) + 1
        if gap:
            ent["hub_archival_gap_n"] = int(ent.get("hub_archival_gap_n") or 0) + 1
    sel = int(ent["selected_n"])
    ent["hit_rate"] = round(int(ent.get("hit_n") or 0) / sel, 4) if sel else 0.0
    ent["tool_hit_rate"] = (
        round(int(ent.get("tool_hit_n") or 0) / sel, 4) if sel else 0.0
    )
    ha_sel = int(ent.get("hub_archival_selected_n") or 0)
    ha_hit = int(ent.get("hub_archival_hit_n") or 0)
    ha_gap_n = int(ent.get("hub_archival_gap_n") or 0)
    ent["hub_archival_util_rate"] = (
        round(ha_hit / ha_sel, 4) if ha_sel else 1.0
    )
    ent["hub_archival_gap_rate"] = (
        round(ha_gap_n / ha_sel, 4) if ha_sel else 0.0
    )
    ent["last_seen"] = _now()
    ent["last_hub_archival_at"] = _now()
    ent["hub_archival_ops"] = True

    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "run_id": "hub_archival_util",
            "feature": FEATURE_HUB_ARCHIVAL,
            "skill_id": sid,
            "tool_hit": int(tool_hit),
            "util_gap": int(gap),
            "hub_archival_gap_n": ha_gap_n,
            "hub_archival_hit_n": ha_hit,
        }
    )
    ledger["history"] = hist[-100:]
    ledger["last_hub_archival_ingest"] = {
        "at": _now(),
        "feature": FEATURE_HUB_ARCHIVAL,
        "skill_id": sid,
        "tool_hit": int(tool_hit),
        "util_gap": int(gap),
        "gap_n": ha_gap_n,
        "hit_n": ha_hit,
        "util_rate": ent.get("hub_archival_util_rate"),
    }

    path = None
    if save:
        path = save_ledger(ledger, ledger_path(root))

    blob = json.dumps(ledger.get("last_hub_archival_ingest") or {})
    privacy_ok = "/Users/" not in blob and "/home/" not in blob

    return {
        "feature": FEATURE_HUB_ARCHIVAL,
        "ingested": 1,
        "skill_id": sid,
        "tool_hit": int(tool_hit),
        "util_gap": int(gap),
        "hub_archival_gap_n": ha_gap_n,
        "hub_archival_hit_n": ha_hit,
        "hub_archival_util_rate": ent.get("hub_archival_util_rate"),
        "hub_archival_gap_rate": ent.get("hub_archival_gap_rate"),
        "privacy_ok": privacy_ok,
        "ledger": str(path) if path else None,
    }


def ingest_refine(
    refine: dict[str, Any] | None = None,
    ledger: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    out_dir: Path | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """F166: fold F165 GEPA-lite refine events into fitness (shield + soft boost).

    Constraint-passed refine is dual-gate investment — shield zombie demote until
    next tool hits accumulate; mark gepa_refined for router soft boost.
    """
    root = root or _root()
    if not refine_fitness_enabled():
        return {
            "feature": "F166",
            "ingested_n": 0,
            "reason": "refine_fitness_off",
            "privacy_ok": True,
        }
    if refine is None and out_dir is not None:
        p = Path(out_dir) / "skill-refine.json"
        if p.is_file():
            try:
                refine = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                refine = None
    if not isinstance(refine, dict):
        return {
            "feature": "F166",
            "ingested_n": 0,
            "reason": "no_refine_doc",
            "privacy_ok": True,
        }
    ledger = ledger if ledger is not None else load_ledger(ledger_path(root))
    skills = ledger.setdefault("skills", {})
    ingested = 0
    ids: list[str] = []
    for ent in refine.get("refined") or []:
        if not isinstance(ent, dict):
            continue
        sid = str(ent.get("skill_id") or ent.get("id") or "")
        if not sid.startswith("skill-"):
            continue
        c = ent.get("constraint") if isinstance(ent.get("constraint"), dict) else {}
        if c and not c.get("ok", True):
            continue
        e = skills.setdefault(sid, {"id": sid})
        e["gepa_refined"] = True
        e["refined_n"] = int(e.get("refined_n") or 0) + 1
        e["last_refined_at"] = _now()
        e["dual_gate_refine"] = "constraint_ok"
        # soft tool shield sample so demote does not kill mid-compound
        e["tool_hit_n"] = int(e.get("tool_hit_n") or 0) + 1
        e["selected_n"] = max(int(e.get("selected_n") or 0), 1)
        sel = int(e.get("selected_n") or 1)
        e["tool_hit_rate"] = round(int(e.get("tool_hit_n") or 0) / sel, 4) if sel else 0.0
        e["demoted"] = False
        ingested += 1
        ids.append(sid)
    ledger["last_refine_ingest"] = {
        "at": _now(),
        "feature": "F166",
        "ingested_n": ingested,
        "skill_ids": ids,
    }
    path = None
    if save and ingested:
        path = save_ledger(ledger, ledger_path(root))
    blob = json.dumps(ledger.get("last_refine_ingest") or {})
    privacy_ok = "/Users/" not in blob and "/home/" not in blob
    return {
        "feature": "F166",
        "ingested_n": ingested,
        "skill_ids": ids,
        "privacy_ok": privacy_ok,
        "ledger": str(path) if path else None,
    }


def ingest_refine_dual(
    report: dict[str, Any] | None = None,
    ledger: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    out_dir: Path | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """F171: fold F167 refine dual pass/fail into fitness (chronic dual_fail decay fuel).

    dual_pass → dual_pass_n++; dual_fail or tool_pp≤0 → dual_fail_n++.
    Computes dual_fail_rate for apply_demotions / always-priority decay.
    """
    root = root or _root()
    if not refine_dual_decay_enabled() and not refine_fitness_enabled():
        return {
            "feature": "F171",
            "ingested_n": 0,
            "reason": "refine_dual_decay_off",
            "privacy_ok": True,
        }
    if report is None and out_dir is not None:
        p = Path(out_dir) / "refine-dual.json"
        if p.is_file():
            try:
                report = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                report = None
    if not isinstance(report, dict):
        return {
            "feature": "F171",
            "ingested_n": 0,
            "reason": "no_refine_dual",
            "privacy_ok": True,
        }
    ledger = ledger if ledger is not None else load_ledger(ledger_path(root))
    skills = ledger.setdefault("skills", {})
    skill_ids = [str(s) for s in (report.get("refined_skill_ids") or []) if str(s).startswith("skill-")]
    if not skill_ids:
        # still count known recovery refine targets from dual report selection
        skill_ids = [str(s) for s in (report.get("selected") or []) if "prefer-" in str(s)]
    dual_pass = bool(report.get("refine_dual_pass"))
    tool_pp = float(report.get("refine_tool_contribution_pp") or 0)
    probe_d = int(report.get("refine_probe_delta") or 0)
    # treat non-positive contribution as fail even if flag true
    effective_pass = dual_pass and (tool_pp > 0 or probe_d > 0)
    ingested = 0
    decayed: list[str] = []
    revived: list[str] = []
    for sid in skill_ids or ["skill-prefer-hub-archival-early"]:
        if not sid.startswith("skill-"):
            continue
        e = skills.setdefault(sid, {"id": sid})
        e["refine_dual_selected_n"] = int(e.get("refine_dual_selected_n") or 0) + 1
        if effective_pass:
            e["refine_dual_pass_n"] = int(e.get("refine_dual_pass_n") or 0) + 1
            e["last_refine_dual_pass"] = True
        else:
            e["refine_dual_fail_n"] = int(e.get("refine_dual_fail_n") or 0) + 1
            e["last_refine_dual_pass"] = False
        sel = int(e.get("refine_dual_selected_n") or 0)
        fail_n = int(e.get("refine_dual_fail_n") or 0)
        pass_n = int(e.get("refine_dual_pass_n") or 0)
        e["refine_dual_fail_rate"] = round(fail_n / sel, 4) if sel else 0.0
        e["refine_dual_pass_rate"] = round(pass_n / sel, 4) if sel else 0.0
        e["last_refine_dual_at"] = _now()
        e["last_refine_tool_pp"] = tool_pp
        # soft decay stamp for router
        thr = refine_dual_fail_thr()
        min_n = _int_env("TORII_SKILL_FITNESS_MIN_N", 3)
        if sel >= min_n and float(e["refine_dual_fail_rate"]) >= thr:
            e["refine_dual_chronic_fail"] = True
            e["refine_dual_revived"] = False
            # negative always-priority fuel (router post_score reads this)
            e["hub_priority_delta"] = min(int(e.get("hub_priority_delta") or 0), -12)
            e["refine_priority_decay"] = -15 - min(15, int(10 * float(e["refine_dual_fail_rate"])))
            e["last_refine_decayed"] = True
            decayed.append(sid)
        elif effective_pass and pass_n >= 1:
            e["refine_dual_chronic_fail"] = False
            if int(e.get("refine_priority_decay") or 0) < 0 and float(e["refine_dual_fail_rate"]) < thr:
                e["refine_priority_decay"] = 0
            # F175/F176: dual_pass revive after prior decay
            # F176: multi-tenant free-rider gate — sticky multi_tenant_decay stays until promote
            prior_decay = bool(
                e.get("last_refine_decayed")
                or e.get("multi_tenant_decay")
                or int(e.get("refine_dual_fail_n") or 0) >= 1
                or int(e.get("refine_priority_decay") or 0) < 0
            )
            rate_ok = float(e["refine_dual_fail_rate"]) < thr
            # also allow revive when recent pass streak dominates (pass_n > fail_n)
            streak_ok = pass_n >= 1 and pass_n > fail_n
            if (
                refine_dual_revive_enabled()
                and prior_decay
                and (rate_ok or streak_ok)
            ):
                min_pp = refine_dual_revive_min_pp()
                pp_gate = refine_dual_revive_pp_gate_enabled()
                # F177: SkillOpt validation — dual_pass without enough tool_pp is not revive
                if pp_gate and float(tool_pp) < float(min_pp):
                    e["revive_pp_blocked"] = True
                    e["last_revive_pp_blocked"] = float(tool_pp)
                    e["last_revive_pp_floor"] = float(min_pp)
                    e["feature_revive_pp_gate"] = "F177"
                    # keep decay/sticky state; do not re-enter always budget
                else:
                    # F179: LOO attribution free-rider / avg_contribution floor
                    loo_block = False
                    attr_ent: dict[str, Any] = {}
                    if refine_dual_revive_loo_gate_enabled():
                        attr_ent = _load_attr_skill(root, sid)
                        min_loo = refine_dual_revive_min_loo()
                        min_n_loo = refine_dual_revive_loo_min_n()
                        if attr_ent:
                            avg_c = float(attr_ent.get("avg_contribution") or 0)
                            n_attr = int(attr_ent.get("n") or 0)
                            is_fr = bool(attr_ent.get("free_rider"))
                            # cold-start: n < min_n and not free_rider → allow
                            if is_fr or (
                                n_attr >= min_n_loo and avg_c < float(min_loo)
                            ):
                                loo_block = True
                                e["revive_loo_blocked"] = True
                                e["last_revive_loo_avg"] = avg_c
                                e["last_revive_loo_floor"] = float(min_loo)
                                e["last_revive_loo_free_rider"] = is_fr
                                e["feature_revive_loo_gate"] = "F179"
                    if not loo_block:
                        boost = 12 + min(12, int(max(0.0, tool_pp) / 10))
                        if attr_ent and float(attr_ent.get("avg_contribution") or 0) >= 1.0:
                            boost += min(
                                8, int(float(attr_ent.get("avg_contribution") or 0))
                            )
                        mt_sticky = bool(
                            e.get("multi_tenant_decay")
                            or int(e.get("multi_tenant_decay_tenants") or 0) >= 2
                        )
                        e["refine_dual_revived"] = True
                        e["last_refine_revive_at"] = _now()
                        e["last_refine_decayed"] = False
                        e["refine_priority_decay"] = 0
                        e["demoted"] = False
                        e["gepa_refined"] = True
                        e["revive_pp_blocked"] = False
                        e["revive_loo_blocked"] = False
                        e["last_revive_tool_pp"] = float(tool_pp)
                        if attr_ent:
                            e["last_revive_loo_avg"] = float(
                                attr_ent.get("avg_contribution") or 0
                            )
                        e["feature_revive_pp_gate"] = "F177"
                        e["feature_revive_loo_gate"] = "F179"
                        if mt_sticky and refine_dual_revive_mt_gate_enabled():
                            # F176 sticky multi_tenant_decay until FederatedSkill promote
                            e["local_revive_pending_mt"] = True
                            e["multi_tenant_decay"] = True
                            soft = max(4, boost // 2)
                            e["hub_priority_delta"] = max(
                                min(int(e.get("hub_priority_delta") or 0), soft), soft
                            )
                            e["free_rider_revive_blocked"] = True
                            e["feature_revive_gate"] = "F176"
                        else:
                            e["multi_tenant_decay"] = False
                            e["local_revive_pending_mt"] = False
                            e["free_rider_revive_blocked"] = False
                            e["hub_priority_delta"] = max(
                                int(e.get("hub_priority_delta") or 0), boost
                            )
                        revived.append(sid)
        ingested += 1
    ledger["last_refine_dual_ingest"] = {
        "at": _now(),
        "feature": "F171",
        "feature_revive": "F175" if revived else None,
        "feature_revive_gate": "F176" if revived else None,
        "ingested_n": ingested,
        "effective_pass": effective_pass,
        "tool_pp": tool_pp,
        "decayed": decayed,
        "revived": revived,
        "skill_ids": skill_ids,
    }
    path = None
    if save and ingested:
        path = save_ledger(ledger, ledger_path(root))
    blob = json.dumps(ledger.get("last_refine_dual_ingest") or {})
    privacy_ok = "/Users/" not in blob and "/home/" not in blob
    result = {
        "feature": "F171",
        "feature_revive": "F175" if revived else None,
        "ingested_n": ingested,
        "effective_pass": effective_pass,
        "decayed": decayed,
        "revived": revived,
        "skill_ids": skill_ids,
        "privacy_ok": privacy_ok,
        "ledger": str(path) if path else None,
    }
    # F172: soft federate chronic dual_fail decay bins (privacy-safe)
    if decayed and refine_dual_decay_enabled():
        try:
            fed = federate_refine_dual_decay(root=root, skill_ids=decayed, ledger=ledger)
            result["federate_decay"] = {
                "federated_n": fed.get("federated_n"),
                "privacy_ok": fed.get("privacy_ok"),
            }
            prom = promote_refine_dual_decay(root=root)
            result["promote_decay"] = {
                "promoted_n": prom.get("promoted_n"),
                "privacy_ok": prom.get("privacy_ok"),
            }
        except Exception as exc:
            result["federate_decay"] = {"error": str(exc)[:80]}
    # F175: soft federate dual_pass revive after decay (privacy-safe) + multi-tenant re-boost
    if revived and refine_dual_revive_enabled():
        try:
            fed_r = federate_refine_dual_revive(
                root=root, skill_ids=revived, ledger=ledger, tool_pp=tool_pp
            )
            result["federate_revive"] = {
                "federated_n": fed_r.get("federated_n"),
                "privacy_ok": fed_r.get("privacy_ok"),
            }
            prom_r = promote_refine_dual_revive(root=root)
            result["promote_revive"] = {
                "promoted_n": prom_r.get("promoted_n"),
                "privacy_ok": prom_r.get("privacy_ok"),
                "revived": prom_r.get("revived"),
            }
        except Exception as exc:
            result["federate_revive"] = {"error": str(exc)[:80]}
    return result


def _tenant_hash_fitness(root: Path) -> str:
    import hashlib

    return hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:12]


def _fail_rate_bin(rate: float) -> str:
    if rate >= 0.9:
        return "crit"
    if rate >= 0.67:
        return "high"
    if rate >= 0.34:
        return "mid"
    if rate > 0:
        return "low"
    return "zero"


def federate_refine_dual_decay(
    root: Path | None = None,
    *,
    skill_ids: list[str] | None = None,
    ledger: dict[str, Any] | None = None,
    tenant_hash: str | None = None,
) -> dict[str, Any]:
    """F172: privacy-safe multi-tenant federate of F171 chronic dual_fail decay.

    Emits skill id + fail_rate bin + decay only — no paths/bodies.
    """
    root = root or _root()
    if not refine_dual_decay_enabled():
        return {
            "feature": "F172",
            "federated_n": 0,
            "reason": "decay_off",
            "privacy_ok": True,
        }
    ledger = ledger if ledger is not None else load_ledger(ledger_path(root))
    skills = ledger.get("skills") or {}
    th = tenant_hash or _tenant_hash_fitness(root)
    dest = root / "memory" / "federation" / "skill-refine-dual-decay-signals.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {
        "schema_version": SCHEMA,
        "feature": "F172",
        "signals": [],
    }
    if dest.is_file():
        try:
            data = json.loads(dest.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                existing = data
                existing.setdefault("signals", [])
        except (OSError, json.JSONDecodeError):
            pass
    by_key: dict[str, dict[str, Any]] = {}
    for s in existing.get("signals") or []:
        if isinstance(s, dict):
            key = f"{s.get('skill_id') or s.get('theme')}|{s.get('tenant_hash') or ''}"
            by_key[key] = s

    targets = skill_ids or [
        sid
        for sid, e in skills.items()
        if isinstance(e, dict) and e.get("refine_dual_chronic_fail")
    ]
    federated = 0
    for sid in targets:
        if not str(sid).startswith("skill-"):
            continue
        ent = skills.get(sid) if isinstance(skills.get(sid), dict) else {}
        if not ent.get("refine_dual_chronic_fail") and sid not in (skill_ids or []):
            # still federate if explicitly listed as decayed this run
            if sid not in (skill_ids or []):
                continue
        key = f"{sid}|{th}"
        prev = by_key.get(key) if isinstance(by_key.get(key), dict) else {}
        fail_rate = float(ent.get("refine_dual_fail_rate") or prev.get("fail_rate") or 1.0)
        decay = int(ent.get("refine_priority_decay") or prev.get("decay") or -15)
        if decay >= 0:
            decay = -15
        entry = {
            "id": f"refine-decay-{sid}"[:64],
            "theme": sid,
            "skill_id": sid,
            "tags": [
                "refine_dual_decay",
                "f171",
                "f172",
                "chronic_fail",
                "federated_skill",
            ],
            "source": "skill_refine_dual_decay",
            "hits": int(prev.get("hits") or 0) + 1,
            "tenants": 1,
            "tenant_hash": th,
            "tenant_hashes": sorted(set(list(prev.get("tenant_hashes") or []) + [th]))[
                :16
            ],
            "fail_rate": fail_rate,
            "fail_rate_bin": _fail_rate_bin(fail_rate),
            "decay": decay,
            "util_rate_bin": "neg",
            "dual_pass": False,
            "updated_at": _now(),
            "feature": "F172",
        }
        by_key[key] = entry
        federated += 1

    signals = list(by_key.values())[-200:]
    doc = {
        "schema_version": SCHEMA,
        "feature": "F172",
        "scope": "skill_refine_dual_decay",
        "updated_at": _now(),
        "privacy": "skill_id_fail_bin_tenant_hash_only",
        "privacy_ok": True,
        "signals": signals,
    }
    blob = json.dumps(doc)
    if "/Users/" in blob or "/home/" in blob:
        doc["privacy_ok"] = False
        doc["signals"] = []
        federated = 0
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {
        "feature": "F172",
        "path": str(dest),
        "federated_n": federated,
        "signals_n": len(doc["signals"]),
        "privacy_ok": doc["privacy_ok"],
        "tenant_hash": th,
    }


def promote_refine_dual_decay(
    root: Path | None = None,
    *,
    min_tenants: int | None = None,
    min_hits: int | None = None,
) -> dict[str, Any]:
    """F172: FederatedSkill gate — multi-tenant chronic dual_fail → local decay amplify.

    When ≥min_tenants report chronic decay for a skill, write promoted decay themes
    and apply stronger local fitness decay so always budget demotes harder.
    """
    root = root or _root()
    if not refine_dual_decay_enabled():
        return {
            "feature": "F172",
            "promoted_n": 0,
            "reason": "decay_off",
            "privacy_ok": True,
            "themes": [],
        }
    min_t = (
        min_tenants
        if min_tenants is not None
        else _int_env("TORII_SKILL_PROMOTE_MIN_TENANTS", 2)
    )
    min_h = (
        min_hits if min_hits is not None else _int_env("TORII_SKILL_PROMOTE_MIN_HITS", 2)
    )
    path = root / "memory" / "federation" / "skill-refine-dual-decay-signals.json"
    sigs: list[dict[str, Any]] = []
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw = data.get("signals") if isinstance(data, dict) else data
            if isinstance(raw, list):
                sigs = [s for s in raw if isinstance(s, dict)]
        except (OSError, json.JSONDecodeError):
            sigs = []

    by_sid: dict[str, dict[str, Any]] = {}
    for s in sigs:
        sid = str(s.get("skill_id") or s.get("theme") or "")
        if not sid.startswith("skill-"):
            continue
        ent = by_sid.setdefault(
            sid,
            {
                "skill_id": sid,
                "tenant_hashes": set(),
                "hits": 0,
                "fail_rate": 0.0,
                "decay": 0,
            },
        )
        ths = s.get("tenant_hashes") or (
            [s.get("tenant_hash")] if s.get("tenant_hash") else []
        )
        for th in ths:
            if th:
                ent["tenant_hashes"].add(str(th))
        if not ths:
            ent["tenant_hashes"].add(f"anon-{s.get('id') or sid}")
        ent["hits"] += max(1, int(s.get("hits") or 1))
        ent["fail_rate"] = max(float(ent["fail_rate"]), float(s.get("fail_rate") or 0))
        ent["decay"] = min(int(ent["decay"] or 0), int(s.get("decay") or -15))

    clean: list[dict[str, Any]] = []
    blocked: list[str] = []
    for sid, ent in by_sid.items():
        tenants = len(ent["tenant_hashes"])
        hits = int(ent["hits"])
        if tenants >= min_t and hits >= min_h and float(ent["fail_rate"]) >= 0.34:
            decay = int(ent["decay"])
            if decay >= 0:
                decay = -20
            # multi-tenant amplify
            decay = min(decay, -20 - min(15, 5 * tenants))
            clean.append(
                {
                    "id": f"promoted-decay-{sid}"[:64],
                    "theme": sid,
                    "skill_id": sid,
                    "tags": [
                        "promoted_refine_dual_decay",
                        "f172",
                        "f171",
                        "chronic_fail",
                        "federated_skill",
                    ],
                    "source": "skill_refine_dual_decay_promote",
                    "hits": hits,
                    "tenants": tenants,
                    "tenant_hashes": sorted(ent["tenant_hashes"])[:16],
                    "fail_rate": float(ent["fail_rate"]),
                    "fail_rate_bin": _fail_rate_bin(float(ent["fail_rate"])),
                    "decay": decay,
                    "util_rate_bin": "neg",
                    "feature": "F172",
                }
            )
        else:
            blocked.append(sid)

    out = root / "memory" / "federation" / "promoted-refine-dual-decay-themes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": SCHEMA,
        "feature": "F172",
        "scope": "promoted_refine_dual_decay_themes",
        "updated_at": _now(),
        "min_tenants": min_t,
        "min_hits": min_h,
        "source_skill_n": len(by_sid),
        "promoted_n": len(clean),
        "blocked": blocked[:32],
        "privacy": "skill_id_fail_bin_tenant_hash_only",
        "privacy_ok": True,
        "signals": clean,
    }
    blob = json.dumps(doc)
    if "/Users/" in blob or "/home/" in blob:
        doc["privacy_ok"] = False
        doc["signals"] = []
        doc["promoted_n"] = 0
        clean = []
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    # amplify local fitness decay for multi-tenant promoted chronic fails
    amplified: list[str] = []
    if clean:
        ledger = load_ledger(ledger_path(root))
        skills = ledger.setdefault("skills", {})
        for c in clean:
            sid = str(c["skill_id"])
            e = skills.setdefault(sid, {"id": sid})
            e["refine_dual_chronic_fail"] = True
            e["refine_priority_decay"] = min(
                int(e.get("refine_priority_decay") or 0), int(c.get("decay") or -20)
            )
            e["hub_priority_delta"] = min(int(e.get("hub_priority_delta") or 0), -20)
            e["multi_tenant_decay"] = True
            e["multi_tenant_decay_tenants"] = int(c.get("tenants") or 0)
            amplified.append(sid)
        if amplified:
            apply_demotions(ledger)
            save_ledger(ledger, ledger_path(root))

    return {
        "feature": "F172",
        "path": str(out),
        "source_skill_n": len(by_sid),
        "promoted_n": doc["promoted_n"],
        "blocked_n": len(blocked),
        "blocked": blocked[:16],
        "min_tenants": min_t,
        "min_hits": min_h,
        "privacy_ok": doc["privacy_ok"],
        "themes": [s.get("theme") for s in clean[:16]],
        "amplified": amplified,
    }


def _pass_rate_bin(rate: float) -> str:
    """Privacy-safe pass_rate bin for federate (no raw floats across tenants)."""
    r = max(0.0, min(1.0, float(rate)))
    if r >= 0.8:
        return "high"
    if r >= 0.5:
        return "mid"
    if r > 0:
        return "low"
    return "zero"


def federate_refine_dual_revive(
    root: Path | None = None,
    skill_ids: list[str] | None = None,
    ledger: dict[str, Any] | None = None,
    *,
    tenant_hash: str | None = None,
    tool_pp: float = 0.0,
) -> dict[str, Any]:
    """F175: privacy-safe multi-tenant federate of dual_pass revive after decay.

    Signals: skill_id + pass_rate_bin + tool_pp_bin + tenant_hash only.
    """
    root = root or _root()
    if not refine_dual_revive_enabled():
        return {
            "feature": "F175",
            "federated_n": 0,
            "reason": "revive_off",
            "privacy_ok": True,
        }
    ledger = ledger if ledger is not None else load_ledger(ledger_path(root))
    skills = ledger.get("skills") or {}
    th = tenant_hash or _tenant_hash_fitness(root)
    dest = root / "memory" / "federation" / "skill-refine-dual-revive-signals.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {
        "schema_version": SCHEMA,
        "feature": "F175",
        "signals": [],
    }
    if dest.is_file():
        try:
            data = json.loads(dest.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                existing = data
                existing.setdefault("signals", [])
        except (OSError, json.JSONDecodeError):
            pass
    by_key: dict[str, dict[str, Any]] = {}
    for s in existing.get("signals") or []:
        if isinstance(s, dict):
            key = f"{s.get('skill_id') or s.get('theme')}|{s.get('tenant_hash') or ''}"
            by_key[key] = s

    targets = skill_ids or [
        sid
        for sid, e in skills.items()
        if isinstance(e, dict) and e.get("refine_dual_revived")
    ]
    federated = 0
    for sid in targets:
        if not str(sid).startswith("skill-"):
            continue
        ent = skills.get(sid) if isinstance(skills.get(sid), dict) else {}
        key = f"{sid}|{th}"
        prev = by_key.get(key) if isinstance(by_key.get(key), dict) else {}
        pass_rate = float(ent.get("refine_dual_pass_rate") or prev.get("pass_rate") or 0.5)
        pp = float(ent.get("last_refine_tool_pp") or tool_pp or prev.get("tool_pp") or 0)
        boost = int(ent.get("hub_priority_delta") or prev.get("boost") or 12)
        if boost < 8:
            boost = 12
        entry = {
            "id": f"refine-revive-{sid}"[:64],
            "theme": sid,
            "skill_id": sid,
            "tags": [
                "refine_dual_revive",
                "f175",
                "dual_pass",
                "federated_skill",
            ],
            "source": "skill_refine_dual_revive",
            "hits": int(prev.get("hits") or 0) + 1,
            "tenants": 1,
            "tenant_hash": th,
            "tenant_hashes": sorted(set(list(prev.get("tenant_hashes") or []) + [th]))[
                :16
            ],
            "pass_rate": pass_rate,
            "pass_rate_bin": _pass_rate_bin(pass_rate),
            "tool_pp": pp,
            "tool_pp_bin": "high" if pp >= 50 else ("mid" if pp >= 10 else "low"),
            "boost": boost,
            "util_rate_bin": "pos",
            "dual_pass": True,
            "updated_at": _now(),
            "feature": "F175",
        }
        by_key[key] = entry
        federated += 1

    signals = list(by_key.values())[-200:]
    doc = {
        "schema_version": SCHEMA,
        "feature": "F175",
        "scope": "skill_refine_dual_revive",
        "updated_at": _now(),
        "privacy": "skill_id_pass_bin_tenant_hash_only",
        "privacy_ok": True,
        "signals": signals,
    }
    blob = json.dumps(doc)
    if "/Users/" in blob or "/home/" in blob:
        doc["privacy_ok"] = False
        doc["signals"] = []
        federated = 0
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {
        "feature": "F175",
        "path": str(dest),
        "federated_n": federated,
        "signals_n": len(doc["signals"]),
        "privacy_ok": doc["privacy_ok"],
        "tenant_hash": th,
    }


def promote_refine_dual_revive(
    root: Path | None = None,
    *,
    min_tenants: int | None = None,
    min_hits: int | None = None,
) -> dict[str, Any]:
    """F175: FederatedSkill gate — multi-tenant dual_pass revive → always re-boost.

    When ≥min_tenants report dual_pass revive for a skill previously under decay,
    clear multi_tenant_decay, restore always-priority boost, supersede decay themes.
    """
    root = root or _root()
    if not refine_dual_revive_enabled():
        return {
            "feature": "F175",
            "promoted_n": 0,
            "reason": "revive_off",
            "privacy_ok": True,
            "themes": [],
            "revived": [],
        }
    min_t = (
        min_tenants
        if min_tenants is not None
        else _int_env("TORII_SKILL_PROMOTE_MIN_TENANTS", 2)
    )
    min_h = (
        min_hits if min_hits is not None else _int_env("TORII_SKILL_PROMOTE_MIN_HITS", 2)
    )
    path = root / "memory" / "federation" / "skill-refine-dual-revive-signals.json"
    sigs: list[dict[str, Any]] = []
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw = data.get("signals") if isinstance(data, dict) else data
            if isinstance(raw, list):
                sigs = [s for s in raw if isinstance(s, dict)]
        except (OSError, json.JSONDecodeError):
            sigs = []

    by_sid: dict[str, dict[str, Any]] = {}
    for s in sigs:
        sid = str(s.get("skill_id") or s.get("theme") or "")
        if not sid.startswith("skill-"):
            continue
        ent = by_sid.setdefault(
            sid,
            {
                "skill_id": sid,
                "tenant_hashes": set(),
                "hits": 0,
                "pass_rate": 0.0,
                "tool_pp": 0.0,
                "boost": 0,
            },
        )
        ths = s.get("tenant_hashes") or (
            [s.get("tenant_hash")] if s.get("tenant_hash") else []
        )
        for th in ths:
            if th:
                ent["tenant_hashes"].add(str(th))
        if not ths:
            ent["tenant_hashes"].add(f"anon-{s.get('id') or sid}")
        ent["hits"] += max(1, int(s.get("hits") or 1))
        ent["pass_rate"] = max(float(ent["pass_rate"]), float(s.get("pass_rate") or 0))
        ent["tool_pp"] = max(float(ent["tool_pp"]), float(s.get("tool_pp") or 0))
        ent["boost"] = max(int(ent["boost"] or 0), int(s.get("boost") or 12))

    clean: list[dict[str, Any]] = []
    blocked: list[str] = []
    for sid, ent in by_sid.items():
        tenants = len(ent["tenant_hashes"])
        hits = int(ent["hits"])
        min_pp = refine_dual_revive_min_pp() if refine_dual_revive_pp_gate_enabled() else 0.0
        if (
            tenants >= min_t
            and hits >= min_h
            and float(ent["pass_rate"]) >= 0.34
            and float(ent["tool_pp"]) >= float(min_pp)
        ):
            boost = max(int(ent["boost"] or 12), 16 + min(12, 4 * tenants))
            if float(ent["tool_pp"]) >= 50:
                boost += 8
            clean.append(
                {
                    "id": f"promoted-revive-{sid}"[:64],
                    "theme": sid,
                    "skill_id": sid,
                    "tags": [
                        "promoted_refine_dual_revive",
                        "f175",
                        "dual_pass",
                        "federated_skill",
                    ],
                    "source": "skill_refine_dual_revive_promote",
                    "hits": hits,
                    "tenants": tenants,
                    "tenant_hashes": sorted(ent["tenant_hashes"])[:16],
                    "pass_rate": float(ent["pass_rate"]),
                    "pass_rate_bin": _pass_rate_bin(float(ent["pass_rate"])),
                    "tool_pp": float(ent["tool_pp"]),
                    "boost": boost,
                    "util_rate_bin": "pos",
                    "dual_pass": True,
                    "feature": "F175",
                }
            )
        else:
            blocked.append(sid)

    out = root / "memory" / "federation" / "promoted-refine-dual-revive-themes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": SCHEMA,
        "feature": "F175",
        "scope": "promoted_refine_dual_revive_themes",
        "updated_at": _now(),
        "min_tenants": min_t,
        "min_hits": min_h,
        "source_skill_n": len(by_sid),
        "promoted_n": len(clean),
        "blocked": blocked[:32],
        "privacy": "skill_id_pass_bin_tenant_hash_only",
        "privacy_ok": True,
        "signals": clean,
    }
    blob = json.dumps(doc)
    if "/Users/" in blob or "/home/" in blob:
        doc["privacy_ok"] = False
        doc["signals"] = []
        doc["promoted_n"] = 0
        clean = []
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    # re-boost local fitness for multi-tenant promoted revive; supersede decay
    revived: list[str] = []
    if clean:
        ledger = load_ledger(ledger_path(root))
        skills = ledger.setdefault("skills", {})
        for c in clean:
            sid = str(c["skill_id"])
            e = skills.setdefault(sid, {"id": sid})
            e["refine_dual_chronic_fail"] = False
            e["refine_dual_revived"] = True
            e["multi_tenant_decay"] = False
            e["multi_tenant_revive"] = True
            e["multi_tenant_revive_tenants"] = int(c.get("tenants") or 0)
            e["local_revive_pending_mt"] = False
            e["free_rider_revive_blocked"] = False
            e["feature_revive_gate"] = "F176"
            e["last_refine_decayed"] = False
            e["refine_priority_decay"] = 0
            e["hub_priority_delta"] = max(
                int(e.get("hub_priority_delta") or 0), int(c.get("boost") or 16)
            )
            e["demoted"] = False
            e["gepa_refined"] = True
            e["last_refine_revive_at"] = _now()
            revived.append(sid)
        if revived:
            apply_demotions(ledger)
            save_ledger(ledger, ledger_path(root))
        # supersede multi-tenant decay themes for revived skills
        decay_path = root / "memory" / "federation" / "promoted-refine-dual-decay-themes.json"
        if decay_path.is_file() and revived:
            try:
                ddoc = json.loads(decay_path.read_text(encoding="utf-8"))
                sigs_d = [
                    s
                    for s in (ddoc.get("signals") or [])
                    if isinstance(s, dict)
                    and str(s.get("skill_id") or s.get("theme") or "") not in set(revived)
                ]
                ddoc["signals"] = sigs_d
                ddoc["promoted_n"] = len(sigs_d)
                ddoc["superseded_by"] = "F175"
                ddoc["updated_at"] = _now()
                decay_path.write_text(json.dumps(ddoc, indent=2) + "\n", encoding="utf-8")
            except (OSError, json.JSONDecodeError, TypeError):
                pass

    return {
        "feature": "F175",
        "path": str(out),
        "source_skill_n": len(by_sid),
        "promoted_n": doc["promoted_n"],
        "blocked_n": len(blocked),
        "blocked": blocked[:16],
        "min_tenants": min_t,
        "min_hits": min_h,
        "privacy_ok": doc["privacy_ok"],
        "themes": [s.get("theme") for s in clean[:16]],
        "revived": revived,
    }


def ingest_hub_recovery(
    hub: dict[str, Any] | None = None,
    ledger: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """F126: privacy-safe hub recovery themes → soft tool_hit / shield on ledger.

    Consumes F125 post_score_recovery_hub (skill_id + hits + tool_hits only).
    Never stores paths, tenants names, or commands.
    """
    root = root or _root()
    if not hub_fitness_enabled():
        return {
            "feature": FEATURE_HUB,
            "ingested_n": 0,
            "reason": "hub_fitness_off",
            "privacy_ok": True,
        }
    if hub is None:
        # soft load from federation store via skill_router
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from skill_router import post_score_recovery_hub  # type: ignore

            hub = post_score_recovery_hub(root=root)
        except Exception as exc:
            return {
                "feature": FEATURE_HUB,
                "ingested_n": 0,
                "error": str(exc)[:120],
                "privacy_ok": True,
            }
    ledger = ledger if ledger is not None else load_ledger(ledger_path(root))
    skills_doc = hub.get("skills") if isinstance(hub, dict) else None
    if not isinstance(skills_doc, dict):
        skills_doc = {}
    # also accept priority_deltas-only
    deltas = (hub.get("priority_deltas") or {}) if isinstance(hub, dict) else {}
    ingested: list[str] = []
    for sid, ent_h in skills_doc.items():
        sid_s = str(sid).strip()
        if not sid_s or _PATH_RX.search(sid_s) or "/" in sid_s or ".." in sid_s:
            continue
        sid_s = re.sub(r"[^A-Za-z0-9._-]+", "-", sid_s)[:96]
        if not sid_s.startswith("skill-"):
            continue
        hits = 1
        tool_hits = 0
        tenants = 1
        if isinstance(ent_h, dict):
            hits = max(1, int(ent_h.get("hits") or 1))
            tool_hits = max(0, int(ent_h.get("tool_hits") or 0))
            tenants = max(1, int(ent_h.get("tenants") or 1))
        # soft sample weight: cap so hub can't drown local
        weight = min(3, max(1, min(hits, tenants)))
        ent = _skill_entry(ledger, sid_s)
        ent["selected_n"] = int(ent.get("selected_n") or 0) + weight
        # hub tool themes count as tool hits (shield demote)
        th_add = min(3, max(1, tool_hits if tool_hits else weight))
        ent["tool_hit_n"] = int(ent.get("tool_hit_n") or 0) + th_add
        ent["hit_n"] = int(ent.get("hit_n") or 0) + min(weight, th_add)
        sel = int(ent["selected_n"])
        ent["hit_rate"] = round(int(ent["hit_n"]) / sel, 4) if sel else 0.0
        ent["tool_hit_rate"] = (
            round(int(ent.get("tool_hit_n") or 0) / sel, 4) if sel else 0.0
        )
        ent["hub_ingested_n"] = int(ent.get("hub_ingested_n") or 0) + 1
        ent["hub_priority_delta"] = int(
            (ent_h or {}).get("priority_delta")
            if isinstance(ent_h, dict)
            else deltas.get(sid_s)
            or 0
        )
        ent["last_seen"] = _now()
        ent["last_hub_at"] = _now()
        # never demote hub tool-effective recovery
        if tool_fitness_enabled() and int(ent.get("tool_hit_n") or 0) >= 1:
            ent["demoted"] = False
        ingested.append(sid_s)

    # deltas-only skills not in skills map
    for sid, delta in deltas.items():
        sid_s = str(sid).strip()
        if sid_s in ingested:
            continue
        if not sid_s.startswith("skill-") or "/" in sid_s:
            continue
        ent = _skill_entry(ledger, sid_s)
        ent["hub_priority_delta"] = int(delta or 0)
        ent["last_hub_at"] = _now()
        ingested.append(sid_s)

    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "run_id": "hub_recovery",
            "feature": FEATURE_HUB,
            "ingested_n": len(ingested),
            "skills": ingested[:16],
            "gap_pressure": (hub or {}).get("gap_pressure") if isinstance(hub, dict) else None,
        }
    )
    ledger["history"] = hist[-100:]
    ledger["last_hub_ingest"] = {
        "at": _now(),
        "feature": FEATURE_HUB,
        "skills": ingested[:16],
        "n": len(ingested),
    }
    path = None
    if save:
        path = save_ledger(ledger, ledger_path(root))
    blob = json.dumps(ingested)
    privacy_ok = "/Users/" not in blob and "/home/" not in blob
    return {
        "feature": FEATURE_HUB,
        "ingested_n": len(ingested),
        "skills": ingested,
        "privacy_ok": privacy_ok,
        "ledger": str(path) if path else str(ledger_path(root)),
        "gap_pressure": (hub or {}).get("gap_pressure") if isinstance(hub, dict) else None,
    }


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def ledger_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_SKILL_FITNESS_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / LEDGER_NAME


def empty_ledger() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "updated_at": _now(),
        "skills": {},
        "history": [],
        "demoted": [],
    }


def load_ledger(path: Path | None = None) -> dict[str, Any]:
    p = path or ledger_path()
    if not p.is_file():
        return empty_ledger()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_ledger()
    if not isinstance(data, dict):
        return empty_ledger()
    data.setdefault("skills", {})
    data.setdefault("history", [])
    data.setdefault("demoted", [])
    data.setdefault("schema_version", SCHEMA)
    data.setdefault("feature", FEATURE)
    return data


def save_ledger(ledger: dict[str, Any], path: Path | None = None) -> Path:
    p = path or ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = _now()
    ledger["feature"] = FEATURE
    ledger["schema_version"] = SCHEMA
    p.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return p


def _skill_entry(ledger: dict[str, Any], sid: str) -> dict[str, Any]:
    skills = ledger.setdefault("skills", {})
    if sid not in skills:
        skills[sid] = {
            "id": sid,
            "selected_n": 0,
            "hit_n": 0,
            "miss_n": 0,
            "hit_rate": 0.0,
            "demoted": False,
            "last_seen": "",
        }
    return skills[sid]


def ingest_hits(
    hits_doc: dict[str, Any],
    ledger: dict[str, Any] | None = None,
    *,
    run_id: str = "",
) -> dict[str, Any]:
    ledger = ledger if ledger is not None else load_ledger()
    for h in hits_doc.get("hits") or []:
        sid = str(h.get("id") or "").strip()
        if not sid or _PATH_RX.search(sid) or "/" in sid:
            continue
        # normalize skill ids only
        sid = re.sub(r"[^A-Za-z0-9._-]+", "-", sid)[:96]
        ent = _skill_entry(ledger, sid)
        ent["selected_n"] = int(ent.get("selected_n") or 0) + 1
        if h.get("hit"):
            ent["hit_n"] = int(ent.get("hit_n") or 0) + 1
        else:
            ent["miss_n"] = int(ent.get("miss_n") or 0) + 1
        # F114: track tool-invocation outcomes separately (prose-only skills leave 0)
        if h.get("tool_hit"):
            ent["tool_hit_n"] = int(ent.get("tool_hit_n") or 0) + 1
        sel = int(ent["selected_n"])
        ent["hit_rate"] = round(int(ent["hit_n"]) / sel, 4) if sel else 0.0
        # F116: tool_hit_rate for demote shield + federate
        ent["tool_hit_rate"] = (
            round(int(ent.get("tool_hit_n") or 0) / sel, 4) if sel else 0.0
        )
        ent["last_seen"] = _now()

    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "run_id": run_id or hits_doc.get("review") or "",
            "hit_rate": hits_doc.get("hit_rate"),
            "selected_n": hits_doc.get("selected_n"),
            "hit_n": hits_doc.get("hit_n"),
            "tool_hit_n": hits_doc.get("tool_hit_n"),
            "tool_hit_rate": hits_doc.get("tool_hit_rate"),
            "themes": list(hits_doc.get("federated_skill_themes") or [])[:16],
        }
    )
    ledger["history"] = hist[-100:]
    return ledger


def _effective_rate(ent: dict[str, Any]) -> float:
    """F116: demote uses max(prose/combined hit_rate, tool_hit_rate)."""
    rate = float(ent.get("hit_rate") or 0.0)
    if not tool_fitness_enabled():
        return rate
    tool_rate = float(ent.get("tool_hit_rate") or 0.0)
    if tool_rate <= 0:
        n = int(ent.get("selected_n") or 0)
        tool_n = int(ent.get("tool_hit_n") or 0)
        tool_rate = (tool_n / n) if n else 0.0
    return max(rate, tool_rate)


def apply_demotions(ledger: dict[str, Any]) -> dict[str, Any]:
    min_n = _int_env("TORII_SKILL_FITNESS_MIN_N", 3)
    thr = _float_env("TORII_SKILL_FITNESS_DEMOTE", 0.25)
    # F158: chronic hub-archival util gap thr (gap_rate ≥ this after min samples)
    ha_gap_thr = _float_env("TORII_SKILL_FITNESS_HUB_ARCHIVAL_GAP_THR", 0.67)
    demoted: list[str] = []
    revived: list[str] = []
    shielded: list[str] = []
    ha_demoted: list[str] = []
    for sid, ent in (ledger.get("skills") or {}).items():
        n = int(ent.get("selected_n") or 0)
        rate = float(ent.get("hit_rate") or 0.0)
        eff = _effective_rate(ent)
        tool_n = int(ent.get("tool_hit_n") or 0)
        was = bool(ent.get("demoted"))
        # F116: tool-effective skills (any tool_hit with samples) never demote
        tool_shield = bool(tool_fitness_enabled() and tool_n >= 1 and n >= 1)
        # F166: recently GEPA-refined skills shield demote — F171 lifts on chronic dual_fail
        chronic_dual_fail = bool(
            refine_dual_decay_enabled()
            and ent.get("refine_dual_chronic_fail")
            and int(ent.get("refine_dual_selected_n") or 0) >= min_n
            and float(ent.get("refine_dual_fail_rate") or 0) >= refine_dual_fail_thr()
        )
        refine_shield = bool(
            refine_fitness_enabled()
            and (ent.get("gepa_refined") or int(ent.get("refined_n") or 0) >= 1)
            and not chronic_dual_fail
        )
        if (tool_shield or refine_shield) and was:
            ent["demoted"] = False
            revived.append(sid)
            shielded.append(sid)
            continue
        if tool_shield or refine_shield:
            ent["demoted"] = False
            shielded.append(sid)
            continue
        # F171: chronic refine dual_fail → soft demote + priority decay (Assay: not all skills help)
        if chronic_dual_fail:
            ent["demoted"] = True
            demoted.append(sid)
            ent["refine_priority_decay"] = int(
                ent.get("refine_priority_decay")
                or (-15 - min(15, int(10 * float(ent.get("refine_dual_fail_rate") or 0))))
            )
            continue
        # F158: hub-archival chronic util gap (inject ≠ hub_boost) → demote
        # even when always:true — soft demote hits fitness_boosts / router, not inject flag
        if (
            hub_archival_fitness_enabled()
            and sid == HUB_ARCHIVAL_SKILL_ID
            and int(ent.get("hub_archival_selected_n") or 0) >= min_n
        ):
            ha_gap_rate = float(ent.get("hub_archival_gap_rate") or 0.0)
            ha_hit = int(ent.get("hub_archival_hit_n") or 0)
            if ha_hit < 1 and ha_gap_rate >= ha_gap_thr:
                ent["demoted"] = True
                demoted.append(sid)
                ha_demoted.append(sid)
                continue
            if ha_hit >= 1 and float(ent.get("hub_archival_util_rate") or 0) >= 0.34:
                if was:
                    revived.append(sid)
                ent["demoted"] = False
                continue
        # never demote always-on core by id heuristic — skill_router still
        # respects always flag; ledger may still mark low performers for info
        if n >= min_n and eff < thr:
            ent["demoted"] = True
            demoted.append(sid)
        elif n >= min_n and eff >= thr + 0.15:
            # revive on sustained recovery
            if was:
                revived.append(sid)
            ent["demoted"] = False
        # if under min_n keep current demoted flag
    ledger["demoted"] = sorted(
        sid for sid, e in (ledger.get("skills") or {}).items() if e.get("demoted")
    )
    ledger["last_demote"] = {
        "at": _now(),
        "min_n": min_n,
        "threshold": thr,
        "newly_demoted": demoted,
        "revived": revived,
        "tool_shielded": shielded,
        "hub_archival_demoted": ha_demoted,
        "hub_archival_gap_thr": ha_gap_thr,
        "demoted_n": len(ledger["demoted"]),
        "feature_tool": FEATURE_TOOL if tool_fitness_enabled() else None,
        "feature_hub_archival": FEATURE_HUB_ARCHIVAL
        if hub_archival_fitness_enabled()
        else None,
    }
    return ledger


def fitness_boosts(ledger: dict[str, Any] | None = None) -> dict[str, float]:
    """Score deltas for skill_router: hit_rate + F116 tool bonus; demoted negative."""
    ledger = ledger if ledger is not None else load_ledger()
    max_boost = _float_env("TORII_SKILL_FITNESS_BOOST", 2.0)
    out: dict[str, float] = {}
    use_tool = tool_fitness_enabled()
    for sid, ent in (ledger.get("skills") or {}).items():
        n = int(ent.get("selected_n") or 0)
        if n < 1:
            continue
        rate = float(ent.get("hit_rate") or 0.0)
        if ent.get("demoted"):
            out[sid] = -max_boost  # strong penalty (unless always)
            continue
        # map hit_rate [0,1] → [0, max_boost] after min 1 sample; stronger after 3
        conf = min(1.0, n / 3.0)
        score = rate * max_boost * conf
        if use_tool:
            tool_n = int(ent.get("tool_hit_n") or 0)
            tool_rate = tool_n / n if n else 0.0
            # half-weight tool bonus so recovery skills rank above prose-only peers
            score += tool_rate * max_boost * 0.5 * conf
        # F158: hub-archival util_rate boost / chronic gap penalty (soft rank)
        if (
            hub_archival_fitness_enabled()
            and sid == HUB_ARCHIVAL_SKILL_ID
            and int(ent.get("hub_archival_selected_n") or 0) >= 1
        ):
            ha_rate = float(ent.get("hub_archival_util_rate") or 0.0)
            ha_gap = float(ent.get("hub_archival_gap_rate") or 0.0)
            score += ha_rate * max_boost * 0.6 * conf
            score -= ha_gap * max_boost * 0.8 * conf
        out[sid] = round(score, 3)
    return out


def demoted_set(ledger: dict[str, Any] | None = None) -> set[str]:
    ledger = ledger if ledger is not None else load_ledger()
    return set(ledger.get("demoted") or [])


def federate_signals(
    ledger: dict[str, Any] | None = None,
    *,
    tenant: str = "",
) -> list[dict[str, Any]]:
    """Privacy-safe F77-shaped signals for high-hit / tool-hit skills (ids only)."""
    ledger = ledger if ledger is not None else load_ledger()
    tenant = tenant or (os.environ.get("TORII_MEMORY_TENANT") or "").strip()
    th = ""
    if tenant:
        th = hashlib.sha256(tenant.encode("utf-8")).hexdigest()[:12]
    signals: list[dict[str, Any]] = []
    use_tool = tool_fitness_enabled()
    for sid, ent in (ledger.get("skills") or {}).items():
        if _PATH_RX.search(sid) or "/" in sid:
            continue
        hit_n = int(ent.get("hit_n") or 0)
        tool_n = int(ent.get("tool_hit_n") or 0)
        # F116: tool-only contributors still federate (even if prose hit_n=0)
        if hit_n < 1 and not (use_tool and tool_n >= 1):
            continue
        if ent.get("demoted"):
            continue
        theme = f"skill:{sid}" if not sid.startswith("skill") else sid
        # F77 theme is free-form lower slug
        theme_slug = re.sub(r"[^a-z0-9._-]+", "-", theme.lower())[:64]
        tags = ["skill_hit", "f85", "federated_skill"]
        keywords = [sid.replace("skill-", "")[:48], "skill-fitness"]
        if use_tool and tool_n >= 1:
            tags.extend(["tool_outcome", "f116"])
            keywords.append("tool-outcome")
        if ent.get("scorecard_ops") or int(ent.get("scorecard_ingested_n") or 0) >= 1:
            tags.extend(["scorecard_ops", "f135"])
            keywords.append("scorecard-ops")
        if ent.get("hub_archival_ops") or int(ent.get("hub_archival_hit_n") or 0) >= 1:
            tags.extend(["hub_archival", "f158", "hub_boost"])
            keywords.extend(["hub-archival", "hub-boost"])
        sig: dict[str, Any] = {
            "id": theme_slug,
            "theme": theme_slug,
            "cwe": [],
            "tags": tags,
            "keywords": keywords,
            "path_basenames": [],  # never paths
            "hits": max(1, hit_n, tool_n),
            "source": "skill_fitness",
            "tenants": 1,
        }
        if use_tool and tool_n >= 1:
            # privacy-safe count only — no commands/paths
            sig["tool_hits"] = tool_n
        if th:
            sig["tenant_hashes"] = [th]
            sig["tenant_hash"] = th
        signals.append(sig)

    # F161: chronic hub-archival util gap (even when demoted) → multi-tenant pressure
    if hub_archival_fitness_enabled():
        ha_ent = (ledger.get("skills") or {}).get(HUB_ARCHIVAL_SKILL_ID) or {}
        ha_gap_n = int(ha_ent.get("hub_archival_gap_n") or 0)
        ha_sel = int(ha_ent.get("hub_archival_selected_n") or 0)
        ha_gap_rate = float(ha_ent.get("hub_archival_gap_rate") or 0.0)
        if ha_sel >= 1 and ha_gap_n >= 1 and ha_gap_rate >= 0.34:
            gap_sig: dict[str, Any] = {
                "id": "hub-archival-util-gap",
                "theme": "hub-archival-util-gap",
                "cwe": [],
                "tags": [
                    "hub_archival",
                    "utilization_gap",
                    "hub_archival_idle",
                    "f161",
                    "f158",
                    "federated_skill",
                ],
                "keywords": ["hub-archival-gap", "hub-boost-idle", "chronic"],
                "path_basenames": [],
                "hits": max(1, ha_gap_n),
                "source": "skill_fitness_hub_archival",
                "tenants": 1,
                "util_rate_bin": "gap",
                "hub_archival_idle": True,
            }
            if th:
                gap_sig["tenant_hashes"] = [th]
                gap_sig["tenant_hash"] = th
            signals.append(gap_sig)
    return signals


def write_fed_file(
    signals: list[dict[str, Any]],
    root: Path | None = None,
    dest: Path | None = None,
) -> Path:
    root = root or _root()
    dest = dest or (root / "memory" / "federation" / "skill-fitness-signals.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # privacy assert
    issues = []
    for s in signals:
        blob = json.dumps(s)
        if "/Users/" in blob or "/home/" in blob:
            issues.append(s.get("id"))
    clean = [s for s in signals if s.get("id") not in issues]
    tool_n = sum(1 for s in clean if "tool_outcome" in (s.get("tags") or []))
    # F161: also write hub-archival slice for multi-tenant pressure consumers
    ha_sigs = [
        s
        for s in clean
        if "hub_archival" in (s.get("tags") or [])
        or str(s.get("theme") or "").startswith("hub-archival")
    ]
    if ha_sigs:
        try:
            ha_dest = root / "memory" / "federation" / "hub-archival-util-signals.json"
            ha_dest.write_text(
                json.dumps(
                    {
                        "schema_version": SCHEMA,
                        "feature": FEATURE_HUB_ARCHIVAL,
                        "feature_hub": "F161",
                        "scope": "hub_archival_util",
                        "updated_at": _now(),
                        "privacy_ok": True,
                        "signals": ha_sigs,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
    doc = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "feature_tool": FEATURE_TOOL if tool_fitness_enabled() else None,
        "scope": "skill_fitness",
        "updated_at": _now(),
        "count": len(clean),
        "tool_outcome_n": tool_n,
        "privacy": "skill_id_hits_tenant_hash_only",
        "privacy_ok": len(issues) == 0,
        "privacy_issues": issues,
        "signals": clean,
    }
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return dest


def cycle(out_dir: Path | None = None, root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    ledger = load_ledger(ledger_path(root))
    ingested = False
    hits_path = None
    if out_dir:
        hits_path = Path(out_dir) / "skill-hits.json"
        if hits_path.is_file():
            try:
                hits = json.loads(hits_path.read_text(encoding="utf-8"))
                ledger = ingest_hits(hits, ledger, run_id=str(out_dir))
                ingested = True
            except (OSError, json.JSONDecodeError):
                pass
    # F126: fold hub recovery-util post-score into ledger before demote
    hub_fit = None
    if hub_fitness_enabled():
        try:
            hub_fit = ingest_hub_recovery(None, ledger, root=root, save=False)
            # ledger already mutated; ensure demote sees tool shields
        except Exception as exc:
            hub_fit = {"soft_error": str(exc)[:120]}
    # F135: fold F134 scorecard skill themes into ledger before demote
    sc_fit = None
    if scorecard_fitness_enabled():
        try:
            sc_fit = ingest_scorecard_skills(None, ledger, root=root, save=False)
        except Exception as exc:
            sc_fit = {"soft_error": str(exc)[:120]}
    # F158: fold hub-archival util gap/hit before demote
    ha_fit = None
    if hub_archival_fitness_enabled():
        try:
            ha_fit = ingest_hub_archival_util(
                None, ledger, root=root, out_dir=out_dir, save=False
            )
        except Exception as exc:
            ha_fit = {"soft_error": str(exc)[:120]}
    ledger = apply_demotions(ledger)
    path = save_ledger(ledger, ledger_path(root))
    signals = federate_signals(ledger)
    fed_path = write_fed_file(signals, root=root)
    # soft hub ingest if available
    hub_result = None
    try:
        sys.path.insert(0, str(root / "scripts"))
        from federated_hub_ingest import ingest as hub_ingest  # type: ignore

        tenant = (os.environ.get("TORII_MEMORY_TENANT") or "").strip()
        hub_result = hub_ingest(
            root,
            signals,
            tenant=tenant,
            source_repo="skill_fitness",
            write_tenant=bool(tenant),
        )
    except Exception as exc:  # soft
        hub_result = {"soft_error": str(exc)[:120]}

    tool_skills = [
        sid
        for sid, e in (ledger.get("skills") or {}).items()
        if int(e.get("tool_hit_n") or 0) >= 1
    ]
    scorecard_skills = [
        sid
        for sid, e in (ledger.get("skills") or {}).items()
        if e.get("scorecard_ops") or int(e.get("scorecard_ingested_n") or 0) >= 1
    ]
    hub_archival_skills = [
        sid
        for sid, e in (ledger.get("skills") or {}).items()
        if e.get("hub_archival_ops")
        or int(e.get("hub_archival_selected_n") or 0) >= 1
    ]
    return {
        "feature": FEATURE,
        "feature_tool": FEATURE_TOOL if tool_fitness_enabled() else None,
        "feature_hub": FEATURE_HUB if hub_fitness_enabled() else None,
        "feature_scorecard": FEATURE_SCORECARD if scorecard_fitness_enabled() else None,
        "feature_hub_archival": FEATURE_HUB_ARCHIVAL
        if hub_archival_fitness_enabled()
        else None,
        "ingested": ingested,
        "hits_path": str(hits_path) if hits_path else None,
        "ledger": str(path),
        "demoted": list(ledger.get("demoted") or []),
        "tool_shielded": list((ledger.get("last_demote") or {}).get("tool_shielded") or []),
        "hub_archival_demoted": list(
            (ledger.get("last_demote") or {}).get("hub_archival_demoted") or []
        ),
        "tool_skills": tool_skills,
        "scorecard_skills": scorecard_skills,
        "hub_archival_skills": hub_archival_skills,
        "boosts": fitness_boosts(ledger),
        "fed_path": str(fed_path),
        "fed_n": len(signals),
        "tool_outcome_fed_n": sum(
            1 for s in signals if "tool_outcome" in (s.get("tags") or [])
        ),
        "hub": hub_result,
        "hub_fitness": hub_fit,
        "scorecard_fitness": sc_fit,
        "hub_archival_fitness": ha_fit,
        "privacy_ok": True,
    }


# --- CLI ---


def cmd_ingest(args: argparse.Namespace) -> int:
    root = _root()
    out_dir = Path(args.out_dir) if args.out_dir else Path(os.environ.get("OUT_DIR") or ".")
    hits_path = Path(args.hits) if args.hits else out_dir / "skill-hits.json"
    if not hits_path.is_file():
        print(json.dumps({"feature": FEATURE, "ingested": 0, "reason": "no skill-hits.json"}))
        return 0
    hits = json.loads(hits_path.read_text(encoding="utf-8"))
    ledger = ingest_hits(hits, load_ledger(ledger_path(root)), run_id=str(out_dir))
    path = save_ledger(ledger, ledger_path(root))
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "ingested": 1,
                "ledger": str(path),
                "skills_n": len(ledger.get("skills") or {}),
                "history_n": len(ledger.get("history") or []),
            },
            indent=2,
        )
    )
    return 0


def cmd_demote(args: argparse.Namespace) -> int:
    root = _root()
    ledger = apply_demotions(load_ledger(ledger_path(root)))
    path = save_ledger(ledger, ledger_path(root))
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "ledger": str(path),
                "demoted": ledger.get("demoted") or [],
                "last_demote": ledger.get("last_demote"),
            },
            indent=2,
        )
    )
    return 0


def cmd_boosts(args: argparse.Namespace) -> int:
    b = fitness_boosts(load_ledger())
    print(json.dumps({"feature": FEATURE, "boosts": b, "demoted": sorted(demoted_set())}, indent=2))
    return 0


def cmd_federate(args: argparse.Namespace) -> int:
    root = _root()
    ledger = load_ledger(ledger_path(root))
    signals = federate_signals(ledger)
    dest = write_fed_file(signals, root=root, dest=Path(args.out) if args.out else None)
    hub = None
    if not args.no_hub:
        try:
            sys.path.insert(0, str(root / "scripts"))
            from federated_hub_ingest import ingest as hub_ingest  # type: ignore

            hub = hub_ingest(
                root,
                signals,
                tenant=(os.environ.get("TORII_MEMORY_TENANT") or "").strip(),
                source_repo="skill_fitness",
            )
        except Exception as exc:
            hub = {"soft_error": str(exc)[:120]}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fed_path": str(dest),
                "fed_n": len(signals),
                "privacy_ok": "/Users/" not in dest.read_text(encoding="utf-8"),
                "hub": hub,
            },
            indent=2,
        )
    )
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "skipped": 1, "reason": "disabled"}))
        return 0
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir is None and (os.environ.get("OUT_DIR") or "").strip():
        out_dir = Path(os.environ["OUT_DIR"])
    result = cycle(out_dir=out_dir, root=_root())
    print(json.dumps(result, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ledger = load_ledger()
    skills = ledger.get("skills") or {}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "ledger": str(ledger_path()),
                "skills_n": len(skills),
                "demoted": list(ledger.get("demoted") or []),
                "history_n": len(ledger.get("history") or []),
                "boosts": fitness_boosts(ledger),
                "top": sorted(
                    (
                        {
                            "id": s,
                            "hit_rate": e.get("hit_rate"),
                            "selected_n": e.get("selected_n"),
                            "demoted": e.get("demoted"),
                        }
                        for s, e in skills.items()
                    ),
                    key=lambda x: (-float(x.get("hit_rate") or 0), str(x["id"])),
                )[:10],
            },
            indent=2,
        )
    )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Machine-readable demoted set + boosts for skill_router."""
    ledger = load_ledger()
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "demoted": sorted(demoted_set(ledger)),
                "boosts": fitness_boosts(ledger),
            }
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    prev_env = {
        k: os.environ.get(k)
        for k in (
            "TORII_ROOT",
            "TORII_SKILL_FITNESS",
            "TORII_SKILL_FITNESS_MIN_N",
            "TORII_SKILL_FITNESS_DEMOTE",
            "TORII_SKILL_FITNESS_BOOST",
            "TORII_MEMORY_TENANT",
            "TORII_SKILL_FITNESS_SCORECARD",
        )
    }
    try:
        return _cmd_fixture_body()
    finally:
        for k, v in prev_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _cmd_fixture_body() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        os.environ["TORII_ROOT"] = str(root)
        os.environ["TORII_SKILL_FITNESS"] = "1"
        os.environ["TORII_SKILL_FITNESS_MIN_N"] = "3"
        os.environ["TORII_SKILL_FITNESS_DEMOTE"] = "0.34"
        os.environ["TORII_SKILL_FITNESS_BOOST"] = "2.0"
        os.environ["TORII_MEMORY_TENANT"] = "fixture-tenant-a"
        os.environ["TORII_SKILL_FITNESS_SCORECARD"] = "1"

        # good skill always hits; zombie never hits
        good = "skill-f74-prefer-chain-json"
        zombie = "skill-zombie-docs"
        ledger = empty_ledger()
        for i in range(4):
            hits = {
                "hit_rate": 0.5,
                "selected_n": 2,
                "hit_n": 1,
                "hits": [
                    {"id": good, "hit": True, "matched": ["chain"]},
                    {"id": zombie, "hit": False, "matched": []},
                ],
                "federated_skill_themes": [good],
                "review": f"run-{i}",
            }
            ledger = ingest_hits(hits, ledger, run_id=f"run-{i}")
        # one extra hit for good to push rate up
        ledger = ingest_hits(
            {
                "hits": [{"id": good, "hit": True, "matched": ["taint"]}],
                "federated_skill_themes": [good],
            },
            ledger,
            run_id="run-extra",
        )
        ledger = apply_demotions(ledger)
        path = save_ledger(ledger, ledger_path(root))

        boosts = fitness_boosts(ledger)
        demoted = demoted_set(ledger)
        zombie_demoted = zombie in demoted
        good_not_demoted = good not in demoted
        good_boost = boosts.get(good, 0) > 0
        zombie_pen = boosts.get(zombie, 0) < 0

        signals = federate_signals(ledger, tenant="fixture-tenant-a")
        fed_path = write_fed_file(signals, root=root)
        fed_text = fed_path.read_text(encoding="utf-8")
        privacy_ok = "/Users/" not in fed_text and "fixture-tenant-a" not in fed_text
        good_in_fed = any(good in str(s.get("id")) or good in str(s.get("theme")) for s in signals)
        zombie_not_fed = not any(zombie in str(s) for s in signals)

        # router integration: patch score via boosts API
        # simulate select preference: good boost > zombie
        order_ok = boosts.get(good, 0) > boosts.get(zombie, -99)

        # F116: tool-only recovery skill — low prose hit_rate but tool_hit_n>0 → shield
        tool_skill = "skill-prefer-memory-cli-early"
        for i in range(4):
            ledger = ingest_hits(
                {
                    "hits": [
                        {
                            "id": tool_skill,
                            # combined hit via tool (F114) may still be True;
                            # stress shield even when hit True only via tools
                            "hit": True,
                            "tool_hit": True,
                            "prose_hit": False,
                            "matched": [],
                        }
                    ],
                    "tool_hit_n": 1,
                    "tool_hit_rate": 1.0,
                    "hit_n": 1,
                    "selected_n": 1,
                    "hit_rate": 1.0,
                },
                ledger,
                run_id=f"tool-run-{i}",
            )
        # adversarial: force low hit_rate with tool hits still present
        ent_t = (ledger.get("skills") or {}).get(tool_skill) or {}
        ent_t["hit_rate"] = 0.1  # would demote without shield
        ent_t["selected_n"] = 4
        ent_t["hit_n"] = 1
        ent_t["tool_hit_n"] = 3
        ent_t["tool_hit_rate"] = 0.75
        ent_t["demoted"] = True  # was wrongly demoted pre-F116
        (ledger.setdefault("skills", {}))[tool_skill] = ent_t
        ledger = apply_demotions(ledger)
        tool_shielded = tool_skill not in demoted_set(ledger)
        tool_boost = fitness_boosts(ledger).get(tool_skill, 0) > fitness_boosts(ledger).get(
            zombie, -99
        )
        tool_sigs = federate_signals(ledger, tenant="fixture-tenant-a")
        tool_in_fed = any(
            tool_skill in str(s.get("id") or s.get("theme") or "")
            and "tool_outcome" in (s.get("tags") or [])
            for s in tool_sigs
        )
        tool_privacy = "/Users/" not in json.dumps(tool_sigs)

        # cycle with out_dir skill-hits
        out_dir = root / "out"
        out_dir.mkdir()
        (out_dir / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {"id": good, "hit": True, "matched": ["chain"]},
                        {"id": zombie, "hit": False, "matched": []},
                        {
                            "id": tool_skill,
                            "hit": True,
                            "tool_hit": True,
                            "prose_hit": False,
                            "matched": [],
                        },
                    ],
                    "hit_rate": 0.67,
                    "selected_n": 3,
                    "hit_n": 2,
                    "tool_hit_n": 1,
                    "tool_hit_rate": 0.33,
                    "federated_skill_themes": [good, tool_skill],
                }
            ),
            encoding="utf-8",
        )
        cyc = cycle(out_dir=out_dir, root=root)

        # F135: plant scorecard skill signals → fitness ingest shields ops skills
        sc_skill = "skill-prefer-product-scorecard"
        fed_dir = root / "memory" / "federation"
        fed_dir.mkdir(parents=True, exist_ok=True)
        sc_doc = {
            "schema_version": 1,
            "feature": "F133",
            "feature_federate": "F134",
            "privacy_ok": True,
            "skill_ids": [sc_skill, "skill-prefer-demote-eval-check"],
            "signals": [
                {
                    "id": "scorecard-skill-skill-prefer-product-scorecard",
                    "theme": sc_skill,
                    "tags": ["scorecard_ops", "federated_skill", "f134", "tool_outcome"],
                    "keywords": ["product-scorecard", "scorecard-gap"],
                    "path_basenames": [],
                    "hits": 1,
                    "tool_hits": 1,
                    "source": "scorecard_skill_adopt",
                }
            ],
        }
        (fed_dir / "scorecard-skill-signals.json").write_text(
            json.dumps(sc_doc, indent=2) + "\n", encoding="utf-8"
        )
        # adversarial: pretent demoted before ingest
        ent_sc = _skill_entry(ledger, sc_skill)
        ent_sc["selected_n"] = 4
        ent_sc["hit_n"] = 0
        ent_sc["hit_rate"] = 0.0
        ent_sc["demoted"] = True
        ledger.setdefault("skills", {})[sc_skill] = ent_sc
        sc_fit = ingest_scorecard_skills(sc_doc, ledger, root=root, save=True)
        ledger = apply_demotions(load_ledger(ledger_path(root)))
        sc_shielded = sc_skill not in demoted_set(ledger)
        sc_boost = fitness_boosts(ledger).get(sc_skill, 0) > 0
        sc_privacy = bool(sc_fit.get("privacy_ok")) and "fixture-tenant-a" not in json.dumps(
            sc_fit
        )
        sc_ops_ok = bool(sc_fit.get("scorecard_ops_ok"))
        sc_in_fed_out = any(
            sc_skill in str(s.get("id") or s.get("theme") or "")
            for s in federate_signals(ledger, tenant="fixture-tenant-a")
        )

        # F158: chronic hub-archival util gap → demote; hub_boost hit → revive/boost
        os.environ["TORII_SKILL_FITNESS_HUB_ARCHIVAL"] = "1"
        ha_sid = HUB_ARCHIVAL_SKILL_ID
        # 3 gap samples (inject idle)
        for i in range(3):
            util_gap = {
                "hub_archival_injected": True,
                "hub_archival_tool_hit": False,
                "hub_archival_util_gap": True,
                "util_rate": 0.5,
            }
            ingest_hub_archival_util(util_gap, ledger, root=root, save=False)
        ledger = apply_demotions(ledger)
        ha_gap_demoted = ha_sid in demoted_set(ledger)
        ha_gap_boost = fitness_boosts(ledger).get(ha_sid, 0)
        # revive with tool hit samples
        for i in range(2):
            util_hit = {
                "hub_archival_injected": True,
                "hub_archival_tool_hit": True,
                "hub_archival_util_gap": False,
                "util_rate": 1.0,
            }
            ingest_hub_archival_util(util_hit, ledger, root=root, save=False)
        ledger = apply_demotions(ledger)
        save_ledger(ledger, ledger_path(root))
        ha_revived = ha_sid not in demoted_set(ledger)
        ha_hit_boost = fitness_boosts(ledger).get(ha_sid, 0)
        ha_ent = (ledger.get("skills") or {}).get(ha_sid) or {}
        ha_privacy = "/Users/" not in json.dumps(ha_ent)
        ha_in_fed = any(
            ha_sid in str(s.get("id") or s.get("theme") or "")
            and "hub_archival" in (s.get("tags") or [])
            for s in federate_signals(ledger, tenant="fixture-tenant-a")
        )
        # cycle path: plant recovery-skill-util and run cycle
        (out_dir / "recovery-skill-util.json").write_text(
            json.dumps(
                {
                    "hub_archival_injected": True,
                    "hub_archival_tool_hit": True,
                    "hub_archival_util_gap": False,
                    "feature_hub_archival_util": "F155",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        cyc2 = cycle(out_dir=out_dir, root=root)
        f158_ok = (
            ha_gap_demoted
            and ha_revived
            and ha_hit_boost > ha_gap_boost
            and float(ha_ent.get("hub_archival_util_rate") or 0) > 0
            and int(ha_ent.get("hub_archival_hit_n") or 0) >= 2
            and ha_privacy
            and ha_in_fed
            and int((cyc2.get("hub_archival_fitness") or {}).get("ingested") or 0) >= 1
        )

        fixture_pass = all(
            [
                zombie_demoted,
                good_not_demoted,
                good_boost,
                zombie_pen,
                privacy_ok,
                good_in_fed,
                zombie_not_fed,
                order_ok,
                cyc.get("ingested") is True,
                path.is_file(),
                tool_shielded,
                tool_boost,
                tool_in_fed,
                tool_privacy,
                int(cyc.get("tool_outcome_fed_n") or 0) >= 1
                or tool_skill in (cyc.get("tool_skills") or []),
                # F135
                sc_shielded,
                sc_boost,
                sc_privacy,
                sc_ops_ok,
                int(sc_fit.get("ingested_n") or 0) >= 1,
                sc_in_fed_out,
                # F158
                f158_ok,
            ]
        )
        print(
            json.dumps(
                {
                    "feature": FEATURE,
                    "feature_tool": FEATURE_TOOL,
                    "feature_scorecard": FEATURE_SCORECARD,
                    "feature_hub_archival": FEATURE_HUB_ARCHIVAL,
                    "f116": True,
                    "f135": True,
                    "f158": True,
                    "fixture_pass": fixture_pass,
                    "zombie_demoted": zombie_demoted,
                    "good_not_demoted": good_not_demoted,
                    "good_boost": boosts.get(good),
                    "zombie_boost": boosts.get(zombie),
                    "privacy_ok": privacy_ok,
                    "good_in_fed": good_in_fed,
                    "zombie_not_fed": zombie_not_fed,
                    "tool_shielded": tool_shielded,
                    "tool_boost_ok": tool_boost,
                    "tool_in_fed": tool_in_fed,
                    "tool_outcome_fed_n": cyc.get("tool_outcome_fed_n"),
                    "tool_skills": cyc.get("tool_skills"),
                    "f135_sc_shielded": sc_shielded,
                    "f135_sc_boost": fitness_boosts(ledger).get(sc_skill),
                    "f135_sc_ops_ok": sc_ops_ok,
                    "f135_sc_privacy_ok": sc_privacy,
                    "f135_sc_ingested_n": sc_fit.get("ingested_n"),
                    "f135_sc_in_fed": sc_in_fed_out,
                    "f158_ok": f158_ok,
                    "f158_ha_gap_demoted": ha_gap_demoted,
                    "f158_ha_revived": ha_revived,
                    "f158_ha_gap_boost": ha_gap_boost,
                    "f158_ha_hit_boost": ha_hit_boost,
                    "f158_ha_util_rate": ha_ent.get("hub_archival_util_rate"),
                    "f158_ha_in_fed": ha_in_fed,
                    "f158_cycle_ingested": (cyc2.get("hub_archival_fitness") or {}).get(
                        "ingested"
                    ),
                    "demoted": sorted(demoted_set(ledger)),
                    "cycle_fed_n": cyc.get("fed_n"),
                    "ledger": str(path),
                },
                indent=2,
            )
        )
        return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F85 skill fitness ledger")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="Ingest skill-hits.json into ledger")
    pi.add_argument("--out-dir", default="")
    pi.add_argument("--hits", default="")
    pi.set_defaults(func=cmd_ingest)

    sub.add_parser("demote", help="Apply demotion thresholds").set_defaults(func=cmd_demote)
    sub.add_parser("boosts", help="Print fitness score deltas").set_defaults(func=cmd_boosts)
    sub.add_parser("status", help="Ledger summary").set_defaults(func=cmd_status)
    sub.add_parser("apply", help="JSON demoted+boosts for router").set_defaults(func=cmd_apply)
    sub.add_parser("fixture", help="Hermetic offline fixture").set_defaults(func=cmd_fixture)

    pf = sub.add_parser("federate", help="Emit skill themes to federation")
    pf.add_argument("--out", default="")
    pf.add_argument("--no-hub", action="store_true")
    pf.set_defaults(func=cmd_federate)

    pc = sub.add_parser("cycle", help="ingest → demote → federate")
    pc.add_argument("--out-dir", default="")
    pc.add_argument("--force", action="store_true")
    pc.set_defaults(func=cmd_cycle)

    psc = sub.add_parser(
        "ingest-scorecard",
        help="F135 fold scorecard-skill-signals into fitness ledger",
    )
    psc.add_argument(
        "--file",
        default="",
        help="Optional path to scorecard-skill-signals.json",
    )
    psc.set_defaults(func=cmd_ingest_scorecard)

    prf = sub.add_parser(
        "ingest-refine",
        help="F166 ingest F165 skill-refine.json into fitness (shield demote)",
    )
    prf.add_argument("--out-dir", default="", help="dir with skill-refine.json")
    prf.add_argument("--refine", default="", help="path to skill-refine.json")
    prf.set_defaults(func=cmd_ingest_refine)

    prd = sub.add_parser(
        "ingest-refine-dual",
        help="F171 ingest refine-dual.json pass/fail for chronic dual_fail decay",
    )
    prd.add_argument("--out-dir", default="", help="dir with refine-dual.json")
    prd.add_argument("--report", default="", help="path to refine-dual.json")
    prd.set_defaults(func=cmd_ingest_refine_dual)

    pfd = sub.add_parser(
        "federate-refine-decay",
        help="F172 privacy-safe federate of chronic dual_fail decay bins",
    )
    pfd.add_argument(
        "--skills",
        default="",
        help="comma skill ids (default: chronic_fail from ledger)",
    )
    pfd.set_defaults(func=cmd_federate_refine_decay)

    ppd = sub.add_parser(
        "promote-refine-decay",
        help="F172 multi-tenant promote gate for chronic dual_fail decay",
    )
    ppd.add_argument("--min-tenants", type=int, default=None)
    ppd.add_argument("--min-hits", type=int, default=None)
    ppd.set_defaults(func=cmd_promote_refine_decay)

    pfrv = sub.add_parser(
        "federate-refine-revive",
        help="F175 privacy-safe federate of dual_pass revive after decay",
    )
    pfrv.add_argument(
        "--skills",
        default="",
        help="comma skill ids (default: refine_dual_revived from ledger)",
    )
    pfrv.set_defaults(func=cmd_federate_refine_revive)

    pprv = sub.add_parser(
        "promote-refine-revive",
        help="F175 multi-tenant promote gate for dual_pass revive re-boost",
    )
    pprv.add_argument("--min-tenants", type=int, default=None)
    pprv.add_argument("--min-hits", type=int, default=None)
    pprv.set_defaults(func=cmd_promote_refine_revive)

    pfix = sub.add_parser(
        "fixture-refine-revive",
        help="F175 hermetic: local revive + multi-tenant re-boost after decay",
    )
    pfix.set_defaults(func=cmd_fixture_refine_revive)

    pfrpp = sub.add_parser(
        "fixture-refine-revive-pp",
        help="F177 hermetic: contribution_pp floor for dual_pass revive",
    )
    pfrpp.set_defaults(func=cmd_fixture_refine_revive_pp)

    pfrloo = sub.add_parser(
        "fixture-refine-revive-loo",
        help="F179 hermetic: LOO free-rider blocks dual_pass revive; positive LOO allows",
    )
    pfrloo.set_defaults(func=cmd_fixture_refine_revive_loo)

    pha = sub.add_parser(
        "ingest-hub-archival",
        help="F158 fold recovery hub-archival util gap/hit into fitness ledger",
    )
    pha.add_argument("--out-dir", default="")
    pha.add_argument(
        "--util",
        default="",
        help="Optional path to recovery-skill-util.json",
    )
    pha.set_defaults(func=cmd_ingest_hub_archival)

    args = p.parse_args(argv)
    return int(args.func(args))


def cmd_ingest_refine(args: argparse.Namespace) -> int:
    """F166: ingest skill-refine.json into fitness ledger."""
    root = _root()
    refine_doc = None
    refine_path = (getattr(args, "refine", "") or "").strip()
    if refine_path:
        p = Path(refine_path)
        if p.is_file():
            try:
                refine_doc = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                refine_doc = None
    out_dir = (getattr(args, "out_dir", "") or "").strip()
    od = Path(out_dir) if out_dir else None
    result = ingest_refine(refine_doc, root=root, out_dir=od, save=True)
    print(json.dumps(result, indent=2))
    return 0 if result.get("privacy_ok", True) else 1


def cmd_ingest_refine_dual(args: argparse.Namespace) -> int:
    """F171: ingest refine-dual.json into fitness for chronic dual_fail decay."""
    root = _root()
    report = None
    rp = (getattr(args, "report", "") or "").strip()
    if rp:
        p = Path(rp)
        if p.is_file():
            try:
                report = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                report = None
    out_dir = (getattr(args, "out_dir", "") or "").strip()
    od = Path(out_dir) if out_dir else None
    result = ingest_refine_dual(report, root=root, out_dir=od, save=True)
    # soft demote pass after ingest
    if result.get("ingested_n"):
        ledger = load_ledger(ledger_path(root))
        apply_demotions(ledger)
        save_ledger(ledger, ledger_path(root))
        result["demote_applied"] = True
        result["demoted"] = list(ledger.get("demoted") or [])[:16]
    print(json.dumps(result, indent=2))
    return 0 if result.get("privacy_ok", True) else 1


def cmd_federate_refine_decay(args: argparse.Namespace) -> int:
    """F172: federate chronic dual_fail decay bins."""
    skills_raw = (getattr(args, "skills", "") or "").strip()
    skill_ids = [s.strip() for s in skills_raw.split(",") if s.strip()] or None
    result = federate_refine_dual_decay(_root(), skill_ids=skill_ids)
    print(json.dumps(result, indent=2))
    return 0 if result.get("privacy_ok", True) else 1


def cmd_promote_refine_decay(args: argparse.Namespace) -> int:
    """F172: multi-tenant promote chronic dual_fail decay."""
    result = promote_refine_dual_decay(
        _root(),
        min_tenants=getattr(args, "min_tenants", None),
        min_hits=getattr(args, "min_hits", None),
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("privacy_ok", True) else 1


def cmd_federate_refine_revive(args: argparse.Namespace) -> int:
    """F175: federate dual_pass revive bins."""
    skills_raw = (getattr(args, "skills", "") or "").strip()
    skill_ids = [s.strip() for s in skills_raw.split(",") if s.strip()] or None
    result = federate_refine_dual_revive(_root(), skill_ids=skill_ids)
    print(json.dumps(result, indent=2))
    return 0 if result.get("privacy_ok", True) else 1


def cmd_promote_refine_revive(args: argparse.Namespace) -> int:
    """F175: multi-tenant promote dual_pass revive re-boost."""
    result = promote_refine_dual_revive(
        _root(),
        min_tenants=getattr(args, "min_tenants", None),
        min_hits=getattr(args, "min_hits", None),
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("privacy_ok", True) else 1


def cmd_fixture_refine_revive(args: argparse.Namespace) -> int:
    """F175 hermetic: decay → dual_pass local revive → multi-tenant re-boost."""
    del args  # unused
    root = _root()
    sid = "skill-prefer-hub-archival-early"
    os.environ["TORII_SKILL_FITNESS_REFINE_DUAL_DECAY"] = "1"
    os.environ["TORII_SKILL_FITNESS_REFINE_DUAL_REVIVE"] = "1"
    os.environ["TORII_SKILL_FITNESS_MIN_N"] = "3"
    os.environ["TORII_SKILL_FITNESS_REFINE_DUAL_FAIL_THR"] = "0.67"
    # plant chronic dual_fail decayed skill
    ledger = load_ledger(ledger_path(root))
    skills = ledger.setdefault("skills", {})
    skills[sid] = {
        "id": sid,
        "refine_dual_selected_n": 3,
        "refine_dual_fail_n": 3,
        "refine_dual_pass_n": 0,
        "refine_dual_fail_rate": 1.0,
        "refine_dual_pass_rate": 0.0,
        "refine_dual_chronic_fail": True,
        "last_refine_decayed": True,
        "multi_tenant_decay": True,
        "multi_tenant_decay_tenants": 2,
        "refine_priority_decay": -25,
        "hub_priority_delta": -20,
        "demoted": True,
        "gepa_refined": True,
        "selected_n": 3,
    }
    save_ledger(ledger, ledger_path(root))
    # isolate free-rider local path: clear multi-tenant revive/decay federation
    # so soft promote during ingest cannot free-ride clear multi_tenant_decay
    fed_dir = root / "memory" / "federation"
    fed_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "skill-refine-dual-revive-signals.json",
        "promoted-refine-dual-revive-themes.json",
        "skill-refine-dual-decay-signals.json",
        "promoted-refine-dual-decay-themes.json",
    ):
        fp = fed_dir / name
        if fp.is_file():
            try:
                fp.unlink()
            except OSError:
                pass
    # dual_pass recovery samples (need pass > fail to streak_ok, or rate < thr)
    # 3 fails + 4 passes → fail_rate=3/7≈0.43 < 0.67
    revived_local = False
    for i in range(4):
        rep = {
            "refine_dual_pass": True,
            "refine_tool_contribution_pp": 50.0,
            "refine_probe_delta": 1,
            "refined_skill_ids": [sid],
            "selected": [sid],
        }
        r = ingest_refine_dual(rep, root=root, save=True)
        if sid in (r.get("revived") or []):
            revived_local = True
    ledger = load_ledger(ledger_path(root))
    ent = (ledger.get("skills") or {}).get(sid) or {}
    local_ok = bool(
        revived_local
        or ent.get("refine_dual_revived")
    ) and not ent.get("refine_dual_chronic_fail") and int(
        ent.get("refine_priority_decay") or 0
    ) >= 0 and int(ent.get("hub_priority_delta") or 0) > 0
    # F176: multi-tenant free-rider gate — local revive must NOT clear multi_tenant_decay
    free_rider_gate_ok = bool(
        ent.get("multi_tenant_decay")
        and ent.get("local_revive_pending_mt")
        and ent.get("free_rider_revive_blocked")
        and not ent.get("multi_tenant_revive")
    )

    # multi-tenant: plant second-tenant revive signal then promote
    fed_path = root / "memory" / "federation" / "skill-refine-dual-revive-signals.json"
    fed_path.parent.mkdir(parents=True, exist_ok=True)
    th_a = _tenant_hash_fitness(root)
    th_b = "fixture-tenant-b12"
    multi_doc = {
        "schema_version": SCHEMA,
        "feature": "F175",
        "scope": "skill_refine_dual_revive",
        "privacy": "skill_id_pass_bin_tenant_hash_only",
        "privacy_ok": True,
        "signals": [
            {
                "id": f"refine-revive-{sid}",
                "theme": sid,
                "skill_id": sid,
                "tags": ["refine_dual_revive", "f175", "dual_pass"],
                "source": "skill_refine_dual_revive",
                "hits": 2,
                "tenants": 1,
                "tenant_hash": th_a,
                "tenant_hashes": [th_a],
                "pass_rate": 0.6,
                "pass_rate_bin": "mid",
                "tool_pp": 50.0,
                "tool_pp_bin": "high",
                "boost": 16,
                "dual_pass": True,
                "feature": "F175",
            },
            {
                "id": f"refine-revive-{sid}-b",
                "theme": sid,
                "skill_id": sid,
                "tags": ["refine_dual_revive", "f175", "dual_pass"],
                "source": "skill_refine_dual_revive",
                "hits": 2,
                "tenants": 1,
                "tenant_hash": th_b,
                "tenant_hashes": [th_b],
                "pass_rate": 0.7,
                "pass_rate_bin": "mid",
                "tool_pp": 50.0,
                "tool_pp_bin": "high",
                "boost": 16,
                "dual_pass": True,
                "feature": "F175",
            },
        ],
    }
    fed_path.write_text(json.dumps(multi_doc, indent=2) + "\n", encoding="utf-8")
    # plant decay themes so supersede can fire
    decay_themes = root / "memory" / "federation" / "promoted-refine-dual-decay-themes.json"
    decay_themes.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA,
                "feature": "F172",
                "promoted_n": 1,
                "signals": [
                    {
                        "skill_id": sid,
                        "theme": sid,
                        "decay": -30,
                        "tenants": 2,
                        "tags": ["promoted_refine_dual_decay"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    prom = promote_refine_dual_revive(root=root, min_tenants=2, min_hits=2)
    multi_ok = (
        int(prom.get("promoted_n") or 0) >= 1
        and sid in (prom.get("revived") or [])
        and bool(prom.get("privacy_ok"))
    )
    ledger2 = load_ledger(ledger_path(root))
    ent2 = (ledger2.get("skills") or {}).get(sid) or {}
    multi_ledger_ok = bool(ent2.get("multi_tenant_revive")) and not ent2.get(
        "multi_tenant_decay"
    ) and int(ent2.get("hub_priority_delta") or 0) >= 16
    # supersede decay themes
    superseded = False
    if decay_themes.is_file():
        try:
            dd = json.loads(decay_themes.read_text(encoding="utf-8"))
            left = [
                s
                for s in (dd.get("signals") or [])
                if str(s.get("skill_id") or "") == sid
            ]
            superseded = len(left) == 0 or dd.get("superseded_by") == "F175"
        except (OSError, json.JSONDecodeError):
            superseded = False
    # federate privacy: signals use tenant hashes only (paths may appear in CLI path field)
    sig_only = {
        "revived": prom.get("revived"),
        "themes": prom.get("themes"),
        "signals_n": prom.get("promoted_n"),
    }
    privacy_ok = bool(prom.get("privacy_ok")) and "/Users/" not in json.dumps(sig_only)
    fed_blob = fed_path.read_text(encoding="utf-8") if fed_path.is_file() else ""
    privacy_ok = privacy_ok and "/Users/" not in fed_blob and "/home/" not in fed_blob
    # bare tenant labels must not appear in promoted themes file
    prom_path = root / "memory" / "federation" / "promoted-refine-dual-revive-themes.json"
    if prom_path.is_file():
        pb = prom_path.read_text(encoding="utf-8")
        privacy_ok = privacy_ok and "/Users/" not in pb and "/home/" not in pb

    f175_ok = bool(local_ok and multi_ok and multi_ledger_ok and superseded and privacy_ok)
    f176_ok = bool(free_rider_gate_ok and multi_ledger_ok and not ent2.get("local_revive_pending_mt"))
    fixture_pass = bool(f175_ok and f176_ok)
    out = {
        "feature": "F175",
        "feature_mt_gate": "F176",
        "fixture_pass": fixture_pass,
        "local_revive_ok": local_ok,
        "free_rider_gate_ok": free_rider_gate_ok,
        "multi_tenant_promote_ok": multi_ok,
        "multi_ledger_ok": multi_ledger_ok,
        "f176_ok": f176_ok,
        "decay_superseded": superseded,
        "privacy_ok": privacy_ok,
        "promoted_n": prom.get("promoted_n"),
        "revived": prom.get("revived"),
        "hub_priority_delta": ent2.get("hub_priority_delta"),
        "multi_tenant_revive": ent2.get("multi_tenant_revive"),
        "multi_tenant_decay_after_local": ent.get("multi_tenant_decay"),
        "multi_tenant_decay_after_promote": ent2.get("multi_tenant_decay"),
        "refine_dual_revived": ent2.get("refine_dual_revived"),
        "refine_priority_decay": ent2.get("refine_priority_decay"),
    }
    print(json.dumps(out, indent=2))
    return 0 if fixture_pass else 1


def cmd_fixture_refine_revive_pp(args: argparse.Namespace) -> int:
    """F177 hermetic: low tool_pp dual_pass does not revive; min_pp+ does."""
    del args
    root = _root()
    sid = "skill-prefer-hub-archival-early"
    os.environ["TORII_SKILL_FITNESS_REFINE_DUAL_DECAY"] = "1"
    os.environ["TORII_SKILL_FITNESS_REFINE_DUAL_REVIVE"] = "1"
    os.environ["TORII_SKILL_FITNESS_REVIVE_PP_GATE"] = "1"
    os.environ["TORII_REFINE_REVIVE_MIN_PP"] = "10"
    os.environ["TORII_SKILL_FITNESS_MIN_N"] = "3"
    os.environ["TORII_SKILL_FITNESS_REFINE_DUAL_FAIL_THR"] = "0.67"
    ledger = load_ledger(ledger_path(root))
    skills = ledger.setdefault("skills", {})
    skills[sid] = {
        "id": sid,
        "refine_dual_selected_n": 3,
        "refine_dual_fail_n": 3,
        "refine_dual_pass_n": 0,
        "refine_dual_fail_rate": 1.0,
        "refine_dual_pass_rate": 0.0,
        "refine_dual_chronic_fail": True,
        "last_refine_decayed": True,
        "multi_tenant_decay": False,
        "multi_tenant_decay_tenants": 0,
        "refine_priority_decay": -25,
        "hub_priority_delta": -20,
        "demoted": True,
        "gepa_refined": True,
        "selected_n": 3,
    }
    save_ledger(ledger, ledger_path(root))
    fed_dir = root / "memory" / "federation"
    fed_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "skill-refine-dual-revive-signals.json",
        "promoted-refine-dual-revive-themes.json",
    ):
        fp = fed_dir / name
        if fp.is_file():
            try:
                fp.unlink()
            except OSError:
                pass

    for _ in range(4):
        rep = {
            "refine_dual_pass": True,
            "refine_tool_contribution_pp": 5.0,
            "refine_probe_delta": 1,
            "refined_skill_ids": [sid],
            "selected": [sid],
        }
        ingest_refine_dual(rep, root=root, save=True)
    ledger = load_ledger(ledger_path(root))
    ent = (ledger.get("skills") or {}).get(sid) or {}
    blocked_ok = bool(
        ent.get("revive_pp_blocked")
        and not ent.get("refine_dual_revived")
        and int(ent.get("hub_priority_delta") or 0) <= 0
    )

    for _ in range(4):
        rep = {
            "refine_dual_pass": True,
            "refine_tool_contribution_pp": 50.0,
            "refine_probe_delta": 1,
            "refined_skill_ids": [sid],
            "selected": [sid],
        }
        ingest_refine_dual(rep, root=root, save=True)
    ledger2 = load_ledger(ledger_path(root))
    ent2 = (ledger2.get("skills") or {}).get(sid) or {}
    revive_ok = bool(
        ent2.get("refine_dual_revived")
        and not ent2.get("revive_pp_blocked")
        and int(ent2.get("hub_priority_delta") or 0) > 0
        and float(ent2.get("last_revive_tool_pp") or 0) >= 10
    )

    th_a = _tenant_hash_fitness(root)
    th_b = "fixture-tenant-b12"
    fed_path = fed_dir / "skill-refine-dual-revive-signals.json"

    def _write_sigs(tool_pp: float) -> None:
        nl = chr(10)
        doc = {
            "schema_version": SCHEMA,
            "feature": "F177",
            "scope": "skill_refine_dual_revive",
            "privacy_ok": True,
            "signals": [
                {
                    "id": f"pp{tool_pp}-{sid}-a",
                    "theme": sid,
                    "skill_id": sid,
                    "tags": ["refine_dual_revive", "f177"],
                    "hits": 2,
                    "tenant_hash": th_a,
                    "tenant_hashes": [th_a],
                    "pass_rate": 0.8,
                    "tool_pp": tool_pp,
                    "boost": 16,
                    "dual_pass": True,
                },
                {
                    "id": f"pp{tool_pp}-{sid}-b",
                    "theme": sid,
                    "skill_id": sid,
                    "tags": ["refine_dual_revive", "f177"],
                    "hits": 2,
                    "tenant_hash": th_b,
                    "tenant_hashes": [th_b],
                    "pass_rate": 0.8,
                    "tool_pp": tool_pp,
                    "boost": 16,
                    "dual_pass": True,
                },
            ],
        }
        fed_path.write_text(json.dumps(doc, indent=2) + nl, encoding="utf-8")

    _write_sigs(3.0)
    prom_low = promote_refine_dual_revive(root=root, min_tenants=2, min_hits=2)
    low_blocked = int(prom_low.get("promoted_n") or 0) == 0

    _write_sigs(50.0)
    prom_hi = promote_refine_dual_revive(root=root, min_tenants=2, min_hits=2)
    high_ok = int(prom_hi.get("promoted_n") or 0) >= 1 and bool(prom_hi.get("privacy_ok"))

    f177_ok = bool(blocked_ok and revive_ok and low_blocked and high_ok)
    out = {
        "feature": "F177",
        "fixture_pass": f177_ok,
        "low_pp_blocked_ok": blocked_ok,
        "high_pp_revive_ok": revive_ok,
        "low_pp_promote_blocked": low_blocked,
        "high_pp_promote_ok": high_ok,
        "min_pp": refine_dual_revive_min_pp(),
        "privacy_ok": bool(prom_hi.get("privacy_ok")),
        "promoted_n_high": prom_hi.get("promoted_n"),
        "hub_priority_delta": ent2.get("hub_priority_delta"),
        "last_revive_tool_pp": ent2.get("last_revive_tool_pp"),
    }
    print(json.dumps(out, indent=2))
    return 0 if f177_ok else 1



def cmd_fixture_refine_revive_loo(args: argparse.Namespace) -> int:
    """F179 hermetic: free-rider LOO blocks revive; positive avg_contribution allows."""
    del args
    root = _root()
    sid = "skill-prefer-hub-archival-early"
    os.environ["TORII_SKILL_FITNESS_REFINE_DUAL_DECAY"] = "1"
    os.environ["TORII_SKILL_FITNESS_REFINE_DUAL_REVIVE"] = "1"
    os.environ["TORII_SKILL_FITNESS_REVIVE_PP_GATE"] = "1"
    os.environ["TORII_SKILL_FITNESS_REVIVE_LOO_GATE"] = "1"
    os.environ["TORII_REFINE_REVIVE_MIN_PP"] = "10"
    os.environ["TORII_REFINE_REVIVE_MIN_LOO"] = "0.5"
    os.environ["TORII_REFINE_REVIVE_LOO_MIN_N"] = "2"
    os.environ["TORII_SKILL_FITNESS_MIN_N"] = "3"
    os.environ["TORII_SKILL_FITNESS_REFINE_DUAL_FAIL_THR"] = "0.67"

    def _plant_decayed() -> None:
        ledger = load_ledger(ledger_path(root))
        skills = ledger.setdefault("skills", {})
        skills[sid] = {
            "id": sid,
            "refine_dual_selected_n": 3,
            "refine_dual_fail_n": 3,
            "refine_dual_pass_n": 0,
            "refine_dual_fail_rate": 1.0,
            "refine_dual_pass_rate": 0.0,
            "refine_dual_chronic_fail": True,
            "last_refine_decayed": True,
            "multi_tenant_decay": False,
            "multi_tenant_decay_tenants": 0,
            "refine_priority_decay": -25,
            "hub_priority_delta": -20,
            "demoted": True,
            "gepa_refined": True,
            "selected_n": 3,
            "refine_dual_revived": False,
            "revive_loo_blocked": False,
        }
        save_ledger(ledger, ledger_path(root))

    attr_path = root / ".torii" / "skill-attribution.json"
    attr_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) free-rider LOO — should block revive despite high tool_pp
    _plant_decayed()
    attr_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature": "F89",
                "free_riders": [sid],
                "skills": {
                    sid: {
                        "id": sid,
                        "n": 4,
                        "avg_contribution": 0.1,
                        "free_rider": True,
                        "free_rider_n": 4,
                        "contribution_sum": 0.4,
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    for _ in range(4):
        ingest_refine_dual(
            {
                "refine_dual_pass": True,
                "refine_tool_contribution_pp": 50.0,
                "refine_probe_delta": 1,
                "refined_skill_ids": [sid],
                "selected": [sid],
            },
            root=root,
            save=True,
        )
    ent_fr = (load_ledger(ledger_path(root)).get("skills") or {}).get(sid) or {}
    free_rider_blocked = bool(
        ent_fr.get("revive_loo_blocked")
        and not ent_fr.get("refine_dual_revived")
        and int(ent_fr.get("hub_priority_delta") or 0) <= 0
    )

    # 2) positive LOO — should revive
    _plant_decayed()
    attr_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature": "F89",
                "free_riders": [],
                "skills": {
                    sid: {
                        "id": sid,
                        "n": 4,
                        "avg_contribution": 3.5,
                        "free_rider": False,
                        "free_rider_n": 0,
                        "contribution_sum": 14.0,
                        "tool_hits": 3,
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    for _ in range(4):
        ingest_refine_dual(
            {
                "refine_dual_pass": True,
                "refine_tool_contribution_pp": 50.0,
                "refine_probe_delta": 1,
                "refined_skill_ids": [sid],
                "selected": [sid],
            },
            root=root,
            save=True,
        )
    ent_ok = (load_ledger(ledger_path(root)).get("skills") or {}).get(sid) or {}
    loo_revive_ok = bool(
        ent_ok.get("refine_dual_revived")
        and not ent_ok.get("revive_loo_blocked")
        and int(ent_ok.get("hub_priority_delta") or 0) > 0
        and float(ent_ok.get("last_revive_loo_avg") or 0) >= 0.5
    )

    f179_ok = bool(free_rider_blocked and loo_revive_ok)
    out = {
        "feature": "F179",
        "fixture_pass": f179_ok,
        "free_rider_blocked_ok": free_rider_blocked,
        "loo_positive_revive_ok": loo_revive_ok,
        "last_revive_loo_avg": ent_ok.get("last_revive_loo_avg"),
        "hub_priority_delta": ent_ok.get("hub_priority_delta"),
        "min_loo": refine_dual_revive_min_loo(),
    }
    print(json.dumps(out, indent=2))
    return 0 if f179_ok else 1


def cmd_ingest_hub_archival(args: argparse.Namespace) -> int:
    """F158: CLI for hub-archival util → fitness ledger demote/boost."""
    root = _root()
    util = None
    out_dir = Path(args.out_dir) if args.out_dir else None
    if args.util:
        p = Path(args.util)
        if p.is_file():
            try:
                util = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(
                    json.dumps(
                        {"feature": FEATURE_HUB_ARCHIVAL, "error": str(exc)[:120]}
                    )
                )
                return 1
    report = ingest_hub_archival_util(
        util, root=root, out_dir=out_dir, save=True
    )
    ledger = apply_demotions(load_ledger(ledger_path(root)))
    save_ledger(ledger, ledger_path(root))
    report["demoted"] = list(ledger.get("demoted") or [])
    report["hub_archival_demoted"] = list(
        (ledger.get("last_demote") or {}).get("hub_archival_demoted") or []
    )
    report["boost"] = fitness_boosts(ledger).get(HUB_ARCHIVAL_SKILL_ID)
    print(json.dumps(report, indent=2))
    return 0 if report.get("privacy_ok", True) else 1


def cmd_ingest_scorecard(args: argparse.Namespace) -> int:
    """F135: CLI for scorecard skill theme → fitness ledger."""
    root = _root()
    doc = None
    if args.file:
        p = Path(args.file)
        if p.is_file():
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(json.dumps({"feature": FEATURE_SCORECARD, "error": str(exc)[:120]}))
                return 1
    report = ingest_scorecard_skills(doc, root=root, save=True)
    # re-apply demotions so shields take effect
    ledger = apply_demotions(load_ledger(ledger_path(root)))
    save_ledger(ledger, ledger_path(root))
    report["demoted"] = list(ledger.get("demoted") or [])
    report["boosts"] = {
        k: v
        for k, v in fitness_boosts(ledger).items()
        if k in (report.get("skills") or [])
    }
    print(json.dumps(report, indent=2))
    return 0 if report.get("privacy_ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())

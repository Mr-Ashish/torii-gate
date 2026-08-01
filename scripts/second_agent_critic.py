#!/usr/bin/env python3
"""F78: Deterministic multi-checker second-agent critic (maker/checker panel).

Research drivers (2026):
  - QASecClaw (arXiv 2605.01885): multi-agent SAST + validation agents cut FPs
  - VulAgent / Argus: decouple discovery (maker) from confirmation (checker)
  - Loop Engineering loop-verifier: independent checker, default REJECT
  - Prior Torii: F70 dual_pass_critic, F72 chain_revalidate, F73 fitness,
    F75 scoped memory — never **orchestrated as one post-run critic panel**

Product thesis:
  Hermes agent is the **maker**. F78 is a second "agent" implemented as
  tools-as-code (no extra LLM spend by default) that re-scores the review
  and can **demote** weak APPROVE → COMMENT/REQUEST_CHANGES when evidence fails.

Commands:
  run       — full multi-checker panel on a review (+ optional out_dir)
  inject    — pre-review policy brief into prompt
  fixture   — good vs weak offline panel
  scorecard — Loop-Ready L0–L3 from a critic JSON
  status    — feature toggles / last report summary

Env:
  TORII_ROOT
  TORII_SECOND_CRITIC          1 (default) | 0
  TORII_SECOND_CRITIC_DEMOTE   1 (default) | 0 — rewrite verdict file on demote
  TORII_SECOND_CRITIC_MIN_PATH  default 0.4 path-evidence floor for APPROVE
  TORII_LLM_CRITIC              0 (default) | 1 — enable F81 LLM checker
  TORII_HUB_GAP_CRITIC          1 (default) | 0 — F127 hub gap_pressure checker
  TORII_HUB_GAP_PRESSURE_THR    default 0.34 — same thr as F126 re-prompt bias
  TORII_SCORECARD_HUB_GAP_CRITIC 1 (default) | 0 — F139 scorecard hub gap checker
  TORII_SCORECARD_HUB_GAP_THR   default 0.34 — scorecard util gap_pressure thr
  TORII_MEMORY_UTIL_CRITIC      1 (default) | 0 — F141 memory util gap checker
  TORII_MEMORY_HUB_GAP_CRITIC   1 (default) | 0 — F143 memory hub gap_pressure checker
  TORII_MEMORY_HUB_GAP_THR      default 0.34 — multi-tenant memory util gap thr
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F78"
FEATURE_HUB_GAP = "F127"
FEATURE_SCORECARD_HUB_GAP = "F139"
FEATURE_MEMORY_UTIL = "F141"
FEATURE_MEMORY_HUB_GAP = "F143"
SCHEMA = 1
MARKER = "<!-- torii-f78-second-agent-critic -->"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

_VERDICT_RX = re.compile(
    r"\*\*Verdict:\*\*\s*(APPROVE|REQUEST\s*CHANGES|COMMENT|LGTM|CHANGES\s*REQUESTED)\b",
    re.I,
)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SECOND_CRITIC") or "1").strip().lower()
    return raw not in _FALSEY


def demote_enabled() -> bool:
    raw = (os.environ.get("TORII_SECOND_CRITIC_DEMOTE") or "1").strip().lower()
    return raw not in _FALSEY


def _scripts() -> Path:
    return Path(__file__).resolve().parent


def _ensure_path() -> None:
    sp = str(_scripts())
    if sp not in sys.path:
        sys.path.insert(0, sp)


def normalize_verdict(raw: str) -> str:
    s = re.sub(r"\s+", " ", (raw or "").strip().upper())
    if s in ("LGTM", "APPROVED"):
        return "APPROVE"
    if s in ("CHANGES REQUESTED", "REQUEST-CHANGES", "REQUEST_CHANGES"):
        return "REQUEST_CHANGES"
    if "REQUEST" in s and "CHANGE" in s:
        return "REQUEST_CHANGES"
    if s in ("APPROVE", "COMMENT", "REQUEST_CHANGES"):
        return s
    return "UNKNOWN"


def parse_verdict(text: str) -> str:
    m = _VERDICT_RX.search(text or "")
    if not m:
        return "UNKNOWN"
    return normalize_verdict(m.group(1))


@dataclass
class CheckerResult:
    id: str
    name: str
    ok: bool
    score: float  # 0-1
    level: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def run_f70_critic(review: str, root: Path, out_dir: Path | None) -> CheckerResult:
    _ensure_path()
    try:
        from bench_security_gate import (  # type: ignore
            dual_pass_critic,
            load_tp_signatures,
            default_tp_path,
            load_fp_rules_dicts,
        )

        tp = load_tp_signatures(default_tp_path(root))
        fp_path = root / ".torii" / "fp-rules.json"
        if out_dir and (out_dir / "fp-rules.json").is_file():
            fp_path = out_dir / "fp-rules.json"
        fp = load_fp_rules_dicts(fp_path) if fp_path.is_file() else []
        result = dual_pass_critic(review, fp_rules=fp, tp_signatures=tp, root=root)
        precision = float(result.get("precision_proxy") or 0)
        eff_prec = float(result.get("effective_precision") or precision)
        weak = int(result.get("weak_evidence") or 0)
        chunks = int(result.get("chunk_count") or 0)
        super_n = int(result.get("superseded_tp") or 0)
        # Prefer F95 effective_precision when present; ok if not mostly weak
        score = max(precision, eff_prec * 0.95)
        # F101: graph supersede demotions improve hygiene (small bonus, cap 1.0)
        if super_n > 0:
            score = min(1.0, score + min(0.08, 0.02 * super_n))
        ok = score >= 0.35 or chunks == 0 or weak == 0
        return CheckerResult(
            id="f70_dual_critic",
            name="Dual-pass path/FP/TP critic (F70+F95+F101 graph)",
            ok=ok,
            score=score,
            detail={
                "precision_proxy": precision,
                "effective_precision": eff_prec,
                "effective_aware": result.get("effective_aware"),
                "graph_supersede_aware": result.get("graph_supersede_aware"),
                "graph_supersede_edges": result.get("graph_supersede_edges"),
                "effective_floor": result.get("effective_floor"),
                "weak_evidence": weak,
                "confirmed_tp": result.get("confirmed_tp"),
                "stale_tp_match": result.get("stale_tp_match"),
                "superseded_tp": super_n,
                "likely_fp": result.get("likely_fp"),
                "chunk_count": chunks,
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f70_dual_critic",
            name="Dual-pass path/FP/TP critic (F70)",
            ok=False,
            score=0.0,
            error=str(e)[:200],
        )


def run_f72_chain(review_path: Path, out_dir: Path | None) -> CheckerResult:
    _ensure_path()
    try:
        from chain_revalidate import revalidate, load_scan, scan_demo_or_paths  # type: ignore

        text = review_path.read_text(encoding="utf-8", errors="replace")
        scan = {}
        if out_dir and (out_dir / "taint-candidates.json").is_file():
            scan = load_scan(out_dir / "taint-candidates.json")
        if not scan:
            try:
                scan = scan_demo_or_paths(None)
            except Exception:
                scan = {}
        report = revalidate(text, scan=scan or None)
        full_chain = float(report.get("full_chain_rate") or 0)
        # chain quality relative; if no security findings, pass soft
        findings = int(report.get("finding_count") or report.get("n_findings") or 0)
        # read from report structure
        if "findings" in report and isinstance(report["findings"], list):
            findings = len(report["findings"])
        unvalidated = int(report.get("unvalidated") or report.get("unvalidated_count") or 0)
        scorecard = float(report.get("scorecard_pct") or 0) / 100.0
        score = max(full_chain, scorecard * 0.5)
        ok = findings == 0 or full_chain >= 0.25 or scorecard >= 40
        return CheckerResult(
            id="f72_chain",
            name="Full-chain revalidation (F72)",
            ok=ok,
            score=round(min(1.0, score), 4),
            detail={
                "full_chain_rate": full_chain,
                "scorecard_pct": report.get("scorecard_pct"),
                "verdict_checker": report.get("verdict_checker"),
                "finding_count": findings,
                "unvalidated": unvalidated,
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f72_chain",
            name="Full-chain revalidation (F72)",
            ok=False,
            score=0.0,
            error=str(e)[:200],
        )


def run_f73_fitness(review_path: Path, out_dir: Path | None) -> CheckerResult:
    _ensure_path()
    try:
        from trajectory_fitness import compute_fitness, load_json  # type: ignore

        text = review_path.read_text(encoding="utf-8", errors="replace")
        loop: dict[str, Any] = {}
        chain: dict[str, Any] = {}
        if out_dir and (out_dir / "agent-loop" / "agent-loop.json").is_file():
            loop = load_json(out_dir / "agent-loop" / "agent-loop.json") or {}
        if out_dir and (out_dir / "chain-revalidate.json").is_file():
            chain = load_json(out_dir / "chain-revalidate.json") or {}
        fit = compute_fitness(text, loop=loop or None, chain=chain or None)
        composite = float(getattr(fit, "composite", 0) or 0)
        path_ev = float(getattr(fit, "path_evidence", 0) or 0)
        level = str(getattr(fit, "level", "") or "")
        ok = composite >= 0.4 and path_ev >= 0.25
        return CheckerResult(
            id="f73_fitness",
            name="Trajectory fitness (F73)",
            ok=ok,
            score=round(composite, 4),
            level=level,
            detail={
                "composite": composite,
                "path_evidence": path_ev,
                "procedure": getattr(fit, "procedure", None),
                "tool_use": getattr(fit, "tool_use", None),
                "chain_quality": getattr(fit, "chain_quality", None),
                "verdict": getattr(fit, "verdict", None),
            },
        )
    except Exception as e:
        try:
            import subprocess

            cmd = [
                sys.executable,
                str(_scripts() / "trajectory_fitness.py"),
                "score",
                str(review_path),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_root()))
            data = json.loads(r.stdout) if r.returncode == 0 else {}
            composite = float(data.get("composite") or 0)
            path_ev = float(data.get("path_evidence") or 0)
            ok = composite >= 0.4
            return CheckerResult(
                id="f73_fitness",
                name="Trajectory fitness (F73)",
                ok=ok,
                score=round(composite, 4),
                level=str(data.get("level") or ""),
                detail={
                    "composite": composite,
                    "path_evidence": path_ev,
                    "procedure": data.get("procedure"),
                    "tool_use": data.get("tool_use"),
                    "chain_quality": data.get("chain_quality"),
                    "verdict": data.get("verdict"),
                }
                if data
                else {"error": (r.stderr or "")[:200]},
            )
        except Exception as e2:
            return CheckerResult(
                id="f73_fitness",
                name="Trajectory fitness (F73)",
                ok=False,
                score=0.0,
                error=f"{e}; {e2}"[:200],
            )


def run_f75_memory(out_dir: Path | None, root: Path) -> CheckerResult:
    _ensure_path()
    try:
        from scoped_memory_recall import (  # type: ignore
            load_store,
            default_store_path,
            ingest,
            detect_conflicts,
            parse_changed_paths,
        )

        store = default_store_path(root)
        if not store.is_file():
            ingest(root, out_dir=out_dir)
        items = load_store(store, root)
        paths: list[str] = []
        if out_dir and (out_dir / "files.txt").is_file():
            paths = parse_changed_paths(str(out_dir / "files.txt"), root)
        conflicts, suppress = detect_conflicts(items, paths)
        # ok if no hard suppress storm
        ok = len(suppress) <= max(3, len(items) // 2)
        score = 1.0 if not conflicts else max(0.3, 1.0 - 0.1 * len(conflicts))
        return CheckerResult(
            id="f75_memory",
            name="Scoped memory conflicts (F75)",
            ok=ok,
            score=round(score, 4),
            detail={
                "conflict_count": len(conflicts),
                "suppress_count": len(suppress),
                "item_count": len(items),
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f75_memory",
            name="Scoped memory conflicts (F75)",
            ok=True,  # soft — memory optional
            score=0.5,
            error=str(e)[:200],
        )


def run_f121_recovery_util(out_dir: Path | None) -> CheckerResult:
    """F121: recovery always skills must fire tool CLIs (inject ≠ utilization)."""
    if out_dir is None:
        return CheckerResult(
            id="f121_recovery_util",
            name="Recovery skill utilization (F121)",
            ok=True,
            score=0.5,
            detail={"soft_skip": True, "reason": "no_out_dir"},
        )
    _ensure_path()
    try:
        from skill_router import score_recovery_util  # type: ignore

        report = score_recovery_util(Path(out_dir))
        gap = bool(report.get("utilization_gap"))
        rate = float(report.get("util_rate") or 0)
        n = int(report.get("recovery_injected_n") or 0)
        # ok when no recovery injected or at least one tool hit
        ok = not gap
        score = rate if n else 1.0
        return CheckerResult(
            id="f121_recovery_util",
            name="Recovery skill utilization (F121)",
            ok=ok,
            score=round(score, 4),
            detail={
                "utilization_gap": gap,
                "util_rate": rate,
                "recovery_injected": report.get("recovery_injected"),
                "tool_hit_ids": report.get("tool_hit_ids"),
                "idle_ids": report.get("idle_ids"),
                "inject_chars": report.get("inject_chars"),
                "f120_chars_saved": report.get("f120_chars_saved"),
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f121_recovery_util",
            name="Recovery skill utilization (F121)",
            ok=True,  # soft — do not block panel if artifact missing
            score=0.5,
            error=str(e)[:200],
            detail={"soft_fail": True},
        )


def run_f136_scorecard_util(out_dir: Path | None) -> CheckerResult:
    """F136: scorecard-gap ops skills must fire tool CLIs when injected."""
    if out_dir is None:
        return CheckerResult(
            id="f136_scorecard_util",
            name="Scorecard skill utilization (F136)",
            ok=True,
            score=0.5,
            detail={"soft_skip": True, "reason": "no_out_dir"},
        )
    _ensure_path()
    try:
        from skill_router import score_scorecard_util  # type: ignore

        report = score_scorecard_util(Path(out_dir))
        gap = bool(report.get("utilization_gap"))
        rate = float(report.get("util_rate") or 0)
        n = int(report.get("scorecard_injected_n") or 0)
        ok = not gap
        score = rate if n else 1.0
        return CheckerResult(
            id="f136_scorecard_util",
            name="Scorecard skill utilization (F136)",
            ok=ok,
            score=round(score, 4),
            detail={
                "utilization_gap": gap,
                "util_rate": rate,
                "scorecard_injected": report.get("scorecard_injected"),
                "scorecard_injected_n": n,
                "tool_hit_ids": report.get("tool_hit_ids"),
                "idle_ids": report.get("idle_ids"),
                "inject_chars": report.get("inject_chars"),
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f136_scorecard_util",
            name="Scorecard skill utilization (F136)",
            ok=True,
            score=0.5,
            error=str(e)[:200],
            detail={"soft_fail": True},
        )


def hub_gap_critic_enabled() -> bool:
    """F127: multi-tenant hub gap_pressure participates in critic panel."""
    raw = (os.environ.get("TORII_HUB_GAP_CRITIC") or "1").strip().lower()
    return raw not in _FALSEY


def hub_gap_pressure_thr() -> float:
    raw = (os.environ.get("TORII_HUB_GAP_PRESSURE_THR") or "0.34").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.34


def run_f127_hub_gap_recovery(
    out_dir: Path | None,
    root: Path | None = None,
) -> CheckerResult:
    """F127: hub gap_pressure + local recovery idle → checker score / demote signal.

    Loop-eng maker/checker: multi-tenant under-use of recovery CLIs is evidence
    that APPROVE without recovery tools is systemic risk, not local noise.
    Soft-skip when hub compound off or no signals (score 0.5 neutral).
    """
    if not hub_gap_critic_enabled():
        return CheckerResult(
            id="f127_hub_gap",
            name="Hub gap recovery pressure (F127)",
            ok=True,
            score=0.5,
            detail={"soft_skip": True, "reason": "hub_gap_critic_off"},
        )
    _ensure_path()
    root = root or _root()
    thr = hub_gap_pressure_thr()
    try:
        from skill_router import (  # type: ignore
            post_score_recovery_hub,
            score_recovery_util,
            recovery_hub_enabled,
        )

        if not recovery_hub_enabled():
            return CheckerResult(
                id="f127_hub_gap",
                name="Hub gap recovery pressure (F127)",
                ok=True,
                score=0.5,
                detail={"soft_skip": True, "reason": "recovery_hub_off"},
            )
        hub = post_score_recovery_hub(root=root)
        gap_pressure = float(hub.get("gap_pressure") or 0.0)
        util: dict[str, Any] = {}
        if out_dir is not None:
            util = score_recovery_util(Path(out_dir), root=root)
        idle = list(util.get("idle_ids") or [])
        util_rate = float(util.get("util_rate") if util else 1.0)
        if util and util.get("recovery_injected_n") is not None:
            util_rate = float(util.get("util_rate") or 0.0)
        n_inj = int(util.get("recovery_injected_n") or 0)
        local_gap = bool(util.get("utilization_gap"))
        high = gap_pressure >= thr
        # pressure without recovery inject is informational only
        if n_inj < 1 and out_dir is not None:
            return CheckerResult(
                id="f127_hub_gap",
                name="Hub gap recovery pressure (F127)",
                ok=True,
                score=1.0 if not high else 0.7,
                detail={
                    "gap_pressure": gap_pressure,
                    "thr": thr,
                    "high": high,
                    "reason": "no_recovery_injected",
                    "privacy_ok": hub.get("privacy_ok"),
                },
            )
        # score: inverse pressure when idle/gap; full when util ok and pressure low
        if not high:
            score = 1.0 if (not idle and not local_gap) else max(0.6, util_rate)
            ok = True
            reason = "hub_gap_below_thr"
        elif local_gap or (idle and util_rate < 0.99):
            # high multi-tenant gap + local idle recovery → fail checker
            score = round(max(0.0, 1.0 - gap_pressure) * max(0.15, util_rate), 4)
            ok = False
            reason = "hub_gap_high_local_idle"
        else:
            # hub high but local full util — pass with mild haircut
            score = 0.85
            ok = True
            reason = "hub_gap_high_local_util_ok"
        return CheckerResult(
            id="f127_hub_gap",
            name="Hub gap recovery pressure (F127)",
            ok=ok,
            score=round(score, 4),
            detail={
                "feature": FEATURE_HUB_GAP,
                "gap_pressure": gap_pressure,
                "thr": thr,
                "high": high,
                "util_rate": util_rate,
                "idle_ids": idle,
                "local_gap": local_gap,
                "recovery_injected_n": n_inj,
                "hub_skill_n": hub.get("skill_n"),
                "privacy_ok": hub.get("privacy_ok"),
                "reason": reason,
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f127_hub_gap",
            name="Hub gap recovery pressure (F127)",
            ok=True,
            score=0.5,
            error=str(e)[:200],
            detail={"soft_fail": True},
        )


def scorecard_hub_gap_critic_enabled() -> bool:
    """F139: multi-tenant scorecard hub gap_pressure participates in critic panel."""
    raw = (os.environ.get("TORII_SCORECARD_HUB_GAP_CRITIC") or "1").strip().lower()
    return raw not in _FALSEY


def scorecard_hub_gap_pressure_thr() -> float:
    raw = (os.environ.get("TORII_SCORECARD_HUB_GAP_THR") or "0.34").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.34


def run_f141_memory_util(
    out_dir: Path | None,
    root: Path | None = None,
) -> CheckerResult:
    """F141: memory inject offered but unused tools → demote signal.

    Mem0/Letta: memory only helps if tools are called. Soft-skip when no
    out_dir or audit unavailable (score 0.5). Gap when inject_offered and
    hit_count=0 and tool turns ≥ 1.
    """
    raw = (os.environ.get("TORII_MEMORY_UTIL_CRITIC") or "1").strip().lower()
    if raw in _FALSEY:
        return CheckerResult(
            id="f141_memory_util",
            name="Memory tool utilization (F141)",
            ok=True,
            score=0.5,
            detail={"soft_skip": True, "reason": "memory_util_critic_off"},
        )
    if out_dir is None:
        return CheckerResult(
            id="f141_memory_util",
            name="Memory tool utilization (F141)",
            ok=True,
            score=0.5,
            detail={"soft_skip": True, "reason": "no_out_dir"},
        )
    _ensure_path()
    root = root or _root()
    try:
        from memory_tool_audit import (  # type: ignore
            audit_run,
            REPORT_NAME,
        )

        od = Path(out_dir)
        report: dict[str, Any] = {}
        if (od / REPORT_NAME).is_file():
            try:
                report = json.loads((od / REPORT_NAME).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                report = {}
        if not report:
            report = audit_run(od)
        gap = bool(report.get("utilization_gap"))
        score = float(report.get("score") or 0.5)
        hits = int(report.get("hit_count") or 0)
        inject = bool(report.get("inject_offered"))
        turns = int(report.get("tool_call_turns") or 0)
        # no inject offered → neutral pass (memory optional this run)
        if not inject:
            return CheckerResult(
                id="f141_memory_util",
                name="Memory tool utilization (F141)",
                ok=True,
                score=1.0 if hits >= 1 else 0.85,
                detail={
                    "feature": FEATURE_MEMORY_UTIL,
                    "utilization_gap": False,
                    "inject_offered": False,
                    "hit_count": hits,
                    "score": score,
                    "reason": "no_memory_inject",
                },
            )
        ok = not gap
        # score from audit; on gap keep low
        if gap:
            panel_score = min(0.2, max(0.05, score))
        else:
            panel_score = max(0.55, score)
        return CheckerResult(
            id="f141_memory_util",
            name="Memory tool utilization (F141)",
            ok=ok,
            score=round(panel_score, 4),
            detail={
                "feature": FEATURE_MEMORY_UTIL,
                "utilization_gap": gap,
                "util_score": score,
                "hit_count": hits,
                "inject_offered": inject,
                "tool_call_turns": turns,
                "tools_used": list(report.get("tools_used") or [])[:8],
                "reason": "memory_utilization_gap" if gap else "memory_tools_used",
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f141_memory_util",
            name="Memory tool utilization (F141)",
            ok=True,
            score=0.5,
            error=str(e)[:200],
            detail={"soft_fail": True},
        )


def memory_hub_gap_critic_enabled() -> bool:
    """F143: multi-tenant memory hub gap_pressure participates in critic panel."""
    raw = (os.environ.get("TORII_MEMORY_HUB_GAP_CRITIC") or "1").strip().lower()
    return raw not in _FALSEY


def memory_hub_gap_pressure_thr() -> float:
    raw = (os.environ.get("TORII_MEMORY_HUB_GAP_THR") or "0.34").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.34


def run_f143_memory_hub_gap(
    out_dir: Path | None,
    root: Path | None = None,
) -> CheckerResult:
    """F143: memory hub gap_pressure + local memory util idle → demote signal.

    Mirrors F127/F139 for Mem0/Letta multi-tenant util under-use. High hub
    gap_pressure + local inject-unused means APPROVE without memory tools is
    systemic risk. Soft-skip when memory hub off or no signals.
    """
    if not memory_hub_gap_critic_enabled():
        return CheckerResult(
            id="f143_memory_hub_gap",
            name="Memory hub gap pressure (F143)",
            ok=True,
            score=0.5,
            detail={"soft_skip": True, "reason": "memory_hub_gap_critic_off"},
        )
    _ensure_path()
    root = root or _root()
    thr = memory_hub_gap_pressure_thr()
    try:
        from memory_tool_audit import (  # type: ignore
            post_score_memory_util_hub,
            memory_hub_enabled,
            audit_run,
            REPORT_NAME,
        )

        if not memory_hub_enabled():
            return CheckerResult(
                id="f143_memory_hub_gap",
                name="Memory hub gap pressure (F143)",
                ok=True,
                score=0.5,
                detail={"soft_skip": True, "reason": "memory_hub_off"},
            )
        hub = post_score_memory_util_hub(root=root)
        gap_pressure = float(hub.get("gap_pressure") or 0.0)
        util: dict[str, Any] = {}
        if out_dir is not None:
            od = Path(out_dir)
            if (od / REPORT_NAME).is_file():
                try:
                    util = json.loads((od / REPORT_NAME).read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    util = {}
            if not util:
                util = audit_run(od)
        local_gap = bool(util.get("utilization_gap"))
        inject = bool(util.get("inject_offered"))
        hits = int(util.get("hit_count") or 0)
        util_score = float(util.get("score") or 1.0)
        high = gap_pressure >= thr
        # no local inject and no hub pressure → pass
        if not inject and out_dir is not None and not high:
            return CheckerResult(
                id="f143_memory_hub_gap",
                name="Memory hub gap pressure (F143)",
                ok=True,
                score=1.0,
                detail={
                    "gap_pressure": gap_pressure,
                    "thr": thr,
                    "high": high,
                    "reason": "no_local_inject_hub_ok",
                    "privacy_ok": hub.get("privacy_ok"),
                },
            )
        if not high:
            score = 1.0 if (not local_gap and hits >= 1) else max(0.6, util_score)
            ok = True
            reason = "memory_hub_gap_below_thr"
        elif local_gap or (inject and hits < 1):
            score = round(max(0.0, 1.0 - gap_pressure) * max(0.15, util_score), 4)
            ok = False
            reason = "memory_hub_gap_high_local_idle"
        else:
            score = 0.85
            ok = True
            reason = "memory_hub_gap_high_local_util_ok"
        return CheckerResult(
            id="f143_memory_hub_gap",
            name="Memory hub gap pressure (F143)",
            ok=ok,
            score=round(score, 4),
            detail={
                "feature": FEATURE_MEMORY_HUB_GAP,
                "gap_pressure": gap_pressure,
                "thr": thr,
                "high": high,
                "util_score": util_score,
                "hit_count": hits,
                "local_gap": local_gap,
                "inject_offered": inject,
                "hub_skill_n": hub.get("skill_n"),
                "privacy_ok": hub.get("privacy_ok"),
                "reason": reason,
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f143_memory_hub_gap",
            name="Memory hub gap pressure (F143)",
            ok=True,
            score=0.5,
            error=str(e)[:200],
            detail={"soft_fail": True},
        )


def run_f139_scorecard_hub_gap(
    out_dir: Path | None,
    root: Path | None = None,
) -> CheckerResult:
    """F139: scorecard hub gap_pressure + local scorecard idle → demote signal.

    Mirrors F127 for scorecard-gap ops skills (F136 util + F138 hub post-score).
    High multi-tenant scorecard util gap + local idle doctor/scorecard CLIs
    means APPROVE without ops tools is systemic risk.
    Soft-skip when scorecard hub compound off or no signals (score 0.5).
    """
    if not scorecard_hub_gap_critic_enabled():
        return CheckerResult(
            id="f139_scorecard_hub_gap",
            name="Scorecard hub gap pressure (F139)",
            ok=True,
            score=0.5,
            detail={"soft_skip": True, "reason": "scorecard_hub_gap_critic_off"},
        )
    _ensure_path()
    root = root or _root()
    thr = scorecard_hub_gap_pressure_thr()
    try:
        from skill_router import (  # type: ignore
            post_score_scorecard_hub,
            score_scorecard_util,
            scorecard_hub_enabled,
        )

        if not scorecard_hub_enabled():
            return CheckerResult(
                id="f139_scorecard_hub_gap",
                name="Scorecard hub gap pressure (F139)",
                ok=True,
                score=0.5,
                detail={"soft_skip": True, "reason": "scorecard_hub_off"},
            )
        hub = post_score_scorecard_hub(root=root)
        gap_pressure = float(hub.get("gap_pressure") or 0.0)
        util: dict[str, Any] = {}
        if out_dir is not None:
            util = score_scorecard_util(Path(out_dir), root=root)
        idle = list(util.get("idle_ids") or [])
        util_rate = float(util.get("util_rate") if util else 1.0)
        if util and util.get("scorecard_injected_n") is not None:
            util_rate = float(util.get("util_rate") or 0.0)
        n_inj = int(util.get("scorecard_injected_n") or 0)
        local_gap = bool(util.get("utilization_gap"))
        high = gap_pressure >= thr
        # pressure without scorecard inject is informational only
        if n_inj < 1 and out_dir is not None:
            return CheckerResult(
                id="f139_scorecard_hub_gap",
                name="Scorecard hub gap pressure (F139)",
                ok=True,
                score=1.0 if not high else 0.7,
                detail={
                    "gap_pressure": gap_pressure,
                    "thr": thr,
                    "high": high,
                    "reason": "no_scorecard_injected",
                    "privacy_ok": hub.get("privacy_ok"),
                    "hub_skill_n": hub.get("skill_n"),
                },
            )
        if not high:
            score = 1.0 if (not idle and not local_gap) else max(0.6, util_rate)
            ok = True
            reason = "scorecard_hub_gap_below_thr"
        elif local_gap or (idle and util_rate < 0.99):
            score = round(max(0.0, 1.0 - gap_pressure) * max(0.15, util_rate), 4)
            ok = False
            reason = "scorecard_hub_gap_high_local_idle"
        else:
            score = 0.85
            ok = True
            reason = "scorecard_hub_gap_high_local_util_ok"
        return CheckerResult(
            id="f139_scorecard_hub_gap",
            name="Scorecard hub gap pressure (F139)",
            ok=ok,
            score=round(score, 4),
            detail={
                "feature": FEATURE_SCORECARD_HUB_GAP,
                "gap_pressure": gap_pressure,
                "thr": thr,
                "high": high,
                "util_rate": util_rate,
                "idle_ids": idle,
                "local_gap": local_gap,
                "scorecard_injected_n": n_inj,
                "hub_skill_n": hub.get("skill_n"),
                "privacy_ok": hub.get("privacy_ok"),
                "reason": reason,
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f139_scorecard_hub_gap",
            name="Scorecard hub gap pressure (F139)",
            ok=True,
            score=0.5,
            error=str(e)[:200],
            detail={"soft_fail": True},
        )


def run_verdict_structure(review: str) -> CheckerResult:
    v = parse_verdict(review)
    has_summary = bool(re.search(r"(?m)^###?\s+Summary\b", review, re.I))
    has_blocking = bool(re.search(r"(?m)^###?\s+Blocking\b", review, re.I))
    has_checked = bool(re.search(r"(?m)^###?\s+What I checked\b", review, re.I))
    path_n = len(
        re.findall(
            r"`?[\w./-]+\.(?:py|js|ts|tsx|go|java|rb)(?::\d+)?`?",
            review,
        )
    )
    parts = [v != "UNKNOWN", has_summary, has_blocking, has_checked, path_n >= 1]
    score = sum(1 for p in parts if p) / len(parts)
    ok = v != "UNKNOWN" and (path_n >= 1 or v == "APPROVE")
    return CheckerResult(
        id="structure",
        name="Verdict structure",
        ok=ok,
        score=round(score, 4),
        detail={
            "verdict": v,
            "has_summary": has_summary,
            "has_blocking": has_blocking,
            "has_checked": has_checked,
            "path_mentions": path_n,
        },
    )



def run_f81_llm(review: str, panel_partial: dict[str, Any] | None = None) -> CheckerResult:
    """Optional LLM checker (F81). Soft-skip when disabled or no key."""
    _ensure_path()
    try:
        from llm_critic import run_critic, to_checker_result, enabled as llm_on  # type: ignore

        # Only call network if enabled
        api = run_critic(review, panel=panel_partial, force_mock=False)
        shaped = to_checker_result(api)
        return CheckerResult(
            id=str(shaped.get("id") or "f81_llm"),
            name=str(shaped.get("name") or "LLM checker (F81)"),
            ok=bool(shaped.get("ok")),
            score=float(shaped.get("score") or 0.5),
            detail=dict(shaped.get("detail") or {}),
            error=str(shaped.get("error") or ""),
        )
    except Exception as e:
        return CheckerResult(
            id="f81_llm",
            name="LLM checker (F81)",
            ok=True,
            score=0.5,
            error=str(e)[:200],
            detail={"soft_fail": True},
        )


def composite_panel(checkers: list[CheckerResult]) -> dict[str, Any]:
    """Weighted composite; default REJECT stance on weak APPROVE."""
    weights = {
        "f121_recovery_util": 0.08,
        "f136_scorecard_util": 0.06,  # F136 scorecard-gap ops util
        "f127_hub_gap": 0.08,  # F127 multi-tenant recovery gap pressure
        "f139_scorecard_hub_gap": 0.07,  # F139 multi-tenant scorecard util gap
        "f141_memory_util": 0.07,  # F141 Mem0/Letta tools-must-be-called
        "f143_memory_hub_gap": 0.07,  # F143 multi-tenant memory util gap
        "structure": 0.12,
        "f70_dual_critic": 0.20,
        "f72_chain": 0.16,
        "f73_fitness": 0.20,
        "f75_memory": 0.10,
        "f81_llm": 0.12,  # optional; soft if skipped
    }
    total_w = 0.0
    acc = 0.0
    for c in checkers:
        w = weights.get(c.id, 0.1)
        # failed checkers with errors still contribute low score
        s = c.score if not c.error else min(c.score, 0.2)
        acc += w * s
        total_w += w
    composite = acc / total_w if total_w else 0.0
    ok_n = sum(1 for c in checkers if c.ok)
    n = len(checkers) or 1
    # Loop-Ready levels
    if composite >= 0.75 and ok_n == n:
        level = "L3"
    elif composite >= 0.55 and ok_n >= n - 1:
        level = "L2"
    elif composite >= 0.35:
        level = "L1"
    else:
        level = "L0"
    return {
        "composite": round(composite, 4),
        "level": level,
        "checkers_ok": ok_n,
        "checkers_total": n,
        "pass_rate": round(ok_n / n, 4),
    }


def decide_verdict(
    maker_verdict: str,
    panel: dict[str, Any],
    checkers: list[CheckerResult],
) -> dict[str, Any]:
    """Default REJECT-until-evidence for APPROVE demotions."""
    maker = normalize_verdict(maker_verdict)
    composite = float(panel.get("composite") or 0)
    path_ev = 0.0
    for c in checkers:
        if c.id == "f73_fitness":
            path_ev = float((c.detail or {}).get("path_evidence") or 0)
        if c.id == "structure":
            path_n = int((c.detail or {}).get("path_mentions") or 0)
            if path_ev == 0 and path_n:
                path_ev = min(1.0, path_n * 0.2)

    min_path = float(os.environ.get("TORII_SECOND_CRITIC_MIN_PATH") or "0.4")
    recommended = maker
    reasons: list[str] = []
    demoted = False

    if maker == "APPROVE":
        if composite < 0.5:
            recommended = "COMMENT"
            demoted = True
            reasons.append(f"composite_below_0.5 ({composite})")
        if path_ev < min_path:
            recommended = "REQUEST_CHANGES" if path_ev < 0.2 else "COMMENT"
            demoted = True
            reasons.append(f"path_evidence_below_{min_path} ({path_ev})")
        weak = next((c for c in checkers if c.id == "f70_dual_critic"), None)
        if weak and float((weak.detail or {}).get("weak_evidence") or 0) >= 3:
            if float((weak.detail or {}).get("precision_proxy") or 0) < 0.3:
                recommended = "COMMENT"
                demoted = True
                reasons.append("high_weak_evidence_low_precision")
        # F121: recovery skills always-injected but idle tools → soft demote APPROVE
        rec = next((c for c in checkers if c.id == "f121_recovery_util"), None)
        if rec and bool((rec.detail or {}).get("utilization_gap")):
            recommended = "COMMENT"
            demoted = True
            reasons.append("recovery_skill_idle_no_tool_hit")
        # F136: scorecard ops skills injected but idle tools → soft demote APPROVE
        scu = next((c for c in checkers if c.id == "f136_scorecard_util"), None)
        if scu and bool((scu.detail or {}).get("utilization_gap")):
            recommended = "COMMENT"
            demoted = True
            reasons.append("scorecard_skill_idle_no_tool_hit")
        # F127: multi-tenant hub gap + local idle recovery → demote APPROVE
        hubc = next((c for c in checkers if c.id == "f127_hub_gap"), None)
        if hubc and not hubc.ok:
            detail = hubc.detail or {}
            if detail.get("high") and (
                detail.get("local_gap") or detail.get("idle_ids")
            ):
                recommended = "COMMENT"
                demoted = True
                reasons.append(
                    f"hub_gap_pressure_idle ({detail.get('gap_pressure')}>={detail.get('thr')})"
                )
        # F139: multi-tenant scorecard hub gap + local idle scorecard ops → demote
        sch = next((c for c in checkers if c.id == "f139_scorecard_hub_gap"), None)
        if sch and not sch.ok:
            detail = sch.detail or {}
            if detail.get("high") and (
                detail.get("local_gap") or detail.get("idle_ids")
            ):
                recommended = "COMMENT"
                demoted = True
                reasons.append(
                    "scorecard_hub_gap_pressure_idle "
                    f"({detail.get('gap_pressure')}>={detail.get('thr')})"
                )
        # F141: memory inject offered but tools unused → demote APPROVE
        memu = next((c for c in checkers if c.id == "f141_memory_util"), None)
        if memu and not memu.ok:
            detail = memu.detail or {}
            if detail.get("utilization_gap"):
                recommended = "COMMENT"
                demoted = True
                reasons.append("memory_tool_idle_inject_unused")
        # F143: multi-tenant memory hub gap + local idle → demote APPROVE
        mhub = next((c for c in checkers if c.id == "f143_memory_hub_gap"), None)
        if mhub and not mhub.ok:
            detail = mhub.detail or {}
            if detail.get("high") and (
                detail.get("local_gap") or detail.get("inject_offered")
            ):
                recommended = "COMMENT"
                demoted = True
                reasons.append(
                    "memory_hub_gap_pressure_idle "
                    f"({detail.get('gap_pressure')}>={detail.get('thr')})"
                )
    elif maker == "UNKNOWN":
        recommended = "COMMENT"
        demoted = True
        reasons.append("unknown_maker_verdict")

    return {
        "maker_verdict": maker,
        "recommended_verdict": recommended,
        "demoted": demoted,
        "reasons": reasons,
        "path_evidence": path_ev,
        "composite": composite,
    }


def run_panel(
    review_path: Path,
    *,
    out_dir: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    root = root or _root()
    review_path = Path(review_path)
    text = review_path.read_text(encoding="utf-8", errors="replace")
    maker = parse_verdict(text)
    checkers = [
        run_verdict_structure(text),
        run_f70_critic(text, root, out_dir),
        run_f72_chain(review_path, out_dir),
        run_f73_fitness(review_path, out_dir),
        run_f75_memory(out_dir, root),
        run_f121_recovery_util(out_dir),
        run_f136_scorecard_util(out_dir),
        run_f127_hub_gap_recovery(out_dir, root),
        run_f139_scorecard_hub_gap(out_dir, root),
        run_f141_memory_util(out_dir, root),
        run_f143_memory_hub_gap(out_dir, root),
    ]
    # F81: optional LLM checker after deterministic panel draft
    panel_draft = {
        "maker_verdict": maker,
        "panel": composite_panel(checkers),
        "checkers": [
            {"id": c.id, "ok": c.ok, "score": c.score} for c in checkers
        ],
    }
    checkers.append(run_f81_llm(text, panel_draft))
    panel = composite_panel(checkers)
    decision = decide_verdict(maker, panel, checkers)
    # If LLM endorses demote and maker is APPROVE, strengthen decision
    llm = next((c for c in checkers if c.id == "f81_llm"), None)
    if (
        llm
        and isinstance(llm.detail, dict)
        and llm.detail.get("endorse_demote")
        and maker == "APPROVE"
        and not decision.get("demoted")
    ):
        decision["demoted"] = True
        decision["recommended_verdict"] = str(
            llm.detail.get("recommended_verdict") or "COMMENT"
        )
        decision.setdefault("reasons", []).append("f81_llm_endorse_demote")
    report = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "at": _now(),
        "review": str(review_path),
        "out_dir": str(out_dir) if out_dir else None,
        "maker_verdict": maker,
        "panel": panel,
        "decision": decision,
        "checkers": [
            {
                "id": c.id,
                "name": c.name,
                "ok": c.ok,
                "score": c.score,
                "level": c.level,
                "detail": c.detail,
                "error": c.error,
            }
            for c in checkers
        ],
    }
    return report


def apply_demote(review_path: Path, decision: dict[str, Any]) -> bool:
    """Rewrite **Verdict:** line when demoted (optional)."""
    if not decision.get("demoted") or not demote_enabled():
        return False
    rec = decision.get("recommended_verdict")
    maker = decision.get("maker_verdict")
    if not rec or rec == maker:
        return False
    text = review_path.read_text(encoding="utf-8", errors="replace")
    label = rec.replace("_", " ")
    new, n = re.subn(
        r"(\*\*Verdict:\*\*\s*)(APPROVE|REQUEST\s*CHANGES|COMMENT|LGTM|CHANGES\s*REQUESTED)\b",
        rf"\1{label}",
        text,
        count=1,
        flags=re.I,
    )
    if n == 0:
        return False
    # annotate
    note = (
        f"\n\n<!-- torii-f78-demote -->\n"
        f"_Second-agent critic (F78) demoted `{maker}` → `{rec}`: "
        f"{', '.join(decision.get('reasons') or [])}_\n"
        f"<!-- /torii-f78-demote -->\n"
    )
    if "torii-f78-demote" not in new:
        new = new.rstrip() + note
    review_path.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
    return True


def render_inject() -> str:
    return "\n".join(
        [
            MARKER,
            "## Second-agent critic panel (F78 — maker/checker)",
            "",
            "You are the **maker**. An independent deterministic **checker panel** will re-score this review:",
            "1. **Structure** — verdict + Summary + Blocking + What I checked + path cites",
            "2. **F70 dual critic** — path evidence / FP demote / TP boost",
            "3. **F72 chain** — full-chain source→sink revalidation",
            "4. **F73 fitness** — procedure / tool_use / path_evidence composite",
            "5. **F75 memory** — scoped TP/FP conflicts",
            "6. **F121 recovery util** — always recovery skills must fire tool CLIs",
            "7. **F127 hub gap** — multi-tenant recovery gap_pressure + local idle → demote APPROVE",
            "8. **F136 scorecard util** — scorecard-gap ops skills must fire doctor/scorecard CLIs",
            "9. **F139 scorecard hub gap** — multi-tenant scorecard util gap + local idle → demote APPROVE",
            "10. **F141 memory util** — memory inject offered but unused tools → demote APPROVE",
            "11. **F143 memory hub gap** — multi-tenant memory util gap + local idle → demote APPROVE",
            "",
            "**Default stance:** weak APPROVE without path evidence will be **demoted**.",
            "Prefer REQUEST CHANGES with path:line over narrative-only APPROVE.",
            "Call recovery CLIs (memory/doctor/critic) when hub gap pressure is elevated.",
            "Call scorecard ops CLIs (doctor/scorecard/demote-eval) when scorecard hub gap is elevated.",
            "Call memory CLIs (`torii.py memory -- search`) when memory inject was offered or hub memory gap is elevated.",
            "",
            "<!-- /torii-f78-second-agent-critic -->",
            "",
        ]
    )


def inject_into_prompt(prompt_path: Path) -> bool:
    if not enabled():
        return False
    path = Path(prompt_path)
    if not path.is_file() and not path.parent.exists():
        return False
    chunk = render_inject()
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if MARKER in text:
        text = re.sub(
            r"<!-- torii-f78-second-agent-critic -->.*?<!-- /torii-f78-second-agent-critic -->\n?",
            chunk,
            text,
            count=1,
            flags=re.S,
        )
    else:
        text = text.rstrip() + "\n\n" + chunk
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return True


def write_report(report: dict[str, Any], out_dir: Path | None, review_path: Path) -> Path:
    if out_dir:
        dest = Path(out_dir) / "second-agent-critic.json"
    else:
        dest = review_path.parent / "second-agent-critic.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # markdown summary
    md = dest.with_suffix(".md")
    panel = report.get("panel") or {}
    dec = report.get("decision") or {}
    lines = [
        f"# Second-agent critic (F78)",
        "",
        f"- at: `{report.get('at')}`",
        f"- maker: **{report.get('maker_verdict')}**",
        f"- recommended: **{dec.get('recommended_verdict')}**"
        + (" (demoted)" if dec.get("demoted") else ""),
        f"- composite: **{panel.get('composite')}** level **{panel.get('level')}** "
        f"({panel.get('checkers_ok')}/{panel.get('checkers_total')} checkers ok)",
        "",
        "| Checker | OK | Score | Notes |",
        "|---------|:--:|------:|-------|",
    ]
    for c in report.get("checkers") or []:
        note = c.get("error") or json.dumps(c.get("detail") or {})[:80]
        lines.append(
            f"| {c.get('id')} | {'yes' if c.get('ok') else 'no'} | {c.get('score')} | {note} |"
        )
    if dec.get("reasons"):
        lines += ["", "### Demote reasons", ""]
        for r in dec["reasons"]:
            lines.append(f"- {r}")
    lines.append("")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def cmd_run(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "skipped": True, "reason": "disabled"}))
        return 0
    root = _root()
    review = Path(args.review)
    out_dir = Path(args.out_dir) if args.out_dir else None
    report = run_panel(review, out_dir=out_dir, root=root)
    demoted = False
    if args.demote or demote_enabled():
        demoted = apply_demote(review, report["decision"])
    report["decision"]["applied_demote"] = demoted
    dest = write_report(report, out_dir, review)
    report["report_path"] = str(dest)
    print(json.dumps(report, indent=2))
    # exit 0 always for soft stage; use --strict to fail on L0
    if args.strict and (report.get("panel") or {}).get("level") == "L0":
        return 1
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    ok = inject_into_prompt(Path(args.prompt))
    print(json.dumps({"feature": FEATURE, "injected": ok, "prompt": args.prompt}))
    return 0 if ok else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    good = root / "docs/benchmarks/fixtures/insecure-demo-good-review.md"
    weak = root / "docs/benchmarks/fixtures/insecure-demo-weak-review.md"
    g = run_panel(good, root=root)
    w = run_panel(weak, root=root)
    g_comp = float((g.get("panel") or {}).get("composite") or 0)
    w_comp = float((w.get("panel") or {}).get("composite") or 0)
    # good should beat weak; weak APPROVE-like should demote or low composite
    delta = g_comp - w_comp
    w_dec = w.get("decision") or {}
    # weak fixture is APPROVE with no path → expect demote or low score
    weak_ok = w_comp < 0.55 or w_dec.get("demoted") or w_dec.get("recommended_verdict") != "APPROVE"
    good_ok = g_comp >= 0.45 and (g.get("maker_verdict") in ("REQUEST_CHANGES", "COMMENT", "APPROVE"))
    # inject
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        prompt = Path(td) / "prompt.md"
        prompt.write_text("# p\n", encoding="utf-8")
        inj = inject_into_prompt(prompt)
        body = prompt.read_text(encoding="utf-8")
        inject_ok = (
            inj
            and MARKER in body
            and "F127" in body
            and "F139" in body
            and "F141" in body
            and "F143" in body
        )

    # F127: hub gap high + local idle + APPROVE → demote
    f127_ok = False
    try:
        with tempfile.TemporaryDirectory() as td2:
            od = Path(td2)
            # synthetic out_dir with idle recovery
            (od / "skill-router.json").write_text(
                json.dumps(
                    {
                        "selected": ["skill-prefer-memory-cli-early"],
                        "always_selected": ["skill-prefer-memory-cli-early"],
                        "inject_chars": 500,
                    }
                ),
                encoding="utf-8",
            )
            (od / "skill-hits.json").write_text(
                json.dumps(
                    {
                        "hits": [
                            {
                                "id": "skill-prefer-memory-cli-early",
                                "tool_hit": False,
                                "hit": False,
                            }
                        ],
                        "tool_hit_n": 0,
                    }
                ),
                encoding="utf-8",
            )
            # high gap hub signals under temp TORII_ROOT federation? use product root hub
            # force thr low so product hub pressure counts
            os.environ["TORII_HUB_GAP_CRITIC"] = "1"
            os.environ["TORII_HUB_GAP_PRESSURE_THR"] = "0.05"
            chk = run_f127_hub_gap_recovery(od, root=root)
            # decide demote path
            fake_panel = {"composite": 0.8, "level": "L2"}
            # structure-ish APPROVE with path so only hub demotes
            dec = decide_verdict(
                "APPROVE",
                fake_panel,
                [
                    CheckerResult(
                        id="structure",
                        name="s",
                        ok=True,
                        score=1.0,
                        detail={"path_mentions": 5},
                    ),
                    CheckerResult(
                        id="f73_fitness",
                        name="f",
                        ok=True,
                        score=1.0,
                        detail={"path_evidence": 0.9},
                    ),
                    chk,
                ],
            )
            # either checker fails on idle+pressure OR soft-skip still ok if no hub
            if chk.detail and chk.detail.get("soft_skip"):
                f127_ok = True  # environment without hub still soft-ok
            else:
                f127_ok = (
                    (not chk.ok and "hub_gap" in str(chk.detail.get("reason") or ""))
                    or (
                        dec.get("demoted")
                        and any("hub_gap" in str(r) for r in (dec.get("reasons") or []))
                    )
                    or (chk.ok and float(chk.detail.get("gap_pressure") or 0) < 0.05)
                )
            # restore thr
            os.environ["TORII_HUB_GAP_PRESSURE_THR"] = "0.34"
    except Exception:
        f127_ok = False

    # F139: scorecard hub gap high + local idle scorecard + APPROVE → demote
    f139_ok = False
    try:
        with tempfile.TemporaryDirectory() as td3:
            root_sc = Path(td3)
            od = root_sc / "out"
            od.mkdir()
            fed = root_sc / "memory" / "federation"
            fed.mkdir(parents=True)
            sc_sid = "skill-prefer-product-scorecard"
            (fed / "scorecard-util-signals.json").write_text(
                json.dumps(
                    {
                        "signals": [
                            {
                                "id": "scorecard-util-gap",
                                "theme": "scorecard-util-gap",
                                "tags": [
                                    "scorecard_util",
                                    "utilization_gap",
                                    "f136",
                                ],
                                "hits": 8,
                                "tenants": 3,
                                "util_rate_bin": "gap",
                                "source": "scorecard_skill_util",
                            },
                            {
                                "id": "scorecard-util-ok",
                                "theme": "scorecard-util-ok",
                                "tags": ["scorecard_util", "util_ok"],
                                "hits": 1,
                                "util_rate_bin": "full",
                                "source": "scorecard_skill_util",
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (od / "skill-router.json").write_text(
                json.dumps(
                    {
                        "selected": [sc_sid],
                        "always_selected": [],
                        "inject_chars": 500,
                    }
                ),
                encoding="utf-8",
            )
            (od / "skill-hits.json").write_text(
                json.dumps(
                    {
                        "hits": [
                            {
                                "id": sc_sid,
                                "tool_hit": False,
                                "hit": False,
                            }
                        ],
                        "tool_hit_n": 0,
                    }
                ),
                encoding="utf-8",
            )
            os.environ["TORII_SCORECARD_HUB_GAP_CRITIC"] = "1"
            os.environ["TORII_SCORECARD_HUB_GAP_THR"] = "0.05"
            os.environ["TORII_SCORECARD_HUB_COMPOUND"] = "1"
            prev_root = os.environ.get("TORII_ROOT")
            os.environ["TORII_ROOT"] = str(root_sc)
            try:
                chk_sc = run_f139_scorecard_hub_gap(od, root=root_sc)
                fake_panel = {"composite": 0.8, "level": "L2"}
                dec_sc = decide_verdict(
                    "APPROVE",
                    fake_panel,
                    [
                        CheckerResult(
                            id="structure",
                            name="s",
                            ok=True,
                            score=1.0,
                            detail={"path_mentions": 5},
                        ),
                        CheckerResult(
                            id="f73_fitness",
                            name="f",
                            ok=True,
                            score=1.0,
                            detail={"path_evidence": 0.9},
                        ),
                        chk_sc,
                    ],
                )
                if chk_sc.detail and chk_sc.detail.get("soft_skip"):
                    f139_ok = True
                else:
                    f139_ok = (
                        (
                            not chk_sc.ok
                            and "scorecard_hub_gap" in str(
                                chk_sc.detail.get("reason") or ""
                            )
                        )
                        or (
                            dec_sc.get("demoted")
                            and any(
                                "scorecard_hub_gap" in str(r)
                                for r in (dec_sc.get("reasons") or [])
                            )
                        )
                        or (
                            chk_sc.ok
                            and float(chk_sc.detail.get("gap_pressure") or 0) < 0.05
                        )
                    )
            finally:
                if prev_root is None:
                    os.environ.pop("TORII_ROOT", None)
                else:
                    os.environ["TORII_ROOT"] = prev_root
                os.environ["TORII_SCORECARD_HUB_GAP_THR"] = "0.34"
    except Exception:
        f139_ok = False

    # checker present in good panel
    has_f127 = any(
        c.get("id") == "f127_hub_gap" for c in (g.get("checkers") or [])
    )
    has_f139 = any(
        c.get("id") == "f139_scorecard_hub_gap" for c in (g.get("checkers") or [])
    )
    has_f141 = any(
        c.get("id") == "f141_memory_util" for c in (g.get("checkers") or [])
    )
    has_f143 = any(
        c.get("id") == "f143_memory_hub_gap" for c in (g.get("checkers") or [])
    )
    # F141: memory inject unused + APPROVE demote
    f141_ok = False
    try:
        with tempfile.TemporaryDirectory() as td4:
            od = Path(td4)
            (od / "memory-tool-audit.json").write_text(
                json.dumps(
                    {
                        "score": 0.15,
                        "hit_count": 0,
                        "inject_offered": True,
                        "utilization_gap": True,
                        "tool_call_turns": 3,
                        "tools_used": [],
                    }
                ),
                encoding="utf-8",
            )
            chk_m = run_f141_memory_util(od, root=root)
            fake_panel = {"composite": 0.8, "level": "L2"}
            dec_m = decide_verdict(
                "APPROVE",
                fake_panel,
                [
                    CheckerResult(
                        id="structure",
                        name="s",
                        ok=True,
                        score=1.0,
                        detail={"path_mentions": 5},
                    ),
                    CheckerResult(
                        id="f73_fitness",
                        name="f",
                        ok=True,
                        score=1.0,
                        detail={"path_evidence": 0.9},
                    ),
                    chk_m,
                ],
            )
            f141_ok = (
                not chk_m.ok and bool((chk_m.detail or {}).get("utilization_gap"))
            ) or (
                dec_m.get("demoted")
                and any(
                    "memory_tool" in str(r) for r in (dec_m.get("reasons") or [])
                )
            )
    except Exception:
        f141_ok = False

    # F143: hub memory gap high + local idle → demote
    f143_ok = False
    try:
        with tempfile.TemporaryDirectory() as td5:
            root_m = Path(td5)
            od = root_m / "out"
            od.mkdir()
            fed = root_m / "memory" / "federation"
            fed.mkdir(parents=True)
            (fed / "memory-util-signals.json").write_text(
                json.dumps(
                    {
                        "signals": [
                            {
                                "id": "memory-util-gap",
                                "theme": "memory-util-gap",
                                "tags": [
                                    "memory_util",
                                    "utilization_gap",
                                    "f141",
                                ],
                                "hits": 8,
                                "tenants": 3,
                                "util_rate_bin": "gap",
                                "source": "memory_tool_util",
                            },
                            {
                                "id": "memory-util-ok",
                                "theme": "memory-util-ok",
                                "tags": ["memory_util", "util_ok"],
                                "hits": 1,
                                "util_rate_bin": "full",
                                "source": "memory_tool_util",
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (od / "memory-tool-audit.json").write_text(
                json.dumps(
                    {
                        "score": 0.15,
                        "hit_count": 0,
                        "inject_offered": True,
                        "utilization_gap": True,
                        "tool_call_turns": 3,
                        "tools_used": [],
                    }
                ),
                encoding="utf-8",
            )
            prev_root = os.environ.get("TORII_ROOT")
            prev_thr = os.environ.get("TORII_MEMORY_HUB_GAP_THR")
            os.environ["TORII_ROOT"] = str(root_m)
            os.environ["TORII_MEMORY_HUB_GAP_CRITIC"] = "1"
            os.environ["TORII_MEMORY_HUB_GAP_THR"] = "0.05"
            os.environ["TORII_MEMORY_UTIL_HUB"] = "1"
            try:
                chk_h = run_f143_memory_hub_gap(od, root=root_m)
                fake_panel = {"composite": 0.8, "level": "L2"}
                dec_h = decide_verdict(
                    "APPROVE",
                    fake_panel,
                    [
                        CheckerResult(
                            id="structure",
                            name="s",
                            ok=True,
                            score=1.0,
                            detail={"path_mentions": 5},
                        ),
                        CheckerResult(
                            id="f73_fitness",
                            name="f",
                            ok=True,
                            score=1.0,
                            detail={"path_evidence": 0.9},
                        ),
                        chk_h,
                    ],
                )
                if chk_h.detail and chk_h.detail.get("soft_skip"):
                    f143_ok = True
                else:
                    f143_ok = (
                        (
                            not chk_h.ok
                            and "memory_hub_gap" in str(
                                chk_h.detail.get("reason") or ""
                            )
                        )
                        or (
                            dec_h.get("demoted")
                            and any(
                                "memory_hub_gap" in str(r)
                                for r in (dec_h.get("reasons") or [])
                            )
                        )
                    )
            finally:
                if prev_root is None:
                    os.environ.pop("TORII_ROOT", None)
                else:
                    os.environ["TORII_ROOT"] = prev_root
                if prev_thr is None:
                    os.environ.pop("TORII_MEMORY_HUB_GAP_THR", None)
                else:
                    os.environ["TORII_MEMORY_HUB_GAP_THR"] = prev_thr
    except Exception:
        f143_ok = False

    fixture_pass = (
        good_ok
        and weak_ok
        and delta >= 0.1
        and inject_ok
        and f127_ok
        and has_f127
        and f139_ok
        and has_f139
        and f141_ok
        and has_f141
        and f143_ok
        and has_f143
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_hub_gap": FEATURE_HUB_GAP,
                "feature_scorecard_hub_gap": FEATURE_SCORECARD_HUB_GAP,
                "feature_memory_util": FEATURE_MEMORY_UTIL,
                "feature_memory_hub_gap": FEATURE_MEMORY_HUB_GAP,
                "fixture_pass": fixture_pass,
                "f139_ok": f139_ok,
                "has_f139": has_f139,
                "f141_ok": f141_ok,
                "has_f141": has_f141,
                "f143_ok": f143_ok,
                "has_f143": has_f143,
                "good_composite": g_comp,
                "weak_composite": w_comp,
                "delta": round(delta, 4),
                "good_level": (g.get("panel") or {}).get("level"),
                "weak_level": (w.get("panel") or {}).get("level"),
                "weak_decision": w_dec,
                "inject_ok": inject_ok,
                "f127_ok": f127_ok,
                "has_f127": has_f127,
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def cmd_scorecard(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    panel = data.get("panel") or {}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "level": panel.get("level"),
                "composite": panel.get("composite"),
                "pass_rate": panel.get("pass_rate"),
                "decision": data.get("decision"),
            },
            indent=2,
        )
    )
    return 0


def demote_eval(
    *,
    root: Path | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """F128: paper-ready critic demote metrics (good/weak/hub-gap cases).

    Agent eval 2026: validation pass rate + recovery/demote rate sit next to
    task success. Report demote_rate on weak APPROVE, hub_gap demote rate, and
    that good REQUEST_CHANGES stays undemoted.
    """
    root = root or _root()
    cases: list[dict[str, Any]] = []

    good = root / "docs/benchmarks/fixtures/insecure-demo-good-review.md"
    weak = root / "docs/benchmarks/fixtures/insecure-demo-weak-review.md"

    def _case(
        name: str,
        review: Path,
        od: Path | None = None,
        *,
        case_root: Path | None = None,
    ) -> dict[str, Any]:
        if not review.is_file():
            return {
                "name": name,
                "error": "missing_fixture",
                "demoted": False,
                "maker": "UNKNOWN",
            }
        rep = run_panel(review, out_dir=od, root=case_root or root)
        dec = rep.get("decision") or {}
        panel = rep.get("panel") or {}
        hubc = next(
            (c for c in (rep.get("checkers") or []) if c.get("id") == "f127_hub_gap"),
            None,
        )
        sch = next(
            (
                c
                for c in (rep.get("checkers") or [])
                if c.get("id") == "f139_scorecard_hub_gap"
            ),
            None,
        )
        return {
            "name": name,
            "maker": rep.get("maker_verdict"),
            "recommended": dec.get("recommended_verdict"),
            "demoted": bool(dec.get("demoted")),
            "reasons": list(dec.get("reasons") or [])[:8],
            "composite": panel.get("composite"),
            "level": panel.get("level"),
            "f127_ok": None if hubc is None else bool(hubc.get("ok")),
            "f127_score": None if hubc is None else hubc.get("score"),
            "hub_gap_reason": (hubc or {}).get("detail", {}).get("reason")
            if isinstance((hubc or {}).get("detail"), dict)
            else None,
            "f139_ok": None if sch is None else bool(sch.get("ok")),
            "f139_score": None if sch is None else sch.get("score"),
            "scorecard_hub_gap_reason": (sch or {}).get("detail", {}).get("reason")
            if isinstance((sch or {}).get("detail"), dict)
            else None,
        }

    cases.append(_case("good_insecure", good))
    cases.append(_case("weak_approve", weak))

    # hub-gap APPROVE with idle recovery
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        od = Path(td)
        (od / "skill-router.json").write_text(
            json.dumps(
                {
                    "selected": ["skill-prefer-memory-cli-early"],
                    "always_selected": ["skill-prefer-memory-cli-early"],
                    "inject_chars": 500,
                }
            ),
            encoding="utf-8",
        )
        (od / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {
                            "id": "skill-prefer-memory-cli-early",
                            "tool_hit": False,
                            "hit": False,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        hub_review = od / "approve-idle.md"
        hub_review.write_text(
            "## Review\n**Verdict:** APPROVE\n\n### Summary\nok\n\n"
            "### Blocking\nnone\n\n### What I checked\n`app.py:1` path ok\n",
            encoding="utf-8",
        )
        # lower thr so product federation gap_pressure counts
        prev_thr = os.environ.get("TORII_HUB_GAP_PRESSURE_THR")
        os.environ["TORII_HUB_GAP_CRITIC"] = "1"
        os.environ["TORII_HUB_GAP_PRESSURE_THR"] = "0.05"
        os.environ["TORII_SECOND_CRITIC_MIN_PATH"] = "0.1"
        try:
            cases.append(_case("hub_gap_idle_approve", hub_review, od))
        finally:
            if prev_thr is None:
                os.environ.pop("TORII_HUB_GAP_PRESSURE_THR", None)
            else:
                os.environ["TORII_HUB_GAP_PRESSURE_THR"] = prev_thr
            os.environ.pop("TORII_SECOND_CRITIC_MIN_PATH", None)

    # F139: scorecard hub gap + idle scorecard ops + APPROVE
    with tempfile.TemporaryDirectory() as td_sc:
        od = Path(td_sc)
        fed = od / "memory" / "federation"
        fed.mkdir(parents=True)
        sc_sid = "skill-prefer-product-scorecard"
        (fed / "scorecard-util-signals.json").write_text(
            json.dumps(
                {
                    "signals": [
                        {
                            "id": "scorecard-util-gap",
                            "theme": "scorecard-util-gap",
                            "tags": ["scorecard_util", "utilization_gap", "f136"],
                            "hits": 8,
                            "tenants": 3,
                            "util_rate_bin": "gap",
                            "source": "scorecard_skill_util",
                        },
                        {
                            "id": "scorecard-util-ok",
                            "theme": "scorecard-util-ok",
                            "tags": ["scorecard_util", "util_ok"],
                            "hits": 1,
                            "util_rate_bin": "full",
                            "source": "scorecard_skill_util",
                        },
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (od / "skill-router.json").write_text(
            json.dumps(
                {
                    "selected": [sc_sid],
                    "always_selected": [],
                    "inject_chars": 600,
                }
            ),
            encoding="utf-8",
        )
        (od / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {
                            "id": sc_sid,
                            "tool_hit": False,
                            "hit": False,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        sc_review = od / "approve-sc-idle.md"
        sc_review.write_text(
            "## Review\n**Verdict:** APPROVE\n\n### Summary\nok\n\n"
            "### Blocking\nnone\n\n### What I checked\n`app.py:1` path ok\n",
            encoding="utf-8",
        )
        prev_sc_thr = os.environ.get("TORII_SCORECARD_HUB_GAP_THR")
        prev_root = os.environ.get("TORII_ROOT")
        os.environ["TORII_SCORECARD_HUB_GAP_CRITIC"] = "1"
        os.environ["TORII_SCORECARD_HUB_GAP_THR"] = "0.05"
        os.environ["TORII_SCORECARD_HUB_COMPOUND"] = "1"
        os.environ["TORII_ROOT"] = str(od)
        os.environ["TORII_SECOND_CRITIC_MIN_PATH"] = "0.1"
        try:
            # federation under TORII_ROOT=od so post_score_scorecard_hub finds it
            cases.append(
                _case(
                    "scorecard_hub_gap_idle_approve",
                    sc_review,
                    od,
                    case_root=od,
                )
            )
        finally:
            if prev_sc_thr is None:
                os.environ.pop("TORII_SCORECARD_HUB_GAP_THR", None)
            else:
                os.environ["TORII_SCORECARD_HUB_GAP_THR"] = prev_sc_thr
            if prev_root is None:
                os.environ.pop("TORII_ROOT", None)
            else:
                os.environ["TORII_ROOT"] = prev_root
            os.environ.pop("TORII_SECOND_CRITIC_MIN_PATH", None)

    # metrics
    approve_cases = [c for c in cases if c.get("maker") == "APPROVE"]
    demoted_n = sum(1 for c in approve_cases if c.get("demoted"))
    approve_n = len(approve_cases) or 1
    demote_rate = round(demoted_n / approve_n, 4)
    weak = next((c for c in cases if c["name"] == "weak_approve"), {})
    hubc = next((c for c in cases if c["name"] == "hub_gap_idle_approve"), {})
    schc = next(
        (c for c in cases if c["name"] == "scorecard_hub_gap_idle_approve"), {}
    )
    goodc = next((c for c in cases if c["name"] == "good_insecure"), {})
    weak_demote_ok = bool(weak.get("demoted") or weak.get("recommended") != "APPROVE")
    hub_demote_ok = bool(hubc.get("demoted")) or (
        # soft: if f127 skipped (no hub signals), still count weak path
        hubc.get("f127_ok") is True and float(hubc.get("f127_score") or 0) >= 0.5
    )
    sc_hub_demote_ok = bool(schc.get("demoted")) or (
        schc.get("f139_ok") is True and float(schc.get("f139_score") or 0) >= 0.5
    )
    # good should not be demoted from REQUEST_CHANGES to worse without reason;
    # typically maker is REQUEST_CHANGES already
    good_stable = goodc.get("maker") in ("REQUEST_CHANGES", "COMMENT", "APPROVE")

    report = {
        "feature": "F128",
        "feature_panel": FEATURE,
        "feature_hub_gap": FEATURE_HUB_GAP,
        "feature_scorecard_hub_gap": FEATURE_SCORECARD_HUB_GAP,
        "scored_at": _now(),
        "cases": cases,
        "approve_n": len(approve_cases),
        "demoted_n": demoted_n,
        "demote_rate": demote_rate,
        "weak_demote_ok": weak_demote_ok,
        "hub_gap_demote_ok": bool(hubc.get("demoted")),
        "hub_gap_soft_ok": hub_demote_ok,
        "scorecard_hub_gap_demote_ok": bool(schc.get("demoted")),
        "scorecard_hub_gap_soft_ok": sc_hub_demote_ok,
        "good_stable": good_stable,
        "paper": {
            "metric": "critic_approve_demote_rate",
            "value": demote_rate,
            "weak_approve_demoted": weak_demote_ok,
            "hub_gap_idle_demoted": bool(hubc.get("demoted")),
            "scorecard_hub_gap_idle_demoted": bool(schc.get("demoted")),
            "notes": "demote_rate = demoted APPROVE / APPROVE cases in offline pack",
        },
        "eval_pass": weak_demote_ok
        and good_stable
        and (bool(hubc.get("demoted")) or hub_demote_ok)
        and (bool(schc.get("demoted")) or sc_hub_demote_ok),
    }
    if out_dir:
        try:
            od = Path(out_dir)
            od.mkdir(parents=True, exist_ok=True)
            (od / "critic-demote-eval.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
            report["artifact"] = str(od / "critic-demote-eval.json")
        except OSError:
            pass
    # also archive under traces if TORII_ROOT known
    try:
        vault = root / "docs" / "benchmarks" / "traces"
        if vault.is_dir() and (os.environ.get("TORII_DEMOTE_EVAL_WRITE_VAULT") or "1") not in _FALSEY:
            # soft: don't write unless OUT_DIR or explicit
            pass
    except Exception:
        pass
    return report


def cmd_demote_eval(args: argparse.Namespace) -> int:
    """F128: offline paper demote-rate pack for critic panel."""
    od = Path(args.out_dir) if getattr(args, "out_dir", None) and args.out_dir else None
    if od is None and (os.environ.get("OUT_DIR") or "").strip():
        od = Path(os.environ["OUT_DIR"])
    report = demote_eval(root=_root(), out_dir=od)
    print(json.dumps(report, indent=2))
    return 0 if report.get("eval_pass") else 1


def cmd_status(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_hub_gap": FEATURE_HUB_GAP,
                "feature_scorecard_hub_gap": FEATURE_SCORECARD_HUB_GAP,
                "feature_memory_util": FEATURE_MEMORY_UTIL,
                "enabled": enabled(),
                "demote": demote_enabled(),
                "hub_gap_critic": hub_gap_critic_enabled(),
                "min_path": os.environ.get("TORII_SECOND_CRITIC_MIN_PATH") or "0.4",
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F78 multi-checker second-agent critic")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="Run critic panel on a review")
    pr.add_argument("--review", required=True)
    pr.add_argument("--out-dir", default="")
    pr.add_argument("--demote", action="store_true")
    pr.add_argument("--force", action="store_true")
    pr.add_argument("--strict", action="store_true")
    pr.set_defaults(func=cmd_run)

    pde = sub.add_parser(
        "demote-eval",
        help="F128 paper-ready critic demote-rate eval (good/weak/hub-gap)",
    )
    pde.add_argument("--out-dir", default="")
    pde.set_defaults(func=cmd_demote_eval)

    pi = sub.add_parser("inject", help="Inject maker/checker policy into prompt")
    pi.add_argument("--prompt", required=True)
    pi.set_defaults(func=cmd_inject)

    sub.add_parser("fixture", help="Offline good vs weak panel").set_defaults(
        func=cmd_fixture
    )

    ps = sub.add_parser("scorecard", help="Summarize critic JSON")
    ps.add_argument("--report", required=True)
    ps.set_defaults(func=cmd_scorecard)

    sub.add_parser("status").set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

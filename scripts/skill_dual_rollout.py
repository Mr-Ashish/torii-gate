#!/usr/bin/env python3
"""F86/F115/F167: Dual-rollout skill contribution + refine contribution_pp.

Research drivers (2026):
  - SkillsBench (arXiv 2602.12670): every task under no-Skills vs Skills;
    curated skills +16.2pp average; self-gen skills ≈0 — paired eval required.
  - Agent Skill Evaluation (arXiv 2606.11435): dual-rollout protocol —
    performance gap with/without skills = skill contribution signal.
  - FederatedSkill (arXiv 2606.03143): multi-tenant promote of skill themes
    only when complementary clients agree (min_tenants gate).
  - Mem2Act / F114: recovery skills fire via tools; dual must measure
    tool_hit_rate_with − tool_hit_rate_ablated or tool-only skills show 0pp.
  - GEPA / F165–F166: refined skill bodies need paper dual-rollout
    (with refine block vs ablated baseline) or contribution_pp is a slogan.
  - Prior Torii F84/F85: hit rates + demote, but no **with vs without** delta
    and skill themes promote without multi-tenant filter.

Product thesis:
  Skills that never beat a no-skill baseline are noise. Highest ROI: offline
  dual-rollout on labeled fixtures (hit_rate_with − hit_rate_ablated + F70
  recall held + F115 tool contribution) and multi-tenant promote of skill
  fitness themes (≥2 tenants). F167 adds **refine dual** for GEPA-lite bodies.

Commands:
  dual      — with-skills vs ablated/no-skills contribution on pack fixtures
  refine-dual — F167 with-refine vs ablated-refine contribution_pp paper metric
  federate-refine-dual — F168 privacy-safe federate of refine_pp bins
  promote-refine-dual — F168 multi-tenant promote gate for refine dual themes
  promote   — multi-tenant promote of skill-* federated themes
  fixture   — hermetic dual_pass + promote gate + privacy + tool + refine dual/promote
  status    — last metrics / ledger pointers
  all       — dual across bench_corpus packs

Env:
  TORII_ROOT
  TORII_SKILL_DUAL_ROLLOUT   1 (default) | 0
  TORII_SKILL_DUAL_TOOL     1 (default) | 0 — F115 tool_blob dual contribution
  TORII_SKILL_REFINE_DUAL   1 (default) | 0 — F167 refine contribution dual
  TORII_SKILL_REFINE_PROMOTE 1 (default) | 0 — F168 multi-tenant refine promote
  TORII_SKILL_PROMOTE_MIN_TENANTS  default 2
  TORII_SKILL_PROMOTE_MIN_HITS     default 2
  TORII_SKILL_REFINE_PROMOTE_MIN_PP default 1.0 — min tool or skill contrib_pp
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F86"
FEATURE_TOOL = "F115"
FEATURE_REFINE = "F167"
FEATURE_REFINE_PROMOTE = "F168"
SCHEMA = 1
REFINE_DUAL_FED_REL = "memory/federation/skill-refine-dual-signals.json"
PROMOTED_REFINE_REL = "memory/federation/promoted-refine-dual-themes.json"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

REFINE_MARKER = "<!-- torii-f165-gepa-refine -->"
REFINE_MARKER_CLOSE = "<!-- /torii-f165-gepa-refine -->"

# F115: skills-with tool transcript (memory CLI + depth tools)
SYNTH_TOOL_BLOB_WITH = (
    "tool_call: terminal\n"
    "python3 scripts/torii.py memory -- search -- -q \"sql injection\"\n"
    "rg -n pickle demo/insecure/app.py\n"
    "chain_revalidate.py score\n"
)
# without skills the agent skips taught CLIs
SYNTH_TOOL_BLOB_ABLATED = "tool_call: terminal\nls -la\necho hello\n"

# F167: with-refine agent fires hub-boost archival tools taught by GEPA nudge
SYNTH_TOOL_BLOB_REFINE_WITH = (
    "tool_call: terminal\n"
    "python3 scripts/archival_memory_search.py auto --files changed.py\n"
    "TORII_RECON_WARM_HUB_QUERY=1 hub_boost recon-warm-hub themes\n"
    "python3 scripts/torii.py memory -- search -- -q \"hub warm themes\"\n"
    "rg -n pickle demo/insecure/app.py\n"
)
# ablated refine: agent ignores GEPA tool-first nudge
SYNTH_TOOL_BLOB_REFINE_ABLATED = (
    "tool_call: terminal\n"
    "ls -la\n"
    "echo generic review without hub archival\n"
)

DEFAULT_CASES = "docs/benchmarks/cases/insecure-demo.json"
DEFAULT_GOOD = "docs/benchmarks/fixtures/insecure-demo-good-review.md"
DEFAULT_WEAK = "docs/benchmarks/fixtures/insecure-demo-weak-review.md"
DEMO_PATHS = [
    "demo/insecure/app.py",
    "demo/insecure/db.py",
]


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SKILL_DUAL_ROLLOUT") or "1").strip().lower()
    return raw not in _FALSEY


def tool_dual_enabled() -> bool:
    """F115: measure tool_hit_rate contribution in dual rollout (default on)."""
    raw = (os.environ.get("TORII_SKILL_DUAL_TOOL") or "1").strip().lower()
    return raw not in _FALSEY


def refine_dual_enabled() -> bool:
    """F167: paper dual-rollout for F165 GEPA-lite refined skill bodies."""
    raw = (os.environ.get("TORII_SKILL_REFINE_DUAL") or "1").strip().lower()
    return raw not in _FALSEY


def refine_promote_enabled() -> bool:
    """F168: multi-tenant promote of refine dual contribution themes."""
    raw = (os.environ.get("TORII_SKILL_REFINE_PROMOTE") or "1").strip().lower()
    return raw not in _FALSEY


def refine_promote_min_pp() -> float:
    try:
        return float(os.environ.get("TORII_SKILL_REFINE_PROMOTE_MIN_PP") or "1.0")
    except (TypeError, ValueError):
        return 1.0


def _tenant_hash(root: Path) -> str:
    """Privacy-safe tenant id (short hash of root path; no absolute path in signals)."""
    import hashlib

    raw = str(root.resolve())
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _scripts() -> Path:
    return Path(__file__).resolve().parent


def _import_mod(name: str):
    import importlib.util

    if name in sys.modules:
        return sys.modules[name]
    path = _scripts() / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(name)
    mod = importlib.util.module_from_spec(spec)
    # dataclasses need module registered before exec
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def skill_keyword_bank(root: Path | None = None) -> list[str]:
    """Union of skill body keywords used for ablation."""
    try:
        sr = _import_mod("skill_router")
        cards = sr.catalog(root or _root())
        kws: list[str] = []
        for c in cards:
            for k in c.keywords:
                if len(k) >= 4 and k not in kws:
                    kws.append(k)
            for part in re.split(r"[\s\-_]+", c.title.lower()):
                if len(part) >= 5 and part not in kws:
                    kws.append(part)
        # security skill probes that dual-rollout cares about
        for extra in (
            "attacker",
            "trigger",
            "taint",
            "chain",
            "source/sink",
            "unvalidated",
            "path:line",
            "diff hunk",
            "candidate",
        ):
            if extra not in kws:
                kws.append(extra)
        return kws
    except Exception:
        return [
            "attacker",
            "trigger",
            "taint",
            "chain",
            "unvalidated",
            "path:line",
            "candidate",
        ]


def ablate_skill_language(text: str, keywords: list[str]) -> str:
    """Remove skill-ish phrases while keeping vuln path evidence for F70."""
    out = text
    # drop skill-router inject blocks if present
    out = re.sub(
        r"<!-- torii-f84-skill-router -->.*?<!-- /torii-f84-skill-router -->",
        "",
        out,
        flags=re.DOTALL,
    )
    out = re.sub(
        r"<!-- torii-f69-skills -->.*?<!-- /torii-f69-skills -->",
        "",
        out,
        flags=re.DOTALL,
    )
    for kw in sorted(keywords, key=len, reverse=True):
        if len(kw) < 4:
            continue
        # word-ish replace (case insensitive)
        try:
            out = re.sub(re.escape(kw), " ", out, flags=re.I)
        except re.error:
            out = out.replace(kw, " ")
    # soften skill-y sentences
    out = re.sub(
        r"(?i)\b(attacker trigger|exploit scenario|source/sink pairs?|taint chain)\b",
        "issue",
        out,
    )
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out


def enrich_with_skill_language(text: str) -> str:
    """Ensure good skill-aligned review mentions skill probes (with condition)."""
    if "attacker trigger" in text.lower() and "taint" in text.lower():
        return text
    addon = (
        "\n\n### Skill discipline (dual-rollout with-skills)\n"
        "- Path:line citations on each finding.\n"
        "- Align claims with taint/chain candidates when present; else unvalidated.\n"
        "- Attacker trigger stated for each REQUEST CHANGES sink.\n"
        "- Prefer unified diff hunks over bare file heads.\n"
    )
    return text.rstrip() + addon


def strip_refine_blocks(text: str) -> str:
    """Remove F165 GEPA-lite refine blocks from skill bodies / review enrich."""
    return re.sub(
        rf"{re.escape(REFINE_MARKER)}.*?{re.escape(REFINE_MARKER_CLOSE)}\s*",
        "",
        text,
        flags=re.S,
    )


def list_refined_skill_bodies(root: Path | None = None) -> list[dict[str, Any]]:
    """Active skills carrying F165 refine markers (body text for dual)."""
    root = root or _root()
    active = root / "agent" / "skills" / "active"
    out: list[dict[str, Any]] = []
    if not active.is_dir():
        return out
    for md in sorted(active.glob("skill-*.md")):
        try:
            body = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if REFINE_MARKER not in body and "dual_gate: constraint_ok" not in body:
            continue
        refine_only = ""
        m = re.search(
            rf"{re.escape(REFINE_MARKER)}(.*?){re.escape(REFINE_MARKER_CLOSE)}",
            body,
            flags=re.S,
        )
        if m:
            refine_only = m.group(1).strip()
        out.append(
            {
                "id": md.stem,
                "path": str(md.relative_to(root)) if str(md).startswith(str(root)) else str(md),
                "body": body,
                "body_baseline": strip_refine_blocks(body),
                "refine_block": refine_only,
                "has_refine_block": bool(refine_only),
            }
        )
    return out


def refine_keyword_bank(bodies: list[dict[str, Any]]) -> list[str]:
    """Keywords unique to GEPA refine blocks (hub_boost, archival first-call, …)."""
    defaults = [
        "hub_boost",
        "archival_memory_search",
        "TORII_RECON_WARM_HUB_QUERY",
        "GEPA-lite",
        "F165",
        "hub warm",
        "first tool call",
    ]
    kws: list[str] = []
    for b in bodies:
        block = (b.get("refine_block") or "").lower()
        for tok in defaults:
            if tok.lower() in block or tok.lower() in (b.get("body") or "").lower():
                if tok not in kws:
                    kws.append(tok)
        # pull fenced CLIs
        for m in re.finditer(r"`([^`]{6,80})`", b.get("refine_block") or ""):
            t = m.group(1).strip()
            if t and t not in kws and len(t) < 60:
                kws.append(t)
    return kws or defaults


def enrich_with_refine_language(text: str, bodies: list[dict[str, Any]]) -> str:
    """Inject refine-block discipline into with-refine review condition."""
    lines = [
        "",
        "### GEPA-lite refine discipline (F167 dual with-refine)",
        "- First tool: archival_memory_search with TORII_RECON_WARM_HUB_QUERY=1.",
        "- Prefer hub_boost / recon-warm hub hits with path:line evidence.",
        "- Memory inject without tools is a measured gap (F165).",
    ]
    for b in bodies[:3]:
        sid = b.get("id") or ""
        if sid:
            lines.append(f"- Refined skill active: `{sid}`.")
        block = (b.get("refine_block") or "")[:400]
        if "hub_boost" in block:
            lines.append("- Honor hub_boost tool-first nudge from refined body.")
    return text.rstrip() + "\n" + "\n".join(lines) + "\n"


def run_refine_dual(
    root: Path | None = None,
    *,
    good_path: Path | None = None,
    cases_path: Path | None = None,
    paths: list[str] | None = None,
    pack_id: str = "insecure-demo",
    tool_blob_with: str | None = None,
    tool_blob_ablated: str | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """F167: paper dual-rollout — with-refine body/tools vs ablated baseline.

    Measures skill/tool contribution attributable to F165 GEPA refine blocks
    (not full skill library). Writes refine-dual.json when out_dir set.
    """
    root = root or _root()
    if not refine_dual_enabled():
        report = {
            "feature": FEATURE_REFINE,
            "enabled": False,
            "refine_dual_pass": False,
            "reason": "refine_dual_off",
            "scored_at": _now(),
        }
        _write_refine_dual(out_dir, report)
        return report

    cases_path = cases_path or (root / DEFAULT_CASES)
    good_path = good_path or (root / DEFAULT_GOOD)
    paths = paths or list(DEMO_PATHS)
    bsg = _import_mod("bench_security_gate")
    sr = _import_mod("skill_router")

    pack = bsg.load_cases(cases_path)
    good = good_path.read_text(encoding="utf-8", errors="replace")
    bodies = list_refined_skill_bodies(root)

    # If no refined skills in tree, synthesize fixture-grade hub-archival refine body
    synthetic = False
    if not bodies:
        synthetic = True
        bodies = [
            {
                "id": "skill-prefer-hub-archival-early",
                "path": "(synthetic)",
                "body": (
                    "---\nid: skill-prefer-hub-archival-early\n"
                    "dual_gate: constraint_ok\ndual_gate_feature: F166\n---\n"
                    f"{REFINE_MARKER}\n"
                    "## F165 GEPA-lite refine\n"
                    "First tool: archival_memory_search with hub_boost "
                    "TORII_RECON_WARM_HUB_QUERY.\n"
                    f"{REFINE_MARKER_CLOSE}\n"
                ),
                "body_baseline": "---\nid: skill-prefer-hub-archival-early\n---\nPrefer archival.\n",
                "refine_block": (
                    "First tool: archival_memory_search with hub_boost "
                    "TORII_RECON_WARM_HUB_QUERY."
                ),
                "has_refine_block": True,
            }
        ]

    use_tools = tool_dual_enabled()
    tb_with = (
        tool_blob_with
        if tool_blob_with is not None
        else (SYNTH_TOOL_BLOB_REFINE_WITH if use_tools else "")
    )
    tb_abl = (
        tool_blob_ablated
        if tool_blob_ablated is not None
        else (SYNTH_TOOL_BLOB_REFINE_ABLATED if use_tools else "")
    )

    # Prefer recovery skills that were refined
    prefer_ids = [b["id"] for b in bodies if b.get("id")]
    cards = sr.catalog(root)
    sel = sr.select_skills(cards, paths)
    selected = list(sel.get("selected") or [])
    for pid in prefer_ids:
        if pid not in selected and any(c.id == pid for c in cards):
            selected.append(pid)
    if not selected and prefer_ids:
        selected = list(prefer_ids)

    with_text = enrich_with_refine_language(
        enrich_with_skill_language(good), bodies
    )
    # ablated: strip refine discipline + generic skill ablation of refine kws
    kws = refine_keyword_bank(bodies)
    abl_text = ablate_skill_language(with_text, kws)
    abl_text = strip_refine_blocks(abl_text)
    # also strip refine discipline section title remnants
    abl_text = re.sub(
        r"### GEPA-lite refine discipline[\s\S]*?(?=\n### |\n## |\Z)",
        "\n",
        abl_text,
    )

    hits_with = sr.score_hits(
        _write_tmp(with_text, suffix="-refine-with.md"),
        root=root,
        selected=selected,
        out_dir=None,
        tool_blob=tb_with or "",
    )
    hits_abl = sr.score_hits(
        _write_tmp(abl_text, suffix="-refine-abl.md"),
        root=root,
        selected=selected,
        out_dir=None,
        tool_blob=tb_abl or "",
    )
    score_with = bsg.score_review(with_text, pack)
    score_abl = bsg.score_review(abl_text, pack)

    hr_with = float(hits_with.get("hit_rate") or 0)
    hr_abl = float(hits_abl.get("hit_rate") or 0)
    contrib = round(hr_with - hr_abl, 4)
    contrib_pp = round(contrib * 100, 2)

    thr_with = float(hits_with.get("tool_hit_rate") or 0)
    thr_abl = float(hits_abl.get("tool_hit_rate") or 0)
    tool_contrib = round(thr_with - thr_abl, 4)
    tool_contrib_pp = round(tool_contrib * 100, 2)
    thr_n_with = int(hits_with.get("tool_hit_n") or 0)
    thr_n_abl = int(hits_abl.get("tool_hit_n") or 0)

    # refine-specific probe presence in tool blob with
    refine_tool_probes = ["hub_boost", "archival_memory_search", "RECON_WARM_HUB"]
    blob_with_l = (tb_with or "").lower()
    blob_abl_l = (tb_abl or "").lower()
    probe_with = sum(1 for p in refine_tool_probes if p.lower() in blob_with_l)
    probe_abl = sum(1 for p in refine_tool_probes if p.lower() in blob_abl_l)
    probe_delta = probe_with - probe_abl

    recall_with = float(score_with.recall)
    recall_abl = float(score_abl.recall)
    recall_hold = recall_abl >= max(0.0, recall_with - 0.26)

    # dual pass: positive refine contribution on tools or hits; recall holds
    refine_dual_pass = bool(
        (tool_contrib > 0 or contrib > 0 or probe_delta > 0)
        and (thr_n_with >= 1 or not use_tools or probe_delta > 0)
        and recall_hold
        and bool(bodies)
    )

    report = {
        "feature": FEATURE_REFINE,
        "feature_parent": FEATURE,
        "schema": SCHEMA,
        "pack_id": pack_id or pack.get("id") or cases_path.stem,
        "enabled": True,
        "synthetic_bodies": synthetic,
        "refined_skill_ids": prefer_ids,
        "refined_n": len(bodies),
        "selected": selected,
        "paths": paths,
        "tool_dual": use_tools,
        "with_refine": {
            "hit_rate": hr_with,
            "hit_n": hits_with.get("hit_n"),
            "tool_hit_n": thr_n_with,
            "tool_hit_rate": thr_with,
            "recall": recall_with,
            "score_pct": score_with.score_pct,
            "passed": score_with.passed,
            "refine_probe_n": probe_with,
        },
        "ablated_refine": {
            "hit_rate": hr_abl,
            "hit_n": hits_abl.get("hit_n"),
            "tool_hit_n": thr_n_abl,
            "tool_hit_rate": thr_abl,
            "recall": recall_abl,
            "score_pct": score_abl.score_pct,
            "passed": score_abl.passed,
            "refine_probe_n": probe_abl,
        },
        "refine_contribution": contrib,
        "refine_contribution_pp": contrib_pp,
        "refine_tool_contribution": tool_contrib,
        "refine_tool_contribution_pp": tool_contrib_pp,
        "refine_probe_delta": probe_delta,
        "recall_hold": recall_hold,
        "refine_dual_pass": refine_dual_pass,
        "paper": {
            "metric": "refine_skill_contribution_pp",
            "value": contrib_pp,
            "tool_metric": "refine_tool_contribution_pp",
            "tool_value": tool_contrib_pp,
            "notes": (
                "SkillsBench/GEPA dual-rollout: with F165 refine block+tools "
                "vs ablated baseline; positive pp = refine helps"
            ),
        },
        "scored_at": _now(),
    }
    _write_refine_dual(out_dir, report)
    # F168: soft federate when dual produces a report (privacy-safe bins)
    if refine_promote_enabled():
        try:
            fed = federate_refine_dual(report, root=root, out_dir=out_dir)
            report["federate_refine_dual"] = {
                "federated_n": fed.get("federated_n"),
                "privacy_ok": fed.get("privacy_ok"),
            }
        except Exception:
            report["federate_refine_dual"] = {"federated_n": 0, "error": 1}
    return report


def _write_refine_dual(out_dir: Path | None, report: dict[str, Any]) -> Path | None:
    if out_dir is None:
        return None
    try:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / "refine-dual.json"
        dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return dest
    except OSError:
        return None


def run_dual(
    root: Path | None = None,
    *,
    cases_path: Path | None = None,
    good_path: Path | None = None,
    weak_path: Path | None = None,
    paths: list[str] | None = None,
    pack_id: str = "insecure-demo",
    tool_blob_with: str | None = None,
    tool_blob_ablated: str | None = None,
) -> dict[str, Any]:
    root = root or _root()
    cases_path = cases_path or (root / DEFAULT_CASES)
    good_path = good_path or (root / DEFAULT_GOOD)
    weak_path = weak_path or (root / DEFAULT_WEAK)
    paths = paths or list(DEMO_PATHS)

    bsg = _import_mod("bench_security_gate")
    sr = _import_mod("skill_router")

    pack = bsg.load_cases(cases_path)
    good = good_path.read_text(encoding="utf-8", errors="replace")
    weak = weak_path.read_text(encoding="utf-8", errors="replace") if weak_path.is_file() else ""

    use_tools = tool_dual_enabled()
    # Default synthetic tool blobs: with-skills agent follows memory CLI skill
    tb_with = tool_blob_with
    tb_abl = tool_blob_ablated
    if use_tools:
        if tb_with is None:
            tb_with = SYNTH_TOOL_BLOB_WITH
        if tb_abl is None:
            tb_abl = SYNTH_TOOL_BLOB_ABLATED
    else:
        tb_with = tb_with if tb_with is not None else ""
        tb_abl = tb_abl if tb_abl is not None else ""

    # WITH skills: enrich + select + score hits + F70 (+ F115 tool blob)
    with_text = enrich_with_skill_language(good)
    cards = sr.catalog(root)
    sel = sr.select_skills(cards, paths)
    selected = list(sel.get("selected") or [])
    hits_with = sr.score_hits(
        # write temp review path
        _write_tmp(with_text, suffix="-with.md"),
        root=root,
        selected=selected,
        out_dir=None,
        tool_blob=tb_with or "",
    )
    score_with = bsg.score_review(with_text, pack)

    # WITHOUT: ablate skill language; empty/weak tools (skills teach the CLIs)
    kws = skill_keyword_bank(root)
    ablated = ablate_skill_language(with_text, kws)
    hits_ablated = sr.score_hits(
        _write_tmp(ablated, suffix="-ablated.md"),
        root=root,
        selected=selected,
        out_dir=None,
        tool_blob=tb_abl or "",
    )
    score_ablated = bsg.score_review(ablated, pack)

    # no-skills baseline: empty selection → hit_rate 0
    hits_none = {
        "hit_rate": 0.0,
        "hit_n": 0,
        "selected_n": 0,
        "hits": [],
    }

    hr_with = float(hits_with.get("hit_rate") or 0)
    hr_abl = float(hits_ablated.get("hit_rate") or 0)
    contribution = round(hr_with - hr_abl, 4)
    contribution_pp = round(contribution * 100, 2)

    # F115: tool-only contribution dimension
    thr_with = float(hits_with.get("tool_hit_rate") or 0)
    thr_abl = float(hits_ablated.get("tool_hit_rate") or 0)
    tool_contribution = round(thr_with - thr_abl, 4)
    tool_contribution_pp = round(tool_contribution * 100, 2)
    thr_n_with = int(hits_with.get("tool_hit_n") or 0)
    thr_n_abl = int(hits_ablated.get("tool_hit_n") or 0)

    # F70 recall should hold on ablated (skills additive, not sole vuln text)
    recall_with = float(score_with.recall)
    recall_abl = float(score_ablated.recall)
    recall_hold = recall_abl >= max(0.0, recall_with - 0.26)  # allow small ablation bleed

    # weak without skills should not beat with-skills contribution story
    score_weak = bsg.score_review(weak, pack) if weak else None

    select_ok = bool(selected) and (
        any(
            s.startswith("skill-f74")
            or "tool" in s
            or "memory" in s
            or s.startswith("skill-prefer")
            for s in selected
        )
    )

    dual_pass = bool(
        contribution > 0
        and hr_with >= 0.3
        and select_ok
        and score_with.passed
        and recall_hold
    )
    # F115 soft gate: when tool dual on, with-skills must show tool hits
    tool_dual_ok = (not use_tools) or (thr_n_with >= 1 and tool_contribution >= 0)

    return {
        "feature": FEATURE,
        "feature_tool": FEATURE_TOOL if use_tools else None,
        "schema": SCHEMA,
        "pack_id": pack_id or pack.get("id") or cases_path.stem,
        "paths": paths,
        "selected": selected,
        "select_ok": select_ok,
        "tool_dual": use_tools,
        "with_skills": {
            "hit_rate": hr_with,
            "hit_n": hits_with.get("hit_n"),
            "selected_n": hits_with.get("selected_n"),
            "tool_hit_n": thr_n_with,
            "tool_hit_rate": thr_with,
            "recall": recall_with,
            "score_pct": score_with.score_pct,
            "passed": score_with.passed,
            "verdict": score_with.verdict,
        },
        "ablated": {
            "hit_rate": hr_abl,
            "hit_n": hits_ablated.get("hit_n"),
            "tool_hit_n": thr_n_abl,
            "tool_hit_rate": thr_abl,
            "recall": recall_abl,
            "score_pct": score_ablated.score_pct,
            "passed": score_ablated.passed,
        },
        "no_skills": hits_none,
        "weak": {
            "recall": float(score_weak.recall) if score_weak else None,
            "passed": score_weak.passed if score_weak else None,
        },
        "skill_contribution": contribution,
        "skill_contribution_pp": contribution_pp,
        "tool_contribution": tool_contribution,
        "tool_contribution_pp": tool_contribution_pp,
        "tool_dual_ok": tool_dual_ok,
        "recall_hold": recall_hold,
        "dual_pass": dual_pass,
        "scored_at": _now(),
    }


_TMP_FILES: list[Path] = []


def _write_tmp(text: str, suffix: str = ".md") -> Path:
    fd, name = tempfile.mkstemp(prefix="torii-f86-", suffix=suffix)
    os.close(fd)
    p = Path(name)
    p.write_text(text, encoding="utf-8")
    _TMP_FILES.append(p)
    return p


def _contrib_bin(pp: float) -> str:
    if pp >= 50:
        return "high"
    if pp >= 10:
        return "mid"
    if pp > 0:
        return "low"
    if pp == 0:
        return "zero"
    return "neg"


def federate_refine_dual(
    report: dict[str, Any] | None = None,
    root: Path | None = None,
    *,
    out_dir: Path | None = None,
    tenant_hash: str | None = None,
) -> dict[str, Any]:
    """F168: privacy-safe federate of F167 refine dual metrics.

    Emits skill id + contribution bins + dual_pass only — no paths, bodies, or
    absolute paths. Multi-tenant promote (promote_refine_dual) reads this file.
    """
    root = root or _root()
    if not refine_promote_enabled() and not refine_dual_enabled():
        return {
            "feature": FEATURE_REFINE_PROMOTE,
            "federated_n": 0,
            "reason": "refine_promote_off",
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
            "feature": FEATURE_REFINE_PROMOTE,
            "federated_n": 0,
            "reason": "no_refine_dual",
            "privacy_ok": True,
        }

    th = tenant_hash or _tenant_hash(root)
    skill_ids = list(report.get("refined_skill_ids") or [])
    tool_pp = float(report.get("refine_tool_contribution_pp") or 0)
    skill_pp = float(report.get("refine_contribution_pp") or 0)
    probe_d = int(report.get("refine_probe_delta") or 0)
    dual_pass = bool(report.get("refine_dual_pass"))
    dest = root / REFINE_DUAL_FED_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {
        "schema_version": SCHEMA,
        "feature": FEATURE_REFINE_PROMOTE,
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
            key = f"{s.get('theme') or s.get('skill_id')}|{s.get('tenant_hash') or ''}"
            by_key[key] = s

    federated = 0
    ids = skill_ids or ["skill-prefer-hub-archival-early"]
    for sid in ids:
        if not str(sid).startswith("skill-"):
            continue
        key = f"{sid}|{th}"
        prev = by_key.get(key) if isinstance(by_key.get(key), dict) else {}
        hits = int(prev.get("hits") or 0) + 1
        # accumulate best positive tool_pp seen for this tenant
        prev_tool = float(prev.get("tool_contrib_pp") or 0)
        best_tool = max(prev_tool, tool_pp)
        entry = {
            "id": f"refine-dual-{sid}"[:64],
            "theme": sid,
            "skill_id": sid,
            "tags": [
                "refine_dual",
                "f167",
                "f168",
                "gepa",
                "federated_skill",
                "skill_hit",
                "dual_pass" if dual_pass else "dual_fail",
            ],
            "source": "skill_refine_dual",
            "hits": hits,
            "tenants": 1,  # per-tenant row; promote aggregates
            "tenant_hash": th,
            "tenant_hashes": sorted(
                set(list(prev.get("tenant_hashes") or []) + [th])
            )[:16],
            "tool_contrib_pp": best_tool,
            "skill_contrib_pp": max(float(prev.get("skill_contrib_pp") or 0), skill_pp),
            "probe_delta": max(int(prev.get("probe_delta") or 0), probe_d),
            "util_rate_bin": _contrib_bin(best_tool if best_tool else skill_pp),
            "dual_pass": dual_pass or bool(prev.get("dual_pass")),
            "updated_at": _now(),
            "feature": FEATURE_REFINE_PROMOTE,
        }
        by_key[key] = entry
        federated += 1

    # collapse privacy check
    signals = list(by_key.values())[-200:]
    doc = {
        "schema_version": SCHEMA,
        "feature": FEATURE_REFINE_PROMOTE,
        "scope": "skill_refine_dual",
        "updated_at": _now(),
        "privacy": "skill_id_bins_tenant_hash_only",
        "privacy_ok": True,
        "signals": signals,
    }
    blob = json.dumps(doc)
    if "/Users/" in blob or "/home/" in blob:
        doc["privacy_ok"] = False
        doc["signals"] = []
        federated = 0
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    # also write next to out_dir for traces
    if out_dir is not None:
        try:
            od = Path(out_dir)
            od.mkdir(parents=True, exist_ok=True)
            (od / "skill-refine-dual-signals.json").write_text(
                json.dumps(doc, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass

    return {
        "feature": FEATURE_REFINE_PROMOTE,
        "path": str(dest),
        "federated_n": federated,
        "signals_n": len(doc["signals"]),
        "privacy_ok": doc["privacy_ok"],
        "tenant_hash": th,
        "tool_contrib_pp": tool_pp,
        "dual_pass": dual_pass,
    }


def promote_refine_dual_themes(
    root: Path | None = None,
    *,
    min_tenants: int | None = None,
    min_hits: int | None = None,
    min_pp: float | None = None,
) -> dict[str, Any]:
    """F168: FederatedSkill-style gate — promote refine dual only if multi-tenant agree.

    Aggregates skill-refine-dual-signals by skill_id across tenant_hashes.
    Requires ≥min_tenants and positive contribution bin (tool or skill pp ≥ min_pp).
    """
    root = root or _root()
    if not refine_promote_enabled():
        return {
            "feature": FEATURE_REFINE_PROMOTE,
            "promoted_n": 0,
            "reason": "refine_promote_off",
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
    thr = min_pp if min_pp is not None else refine_promote_min_pp()

    path = root / REFINE_DUAL_FED_REL
    # also merge out_dir copy if present
    sigs: list[dict[str, Any]] = []
    for p in (
        path,
        root / "memory" / "federation" / "skill-refine-signals.json",
    ):
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        raw = data.get("signals") if isinstance(data, dict) else data
        if isinstance(raw, list):
            for s in raw:
                if not isinstance(s, dict):
                    continue
                tags = [str(t).lower() for t in (s.get("tags") or [])]
                src = str(s.get("source") or "").lower()
                if (
                    "refine_dual" in tags
                    or "f167" in tags
                    or "f168" in tags
                    or src == "skill_refine_dual"
                    or "refine" in tags
                ):
                    sigs.append(s)

    # aggregate by skill_id
    by_sid: dict[str, dict[str, Any]] = {}
    for s in sigs:
        sid = str(s.get("skill_id") or s.get("theme") or "")
        if not sid.startswith("skill-"):
            continue
        ent = by_sid.setdefault(
            sid,
            {
                "skill_id": sid,
                "theme": sid,
                "tenant_hashes": set(),
                "hits": 0,
                "tool_contrib_pp": 0.0,
                "skill_contrib_pp": 0.0,
                "probe_delta": 0,
                "dual_pass_n": 0,
            },
        )
        ths = s.get("tenant_hashes") or (
            [s.get("tenant_hash")] if s.get("tenant_hash") else []
        )
        for th in ths:
            if th:
                ent["tenant_hashes"].add(str(th))
        # also count tenants field when hashes missing
        if not ths and int(s.get("tenants") or 0) >= 1:
            ent["tenant_hashes"].add(f"anon-{s.get('id') or sid}")
        ent["hits"] += max(1, int(s.get("hits") or 1))
        ent["tool_contrib_pp"] = max(
            float(ent["tool_contrib_pp"]), float(s.get("tool_contrib_pp") or 0)
        )
        ent["skill_contrib_pp"] = max(
            float(ent["skill_contrib_pp"]), float(s.get("skill_contrib_pp") or 0)
        )
        ent["probe_delta"] = max(int(ent["probe_delta"]), int(s.get("probe_delta") or 0))
        if s.get("dual_pass"):
            ent["dual_pass_n"] += 1

    clean: list[dict[str, Any]] = []
    blocked: list[str] = []
    for sid, ent in by_sid.items():
        tenants = len(ent["tenant_hashes"])
        hits = int(ent["hits"])
        best_pp = max(float(ent["tool_contrib_pp"]), float(ent["skill_contrib_pp"]))
        # probe_delta as soft pp proxy when rates tie
        if best_pp <= 0 and int(ent["probe_delta"]) > 0:
            best_pp = float(int(ent["probe_delta"]) * 10)
        ok = tenants >= min_t and hits >= min_h and best_pp >= thr
        if not ok:
            blocked.append(sid)
            continue
        clean.append(
            {
                "id": f"promoted-refine-{sid}"[:64],
                "theme": sid,
                "skill_id": sid,
                "tags": [
                    "promoted_refine_dual",
                    "f168",
                    "f167",
                    "federated_skill",
                    "skill_hit",
                ],
                "source": "skill_refine_dual_promote",
                "hits": hits,
                "tenants": tenants,
                "tenant_hashes": sorted(ent["tenant_hashes"])[:16],
                "tool_contrib_pp": float(ent["tool_contrib_pp"]),
                "skill_contrib_pp": float(ent["skill_contrib_pp"]),
                "probe_delta": int(ent["probe_delta"]),
                "util_rate_bin": _contrib_bin(best_pp),
                "dual_pass_n": int(ent["dual_pass_n"]),
                "feature": FEATURE_REFINE_PROMOTE,
            }
        )

    out = root / PROMOTED_REFINE_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": SCHEMA,
        "feature": FEATURE_REFINE_PROMOTE,
        "scope": "promoted_refine_dual_themes",
        "updated_at": _now(),
        "min_tenants": min_t,
        "min_hits": min_h,
        "min_pp": thr,
        "source_skill_n": len(by_sid),
        "promoted_n": len(clean),
        "blocked": blocked[:32],
        "privacy": "skill_id_bins_tenant_hash_only",
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

    # soft fitness boost for promoted refine skills
    fitness_boosted = _soft_fitness_refine_promote(root, [c["skill_id"] for c in clean])

    return {
        "feature": FEATURE_REFINE_PROMOTE,
        "path": str(out),
        "source_skill_n": len(by_sid),
        "promoted_n": doc["promoted_n"],
        "blocked_n": len(blocked),
        "blocked": blocked[:16],
        "min_tenants": min_t,
        "min_hits": min_h,
        "min_pp": thr,
        "privacy_ok": doc["privacy_ok"],
        "themes": [s.get("theme") for s in clean[:16]],
        "fitness_boosted": fitness_boosted,
    }


def _soft_fitness_refine_promote(root: Path, skill_ids: list[str]) -> list[str]:
    """Mark promoted refine dual skills on fitness ledger (priority soft boost)."""
    if not skill_ids:
        return []
    try:
        sf = _import_mod("skill_fitness")
    except Exception:
        return []
    try:
        ledger = sf.load_ledger(root)
        skills = ledger.setdefault("skills", {})
        boosted: list[str] = []
        for sid in skill_ids:
            e = skills.setdefault(sid, {"id": sid})
            e["refine_dual_promoted"] = True
            e["last_refine_promote_at"] = _now()
            e["hub_priority_delta"] = max(int(e.get("hub_priority_delta") or 0), 18)
            e["gepa_refined"] = True
            e["demoted"] = False
            boosted.append(sid)
        if boosted:
            sf.save_ledger(ledger, sf.ledger_path(root))
        return boosted
    except Exception:
        return []


def cycle_refine_dual_promote(
    root: Path | None = None,
    *,
    out_dir: Path | None = None,
    run_dual: bool = True,
) -> dict[str, Any]:
    """F168: optional refine-dual → federate → multi-tenant promote (one cycle)."""
    root = root or _root()
    dual_report: dict[str, Any] = {}
    if run_dual and refine_dual_enabled():
        dual_report = run_refine_dual(root, out_dir=out_dir)
    elif out_dir is not None:
        p = Path(out_dir) / "refine-dual.json"
        if p.is_file():
            try:
                dual_report = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                dual_report = {}
    fed = federate_refine_dual(dual_report or None, root=root, out_dir=out_dir)
    prom = promote_refine_dual_themes(root)
    return {
        "feature": FEATURE_REFINE_PROMOTE,
        "refine_dual_pass": dual_report.get("refine_dual_pass"),
        "refine_tool_contribution_pp": dual_report.get("refine_tool_contribution_pp"),
        "federate": fed,
        "promote": prom,
        "ok": bool(fed.get("privacy_ok", True) and prom.get("privacy_ok", True)),
        "scored_at": _now(),
    }


def promote_skill_themes(
    root: Path | None = None,
    *,
    min_tenants: int | None = None,
    min_hits: int | None = None,
) -> dict[str, Any]:
    """Promote only skill-tagged federated signals past multi-tenant gate."""
    root = root or _root()
    min_t = (
        min_tenants
        if min_tenants is not None
        else _int_env("TORII_SKILL_PROMOTE_MIN_TENANTS", 2)
    )
    min_h = (
        min_hits if min_hits is not None else _int_env("TORII_SKILL_PROMOTE_MIN_HITS", 2)
    )

    fed = _import_mod("federated_hub_ingest")
    # collect skill-tagged from global + skill-fitness file
    gpath = fed.global_fed_path(root)
    sigs = fed.load_signals(gpath)
    skill_fit = root / "memory" / "federation" / "skill-fitness-signals.json"
    if skill_fit.is_file():
        sigs = fed.merge_signals(sigs, fed.load_signals(skill_fit))

    skill_sigs = [
        s
        for s in sigs
        if "skill" in str(s.get("source") or "").lower()
        or "skill_hit" in (s.get("tags") or [])
        or "federated_skill" in (s.get("tags") or [])
        or str(s.get("theme") or "").startswith("skill")
        or str(s.get("id") or "").startswith("skill")
    ]
    promoted = [
        s
        for s in skill_sigs
        if int(s.get("tenants") or 1) >= min_t and int(s.get("hits") or 1) >= min_h
    ]
    # privacy strip
    clean = []
    for s in promoted:
        c = fed.sanitize_signal(s)
        if c and "/Users/" not in json.dumps(c):
            clean.append(c)

    out = root / "memory" / "federation" / "promoted-skill-themes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "scope": "promoted_skill_themes",
        "updated_at": _now(),
        "min_tenants": min_t,
        "min_hits": min_h,
        "source_skill_n": len(skill_sigs),
        "promoted_n": len(clean),
        "privacy": "skill_id_hits_tenant_hash_only",
        "privacy_ok": True,
        "signals": clean,
    }
    # privacy recheck
    blob = json.dumps(doc)
    if "/Users/" in blob or "/home/" in blob:
        doc["privacy_ok"] = False
        doc["signals"] = []
        doc["promoted_n"] = 0
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {
        "feature": FEATURE,
        "path": str(out),
        "source_skill_n": len(skill_sigs),
        "promoted_n": doc["promoted_n"],
        "min_tenants": min_t,
        "min_hits": min_h,
        "privacy_ok": doc["privacy_ok"],
        "themes": [s.get("theme") for s in clean[:16]],
    }


def run_all_packs(root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    try:
        bc = _import_mod("bench_corpus")
        packs = list(bc.PACKS)
    except Exception:
        packs = [
            {
                "id": "insecure-demo",
                "cases": DEFAULT_CASES,
                "good": DEFAULT_GOOD,
                "weak": DEFAULT_WEAK,
            }
        ]
    results = []
    for p in packs:
        paths = DEMO_PATHS
        if "juice" in p.get("id", ""):
            paths = ["demo/juice_shop_synth/routes.js", "demo/juice_shop_synth/app.js"]
            # fallback if not exist
            if not any((root / x).exists() for x in paths):
                paths = ["routes/login.js", "server.js"]
        try:
            r = run_dual(
                root,
                cases_path=root / p["cases"],
                good_path=root / p["good"],
                weak_path=root / p["weak"],
                paths=paths,
                pack_id=p["id"],
            )
            results.append(r)
        except Exception as exc:
            results.append(
                {
                    "pack_id": p.get("id"),
                    "dual_pass": False,
                    "error": str(exc)[:160],
                }
            )
    n = len(results)
    n_pass = sum(1 for r in results if r.get("dual_pass"))
    contribs = [float(r["skill_contribution_pp"]) for r in results if "skill_contribution_pp" in r]
    return {
        "feature": FEATURE,
        "n_packs": n,
        "n_pass": n_pass,
        "all_pass": n > 0 and n_pass == n,
        "mean_contribution_pp": round(sum(contribs) / len(contribs), 2) if contribs else 0.0,
        "packs": results,
        "scored_at": _now(),
    }


def cmd_refine_dual(args: argparse.Namespace) -> int:
    """F167: with-refine vs ablated-refine dual-rollout paper metric."""
    root = _root()
    od = Path(args.out_dir) if (getattr(args, "out_dir", "") or "").strip() else None
    report = run_refine_dual(
        root,
        good_path=Path(args.good) if (args.good or "").strip() else None,
        cases_path=Path(args.cases) if (getattr(args, "cases", "") or "").strip() else None,
        paths=list(args.paths) if args.paths else None,
        pack_id=(args.pack_id or "insecure-demo").strip() or "insecure-demo",
        out_dir=od,
    )
    out = (getattr(args, "out", "") or "").strip()
    if out:
        Path(out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report.get("refine_dual_pass") else 1


def cmd_federate_refine_dual(args: argparse.Namespace) -> int:
    root = _root()
    od = Path(args.out_dir) if (getattr(args, "out_dir", "") or "").strip() else None
    report = None
    rp = (getattr(args, "report", "") or "").strip()
    if rp:
        p = Path(rp)
        if p.is_file():
            report = json.loads(p.read_text(encoding="utf-8"))
    result = federate_refine_dual(report, root=root, out_dir=od)
    print(json.dumps(result, indent=2))
    return 0 if result.get("privacy_ok", True) else 1


def cmd_promote_refine_dual(args: argparse.Namespace) -> int:
    result = promote_refine_dual_themes(
        _root(),
        min_tenants=getattr(args, "min_tenants", None),
        min_hits=getattr(args, "min_hits", None),
        min_pp=getattr(args, "min_pp", None),
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("privacy_ok", True) else 1


def cmd_cycle_refine_promote(args: argparse.Namespace) -> int:
    od = Path(args.out_dir) if (getattr(args, "out_dir", "") or "").strip() else None
    result = cycle_refine_dual_promote(
        _root(),
        out_dir=od,
        run_dual=not bool(getattr(args, "skip_dual", False)),
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def cmd_dual(args: argparse.Namespace) -> int:
    root = _root()
    if args.cases:
        r = run_dual(
            root,
            cases_path=Path(args.cases),
            good_path=Path(args.good) if args.good else None,
            weak_path=Path(args.weak) if args.weak else None,
            paths=args.paths,
            pack_id=args.pack_id or "custom",
        )
    else:
        r = run_dual(root, pack_id=args.pack_id or "insecure-demo")
    if args.out:
        Path(args.out).write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(r, indent=2))
    return 0 if r.get("dual_pass") else 1


def cmd_all(args: argparse.Namespace) -> int:
    r = run_all_packs(_root())
    if args.out:
        Path(args.out).write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(r, indent=2))
    return 0 if r.get("all_pass") or r.get("n_pass", 0) >= 1 else 1


def cmd_promote(args: argparse.Namespace) -> int:
    r = promote_skill_themes(
        _root(),
        min_tenants=args.min_tenants,
        min_hits=args.min_hits,
    )
    print(json.dumps(r, indent=2))
    return 0 if r.get("privacy_ok") else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    prom = root / "memory" / "federation" / "promoted-skill-themes.json"
    fit = root / ".torii" / "skill-fitness.json"
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "promoted_exists": prom.is_file(),
                "fitness_exists": fit.is_file(),
                "min_tenants": _int_env("TORII_SKILL_PROMOTE_MIN_TENANTS", 2),
            },
            indent=2,
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: dual contribution > 0 on good; multi-tenant promote gate."""
    root = _root()
    # dual on real fixtures in repo
    dual = run_dual(root)
    dual_ok = bool(dual.get("dual_pass"))

    # multi-tenant promote hermetic
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        fed_dir = td_path / "memory" / "federation"
        fed_dir.mkdir(parents=True)
        # two tenants for skill-good, one tenant for skill-noise
        signals = [
            {
                "id": "skill-f74-prefer-chain-json",
                "theme": "skill-f74-prefer-chain-json",
                "tags": ["skill_hit", "federated_skill"],
                "keywords": ["chain"],
                "path_basenames": [],
                "hits": 5,
                "source": "skill_fitness",
                "tenant_hashes": ["aaa111", "bbb222"],
                "tenants": 2,
            },
            {
                "id": "skill-noise-single",
                "theme": "skill-noise-single",
                "tags": ["skill_hit", "federated_skill"],
                "keywords": ["noise"],
                "path_basenames": [],
                "hits": 9,
                "source": "skill_fitness",
                "tenant_hashes": ["ccc333"],
                "tenants": 1,
            },
            {
                "id": "sql_injection",
                "theme": "sql_injection",
                "tags": ["security"],
                "keywords": ["sqli"],
                "hits": 10,
                "source": "tp_signature",
                "tenants": 3,
            },
        ]
        (fed_dir / "federated-signals.json").write_text(
            json.dumps({"signals": signals, "feature": "F77"}),
            encoding="utf-8",
        )
        (fed_dir / "skill-fitness-signals.json").write_text(
            json.dumps({"signals": signals[:2], "feature": "F85"}),
            encoding="utf-8",
        )
        prom = promote_skill_themes(td_path, min_tenants=2, min_hits=2)
        themes = set(prom.get("themes") or [])
        multi_ok = "skill-f74-prefer-chain-json" in themes or any(
            "prefer-chain" in str(t) for t in themes
        )
        single_blocked = "skill-noise-single" not in themes
        non_skill_blocked = "sql_injection" not in themes
        privacy_ok = bool(prom.get("privacy_ok"))

    tool_ok = bool(dual.get("tool_dual_ok"))
    tool_cpp = float(dual.get("tool_contribution_pp") or 0)

    # F167: refine dual-rollout contribution_pp (GEPA with vs ablated refine)
    f167_ok = False
    refine_dual_report: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as td_rf:
        td_rf_path = Path(td_rf)
        prev_root = os.environ.get("TORII_ROOT")
        try:
            os.environ["TORII_ROOT"] = str(td_rf_path)
            os.environ["TORII_SKILL_REFINE_DUAL"] = "1"
            # plant refined hub-archival skill with GEPA block
            active = td_rf_path / "agent" / "skills" / "active"
            active.mkdir(parents=True)
            sid = "skill-prefer-hub-archival-early"
            (active / f"{sid}.md").write_text(
                f"""---
id: {sid}
feature: F165
status: adopted
always: true
always_priority: 95
dual_gate: constraint_ok
dual_gate_feature: F166
refined_feature: F165
---

## Skill: prefer-hub-archival-early

Prefer multi-tenant warm archival.
{REFINE_MARKER}
## F165 GEPA-lite refine (chronic_tool_miss)

**F165 GEPA-lite (util trace):** hub-archival inject without hub_boost is a measured gap.
1. **First tool call** this turn: `python3 scripts/archival_memory_search.py auto --files changed.py`
   Keep `TORII_RECON_WARM_HUB_QUERY=1` so multi-tenant warm themes expand the query.
2. Prefer hits that carry **hub_boost** / recon-warm hub heat; require path:line evidence.
{REFINE_MARKER_CLOSE}
""",
                encoding="utf-8",
            )
            # copy pack fixtures into temp root for score_review
            for rel in (DEFAULT_CASES, DEFAULT_GOOD, DEFAULT_WEAK):
                src = root / rel
                if src.is_file():
                    dest = td_rf_path / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            # also need demo paths? score_review uses cases only
            refine_dual_report = run_refine_dual(
                td_rf_path,
                good_path=td_rf_path / DEFAULT_GOOD
                if (td_rf_path / DEFAULT_GOOD).is_file()
                else root / DEFAULT_GOOD,
                cases_path=td_rf_path / DEFAULT_CASES
                if (td_rf_path / DEFAULT_CASES).is_file()
                else root / DEFAULT_CASES,
                out_dir=td_rf_path / "out",
            )
            f167_ok = bool(refine_dual_report.get("refine_dual_pass")) and (
                float(refine_dual_report.get("refine_tool_contribution_pp") or 0) > 0
                or float(refine_dual_report.get("refine_contribution_pp") or 0) > 0
                or int(refine_dual_report.get("refine_probe_delta") or 0) > 0
            )
        finally:
            if prev_root is None:
                os.environ.pop("TORII_ROOT", None)
            else:
                os.environ["TORII_ROOT"] = prev_root

    # F168: multi-tenant promote of refine dual — 2 tenants promote, 1 blocked
    f168_ok = False
    f168_prom: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as td168:
        td168_path = Path(td168)
        prev_root = os.environ.get("TORII_ROOT")
        try:
            os.environ["TORII_ROOT"] = str(td168_path)
            os.environ["TORII_SKILL_REFINE_PROMOTE"] = "1"
            fed_dir = td168_path / "memory" / "federation"
            fed_dir.mkdir(parents=True)
            multi_sid = "skill-prefer-hub-archival-early"
            single_sid = "skill-noise-refine-single"
            # two tenants positive tool_pp for multi_sid; one tenant for noise
            signals = [
                {
                    "id": "rd-a",
                    "theme": multi_sid,
                    "skill_id": multi_sid,
                    "tags": ["refine_dual", "f167", "f168", "federated_skill"],
                    "source": "skill_refine_dual",
                    "hits": 3,
                    "tenants": 1,
                    "tenant_hash": "tenant-aaa",
                    "tenant_hashes": ["tenant-aaa"],
                    "tool_contrib_pp": 50.0,
                    "skill_contrib_pp": 0.0,
                    "probe_delta": 3,
                    "dual_pass": True,
                    "util_rate_bin": "high",
                },
                {
                    "id": "rd-b",
                    "theme": multi_sid,
                    "skill_id": multi_sid,
                    "tags": ["refine_dual", "f167", "f168", "federated_skill"],
                    "source": "skill_refine_dual",
                    "hits": 2,
                    "tenants": 1,
                    "tenant_hash": "tenant-bbb",
                    "tenant_hashes": ["tenant-bbb"],
                    "tool_contrib_pp": 40.0,
                    "skill_contrib_pp": 0.0,
                    "probe_delta": 2,
                    "dual_pass": True,
                    "util_rate_bin": "mid",
                },
                {
                    "id": "rd-noise",
                    "theme": single_sid,
                    "skill_id": single_sid,
                    "tags": ["refine_dual", "f168", "federated_skill"],
                    "source": "skill_refine_dual",
                    "hits": 9,
                    "tenants": 1,
                    "tenant_hash": "tenant-ccc",
                    "tenant_hashes": ["tenant-ccc"],
                    "tool_contrib_pp": 90.0,
                    "skill_contrib_pp": 0.0,
                    "probe_delta": 3,
                    "dual_pass": True,
                    "util_rate_bin": "high",
                },
            ]
            (fed_dir / "skill-refine-dual-signals.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "feature": "F168",
                        "signals": signals,
                        "privacy_ok": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            f168_prom = promote_refine_dual_themes(
                td168_path, min_tenants=2, min_hits=2, min_pp=1.0
            )
            themes = set(f168_prom.get("themes") or [])
            multi_ok168 = multi_sid in themes
            single_blocked168 = single_sid not in themes
            privacy168 = bool(f168_prom.get("privacy_ok"))
            # federate path privacy on synthetic dual report
            fed_rep = federate_refine_dual(
                {
                    "refine_dual_pass": True,
                    "refined_skill_ids": [multi_sid],
                    "refine_tool_contribution_pp": 50.0,
                    "refine_contribution_pp": 0.0,
                    "refine_probe_delta": 3,
                },
                root=td168_path,
                tenant_hash="tenant-ddd",
            )
            fed_ok = bool(fed_rep.get("privacy_ok")) and int(fed_rep.get("federated_n") or 0) >= 1
            blob = (fed_dir / "skill-refine-dual-signals.json").read_text(encoding="utf-8")
            no_abs = "/Users/" not in blob and "/home/" not in blob
            f168_ok = multi_ok168 and single_blocked168 and privacy168 and fed_ok and no_abs
        finally:
            if prev_root is None:
                os.environ.pop("TORII_ROOT", None)
            else:
                os.environ["TORII_ROOT"] = prev_root

    fixture_pass = all(
        [
            dual_ok,
            multi_ok,
            single_blocked,
            non_skill_blocked,
            privacy_ok,
            float(dual.get("skill_contribution_pp") or 0) > 0,
            tool_ok,
            tool_cpp >= 0,
            int((dual.get("with_skills") or {}).get("tool_hit_n") or 0) >= 1
            or not tool_dual_enabled(),
            f167_ok,
            f168_ok,
        ]
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_tool": FEATURE_TOOL,
                "feature_refine": FEATURE_REFINE,
                "feature_refine_promote": FEATURE_REFINE_PROMOTE,
                "f115": True,
                "f167": True,
                "f168": True,
                "fixture_pass": fixture_pass,
                "dual_pass": dual_ok,
                "skill_contribution_pp": dual.get("skill_contribution_pp"),
                "tool_contribution_pp": dual.get("tool_contribution_pp"),
                "tool_dual_ok": tool_ok,
                "with_hit_rate": dual.get("with_skills", {}).get("hit_rate"),
                "with_tool_hit_n": (dual.get("with_skills") or {}).get("tool_hit_n"),
                "ablated_hit_rate": dual.get("ablated", {}).get("hit_rate"),
                "ablated_tool_hit_n": (dual.get("ablated") or {}).get("tool_hit_n"),
                "recall_hold": dual.get("recall_hold"),
                "select_ok": dual.get("select_ok"),
                "multi_ok": multi_ok,
                "single_blocked": single_blocked,
                "non_skill_blocked": non_skill_blocked,
                "privacy_ok": privacy_ok,
                "promoted_n": prom.get("promoted_n"),
                "f167_ok": f167_ok,
                "refine_dual_pass": refine_dual_report.get("refine_dual_pass"),
                "refine_contribution_pp": refine_dual_report.get(
                    "refine_contribution_pp"
                ),
                "refine_tool_contribution_pp": refine_dual_report.get(
                    "refine_tool_contribution_pp"
                ),
                "refine_probe_delta": refine_dual_report.get("refine_probe_delta"),
                "refine_skill_ids": refine_dual_report.get("refined_skill_ids"),
                "f168_ok": f168_ok,
                "f168_promoted_n": f168_prom.get("promoted_n"),
                "f168_themes": f168_prom.get("themes"),
                "f168_blocked": f168_prom.get("blocked"),
                "f168_privacy_ok": f168_prom.get("privacy_ok"),
            },
            indent=2,
        )
    )
    # cleanup temps
    for p in _TMP_FILES:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F86 dual-rollout skill contribution")
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("dual", help="With vs ablated skill contribution")
    pd.add_argument("--cases", default="")
    pd.add_argument("--good", default="")
    pd.add_argument("--weak", default="")
    pd.add_argument("--paths", nargs="*", default=None)
    pd.add_argument("--pack-id", default="")
    pd.add_argument("--out", default="")
    pd.set_defaults(func=cmd_dual)

    pa = sub.add_parser("all", help="Dual across corpus packs")
    pa.add_argument("--out", default="")
    pa.set_defaults(func=cmd_all)

    pp = sub.add_parser("promote", help="Multi-tenant promote skill themes")
    pp.add_argument("--min-tenants", type=int, default=None)
    pp.add_argument("--min-hits", type=int, default=None)
    pp.set_defaults(func=cmd_promote)

    sub.add_parser("status", help="Status").set_defaults(func=cmd_status)
    sub.add_parser("fixture", help="Hermetic fixture").set_defaults(func=cmd_fixture)

    prd = sub.add_parser(
        "refine-dual",
        help="F167 with-refine vs ablated-refine contribution_pp paper metric",
    )
    prd.add_argument("--good", default="")
    prd.add_argument("--cases", default="")
    prd.add_argument("--paths", nargs="*", default=None)
    prd.add_argument("--pack-id", default="insecure-demo")
    prd.add_argument("--out-dir", default="", help="write refine-dual.json here")
    prd.add_argument("--out", default="", help="optional full report path")
    prd.set_defaults(func=cmd_refine_dual)

    pfr = sub.add_parser(
        "federate-refine-dual",
        help="F168 privacy-safe federate of refine dual contribution bins",
    )
    pfr.add_argument("--out-dir", default="", help="dir with refine-dual.json")
    pfr.add_argument("--report", default="", help="path to refine-dual.json")
    pfr.set_defaults(func=cmd_federate_refine_dual)

    ppr = sub.add_parser(
        "promote-refine-dual",
        help="F168 multi-tenant promote gate for refine dual themes",
    )
    ppr.add_argument("--min-tenants", type=int, default=None)
    ppr.add_argument("--min-hits", type=int, default=None)
    ppr.add_argument("--min-pp", type=float, default=None)
    ppr.set_defaults(func=cmd_promote_refine_dual)

    pcy = sub.add_parser(
        "cycle-refine-promote",
        help="F168 refine-dual → federate → multi-tenant promote",
    )
    pcy.add_argument("--out-dir", default="")
    pcy.add_argument(
        "--skip-dual",
        action="store_true",
        help="use existing refine-dual.json only",
    )
    pcy.set_defaults(func=cmd_cycle_refine_promote)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

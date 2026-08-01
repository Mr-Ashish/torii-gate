#!/usr/bin/env python3
"""F97/F147: Letta/MemGPT-style core · archival · recall memory tiers (tools-as-code).

Research drivers (patterns only — no vendored Letta runtime):
  - MemGPT / Letta: OS hierarchy — core (always-in-context RAM) vs archival
    (cold/searchable) vs recall (paged history)
  - Torii F75 flat budget dump treated path-matched and stale theme-only equal
    once they entered the top-N lists
  - F94 effective_score + F96 promoted strength already measure "how hot" a fact is
  - F146 archival reconsolidation stamps last_retrieved_at / reconsolidated_at
  - Without tier promotion, reconsolidated cold TPs stay archival until path match

Product thesis:
  Highest ROI context control: **deterministic tier assignment** so inject always
  prioritizes core (path-matched / high-effective / **recently reconsolidated** /
  run-scope) and only fills remaining budget from archival (low-effective theme
  noise stays cold). F147 compounds F146 retrieval warm into core inject slots.

Tiers:
  core      — path match > 0 OR effective ≥ floor OR recon-warm OR scope=run OR path FP
  archival  — remaining TP/FP/federated (searchable via store; sparse inject)
  recall    — optional run-distill / MEMORY.md pointers (count-only by default)

Commands:
  classify  — label scored items from store+paths
  inject    — produce tiered prompt section (or dry JSON)
  fixture   — hermetic: path core + recon-warm core + noise archival
  status    — env floors / last counts

Env:
  TORII_ROOT
  TORII_MEMORY_TIERS           1 (default) | 0
  TORII_MEMORY_CORE_FLOOR      default 0.55 (effective_score)
  TORII_MEMORY_CORE_MAX        default 6
  TORII_MEMORY_ARCHIVAL_MAX    default 4
  TORII_MEMORY_RECALL_MAX      default 2
  TORII_MEMORY_RECON_CORE      1 (default) | 0  — F147 recon-warm → core
  TORII_MEMORY_RECON_CORE_HOURS  default 168 (7d window for last_retrieved_at)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

FEATURE = "F97"
FEATURE_RECON_CORE = "F147"
SCHEMA = 1
MARKER = "<!-- torii-f97-memory-tiers -->"
TIERS = ("core", "archival", "recall")

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_MEMORY_TIERS") or "1").strip().lower()
    return raw not in _FALSEY


def _float_env(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def core_floor() -> float:
    return max(0.0, min(1.0, _float_env("TORII_MEMORY_CORE_FLOOR", 0.55)))


def core_max() -> int:
    return _int_env("TORII_MEMORY_CORE_MAX", 6)


def archival_max() -> int:
    return _int_env("TORII_MEMORY_ARCHIVAL_MAX", 4)


def recall_max() -> int:
    return _int_env("TORII_MEMORY_RECALL_MAX", 2)


def recon_core_enabled() -> bool:
    """F147: promote recently reconsolidated / retrieved items into core."""
    raw = (os.environ.get("TORII_MEMORY_RECON_CORE") or "1").strip().lower()
    return raw not in _FALSEY


def recon_core_hours() -> float:
    raw = (os.environ.get("TORII_MEMORY_RECON_CORE_HOURS") or "168").strip()
    try:
        return max(1.0, min(24.0 * 30, float(raw)))
    except ValueError:
        return 168.0


def _eff(item: dict[str, Any]) -> float:
    for k in ("effective_score", "effective"):
        if item.get(k) is not None:
            try:
                return max(0.0, min(1.0, float(item[k])))
            except (TypeError, ValueError):
                pass
    return 0.0


def _path_match(item: dict[str, Any]) -> float:
    try:
        return float(item.get("path_match") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parse_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def recon_warm_meta(
    item: dict[str, Any],
    *,
    as_of: datetime | None = None,
    hours: float | None = None,
) -> dict[str, Any]:
    """F147: whether item is warm from F146 reconsolidation / last retrieve."""
    out: dict[str, Any] = {
        "warm": False,
        "reason": "",
        "age_h": None,
        "feature": FEATURE_RECON_CORE,
    }
    if not recon_core_enabled():
        out["reason"] = "recon_core_off"
        return out
    # never promote superseded / inactive
    if item.get("active") is False or item.get("superseded_by"):
        out["reason"] = "superseded"
        return out
    if item.get("superseded") or item.get("tier_note") == "superseded":
        out["reason"] = "superseded"
        return out
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    window_h = hours if hours is not None else recon_core_hours()
    # explicit flag from reconsolidate_hits
    if item.get("reconsolidated") is True or str(
        item.get("reconsolidation_feature") or ""
    ).upper() in ("F146", FEATURE_RECON_CORE):
        # still require recency if timestamp present; else treat as warm
        ts = _parse_ts(item.get("last_retrieved_at") or item.get("reconsolidated_at"))
        if ts is None:
            out["warm"] = True
            out["reason"] = "recon_flag"
            return out
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_h = (now - ts).total_seconds() / 3600.0
        out["age_h"] = round(age_h, 3)
        if age_h <= window_h:
            out["warm"] = True
            out["reason"] = "recon_flag_fresh"
            return out
        out["reason"] = "recon_flag_stale"
        return out
    ts = _parse_ts(item.get("last_retrieved_at") or item.get("reconsolidated_at"))
    if ts is None:
        out["reason"] = "no_retrieve_ts"
        return out
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_h = (now - ts).total_seconds() / 3600.0
    out["age_h"] = round(age_h, 3)
    if age_h <= window_h:
        out["warm"] = True
        out["reason"] = "last_retrieved"
        return out
    out["reason"] = "retrieve_stale"
    return out


def is_recon_warm(item: dict[str, Any], **kwargs: Any) -> bool:
    return bool(recon_warm_meta(item, **kwargs).get("warm"))


def classify_item(item: dict[str, Any], *, floor: float | None = None) -> str:
    """Assign Letta-style tier for one scored memory item."""
    fl = floor if floor is not None else core_floor()
    kind = str(item.get("kind") or "")
    scope = str(item.get("scope") or "")
    pm = _path_match(item)
    eff = _eff(item)
    hits = int(item.get("hits") or 1)

    # Recall: explicit distill / MEMORY pointers
    if kind in ("recall", "distill", "episode") or item.get("tier") == "recall":
        return "recall"
    if scope == "run" and kind not in ("tp", "fp") and pm <= 0 and eff < fl:
        return "recall"

    # Core: hot path evidence or strong effective memory
    if pm > 0:
        return "core"
    if scope == "run" and kind in ("tp", "fp"):
        return "core"
    if eff >= fl:
        return "core"
    # path-anchored FP always core (prevent re-raise)
    if kind == "fp" and (item.get("path") or ""):
        return "core"
    # F147: recently reconsolidated / retrieved cold TPs promote to core
    if is_recon_warm(item):
        return "core"
    # very high hits with some effective still archival if no path (noise)
    if hits >= 15 and eff < fl * 0.5:
        return "archival"
    return "archival"


def tier_partition(
    scored_items: list[dict[str, Any]],
    *,
    floor: float | None = None,
    c_max: int | None = None,
    a_max: int | None = None,
    r_max: int | None = None,
) -> dict[str, Any]:
    """Partition already-scored items into core/archival/recall with budgets."""
    fl = floor if floor is not None else core_floor()
    cm = c_max if c_max is not None else core_max()
    am = a_max if a_max is not None else archival_max()
    rm = r_max if r_max is not None else recall_max()

    labeled: list[dict[str, Any]] = []
    for it in scored_items:
        if not isinstance(it, dict):
            continue
        row = dict(it)
        warm = recon_warm_meta(row)
        row["recon_warm"] = bool(warm.get("warm"))
        if warm.get("warm"):
            row["recon_warm_reason"] = warm.get("reason")
            row["recon_warm_age_h"] = warm.get("age_h")
        tier = classify_item(row, floor=fl)
        row["tier"] = tier
        if tier == "core" and warm.get("warm") and not (
            _path_match(row) > 0 or _eff(row) >= fl
        ):
            row["tier_note"] = row.get("tier_note") or "recon_warm_core"
            row["tier_feature"] = FEATURE_RECON_CORE
        labeled.append(row)

    # sort within tier by score / path_match / effective / recon-warm recency
    def _key(x: dict[str, Any]) -> tuple:
        age = x.get("recon_warm_age_h")
        try:
            age_v = float(age) if age is not None else 1e9
        except (TypeError, ValueError):
            age_v = 1e9
        return (
            -float(x.get("score") or 0),
            -_path_match(x),
            -_eff(x),
            -int(bool(x.get("recon_warm"))),
            age_v,  # fresher first among recon-warm
            -int(x.get("hits") or 1),
        )

    core = sorted([x for x in labeled if x["tier"] == "core"], key=_key)[:cm]
    archival = sorted([x for x in labeled if x["tier"] == "archival"], key=_key)[:am]
    recall = sorted([x for x in labeled if x["tier"] == "recall"], key=_key)[:rm]

    # overflow core candidates become archival if budget left
    core_ids = {str(x.get("id")) for x in core}
    overflow = [
        x
        for x in labeled
        if x["tier"] == "core" and str(x.get("id")) not in core_ids
    ]
    for x in sorted(overflow, key=_key):
        if len(archival) >= am:
            break
        y = dict(x)
        y["tier"] = "archival"
        y["tier_note"] = "core_overflow"
        archival.append(y)

    recon_core_n = sum(1 for x in core if x.get("recon_warm"))
    return {
        "feature": FEATURE,
        "feature_recon_core": FEATURE_RECON_CORE if recon_core_enabled() else None,
        "schema": SCHEMA,
        "enabled": enabled(),
        "floor": fl,
        "recon_core": {
            "enabled": recon_core_enabled(),
            "hours": recon_core_hours(),
            "core_n": recon_core_n,
        },
        "budgets": {"core": cm, "archival": am, "recall": rm},
        "core": core,
        "archival": archival,
        "recall": recall,
        "counts": {
            "core": len(core),
            "archival": len(archival),
            "recall": len(recall),
            "labeled": len(labeled),
            "recon_warm_core": recon_core_n,
        },
        "metrics": {
            "core_path_matched": sum(1 for x in core if _path_match(x) > 0),
            "core_high_eff": sum(1 for x in core if _eff(x) >= fl),
            "core_recon_warm": recon_core_n,
            "archival_low_eff": sum(1 for x in archival if _eff(x) < fl),
        },
        "scored_at": _now(),
    }


def apply_to_recall_result(result: dict[str, Any]) -> dict[str, Any]:
    """Attach tiers to an F75 recall() result (mutates copy)."""
    if not enabled():
        result = dict(result)
        result["tiers_enabled"] = False
        return result
    flat: list[dict[str, Any]] = []
    for bucket in ("tp", "fp", "federated"):
        for it in result.get(bucket) or []:
            if isinstance(it, dict):
                flat.append(dict(it))
    # optional recall bucket already present
    for it in result.get("recall") or []:
        if isinstance(it, dict):
            row = dict(it)
            row.setdefault("kind", "recall")
            flat.append(row)
    part = tier_partition(flat)
    out = dict(result)
    out["feature_tiers"] = FEATURE
    out["tiers_enabled"] = True
    out["tiers"] = {
        "core": part["core"],
        "archival": part["archival"],
        "recall": part["recall"],
        "budgets": part["budgets"],
        "floor": part["floor"],
        "counts": part["counts"],
        "metrics": part["metrics"],
    }
    # annotate original lists with tier
    by_id = {}
    for tname in ("core", "archival", "recall"):
        for it in part[tname]:
            by_id[str(it.get("id"))] = it.get("tier")
    for bucket in ("tp", "fp", "federated"):
        rows = []
        for it in out.get(bucket) or []:
            if isinstance(it, dict):
                r = dict(it)
                r["tier"] = by_id.get(str(r.get("id")), classify_item(r))
                rows.append(r)
        out[bucket] = rows
    m = dict(out.get("metrics") or {})
    m.update(
        {
            "core_n": part["counts"]["core"],
            "archival_n": part["counts"]["archival"],
            "recall_n": part["counts"]["recall"],
            "tiers_feature": FEATURE,
        }
    )
    out["metrics"] = m
    return out


def render_tiers_section(part_or_result: dict[str, Any]) -> str:
    """Markdown for prompt inject — core always listed before archival."""
    tiers = part_or_result.get("tiers") or part_or_result
    core = tiers.get("core") or []
    archival = tiers.get("archival") or []
    recall = tiers.get("recall") or []
    floor = tiers.get("floor", core_floor())
    budgets = tiers.get("budgets") or {}
    recon = tiers.get("recon_core") or part_or_result.get("recon_core") or {}
    recon_n = int(
        (tiers.get("counts") or {}).get("recon_warm_core")
        or recon.get("core_n")
        or sum(1 for x in core if x.get("recon_warm"))
    )
    title = (
        "## Memory tiers (F97/F147 — Letta core/archival + recon-warm promote)"
        if recon_core_enabled() or recon_n > 0
        else "## Memory tiers (F97 — Letta-style core / archival)"
    )
    lines = [
        MARKER,
        title,
        "",
        "OS-inspired hierarchy (deterministic, no LLM paging):",
        f"- **Core** (always attend): path-matched, effective ≥ {floor}, or "
        f"**F146 recon-warm** (F147) — budget {budgets.get('core', core_max())}",
        f"- **Archival** (cold): low-effective / theme-only — budget {budgets.get('archival', archival_max())}",
        "- Prefer **core** findings; do not promote archival themes to blocking without new path evidence.",
        "",
    ]
    if recon_n > 0 or recon_core_enabled():
        hrs = recon.get("hours") if recon.get("hours") is not None else recon_core_hours()
        lines.append(
            f"**F147 recon-warm → core:** {recon_n} item(s) promoted from recent "
            f"archival retrieve (window={hrs}h)."
        )
        lines.append("")
    if core:
        lines.append("### Core memory (hot)")
        for s in core:
            kind = s.get("kind") or "?"
            eff = s.get("effective_score")
            eff_s = f"{float(eff):.2f}" if eff is not None else "—"
            pm = s.get("path_match", 0)
            note = ""
            if s.get("recon_warm"):
                note = " · recon_warm"
            elif s.get("tier_note"):
                note = f" · {s.get('tier_note')}"
            lines.append(
                f"- [{kind}] `{s.get('raw_id') or s.get('id') or s.get('theme')}` "
                f"theme={s.get('theme')} path_match={pm} eff={eff_s} "
                f"hits={s.get('hits')} scope={s.get('scope')}{note}"
            )
        lines.append("")
    else:
        lines.extend(["### Core memory (hot)", "", "_No core items for this PR path set._", ""])

    if archival:
        lines.append("### Archival memory (cold — sparse)")
        for s in archival:
            kind = s.get("kind") or "?"
            eff = s.get("effective_score")
            eff_s = f"{float(eff):.2f}" if eff is not None else "—"
            note = s.get("tier_note") or ""
            lines.append(
                f"- [{kind}] `{s.get('theme') or s.get('id')}` eff={eff_s} "
                f"hits={s.get('hits')}{(' · ' + note) if note else ''}"
            )
        lines.append("")
    if recall:
        lines.append("### Recall pointers")
        for s in recall:
            lines.append(f"- {s.get('theme') or s.get('id') or s.get('preview', '')}")
        lines.append("")
    lines.append("<!-- /torii-f97-memory-tiers -->")
    return "\n".join(lines) + "\n"


def cmd_classify(args: argparse.Namespace) -> int:
    items = json.loads(Path(args.items).read_text(encoding="utf-8"))
    if isinstance(items, dict):
        flat = []
        for k in ("tp", "fp", "federated", "items", "signals"):
            flat.extend(items.get(k) or [])
        items = flat
    part = tier_partition([x for x in items if isinstance(x, dict)])
    print(json.dumps(part, indent=2))
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.recall_json).read_text(encoding="utf-8"))
    enriched = apply_to_recall_result(data)
    section = render_tiers_section(enriched)
    if args.out:
        Path(args.out).write_text(section, encoding="utf-8")
    if args.prompt and Path(args.prompt).is_file():
        p = Path(args.prompt)
        text = p.read_text(encoding="utf-8")
        if MARKER in text:
            text = re.sub(
                r"<!-- torii-f97-memory-tiers -->.*?<!-- /torii-f97-memory-tiers -->\n?",
                section,
                text,
                count=1,
                flags=re.S,
            )
        else:
            text = text.rstrip() + "\n\n" + section
        p.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "counts": (enriched.get("tiers") or {}).get("counts"),
                "metrics": (enriched.get("tiers") or {}).get("metrics"),
                "prompt": args.prompt or None,
            },
            indent=2,
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Core gets path-matched + recon-warm; archival gets high-hit low-eff noise."""
    now = datetime.now(timezone.utc)
    fresh = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    stale = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = [
        {
            "id": "sqli-path",
            "kind": "tp",
            "theme": "sql_injection",
            "scope": "repo",
            "path_match": 1.0,
            "score": 0.9,
            "hits": 3,
            "effective_score": 0.5,
            "keywords": ["sqli"],
        },
        {
            "id": "cmdi-hot",
            "kind": "tp",
            "theme": "command_injection",
            "scope": "repo",
            "path_match": 0.0,
            "score": 0.4,
            "hits": 2,
            "effective_score": 0.88,
            "keywords": ["shell"],
        },
        {
            "id": "xss-noise",
            "kind": "tp",
            "theme": "xss",
            "scope": "global",
            "path_match": 0.0,
            "score": 0.2,
            "hits": 20,
            "effective_score": 0.1,
            "keywords": ["innerhtml"],
        },
        {
            "id": "fed-weak",
            "kind": "federated",
            "theme": "info_disclosure",
            "scope": "global",
            "path_match": 0.0,
            "score": 0.15,
            "hits": 12,
            "effective_score": 0.12,
        },
        {
            "id": "fp-path",
            "kind": "fp",
            "theme": "sql_injection",
            "scope": "repo",
            "path": "app.py",
            "path_match": 0.8,
            "score": 0.7,
            "hits": 1,
        },
        # F147: cold low-eff but recently reconsolidated → core
        {
            "id": "pickle-recon",
            "kind": "tp",
            "theme": "insecure_deserialization",
            "scope": "repo",
            "path_match": 0.0,
            "score": 0.35,
            "hits": 5,
            "effective_score": 0.38,  # below floor 0.55
            "last_retrieved_at": fresh,
            "reconsolidated_at": fresh,
            "reconsolidation_feature": "F146",
        },
        # F147: stale retrieve stays archival
        {
            "id": "old-recon",
            "kind": "tp",
            "theme": "path_traversal",
            "scope": "repo",
            "path_match": 0.0,
            "score": 0.3,
            "hits": 4,
            "effective_score": 0.2,
            "last_retrieved_at": stale,
            "reconsolidation_feature": "F146",
        },
        # superseded never promotes
        {
            "id": "dead-recon",
            "kind": "tp",
            "theme": "weak_crypto",
            "scope": "repo",
            "path_match": 0.0,
            "score": 0.5,
            "hits": 6,
            "effective_score": 0.2,
            "last_retrieved_at": fresh,
            "superseded_by": "fp-crypto",
            "active": False,
        },
    ]
    # baseline without recon-core: pickle-recon would be archival
    old_env = os.environ.get("TORII_MEMORY_RECON_CORE")
    try:
        os.environ["TORII_MEMORY_RECON_CORE"] = "0"
        cold = tier_partition(items, floor=0.55, c_max=8, a_max=6)
        cold_ids = {x["id"] for x in cold["core"]}
        cold_pickle_arch = "pickle-recon" not in cold_ids

        os.environ["TORII_MEMORY_RECON_CORE"] = "1"
        os.environ["TORII_MEMORY_RECON_CORE_HOURS"] = "168"
        part = tier_partition(items, floor=0.55, c_max=8, a_max=6)
    finally:
        if old_env is None:
            os.environ.pop("TORII_MEMORY_RECON_CORE", None)
        else:
            os.environ["TORII_MEMORY_RECON_CORE"] = old_env

    core_ids = {x["id"] for x in part["core"]}
    arch_ids = {x["id"] for x in part["archival"]}
    core_has_path = "sqli-path" in core_ids and "fp-path" in core_ids
    core_has_hot = "cmdi-hot" in core_ids
    noise_archival = "xss-noise" in arch_ids and "fed-weak" in arch_ids
    noise_not_core = "xss-noise" not in core_ids
    recon_core = "pickle-recon" in core_ids
    stale_not_core = "old-recon" not in core_ids and "dead-recon" not in core_ids
    recon_metric = int((part.get("metrics") or {}).get("core_recon_warm") or 0) >= 1
    # render non-empty
    section = render_tiers_section(part)
    render_ok = (
        "Core memory" in section
        and "Archival memory" in section
        and MARKER in section
        and ("F147" in section or "recon-warm" in section.lower() or "recon_warm" in section)
    )
    f147_ok = recon_core and stale_not_core and cold_pickle_arch and recon_metric and render_ok
    fixture_pass = all(
        [
            core_has_path,
            core_has_hot,
            noise_archival,
            noise_not_core,
            render_ok,
            f147_ok,
        ]
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_recon_core": FEATURE_RECON_CORE,
                "f147": True,
                "fixture_pass": fixture_pass,
                "f147_ok": f147_ok,
                "core_ids": sorted(core_ids),
                "archival_ids": sorted(arch_ids),
                "core_has_path": core_has_path,
                "core_has_hot": core_has_hot,
                "noise_archival": noise_archival,
                "noise_not_core": noise_not_core,
                "recon_warm_core": recon_core,
                "stale_not_core": stale_not_core,
                "cold_without_f147": cold_pickle_arch,
                "render_ok": render_ok,
                "counts": part["counts"],
                "metrics": part["metrics"],
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def cmd_status(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_recon_core": FEATURE_RECON_CORE,
                "enabled": enabled(),
                "core_floor": core_floor(),
                "core_max": core_max(),
                "archival_max": archival_max(),
                "recall_max": recall_max(),
                "recon_core_enabled": recon_core_enabled(),
                "recon_core_hours": recon_core_hours(),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F97 Letta-style memory tiers")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("classify", help="Partition scored items JSON")
    pc.add_argument("--items", required=True)
    pc.set_defaults(func=cmd_classify)

    pi = sub.add_parser("inject", help="Tier section from F75 recall JSON")
    pi.add_argument("--recall-json", required=True)
    pi.add_argument("--prompt", default="")
    pi.add_argument("--out", default="")
    pi.set_defaults(func=cmd_inject)

    sub.add_parser("fixture", help="Hermetic core/archival fixture").set_defaults(
        func=cmd_fixture
    )
    sub.add_parser("status").set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

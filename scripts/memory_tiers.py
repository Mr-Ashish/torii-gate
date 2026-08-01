#!/usr/bin/env python3
"""F97: Letta/MemGPT-style core · archival · recall memory tiers (tools-as-code).

Research drivers (patterns only — no vendored Letta runtime):
  - MemGPT / Letta: OS hierarchy — core (always-in-context RAM) vs archival
    (cold/searchable) vs recall (paged history)
  - Torii F75 flat budget dump treated path-matched and stale theme-only equal
    once they entered the top-N lists
  - F94 effective_score + F96 promoted strength already measure "how hot" a fact is

Product thesis:
  Highest ROI context control: **deterministic tier assignment** so inject always
  prioritizes core (path-matched / high-effective / run-scope) and only fills
  remaining budget from archival (low-effective theme noise stays cold).

Tiers:
  core      — path match > 0 OR effective ≥ floor OR scope=run OR high-hit path FP
  archival  — remaining TP/FP/federated (searchable via store; sparse inject)
  recall    — optional run-distill / MEMORY.md pointers (count-only by default)

Commands:
  classify  — label scored items from store+paths
  inject    — produce tiered prompt section (or dry JSON)
  fixture   — hermetic: core has path-matched, archival has weak high-hit noise
  status    — env floors / last counts

Env:
  TORII_ROOT
  TORII_MEMORY_TIERS           1 (default) | 0
  TORII_MEMORY_CORE_FLOOR      default 0.55 (effective_score)
  TORII_MEMORY_CORE_MAX        default 6
  TORII_MEMORY_ARCHIVAL_MAX    default 4
  TORII_MEMORY_RECALL_MAX      default 2
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

FEATURE = "F97"
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
        tier = classify_item(row, floor=fl)
        row["tier"] = tier
        labeled.append(row)

    # sort within tier by score / path_match / effective
    def _key(x: dict[str, Any]) -> tuple:
        return (
            -float(x.get("score") or 0),
            -_path_match(x),
            -_eff(x),
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

    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "enabled": enabled(),
        "floor": fl,
        "budgets": {"core": cm, "archival": am, "recall": rm},
        "core": core,
        "archival": archival,
        "recall": recall,
        "counts": {
            "core": len(core),
            "archival": len(archival),
            "recall": len(recall),
            "labeled": len(labeled),
        },
        "metrics": {
            "core_path_matched": sum(1 for x in core if _path_match(x) > 0),
            "core_high_eff": sum(1 for x in core if _eff(x) >= fl),
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
    lines = [
        MARKER,
        "## Memory tiers (F97 — Letta-style core / archival)",
        "",
        "OS-inspired hierarchy (deterministic, no LLM paging):",
        f"- **Core** (always attend): path-matched or effective ≥ {floor} — budget {budgets.get('core', core_max())}",
        f"- **Archival** (cold): low-effective / theme-only — budget {budgets.get('archival', archival_max())}",
        "- Prefer **core** findings; do not promote archival themes to blocking without new path evidence.",
        "",
    ]
    if core:
        lines.append("### Core memory (hot)")
        for s in core:
            kind = s.get("kind") or "?"
            eff = s.get("effective_score")
            eff_s = f"{float(eff):.2f}" if eff is not None else "—"
            pm = s.get("path_match", 0)
            lines.append(
                f"- [{kind}] `{s.get('raw_id') or s.get('id') or s.get('theme')}` "
                f"theme={s.get('theme')} path_match={pm} eff={eff_s} "
                f"hits={s.get('hits')} scope={s.get('scope')}"
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
    """Core gets path-matched; archival gets high-hit low-eff noise."""
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
    ]
    part = tier_partition(items, floor=0.55, c_max=6, a_max=4)
    core_ids = {x["id"] for x in part["core"]}
    arch_ids = {x["id"] for x in part["archival"]}
    core_has_path = "sqli-path" in core_ids and "fp-path" in core_ids
    core_has_hot = "cmdi-hot" in core_ids
    noise_archival = "xss-noise" in arch_ids and "fed-weak" in arch_ids
    noise_not_core = "xss-noise" not in core_ids
    # render non-empty
    section = render_tiers_section(part)
    render_ok = "Core memory" in section and "Archival memory" in section and MARKER in section
    fixture_pass = all(
        [core_has_path, core_has_hot, noise_archival, noise_not_core, render_ok]
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fixture_pass": fixture_pass,
                "core_ids": sorted(core_ids),
                "archival_ids": sorted(arch_ids),
                "core_has_path": core_has_path,
                "core_has_hot": core_has_hot,
                "noise_archival": noise_archival,
                "noise_not_core": noise_not_core,
                "render_ok": render_ok,
                "counts": part["counts"],
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
                "enabled": enabled(),
                "core_floor": core_floor(),
                "core_max": core_max(),
                "archival_max": archival_max(),
                "recall_max": recall_max(),
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

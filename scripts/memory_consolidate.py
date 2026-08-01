#!/usr/bin/env python3
"""F94: Memory consolidation — importance · merge · decay · eviction (tools-as-code).

Research drivers (patterns only — no vendored Mem0/Zep runtime):
  - Hindsight/Vectorize 2026: four-lever consolidation (importance, merge, decay, eviction)
  - Mem0: write-time ADD/UPDATE/DELETE (Torii F93) + LLM consolidation; we stay deterministic
  - Zep: temporal edge strength / staleness as first-class; age-weighted retrieval
  - Mem0 LOCOMO / state-of-memory 2026: high-hit stale facts are the hard problem —
    decay alone is weak; combine with importance + merge + eviction

Product thesis:
  F93 events keep writes clean; without consolidation the TP/FP stores still bloat with
  near-duplicates and stale low-value themes that crowd F75 scoped recall. Highest ROI:
  **deterministic maintenance pass** that scores importance, merges near-dup themes,
  applies half-life decay, and evicts dead items — then feeds effective_score into recall.

Commands:
  plan         — dry-run merge + decay + evict ops (no write)
  apply        — apply a plan JSON to a store file
  run          — plan+apply on TP (and optional FP) stores
  score        — print importance/decay/effective for each item
  federate     — F95: emit privacy-safe theme signals with effective_score → hub
  inject       — budgeted prompt note of top effective memories (optional)
  fixture      — hermetic merge + decay rank + eviction
  status       — store summary with consolidation meta

Env:
  TORII_ROOT
  TORII_MEMORY_CONSOLIDATE     1 (default) | 0
  TORII_MEMORY_HALF_LIFE_DAYS  default 30
  TORII_MEMORY_EVICT_THRESHOLD default 0.12
  TORII_MEMORY_MERGE_JACCARD   default 0.45
  TORII_TP_SIGNATURES_FILE / TORII_FP_RULES_FILE
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F94"
SCHEMA = 1
MARKER = "<!-- torii-f94-memory-consolidate -->"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def enabled() -> bool:
    raw = (os.environ.get("TORII_MEMORY_CONSOLIDATE") or "1").strip().lower()
    return raw not in _FALSEY


def _float_env(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def half_life_days() -> float:
    return max(1.0, _float_env("TORII_MEMORY_HALF_LIFE_DAYS", 30.0))


def evict_threshold() -> float:
    return max(0.0, min(1.0, _float_env("TORII_MEMORY_EVICT_THRESHOLD", 0.12)))


def merge_jaccard() -> float:
    return max(0.05, min(1.0, _float_env("TORII_MEMORY_MERGE_JACCARD", 0.45)))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("theme") or "unknown")[:96]


def _theme(item: dict[str, Any]) -> str:
    return _norm(str(item.get("theme") or item.get("id") or ""))


def _keywords(item: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for k in item.get("keywords") or []:
        nk = _norm(str(k))
        if nk:
            out.add(nk)
    return out


def _paths(item: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for k in ("path_globs", "paths", "path"):
        v = item.get(k)
        if isinstance(v, str) and v:
            out.add(_norm(v))
            out.add(_norm(Path(v).name))
        elif isinstance(v, list):
            for x in v:
                xs = str(x)
                out.add(_norm(xs))
                out.add(_norm(Path(xs).name))
    return {p for p in out if p}


def _parse_ts(raw: Any) -> datetime | None:
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # accept Z and offset-less
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError:
        return None


def item_age_days(item: dict[str, Any], now: datetime | None = None) -> float:
    now = now or _now_dt()
    for key in ("last_seen", "updated_at", "promoted_at", "created_at"):
        dt = _parse_ts(item.get(key))
        if dt is not None:
            return max(0.0, (now - dt).total_seconds() / 86400.0)
    # no timestamp: treat as moderately aged if hits==1 (stale-looking), else fresh
    hits = int(item.get("hits") or 1)
    if hits <= 1 and item.get("stale_days") is not None:
        try:
            return max(0.0, float(item["stale_days"]))
        except (TypeError, ValueError):
            pass
    return 0.0


def decay_weight(item: dict[str, Any], *, now: datetime | None = None, half_life: float | None = None) -> float:
    """Exponential half-life decay in [~0, 1]."""
    hl = half_life if half_life is not None else half_life_days()
    age = item_age_days(item, now)
    if age <= 0:
        return 1.0
    return float(0.5 ** (age / hl))


def importance_score(item: dict[str, Any]) -> float:
    """0-1 importance from hits, path specificity, keywords, CWE."""
    if item.get("deleted") or item.get("evicted"):
        return 0.0
    hits = max(1, int(item.get("hits") or 1))
    hits_w = min(1.0, math.log1p(hits) / math.log1p(20))
    path_w = 1.0 if _paths(item) else 0.25
    kws = _keywords(item)
    kw_w = min(1.0, len(kws) / 8.0)
    cwe = item.get("cwe") or []
    if isinstance(cwe, str):
        cwe = [cwe]
    cwe_w = 0.15 if cwe else 0.0
    # path-anchored FP / TP slightly preferred
    score = 0.50 * hits_w + 0.30 * path_w + 0.15 * kw_w + cwe_w
    # explicit override
    if item.get("importance") is not None:
        try:
            score = max(score, min(1.0, float(item["importance"])))
        except (TypeError, ValueError):
            pass
    return max(0.0, min(1.0, score))


def effective_score(item: dict[str, Any], *, now: datetime | None = None, half_life: float | None = None) -> float:
    return importance_score(item) * decay_weight(item, now=now, half_life=half_life)


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_store(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": SCHEMA, "feature": FEATURE, "items": [], "history": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": SCHEMA, "feature": FEATURE, "items": [], "history": []}
    if not isinstance(data, dict):
        return {"schema_version": SCHEMA, "feature": FEATURE, "items": [], "history": []}
    items = data.get("items")
    if items is None:
        items = data.get("signatures") or data.get("patterns") or data.get("rules") or []
    data["items"] = list(items) if isinstance(items, list) else []
    data.setdefault("history", [])
    data.setdefault("consolidation_history", [])
    return data


def save_store(path: Path, store: dict[str, Any], *, kind: str = "tp") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    items = [i for i in (store.get("items") or []) if not i.get("deleted") and not i.get("evicted")]
    doc: dict[str, Any] = {
        "schema_version": int(store.get("schema_version") or SCHEMA),
        "feature": store.get("feature") or ("F70" if kind == "tp" else "F64"),
        "memory_consolidate_feature": FEATURE,
        "updated_at": _now(),
        "count": len(items),
        "consolidation": store.get("last_consolidation") or {},
    }
    if kind == "tp":
        doc["signatures"] = items
    elif kind == "fp":
        # fp-rules often use "rules"
        if any("path" in (i or {}) and "theme" not in (i or {}) for i in items):
            doc["rules"] = items
        else:
            doc["patterns"] = items
    else:
        doc["items"] = items
    doc["consolidation_history"] = (store.get("consolidation_history") or [])[-40:]
    # keep evicted for audit under optional key (slim: last 20)
    evicted = [
        i
        for i in (store.get("items") or [])
        if i.get("evicted") or (i.get("deleted") and i.get("event") == "EVICT")
    ]
    if evicted:
        doc["evicted_audit"] = evicted[-20:]
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def default_tp_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_TP_SIGNATURES_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / "tp-signatures.json"


def default_fp_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_FP_RULES_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / "fp-rules.json"


def plan_consolidation(
    items: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    half_life: float | None = None,
    jacc_thresh: float | None = None,
    evict_thr: float | None = None,
) -> dict[str, Any]:
    """Plan MERGE / DECAY-annotate / EVICT ops. Does not mutate input."""
    now = now or _now_dt()
    hl = half_life if half_life is not None else half_life_days()
    jt = jacc_thresh if jacc_thresh is not None else merge_jaccard()
    et = evict_thr if evict_thr is not None else evict_threshold()

    active = [deepcopy(i) for i in items if not i.get("deleted") and not i.get("evicted")]
    ops: list[dict[str, Any]] = []

    # annotate scores first
    scored: list[tuple[float, dict[str, Any]]] = []
    for it in active:
        eff = effective_score(it, now=now, half_life=hl)
        imp = importance_score(it)
        dec = decay_weight(it, now=now, half_life=hl)
        scored.append((eff, it))
        ops.append(
            {
                "op": "ANNOTATE",
                "id": _id(it),
                "importance": round(imp, 4),
                "decay_weight": round(dec, 4),
                "effective": round(eff, 4),
                "age_days": round(item_age_days(it, now), 2),
            }
        )

    # MERGE near-duplicates: same theme + high keyword jaccard (or identical paths)
    by_theme: dict[str, list[dict[str, Any]]] = {}
    for _, it in scored:
        by_theme.setdefault(_theme(it) or _id(it), []).append(it)

    merged_away: set[str] = set()
    for theme, group in by_theme.items():
        if len(group) < 2 or not theme:
            continue
        # sort keeper = highest effective
        group_sorted = sorted(
            group,
            key=lambda x: (
                effective_score(x, now=now, half_life=hl),
                int(x.get("hits") or 1),
                len(_paths(x)),
            ),
            reverse=True,
        )
        keeper = group_sorted[0]
        for cand in group_sorted[1:]:
            if _id(cand) in merged_away or _id(keeper) in merged_away:
                continue
            j = jaccard(_keywords(keeper), _keywords(cand))
            path_overlap = bool(_paths(keeper) & _paths(cand)) or (not _paths(cand))
            same_id = _id(keeper) == _id(cand)
            if same_id or (j >= jt and path_overlap) or (j >= jt + 0.15):
                ops.append(
                    {
                        "op": "MERGE",
                        "keep_id": _id(keeper),
                        "drop_id": _id(cand),
                        "theme": theme,
                        "jaccard": round(j, 4),
                        "reason": "near_duplicate_theme",
                    }
                )
                merged_away.add(_id(cand))
                # simulate hits on keeper for later eviction
                keeper["hits"] = int(keeper.get("hits") or 1) + int(cand.get("hits") or 1)
                keeper["keywords"] = list(
                    dict.fromkeys(list(keeper.get("keywords") or []) + list(cand.get("keywords") or []))
                )[:16]
                if cand.get("path_globs"):
                    keeper["path_globs"] = list(
                        dict.fromkeys(
                            list(keeper.get("path_globs") or []) + list(cand.get("path_globs") or [])
                        )
                    )[:12]

    # EVICT low effective after decay (never evict high-hit recent)
    for it in active:
        iid = _id(it)
        if iid in merged_away:
            continue
        eff = effective_score(it, now=now, half_life=hl)
        age = item_age_days(it, now)
        hits = int(it.get("hits") or 1)
        # protect path-rich high-hit items
        if hits >= 5 and _paths(it) and age < hl * 2:
            continue
        if eff < et and (age >= hl * 0.5 or hits <= 1):
            ops.append(
                {
                    "op": "EVICT",
                    "id": iid,
                    "effective": round(eff, 4),
                    "importance": round(importance_score(it), 4),
                    "decay_weight": round(decay_weight(it, now=now, half_life=hl), 4),
                    "age_days": round(age, 2),
                    "reason": "below_threshold_after_decay",
                }
            )

    counts = {"ANNOTATE": 0, "MERGE": 0, "EVICT": 0}
    for o in ops:
        counts[o["op"]] = counts.get(o["op"], 0) + 1

    return {
        "feature": FEATURE,
        "half_life_days": hl,
        "evict_threshold": et,
        "merge_jaccard": jt,
        "ops": ops,
        "counts": counts,
        "active_before": len(active),
        "merged_away": sorted(merged_away),
        "planned_at": _now(),
    }


def apply_plan(store: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Apply consolidation plan to store items."""
    items = list(store.get("items") or [])
    by_id: dict[str, dict[str, Any]] = {}
    for i in items:
        by_id[_id(i)] = i

    hist = list(store.get("consolidation_history") or [])
    merge_n = 0
    evict_n = 0
    annotate_n = 0

    # first annotations
    for op in plan.get("ops") or []:
        if op.get("op") != "ANNOTATE":
            continue
        cur = by_id.get(str(op.get("id") or ""))
        if not cur:
            continue
        cur["importance_score"] = op.get("importance")
        cur["decay_weight"] = op.get("decay_weight")
        cur["effective_score"] = op.get("effective")
        cur["age_days"] = op.get("age_days")
        cur["last_consolidated_at"] = _now()
        annotate_n += 1

    for op in plan.get("ops") or []:
        if op.get("op") != "MERGE":
            continue
        keep = by_id.get(str(op.get("keep_id") or ""))
        drop = by_id.get(str(op.get("drop_id") or ""))
        if not keep or not drop:
            continue
        keep["hits"] = int(keep.get("hits") or 1) + int(drop.get("hits") or 1)
        keep["keywords"] = list(
            dict.fromkeys(list(keep.get("keywords") or []) + list(drop.get("keywords") or []))
        )[:16]
        if drop.get("path_globs"):
            keep["path_globs"] = list(
                dict.fromkeys(
                    list(keep.get("path_globs") or []) + list(drop.get("path_globs") or [])
                )
            )[:12]
        if drop.get("cwe"):
            keep["cwe"] = list(
                dict.fromkeys(list(keep.get("cwe") or []) + list(drop.get("cwe") or []))
            )[:8]
        keep["updated_at"] = _now()
        keep["merged_from"] = list(
            dict.fromkeys(list(keep.get("merged_from") or []) + [_id(drop)])
        )[:12]
        # recompute scores after merge
        keep["importance_score"] = round(importance_score(keep), 4)
        keep["decay_weight"] = round(decay_weight(keep), 4)
        keep["effective_score"] = round(effective_score(keep), 4)
        drop["deleted"] = True
        drop["evicted"] = True
        drop["event"] = "MERGE"
        drop["merged_into"] = _id(keep)
        drop["deleted_at"] = _now()
        merge_n += 1

    for op in plan.get("ops") or []:
        if op.get("op") != "EVICT":
            continue
        cur = by_id.get(str(op.get("id") or ""))
        if not cur or cur.get("deleted"):
            continue
        cur["deleted"] = True
        cur["evicted"] = True
        cur["event"] = "EVICT"
        cur["evict_reason"] = op.get("reason")
        cur["deleted_at"] = _now()
        cur["effective_score"] = op.get("effective")
        evict_n += 1

    meta = {
        "feature": FEATURE,
        "at": _now(),
        "annotate": annotate_n,
        "merge": merge_n,
        "evict": evict_n,
        "half_life_days": plan.get("half_life_days"),
        "evict_threshold": plan.get("evict_threshold"),
    }
    hist.append(meta)
    store["items"] = items
    store["consolidation_history"] = hist[-50:]
    store["last_consolidation"] = meta
    store["updated_at"] = _now()
    return store


def consolidate_items(
    items: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """In-memory consolidate list → active items with scores (for merge_tp soft wire)."""
    if not enabled():
        return items
    store = {"items": [deepcopy(i) for i in items if isinstance(i, dict)], "history": []}
    plan = plan_consolidation(store["items"], now=now)
    store = apply_plan(store, plan)
    return [i for i in store["items"] if not i.get("deleted") and not i.get("evicted")]


def cmd_plan(args: argparse.Namespace) -> int:
    path = Path(args.store) if args.store else default_tp_path()
    store = load_store(path)
    plan = plan_consolidation(store.get("items") or [])
    plan["store"] = str(path)
    print(json.dumps(plan, indent=2))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    path = Path(args.store) if args.store else default_tp_path()
    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    store = load_store(path)
    store = apply_plan(store, plan)
    kind = args.kind
    save_store(path, store, kind=kind)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "store": str(path),
                "last_consolidation": store.get("last_consolidation"),
                "active": sum(
                    1 for i in store.get("items") or [] if not i.get("deleted") and not i.get("evicted")
                ),
            },
            indent=2,
        )
    )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "enabled": False, "skipped": True}))
        return 0
    root = _root()
    results = []
    targets: list[tuple[Path, str]] = []
    if args.kind in ("tp", "both"):
        targets.append((Path(args.store) if args.store else default_tp_path(root), "tp"))
    if args.kind in ("fp", "both"):
        targets.append((default_fp_path(root), "fp"))

    for path, kind in targets:
        store = load_store(path)
        before = sum(1 for i in store.get("items") or [] if not i.get("deleted") and not i.get("evicted"))
        if before == 0 and not path.is_file():
            results.append({"kind": kind, "store": str(path), "skipped": "missing", "active_before": 0})
            continue
        plan = plan_consolidation(store.get("items") or [])
        if args.dry_run:
            results.append({"kind": kind, "store": str(path), "dry_run": True, "plan": plan})
            continue
        store = apply_plan(store, plan)
        save_store(path, store, kind=kind)
        after = sum(1 for i in store.get("items") or [] if not i.get("deleted") and not i.get("evicted"))
        results.append(
            {
                "kind": kind,
                "store": str(path),
                "active_before": before,
                "active_after": after,
                "counts": plan.get("counts"),
                "last_consolidation": store.get("last_consolidation"),
            }
        )
    print(json.dumps({"feature": FEATURE, "enabled": True, "results": results}, indent=2))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    path = Path(args.store) if args.store else default_tp_path()
    store = load_store(path)
    now = _now_dt()
    rows = []
    for it in store.get("items") or []:
        if it.get("deleted") and not args.include_deleted:
            continue
        rows.append(
            {
                "id": _id(it),
                "theme": _theme(it),
                "hits": int(it.get("hits") or 1),
                "importance": round(importance_score(it), 4),
                "decay_weight": round(decay_weight(it, now=now), 4),
                "effective": round(effective_score(it, now=now), 4),
                "age_days": round(item_age_days(it, now), 2),
                "deleted": bool(it.get("deleted")),
                "evicted": bool(it.get("evicted")),
            }
        )
    rows.sort(key=lambda r: -r["effective"])
    print(json.dumps({"feature": FEATURE, "store": str(path), "items": rows}, indent=2))
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    path = Path(args.store) if args.store else default_tp_path()
    store = load_store(path)
    now = _now_dt()
    active = [
        i for i in (store.get("items") or []) if not i.get("deleted") and not i.get("evicted")
    ]
    ranked = sorted(active, key=lambda i: effective_score(i, now=now), reverse=True)[: args.limit]
    lines = [
        MARKER,
        "## Memory consolidation (F94 — importance · decay · merge)",
        "",
        "Prefer **high effective_score** memories (importance × half-life decay). "
        "Stale low-hit themes may have been evicted; do not re-raise without path evidence.",
        "",
    ]
    if not ranked:
        lines.append("_No active consolidated memories._")
    for it in ranked:
        lines.append(
            f"- `{_id(it)}` theme={_theme(it)} hits={it.get('hits')} "
            f"importance={importance_score(it):.2f} decay={decay_weight(it, now=now):.2f} "
            f"effective={effective_score(it, now=now):.2f}"
        )
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


def export_federated_signals(
    items: list[dict[str, Any]],
    *,
    tenant: str = "",
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """F95: privacy-safe signals carrying effective_score (no paths/snippets)."""
    now = now or _now_dt()
    out: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict) or it.get("deleted") or it.get("evicted"):
            continue
        theme = _theme(it)
        if not theme:
            continue
        # basenames only — never full paths
        bases: list[str] = []
        for p in it.get("path_globs") or []:
            name = Path(str(p)).name
            if name and "/" not in name:
                bases.append(name[:64])
        bases = list(dict.fromkeys(bases))[:6]
        imp = importance_score(it)
        dec = decay_weight(it, now=now)
        eff = effective_score(it, now=now)
        sig: dict[str, Any] = {
            "id": re.sub(r"[^a-z0-9._-]+", "-", _id(it).lower())[:64] or theme,
            "theme": theme,
            "keywords": list(it.get("keywords") or [])[:12],
            "cwe": list(it.get("cwe") or [])[:8] if isinstance(it.get("cwe"), list) else [],
            "path_basenames": bases,
            "hits": max(1, int(it.get("hits") or 1)),
            "importance_score": round(imp, 4),
            "decay_weight": round(dec, 4),
            "effective_score": round(eff, 4),
            "source": "f94_consolidate",
            "tags": ["memory_effective", "f95"],
        }
        if tenant:
            sig["tenant"] = tenant  # stripped by federated sanitize → tenant_hash
        out.append(sig)
    return out


def cmd_federate(args: argparse.Namespace) -> int:
    """Export consolidated TP effective scores into F77 hub (privacy-safe)."""
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "enabled": False, "skipped": True}))
        return 0
    root = _root()
    path = Path(args.store) if args.store else default_tp_path(root)
    store = load_store(path)
    items = [i for i in (store.get("items") or []) if not i.get("deleted") and not i.get("evicted")]
    # ensure scores present
    now = _now_dt()
    for it in items:
        it.setdefault("importance_score", round(importance_score(it), 4))
        it.setdefault("decay_weight", round(decay_weight(it, now=now), 4))
        it.setdefault("effective_score", round(effective_score(it, now=now), 4))
    signals = export_federated_signals(items, tenant=args.tenant or "", now=now)
    result: dict[str, Any] = {
        "feature": "F95",
        "source_feature": FEATURE,
        "store": str(path),
        "signal_count": len(signals),
        "top": [
            {
                "theme": s.get("theme"),
                "effective_score": s.get("effective_score"),
                "hits": s.get("hits"),
            }
            for s in sorted(signals, key=lambda x: -float(x.get("effective_score") or 0))[:8]
        ],
    }
    if args.dry_run or not signals:
        result["dry_run"] = bool(args.dry_run) or not signals
        print(json.dumps(result, indent=2))
        return 0
    # soft ingest via federated_hub_ingest
    try:
        import importlib.util

        fed_path = Path(__file__).resolve().parent / "federated_hub_ingest.py"
        if fed_path.is_file():
            spec = importlib.util.spec_from_file_location("federated_hub_ingest", fed_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["federated_hub_ingest"] = mod
                spec.loader.exec_module(mod)
                if mod.enabled():
                    hub_root = Path(args.hub_root).resolve() if args.hub_root else root
                    tenant = args.tenant or os.environ.get("TORII_MEMORY_TENANT") or ""
                    ing = mod.ingest(
                        hub_root,
                        signals,
                        tenant=tenant,
                        source_repo=args.repo or "",
                        write_tenant=bool(tenant),
                    )
                    result["ingest"] = {
                        "global_count": ing.get("global_count"),
                        "privacy_ok": ing.get("privacy_ok"),
                        "global_path": ing.get("global_path"),
                        "top_themes": ing.get("top_themes"),
                    }
                    result["privacy_ok"] = ing.get("privacy_ok")
    except Exception as exc:
        result["ingest_error"] = str(exc)[:200]
    print(json.dumps(result, indent=2))
    return 0 if result.get("privacy_ok", True) else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    tp = load_store(default_tp_path(root))
    fp = load_store(default_fp_path(root))

    def _summ(store: dict[str, Any]) -> dict[str, Any]:
        items = store.get("items") or []
        active = [i for i in items if not i.get("deleted") and not i.get("evicted")]
        return {
            "active": len(active),
            "evicted": sum(1 for i in items if i.get("evicted")),
            "last": store.get("last_consolidation"),
        }

    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "half_life_days": half_life_days(),
                "evict_threshold": evict_threshold(),
                "merge_jaccard": merge_jaccard(),
                "tp": _summ(tp),
                "fp": _summ(fp),
            },
            indent=2,
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: merge near-dups, decay ranks stale below fresh, evict ancient low-hit."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        store_path = td_path / "tp-signatures.json"
        # fixed "now" via stale_days field for determinism
        items = [
            {
                "id": "sqli-v1",
                "theme": "sql_injection",
                "kind": "tp",
                "keywords": ["sql injection", "sqli", "f-string"],
                "path_globs": ["app.py"],
                "hits": 3,
                "cwe": ["CWE-89"],
                "created_at": "2026-07-28T00:00:00Z",
                "last_seen": "2026-07-31T12:00:00Z",
            },
            {
                "id": "sqli-v2",
                "theme": "sql_injection",
                "kind": "tp",
                "keywords": ["sql injection", "sqli", "cursor.execute"],
                "path_globs": ["app.py", "db.py"],
                "hits": 2,
                "created_at": "2026-07-29T00:00:00Z",
                "last_seen": "2026-07-31T18:00:00Z",
            },
            {
                "id": "xss-stale",
                "theme": "xss",
                "kind": "tp",
                "keywords": ["innerhtml"],
                "path_globs": [],
                "hits": 1,
                # ~90 days old with half_life=30 → decay ~0.125
                "created_at": "2026-05-01T00:00:00Z",
                "last_seen": "2026-05-01T00:00:00Z",
            },
            {
                "id": "cmdi-fresh",
                "theme": "command_injection",
                "kind": "tp",
                "keywords": ["shell=true", "subprocess"],
                "path_globs": ["runner.py"],
                "hits": 4,
                "cwe": ["CWE-78"],
                "created_at": "2026-07-31T00:00:00Z",
                "last_seen": "2026-08-01T01:00:00Z",
            },
            {
                "id": "noise-ancient",
                "theme": "info_disclosure",
                "kind": "tp",
                "keywords": ["debug"],
                "hits": 1,
                "created_at": "2026-01-01T00:00:00Z",
                "last_seen": "2026-01-01T00:00:00Z",
            },
        ]
        store = {"items": items, "history": []}
        # pin half-life via env for fixture
        os.environ["TORII_MEMORY_HALF_LIFE_DAYS"] = "30"
        os.environ["TORII_MEMORY_EVICT_THRESHOLD"] = "0.12"
        os.environ["TORII_MEMORY_MERGE_JACCARD"] = "0.40"
        os.environ["TORII_MEMORY_CONSOLIDATE"] = "1"

        now = datetime(2026, 8, 1, 2, 0, 0, tzinfo=timezone.utc)
        plan = plan_consolidation(store["items"], now=now)
        store = apply_plan(store, plan)
        save_store(store_path, store, kind="tp")

        active = [i for i in store["items"] if not i.get("deleted") and not i.get("evicted")]
        active_ids = {_id(i) for i in active}
        merge_ops = [o for o in plan["ops"] if o["op"] == "MERGE"]
        evict_ops = [o for o in plan["ops"] if o["op"] == "EVICT"]

        merge_ok = len(merge_ops) >= 1 and (
            ("sqli-v1" in active_ids) ^ ("sqli-v2" in active_ids)
            or (
                # one kept
                sum(1 for i in ("sqli-v1", "sqli-v2") if i in active_ids) == 1
            )
        )
        # both shouldn't remain active after merge
        merge_ok = merge_ok and not ({"sqli-v1", "sqli-v2"} <= active_ids)

        # decay: cmdi-fresh effective > xss-stale effective (if still active)
        cmdi = next((i for i in store["items"] if _id(i) == "cmdi-fresh"), None)
        xss = next((i for i in store["items"] if _id(i) == "xss-stale"), None)
        decay_rank_ok = False
        if cmdi:
            ce = effective_score(cmdi, now=now)
            if xss and not xss.get("evicted"):
                decay_rank_ok = ce > effective_score(xss, now=now)
            else:
                # xss already evicted → decay worked via eviction path
                decay_rank_ok = True
            decay_rank_ok = decay_rank_ok and ce > 0.3

        # noise-ancient should be evicted
        noise = next((i for i in store["items"] if _id(i) == "noise-ancient"), None)
        evict_ok = bool(noise and (noise.get("evicted") or noise.get("deleted")))
        # or in evict ops
        evict_ok = evict_ok or any(o.get("id") == "noise-ancient" for o in evict_ops)

        # annotate present on kept items
        annotate_ok = any(
            i.get("importance_score") is not None for i in active
        )

        # scores command path
        scores = [
            {
                "id": _id(i),
                "effective": effective_score(i, now=now),
            }
            for i in active
        ]
        scores.sort(key=lambda x: -x["effective"])
        top_is_strong = scores and scores[0]["id"] in ("cmdi-fresh", "sqli-v1", "sqli-v2")

        fixture_pass = all([merge_ok, decay_rank_ok, evict_ok, annotate_ok, top_is_strong])
        out = {
            "feature": FEATURE,
            "fixture_pass": fixture_pass,
            "merge_ok": merge_ok,
            "decay_rank_ok": decay_rank_ok,
            "evict_ok": evict_ok,
            "annotate_ok": annotate_ok,
            "top_is_strong": top_is_strong,
            "merge_ops": len(merge_ops),
            "evict_ops": len(evict_ops),
            "active_ids": sorted(active_ids),
            "counts": plan.get("counts"),
            "store": str(store_path),
        }
        print(json.dumps(out, indent=2))
        return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F94 memory consolidation (importance/merge/decay/evict)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("plan", help="Plan consolidation ops")
    pp.add_argument("--store", default="")
    pp.set_defaults(func=cmd_plan)

    pa = sub.add_parser("apply", help="Apply plan JSON to store")
    pa.add_argument("--store", default="")
    pa.add_argument("--plan", required=True)
    pa.add_argument("--kind", default="tp", choices=["tp", "fp"])
    pa.set_defaults(func=cmd_apply)

    pr = sub.add_parser("run", help="Plan+apply on TP/FP stores")
    pr.add_argument("--store", default="")
    pr.add_argument("--kind", default="tp", choices=["tp", "fp", "both"])
    pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--force", action="store_true", help="run even if disabled")
    pr.set_defaults(func=cmd_run)

    ps = sub.add_parser("score", help="Score items")
    ps.add_argument("--store", default="")
    ps.add_argument("--include-deleted", action="store_true")
    ps.set_defaults(func=cmd_score)

    pi = sub.add_parser("inject", help="Prompt section of top effective memories")
    pi.add_argument("--store", default="")
    pi.add_argument("--limit", type=int, default=8)
    pi.add_argument("--out", default="")
    pi.set_defaults(func=cmd_inject)

    pfed = sub.add_parser("federate", help="F95 export effective scores to hub federation")
    pfed.add_argument("--store", default="")
    pfed.add_argument("--tenant", default="")
    pfed.add_argument("--repo", default="")
    pfed.add_argument("--hub-root", default="")
    pfed.add_argument("--dry-run", action="store_true")
    pfed.add_argument("--force", action="store_true")
    pfed.set_defaults(func=cmd_federate)

    pf = sub.add_parser("fixture", help="Hermetic consolidation fixture")
    pf.set_defaults(func=cmd_fixture)

    pst = sub.add_parser("status", help="Store consolidation status")
    pst.set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

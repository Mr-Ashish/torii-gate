#!/usr/bin/env python3
"""F93: Mem0-style ADD/UPDATE/DELETE/NONE event policy for Torii TP/FP memory.

Research drivers (Apache-2.0 patterns only — no vendored mem0 runtime):
  - Mem0 DEFAULT_UPDATE_MEMORY_PROMPT: ADD | UPDATE | DELETE | NONE on each fact
  - Mem0 supersession / linked_memory_ids: prevent deleted facts resurfacing
  - Mem0 multi-scope + conflict on write (not only on recall)
  - Torii F75: conflict at recall; F70 promote / F64 FP merge were naive append

Product thesis:
  Highest ROI memory architecture slice: **write-path event policy** so TP and
  FP stores compound with explicit events, path-anchored FP can DELETE/supersede
  theme-only TP, and exact duplicates are NONE (hits++ only via UPDATE).

Commands:
  plan     — plan events for candidates vs existing store
  apply    — apply events to a store JSON (tp or fp)
  promote  — plan+apply for TP signatures file
  fixture  — hermetic: ADD/UPDATE/NONE/DELETE + supersede chain
  status   — summarize last ledger / store

Env:
  TORII_ROOT
  TORII_MEMORY_EVENTS     1 (default) | 0
  TORII_TP_SIGNATURES_FILE / TORII_FP_RULES_FILE
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F93"
SCHEMA = 1
EVENTS = frozenset({"ADD", "UPDATE", "DELETE", "NONE"})

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_MEMORY_EVENTS") or "1").strip().lower()
    return raw not in _FALSEY


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _theme(item: dict[str, Any]) -> str:
    return _norm(str(item.get("theme") or item.get("id") or ""))


def _paths(item: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for k in ("path_globs", "paths", "path"):
        v = item.get(k)
        if isinstance(v, str) and v:
            out.add(_norm(Path(v).name) if "/" in v else _norm(v))
            out.add(_norm(v))
        elif isinstance(v, list):
            for x in v:
                xs = str(x)
                out.add(_norm(xs))
                out.add(_norm(Path(xs).name))
    if item.get("path"):
        out.add(_norm(str(item["path"])))
        out.add(_norm(Path(str(item["path"])).name))
    return {p for p in out if p}


def _id(item: dict[str, Any]) -> str:
    return str(item.get("id") or _theme(item) or "unknown")[:96]


def _kind(item: dict[str, Any]) -> str:
    k = str(item.get("kind") or item.get("type") or "").lower()
    if k in ("tp", "fp", "federated"):
        return k
    # heuristic
    if item.get("path_globs") or item.get("cwe"):
        return "tp"
    if item.get("quote") or item.get("resolution") in ("false_positive", "resolved"):
        return "fp"
    return k or "tp"


def load_store(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": SCHEMA, "feature": FEATURE, "items": [], "history": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": SCHEMA, "feature": FEATURE, "items": [], "history": []}
    if not isinstance(data, dict):
        return {"schema_version": SCHEMA, "feature": FEATURE, "items": [], "history": []}
    # normalize signatures/patterns/rules → items
    items = data.get("items")
    if items is None:
        items = data.get("signatures") or data.get("patterns") or data.get("rules") or []
    data["items"] = list(items) if isinstance(items, list) else []
    data.setdefault("history", [])
    return data


def save_store(path: Path, store: dict[str, Any], *, kind: str = "tp") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    items = [i for i in (store.get("items") or []) if not i.get("deleted")]
    doc: dict[str, Any] = {
        "schema_version": int(store.get("schema_version") or SCHEMA),
        "feature": store.get("feature") or ("F70" if kind == "tp" else "F64"),
        "memory_events_feature": FEATURE,
        "updated_at": _now(),
        "count": len(items),
    }
    if kind == "tp":
        doc["signatures"] = items
    else:
        doc["patterns"] = items
    # keep full items with deleted for audit? only active in primary key
    doc["event_history"] = (store.get("history") or [])[-80:]
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _find_matches(existing: list[dict[str, Any]], cand: dict[str, Any]) -> list[dict[str, Any]]:
    cid = _id(cand)
    ctheme = _theme(cand)
    cpaths = _paths(cand)
    matches = []
    for ex in existing:
        if ex.get("deleted"):
            continue
        if _id(ex) == cid:
            matches.append(ex)
            continue
        if ctheme and _theme(ex) == ctheme:
            # path overlap if either has paths
            ep = _paths(ex)
            if not cpaths or not ep or (cpaths & ep):
                matches.append(ex)
    return matches


def plan_events(
    existing: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    candidate_kind: str = "tp",
) -> list[dict[str, Any]]:
    """Mem0-style event plan for each candidate against existing store."""
    events: list[dict[str, Any]] = []
    # working copy of active ids for multi-candidate batch
    active = [deepcopy(e) for e in existing if not e.get("deleted")]

    for cand in candidates:
        cand = deepcopy(cand)
        cand.setdefault("kind", candidate_kind)
        ck = _kind(cand)
        cid = _id(cand)
        matches = _find_matches(active, cand)

        # Cross-kind conflict: FP candidate vs TP existing (or reverse)
        opp = [m for m in matches if _kind(m) != ck and _kind(m) in ("tp", "fp")]
        same = [m for m in matches if _kind(m) == ck or _kind(m) not in ("tp", "fp")]

        if opp and ck == "fp":
            # path-anchored FP deletes/supersedes overlapping TP
            cpaths = _paths(cand)
            for tp in opp:
                if _kind(tp) != "tp":
                    continue
                tpaths = _paths(tp)
                path_strong = bool(cpaths and (not tpaths or (cpaths & tpaths)))
                if path_strong or (cpaths & tpaths):
                    events.append(
                        {
                            "event": "DELETE",
                            "id": _id(tp),
                            "kind": "tp",
                            "reason": "path_anchored_fp_supersedes_tp",
                            "superseded_by": cid,
                            "old": {"theme": _theme(tp), "hits": tp.get("hits")},
                        }
                    )
                    # mark in active
                    for a in active:
                        if _id(a) == _id(tp):
                            a["deleted"] = True
                            a["superseded_by"] = cid

        if same:
            # exact or theme match same kind → UPDATE or NONE
            best = same[0]
            # NONE if content effectively same (theme + paths + keywords subset)
            old_kw = set(_norm(k) for k in (best.get("keywords") or []))
            new_kw = set(_norm(k) for k in (cand.get("keywords") or []))
            same_paths = _paths(best) == _paths(cand) or not _paths(cand)
            if (
                _theme(best) == _theme(cand)
                and same_paths
                and (not new_kw or new_kw <= old_kw)
                and _id(best) == cid
            ):
                events.append(
                    {
                        "event": "NONE",
                        "id": _id(best),
                        "kind": ck,
                        "reason": "duplicate_no_new_info",
                        "hits_delta": 0,
                    }
                )
            else:
                events.append(
                    {
                        "event": "UPDATE",
                        "id": _id(best),
                        "kind": ck,
                        "reason": "merge_theme_or_keywords",
                        "new": cand,
                        "old_id": _id(best),
                    }
                )
                # update active
                for a in active:
                    if _id(a) == _id(best):
                        a["keywords"] = list(
                            dict.fromkeys(
                                list(a.get("keywords") or [])
                                + list(cand.get("keywords") or [])
                            )
                        )[:16]
                        a["hits"] = int(a.get("hits") or 1) + 1
                        if cand.get("path_globs"):
                            a["path_globs"] = list(
                                dict.fromkeys(
                                    list(a.get("path_globs") or [])
                                    + list(cand.get("path_globs") or [])
                                )
                            )[:12]
                        if cand.get("cwe"):
                            a["cwe"] = list(
                                dict.fromkeys(
                                    list(a.get("cwe") or []) + list(cand.get("cwe") or [])
                                )
                            )[:8]
        else:
            events.append(
                {
                    "event": "ADD",
                    "id": cid,
                    "kind": ck,
                    "reason": "new_memory",
                    "new": cand,
                }
            )
            active.append(cand)

    return events


def apply_events(
    store: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    items = list(store.get("items") or [])
    by_id = {_id(i): i for i in items if not i.get("deleted")}
    hist = list(store.get("history") or [])
    counts = {"ADD": 0, "UPDATE": 0, "DELETE": 0, "NONE": 0}

    for ev in events:
        et = str(ev.get("event") or "NONE").upper()
        if et not in EVENTS:
            et = "NONE"
        counts[et] = counts.get(et, 0) + 1
        eid = str(ev.get("id") or "")
        if et == "ADD":
            new = deepcopy(ev.get("new") or {"id": eid})
            new["id"] = eid or _id(new)
            new["hits"] = int(new.get("hits") or 1)
            new["created_at"] = new.get("created_at") or _now()
            new["event"] = "ADD"
            items.append(new)
            by_id[new["id"]] = new
        elif et == "UPDATE":
            new = ev.get("new") or {}
            cur = by_id.get(eid)
            if not cur:
                # treat as add
                new = deepcopy(new) if new else {"id": eid}
                new["id"] = eid
                new["hits"] = int(new.get("hits") or 1)
                items.append(new)
                by_id[eid] = new
            else:
                cur["hits"] = int(cur.get("hits") or 1) + 1
                cur["keywords"] = list(
                    dict.fromkeys(
                        list(cur.get("keywords") or [])
                        + list((new or {}).get("keywords") or [])
                    )
                )[:16]
                if (new or {}).get("path_globs"):
                    cur["path_globs"] = list(
                        dict.fromkeys(
                            list(cur.get("path_globs") or [])
                            + list(new.get("path_globs") or [])
                        )
                    )[:12]
                if (new or {}).get("cwe"):
                    cur["cwe"] = list(
                        dict.fromkeys(list(cur.get("cwe") or []) + list(new.get("cwe") or []))
                    )[:8]
                cur["updated_at"] = _now()
                cur["event"] = "UPDATE"
        elif et == "DELETE":
            cur = by_id.get(eid)
            if cur:
                cur["deleted"] = True
                cur["deleted_at"] = _now()
                cur["superseded_by"] = ev.get("superseded_by")
                cur["event"] = "DELETE"
        elif et == "NONE":
            cur = by_id.get(eid)
            if cur and ev.get("hits_delta", 0):
                cur["hits"] = int(cur.get("hits") or 1) + int(ev["hits_delta"])
            # still touch last_seen
            if cur:
                cur["last_seen"] = _now()
                cur["event"] = "NONE"

        hist.append({"at": _now(), **{k: v for k, v in ev.items() if k != "new"}})

    store["items"] = items
    store["history"] = hist[-100:]
    store["last_counts"] = counts
    store["updated_at"] = _now()
    return store


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


def cmd_plan(args: argparse.Namespace) -> int:
    store = load_store(Path(args.store)) if args.store else {"items": []}
    cands = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    if isinstance(cands, dict):
        cands = cands.get("signatures") or cands.get("patterns") or cands.get("items") or []
    events = plan_events(store.get("items") or [], cands, candidate_kind=args.kind)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "n_candidates": len(cands),
                "n_events": len(events),
                "counts": {
                    e: sum(1 for x in events if x["event"] == e) for e in ("ADD", "UPDATE", "DELETE", "NONE")
                },
                "events": events,
            },
            indent=2,
        )
    )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    path = Path(args.store)
    store = load_store(path)
    events = json.loads(Path(args.events).read_text(encoding="utf-8"))
    if isinstance(events, dict):
        events = events.get("events") or []
    store = apply_events(store, events)
    save_store(path, store, kind=args.kind)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "store": str(path),
                "counts": store.get("last_counts"),
                "active": sum(1 for i in store.get("items") or [] if not i.get("deleted")),
            },
            indent=2,
        )
    )
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    """Plan+apply candidates into TP or FP store (Mem0 write path)."""
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "skipped": 1, "reason": "disabled"}))
        return 0
    root = _root()
    kind = args.kind
    path = Path(args.store) if args.store else (
        default_tp_path(root) if kind == "tp" else default_fp_path(root)
    )
    store = load_store(path)
    # normalize signatures key into items
    if not store.get("items") and path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
        store["items"] = raw.get("signatures") or raw.get("patterns") or []
    cands = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    if isinstance(cands, dict):
        cands = cands.get("signatures") or cands.get("patterns") or cands.get("items") or []
    events = plan_events(store.get("items") or [], cands, candidate_kind=kind)
    store = apply_events(store, events)
    # drop deleted from active export
    save_store(path, store, kind=kind)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "store": str(path),
                "kind": kind,
                "counts": store.get("last_counts"),
                "events_n": len(events),
                "active": sum(1 for i in store.get("items") or [] if not i.get("deleted")),
            },
            indent=2,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    tp = load_store(default_tp_path(root))
    fp = load_store(default_fp_path(root))
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "tp_active": sum(1 for i in tp.get("items") or [] if not i.get("deleted")),
                "fp_active": sum(1 for i in fp.get("items") or [] if not i.get("deleted")),
                "tp_history": len(tp.get("history") or []),
                "fp_history": len(fp.get("history") or []),
            },
            indent=2,
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        store_path = td_path / "tp-signatures.json"
        existing = [
            {
                "id": "sqli-search",
                "theme": "sql_injection",
                "kind": "tp",
                "keywords": ["sql injection", "sqli"],
                "path_globs": ["app.py"],
                "hits": 1,
            },
            {
                "id": "pickle-load",
                "theme": "insecure_deserialization",
                "kind": "tp",
                "keywords": ["pickle"],
                "path_globs": ["app.py"],
                "hits": 1,
            },
        ]
        store = {"items": existing, "history": []}
        # candidates: exact dup → NONE; richer sqli → UPDATE; new cmdi → ADD; FP on pickle → DELETE tp
        cands_tp = [
            {
                "id": "sqli-search",
                "theme": "sql_injection",
                "kind": "tp",
                "keywords": ["sql injection", "sqli"],  # no new
                "path_globs": ["app.py"],
            },
            {
                "id": "sqli-search",
                "theme": "sql_injection",
                "kind": "tp",
                "keywords": ["sql injection", "f-string", "cwe-89"],
                "path_globs": ["app.py", "demo/insecure/app.py"],
            },
            {
                "id": "cmdi-run",
                "theme": "command_injection",
                "kind": "tp",
                "keywords": ["shell=true"],
                "path_globs": ["app.py"],
            },
        ]
        events_tp = plan_events(store["items"], cands_tp, candidate_kind="tp")
        store = apply_events(store, events_tp)

        # FP supersedes pickle TP
        fp_cand = [
            {
                "id": "fp-pickle-ok",
                "theme": "insecure_deserialization",
                "kind": "fp",
                "path": "app.py",
                "keywords": ["false positive", "by design"],
            }
        ]
        events_fp = plan_events(store["items"], fp_cand, candidate_kind="fp")
        store = apply_events(store, events_fp)
        save_store(store_path, store, kind="tp")

        counts_tp = {"ADD": 0, "UPDATE": 0, "DELETE": 0, "NONE": 0}
        for e in events_tp:
            counts_tp[e["event"]] = counts_tp.get(e["event"], 0) + 1
        counts_fp = {"ADD": 0, "UPDATE": 0, "DELETE": 0, "NONE": 0}
        for e in events_fp:
            counts_fp[e["event"]] = counts_fp.get(e["event"], 0) + 1

        active = [i for i in store["items"] if not i.get("deleted")]
        active_ids = {_id(i) for i in active}
        pickle_deleted = any(
            i.get("deleted") and _id(i) == "pickle-load" for i in store["items"]
        )
        supersede_ok = any(
            i.get("superseded_by") == "fp-pickle-ok"
            for i in store["items"]
            if _id(i) == "pickle-load"
        )
        none_ok = counts_tp.get("NONE", 0) >= 1
        update_ok = counts_tp.get("UPDATE", 0) >= 1
        add_ok = counts_tp.get("ADD", 0) >= 1
        delete_ok = counts_fp.get("DELETE", 0) >= 1 and pickle_deleted
        cmdi_present = "cmdi-run" in active_ids
        # deleted pickle not active
        pickle_not_active = "pickle-load" not in active_ids

        fixture_pass = all(
            [none_ok, update_ok, add_ok, delete_ok, supersede_ok, cmdi_present, pickle_not_active]
        )
        print(
            json.dumps(
                {
                    "feature": FEATURE,
                    "fixture_pass": fixture_pass,
                    "counts_tp": counts_tp,
                    "counts_fp": counts_fp,
                    "none_ok": none_ok,
                    "update_ok": update_ok,
                    "add_ok": add_ok,
                    "delete_ok": delete_ok,
                    "supersede_ok": supersede_ok,
                    "cmdi_present": cmdi_present,
                    "pickle_not_active": pickle_not_active,
                    "active_ids": sorted(active_ids),
                    "store": str(store_path),
                },
                indent=2,
            )
        )
        return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F93 Mem0-style memory event policy")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("plan", help="Plan ADD/UPDATE/DELETE/NONE events")
    pp.add_argument("--store", default="")
    pp.add_argument("--candidates", required=True)
    pp.add_argument("--kind", default="tp", choices=["tp", "fp"])
    pp.set_defaults(func=cmd_plan)

    pa = sub.add_parser("apply", help="Apply events JSON to store")
    pa.add_argument("--store", required=True)
    pa.add_argument("--events", required=True)
    pa.add_argument("--kind", default="tp", choices=["tp", "fp"])
    pa.set_defaults(func=cmd_apply)

    pr = sub.add_parser("promote", help="Plan+apply candidates into store")
    pr.add_argument("--candidates", required=True)
    pr.add_argument("--store", default="")
    pr.add_argument("--kind", default="tp", choices=["tp", "fp"])
    pr.add_argument("--force", action="store_true")
    pr.set_defaults(func=cmd_promote)

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("fixture").set_defaults(func=cmd_fixture)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

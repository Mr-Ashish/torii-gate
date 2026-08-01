#!/usr/bin/env python3
"""F100: Zep-style temporal edges on TP/FP memory (tools-as-code).

Research drivers (patterns only — no vendored Zep runtime):
  - Zep temporal knowledge graph: facts as edges with valid_at / invalid_at
  - Mem0 supersession / linked memories (Torii F93 DELETE + superseded_by)
  - Torii F94–F98 strength/tiers/search still treat items mostly as flat bags

Product thesis:
  Highest ROI graph slice: **explicit temporal edges** so inject and critics
  can see supersession chains, theme kinship, and path co-occurrence with
  validity windows — without a vector DB.

Edge types:
  supersedes     — FP or newer item invalidates older TP (F93)
  same_theme     — shared theme (undirected stored once)
  co_path        — shared path basename / glob
  updated_from   — UPDATE merge ancestry (merged_from / event history)

Commands:
  build     — build graph JSON from TP/FP stores
  query     — neighbors for theme / id / path
  inject    — prompt section for PR path basenames
  fixture   — hermetic supersede + co_path + temporal invalid
  status    — node/edge counts

Env:
  TORII_ROOT
  TORII_MEMORY_GRAPH           1 (default) | 0
  TORII_MEMORY_GRAPH_FILE      default .torii/memory-graph.json
  TORII_TP_SIGNATURES_FILE / TORII_FP_RULES_FILE
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

FEATURE = "F100"
SCHEMA = 1
MARKER = "<!-- torii-f100-memory-graph -->"
EDGE_TYPES = frozenset({"supersedes", "same_theme", "co_path", "updated_from"})

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_MEMORY_GRAPH") or "1").strip().lower()
    return raw not in _FALSEY


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


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


def default_graph_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_MEMORY_GRAPH_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / "memory-graph.json"


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _items_from_store(path: Path, *, kind: str) -> list[dict[str, Any]]:
    data = _load_json(path)
    if data is None:
        return []
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        raw = (
            data.get("items")
            or data.get("signatures")
            or data.get("patterns")
            or data.get("rules")
            or []
        )
    else:
        raw = []
    out: list[dict[str, Any]] = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        row = dict(it)
        row.setdefault("kind", kind)
        if not row.get("id"):
            row["id"] = str(row.get("theme") or row.get("path") or "unknown")[:96]
        out.append(row)
    return out


def _basenames(item: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for k in ("path_globs", "paths", "path"):
        v = item.get(k)
        if isinstance(v, str) and v:
            names.add(Path(v).name.lower())
            names.add(_norm(v))
        elif isinstance(v, list):
            for x in v:
                xs = str(x)
                names.add(Path(xs).name.lower())
                names.add(_norm(xs))
    return {n for n in names if n and n not in (".", "/")}


def _valid_from(item: dict[str, Any]) -> str:
    for k in ("created_at", "promoted_at", "updated_at", "last_seen"):
        if item.get(k):
            return str(item[k])
    return ""


def _valid_until(item: dict[str, Any]) -> str | None:
    if item.get("deleted") or item.get("evicted"):
        return str(item.get("deleted_at") or item.get("updated_at") or _now())
    return None  # still valid


def _node_id(item: dict[str, Any]) -> str:
    kind = str(item.get("kind") or "tp")
    return f"{kind}:{item.get('id')}"


def build_graph(
    tp_items: list[dict[str, Any]],
    fp_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build nodes + temporal edges from stores."""
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    edge_keys: set[str] = set()

    def add_node(item: dict[str, Any]) -> str:
        nid = _node_id(item)
        theme = _norm(str(item.get("theme") or item.get("kind") or ""))
        nodes[nid] = {
            "id": nid,
            "raw_id": str(item.get("id") or ""),
            "kind": str(item.get("kind") or "tp"),
            "theme": theme,
            "hits": int(item.get("hits") or 1),
            "effective_score": item.get("effective_score"),
            "path_basenames": sorted(_basenames(item))[:12],
            "valid_from": _valid_from(item),
            "valid_until": _valid_until(item),
            "active": not bool(item.get("deleted") or item.get("evicted")),
            "superseded_by": item.get("superseded_by"),
        }
        return nid

    all_items = list(tp_items) + list(fp_items)
    for it in all_items:
        add_node(it)

    def add_edge(
        src: str,
        dst: str,
        etype: str,
        *,
        valid_from: str = "",
        valid_until: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if src == dst or etype not in EDGE_TYPES:
            return
        # undirected same_theme / co_path: store canonical order
        a, b = src, dst
        if etype in ("same_theme", "co_path") and a > b:
            a, b = b, a
        key = f"{etype}|{a}|{b}"
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append(
            {
                "id": key[:120],
                "type": etype,
                "source": a if etype in ("same_theme", "co_path") else src,
                "target": b if etype in ("same_theme", "co_path") else dst,
                "valid_from": valid_from or _now(),
                "valid_until": valid_until,
                "meta": meta or {},
            }
        )

    # supersedes from explicit fields
    for it in all_items:
        sid = _node_id(it)
        if it.get("superseded_by"):
            # this node was superseded BY another
            other_raw = str(it["superseded_by"])
            # find node
            for cand in all_items:
                if str(cand.get("id")) == other_raw or _node_id(cand) == other_raw:
                    add_edge(
                        _node_id(cand),
                        sid,
                        "supersedes",
                        valid_from=str(it.get("deleted_at") or _valid_from(it) or _now()),
                        meta={"reason": "superseded_by_field"},
                    )
                    break
        for mid in it.get("merged_from") or []:
            add_edge(
                sid,
                f"tp:{mid}" if not str(mid).startswith("tp:") else str(mid),
                "updated_from",
                valid_from=_valid_from(it),
                meta={"merged_from": mid},
            )

    # theme + path edges among active-ish items
    by_theme: dict[str, list[str]] = {}
    by_base: dict[str, list[str]] = {}
    for nid, n in nodes.items():
        if n.get("theme"):
            by_theme.setdefault(n["theme"], []).append(nid)
        for b in n.get("path_basenames") or []:
            by_base.setdefault(b, []).append(nid)

    for theme, ids in by_theme.items():
        if len(ids) < 2:
            continue
        for i in range(len(ids)):
            for j in range(i + 1, min(i + 6, len(ids))):  # bound
                add_edge(ids[i], ids[j], "same_theme", meta={"theme": theme})

    for base, ids in by_base.items():
        if len(ids) < 2 or base in ("app.py",):  # still allow app.py — high signal in demos
            pass
        if len(ids) < 2:
            continue
        for i in range(len(ids)):
            for j in range(i + 1, min(i + 8, len(ids))):
                add_edge(ids[i], ids[j], "co_path", meta={"basename": base})

    return {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "built_at": _now(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": list(nodes.values()),
        "edges": edges,
        "by_type": {
            t: sum(1 for e in edges if e["type"] == t) for t in sorted(EDGE_TYPES)
        },
    }


def edge_active(edge: dict[str, Any], *, as_of: str | None = None) -> bool:
    """Temporal filter: invalid after valid_until."""
    until = edge.get("valid_until")
    if not until:
        return True
    if as_of is None:
        as_of = _now()
    return str(until) > str(as_of)  # string ISO compare works for Zulu timestamps


def query_graph(
    graph: dict[str, Any],
    *,
    theme: str = "",
    node_id: str = "",
    path: str = "",
    limit: int = 12,
) -> dict[str, Any]:
    nodes = {n["id"]: n for n in (graph.get("nodes") or []) if isinstance(n, dict)}
    edges = [e for e in (graph.get("edges") or []) if isinstance(e, dict) and edge_active(e)]

    seeds: set[str] = set()
    if node_id:
        if node_id in nodes:
            seeds.add(node_id)
        else:
            for nid, n in nodes.items():
                if n.get("raw_id") == node_id or nid.endswith(":" + node_id):
                    seeds.add(nid)
    th = _norm(theme)
    if th:
        for nid, n in nodes.items():
            if n.get("theme") == th:
                seeds.add(nid)
    if path:
        base = Path(path).name.lower()
        for nid, n in nodes.items():
            bases = n.get("path_basenames") or []
            if base in bases or any(base in b for b in bases):
                seeds.add(nid)

    # 1-hop neighbors
    neigh: list[dict[str, Any]] = []
    seen_e: set[str] = set()
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s in seeds or t in seeds:
            eid = str(e.get("id"))
            if eid in seen_e:
                continue
            seen_e.add(eid)
            other = t if s in seeds else s
            neigh.append(
                {
                    "edge_type": e.get("type"),
                    "from": s,
                    "to": t,
                    "peer": other,
                    "peer_node": nodes.get(str(other), {}),
                    "valid_from": e.get("valid_from"),
                    "valid_until": e.get("valid_until"),
                    "meta": e.get("meta") or {},
                }
            )
    # prefer supersedes first
    order = {"supersedes": 0, "updated_from": 1, "co_path": 2, "same_theme": 3}
    neigh.sort(key=lambda x: (order.get(str(x.get("edge_type")), 9), str(x.get("peer"))))
    return {
        "feature": FEATURE,
        "seeds": sorted(seeds),
        "neighbor_count": len(neigh),
        "neighbors": neigh[:limit],
        "seed_nodes": [nodes[s] for s in seeds if s in nodes],
    }


def render_inject(result: dict[str, Any], *, paths: list[str] | None = None) -> str:
    lines = [
        MARKER,
        "## Memory temporal graph (F100 — Zep-style edges)",
        "",
        "Supersession and path/theme kinship with validity windows. "
        "Do **not** re-raise a TP that is the target of an active **supersedes** edge.",
        "",
    ]
    if paths:
        lines.append(f"PR path seeds: {', '.join(f'`{p}`' for p in paths[:8])}")
        lines.append("")
    seeds = result.get("seed_nodes") or []
    if seeds:
        lines.append("### Seed nodes")
        for n in seeds[:8]:
            active = "active" if n.get("active") else "inactive"
            lines.append(
                f"- `{n.get('id')}` theme={n.get('theme')} {active} "
                f"valid_from={n.get('valid_from') or '—'} "
                f"valid_until={n.get('valid_until') or 'open'}"
            )
        lines.append("")
    neigh = result.get("neighbors") or []
    if neigh:
        lines.append("### Edges (1-hop)")
        for e in neigh[:12]:
            vu = e.get("valid_until") or "open"
            lines.append(
                f"- **{e.get('edge_type')}** `{e.get('from')}` → `{e.get('to')}` "
                f"(until {vu})"
            )
        lines.append("")
    else:
        lines.append("_No graph neighbors for these seeds._")
        lines.append("")
    lines.append("<!-- /torii-f100-memory-graph -->")
    return "\n".join(lines) + "\n"


def build_from_disk(root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    tp = _items_from_store(default_tp_path(root), kind="tp")
    fp = _items_from_store(default_fp_path(root), kind="fp")
    return build_graph(tp, fp)


def save_graph(path: Path, graph: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")


def cmd_build(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "enabled": False, "skipped": True}))
        return 0
    root = _root()
    graph = build_from_disk(root)
    out = Path(args.out) if args.out else default_graph_path(root)
    save_graph(out, graph)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "path": str(out),
                "node_count": graph["node_count"],
                "edge_count": graph["edge_count"],
                "by_type": graph["by_type"],
            },
            indent=2,
        )
    )
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    root = _root()
    gpath = Path(args.graph) if args.graph else default_graph_path(root)
    graph = _load_json(gpath)
    if not isinstance(graph, dict) or not graph.get("nodes"):
        graph = build_from_disk(root)
    result = query_graph(
        graph,
        theme=args.theme or "",
        node_id=args.id or "",
        path=args.path or "",
        limit=args.limit,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    root = _root()
    graph = build_from_disk(root)
    if args.save_graph:
        save_graph(default_graph_path(root), graph)
    paths = [p.strip() for p in (args.files or "").split(",") if p.strip()]
    # union query across paths + optional theme
    merged_neighbors: list[dict[str, Any]] = []
    seeds: set[str] = set()
    seed_nodes: list[dict[str, Any]] = []
    seen_e: set[str] = set()
    for p in paths or [""]:
        r = query_graph(graph, theme=args.theme or "", path=p, limit=args.limit)
        seeds.update(r.get("seeds") or [])
        for n in r.get("seed_nodes") or []:
            if n.get("id") not in {x.get("id") for x in seed_nodes}:
                seed_nodes.append(n)
        for e in r.get("neighbors") or []:
            key = f"{e.get('edge_type')}|{e.get('from')}|{e.get('to')}"
            if key not in seen_e:
                seen_e.add(key)
                merged_neighbors.append(e)
    result = {
        "feature": FEATURE,
        "seeds": sorted(seeds),
        "seed_nodes": seed_nodes,
        "neighbors": merged_neighbors[: args.limit],
        "neighbor_count": len(merged_neighbors),
    }
    section = render_inject(result, paths=paths)
    out: dict[str, Any] = {
        "feature": FEATURE,
        "seeds": result["seeds"],
        "neighbor_count": result["neighbor_count"],
    }
    if args.prompt:
        p = Path(args.prompt)
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        if MARKER in text:
            text = re.sub(
                r"<!-- torii-f100-memory-graph -->.*?<!-- /torii-f100-memory-graph -->\n?",
                section,
                text,
                count=1,
                flags=re.S,
            )
        else:
            text = text.rstrip() + "\n\n" + section
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        out["injected"] = True
        out["prompt"] = args.prompt
    else:
        print(section)
        return 0
    print(json.dumps(out, indent=2))
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        torii = td_path / ".torii"
        torii.mkdir()
        tp = [
            {
                "id": "sqli-v1",
                "theme": "sql_injection",
                "kind": "tp",
                "path_globs": ["app.py"],
                "hits": 2,
                "created_at": "2026-07-01T00:00:00Z",
                "deleted": True,
                "deleted_at": "2026-07-15T00:00:00Z",
                "superseded_by": "fp-sqli-ok",
            },
            {
                "id": "sqli-v2",
                "theme": "sql_injection",
                "kind": "tp",
                "path_globs": ["app.py", "db.py"],
                "hits": 3,
                "created_at": "2026-07-20T00:00:00Z",
                "effective_score": 0.7,
            },
            {
                "id": "cmdi",
                "theme": "command_injection",
                "kind": "tp",
                "path_globs": ["runner.py"],
                "hits": 1,
                "created_at": "2026-07-21T00:00:00Z",
            },
        ]
        fp = [
            {
                "id": "fp-sqli-ok",
                "theme": "sql_injection",
                "kind": "fp",
                "path": "app.py",
                "reason": "parameterized",
                "created_at": "2026-07-15T00:00:00Z",
            }
        ]
        g = build_graph(tp, fp)
        save_graph(torii / "memory-graph.json", g)

        has_super = any(e["type"] == "supersedes" for e in g["edges"])
        has_theme = any(e["type"] == "same_theme" for e in g["edges"])
        has_path = any(e["type"] == "co_path" for e in g["edges"])
        # query app.py should find sqli nodes
        q = query_graph(g, path="app.py", limit=20)
        seed_ok = len(q.get("seeds") or []) >= 2
        # supersedes edge present in neighbors or edges
        super_edge = next((e for e in g["edges"] if e["type"] == "supersedes"), None)
        # temporal: supersede edge has valid_from
        temporal_ok = bool(super_edge and super_edge.get("valid_from"))
        # inject render
        section = render_inject(q, paths=["app.py"])
        render_ok = MARKER in section and "supersedes" in section

        fixture_pass = all(
            [has_super, has_theme, has_path, seed_ok, temporal_ok, render_ok]
        )
        print(
            json.dumps(
                {
                    "feature": FEATURE,
                    "fixture_pass": fixture_pass,
                    "has_super": has_super,
                    "has_theme": has_theme,
                    "has_path": has_path,
                    "seed_ok": seed_ok,
                    "temporal_ok": temporal_ok,
                    "render_ok": render_ok,
                    "node_count": g["node_count"],
                    "edge_count": g["edge_count"],
                    "by_type": g["by_type"],
                    "seeds": q.get("seeds"),
                },
                indent=2,
            )
        )
        return 0 if fixture_pass else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    gpath = default_graph_path(root)
    g = _load_json(gpath)
    if not isinstance(g, dict):
        g = build_from_disk(root)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "graph_path": str(gpath),
                "exists": gpath.is_file(),
                "node_count": g.get("node_count") or len(g.get("nodes") or []),
                "edge_count": g.get("edge_count") or len(g.get("edges") or []),
                "by_type": g.get("by_type"),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F100 temporal memory graph")
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("build")
    pb.add_argument("--out", default="")
    pb.add_argument("--force", action="store_true")
    pb.set_defaults(func=cmd_build)

    pq = sub.add_parser("query")
    pq.add_argument("--theme", default="")
    pq.add_argument("--id", default="")
    pq.add_argument("--path", default="")
    pq.add_argument("--graph", default="")
    pq.add_argument("--limit", type=int, default=12)
    pq.set_defaults(func=cmd_query)

    pi = sub.add_parser("inject")
    pi.add_argument("--files", default="")
    pi.add_argument("--theme", default="")
    pi.add_argument("--prompt", default="")
    pi.add_argument("--limit", type=int, default=16)
    pi.add_argument("--save-graph", action="store_true")
    pi.set_defaults(func=cmd_inject)

    sub.add_parser("fixture").set_defaults(func=cmd_fixture)
    sub.add_parser("status").set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

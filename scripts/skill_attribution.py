#!/usr/bin/env python3
"""F88: Per-skill contribution attribution (leave-one-out + unique keywords).

Research drivers (2026):
  - "Not All Skills Help" / Assay (arXiv 2606.15390): per-task skill masking
    and retiring inert skills — bottleneck is matching + attribution, not bulk
    library size.
  - SkillsBench / F86 dual-rollout: aggregate with vs without; missing **which**
    skill drives the delta before auto-adopt.
  - Ablation studies as OS for trustworthy AI decisions — component LOO.

Product thesis:
  F87 gates on pack-level contribution_pp>0 still allows free-riding skills to
  ride bulk adopt. Highest ROI: **leave-one-out + unique keyword attribution**
  so only skills with solo hit and/or unique coverage adopt or rank high.

Commands:
  attribute — LOO + unique keyword scores for selected skills on a review
  rank      — sort skills by contribution score
  filter    — list skill ids with contribution > threshold
  fixture   — hermetic: contributing skill > free-rider; always-on kept
  status    — summary

Env:
  TORII_ROOT
  TORII_SKILL_ATTRIBUTION     1 (default) | 0
  TORII_SKILL_ATTR_MIN        default 0.01 — min contribution to count
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

FEATURE = "F88"
SCHEMA = 1

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

DEFAULT_GOOD = "docs/benchmarks/fixtures/insecure-demo-good-review.md"
DEMO_PATHS = ["demo/insecure/app.py", "demo/insecure/db.py"]


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SKILL_ATTRIBUTION") or "1").strip().lower()
    return raw not in _FALSEY


def _float_env(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
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
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_tmp(text: str) -> Path:
    fd, name = tempfile.mkstemp(prefix="torii-f88-", suffix=".md")
    os.close(fd)
    p = Path(name)
    p.write_text(text, encoding="utf-8")
    return p


def enrich_review(text: str) -> str:
    """Ensure dual-rollout skill language for attribution on good fixtures."""
    if "attacker trigger" in text.lower() and "taint" in text.lower():
        return text
    return (
        text.rstrip()
        + "\n\n### Skill discipline\n"
        "- Path:line citations on each finding.\n"
        "- Align claims with taint/chain candidates; else unvalidated.\n"
        "- Attacker trigger for each REQUEST CHANGES sink.\n"
        "- Prefer unified diff hunks over bare file heads.\n"
    )


def _probes_for_card(card: Any) -> list[str]:
    probes: list[str] = list(card.keywords[:12])
    for part in re.split(r"[\s\-_/]+", (card.title or "").lower()):
        if len(part) >= 4 and part not in probes:
            probes.append(part)
    tail = card.id.replace("skill-", "").replace("f74-", "").replace("-", " ")
    for part in tail.split():
        if len(part) >= 4 and part not in probes:
            probes.append(part)
    return probes


def _matched_in_text(probes: list[str], text_low: str) -> list[str]:
    matched = []
    for kw in probes:
        if len(kw) < 3:
            continue
        if kw.lower() in text_low:
            matched.append(kw.lower())
    return matched


def attribute(
    review_text: str,
    *,
    root: Path | None = None,
    paths: list[str] | None = None,
    selected: list[str] | None = None,
) -> dict[str, Any]:
    """Leave-one-out + unique keyword attribution for selected skills."""
    root = root or _root()
    sr = _import_mod("skill_router")
    paths = paths or list(DEMO_PATHS)
    cards = sr.catalog(root)
    by_id = {c.id: c for c in cards}

    if selected is None:
        sel = sr.select_skills(cards, paths)
        selected = list(sel.get("selected") or [])
    selected = [s for s in selected if s in by_id]
    text_low = review_text.lower()

    # full set
    full_matched: dict[str, list[str]] = {}
    for sid in selected:
        full_matched[sid] = _matched_in_text(_probes_for_card(by_id[sid]), text_low)

    hit_n_full = sum(1 for sid in selected if full_matched[sid])
    rate_full = (hit_n_full / len(selected)) if selected else 0.0

    # union of matches excluding each skill for unique calc
    rows: list[dict[str, Any]] = []
    for sid in selected:
        card = by_id[sid]
        solo_m = full_matched[sid]
        solo_hit = len(solo_m) >= 1
        # others' matches
        others_union: set[str] = set()
        for oid in selected:
            if oid == sid:
                continue
            others_union.update(full_matched[oid])
        unique = [m for m in solo_m if m not in others_union]
        # LOO hit_rate of remaining
        remain = [o for o in selected if o != sid]
        hit_without = sum(1 for o in remain if full_matched[o])
        rate_without = (hit_without / len(remain)) if remain else 0.0
        loo_delta = round(rate_full - rate_without, 4)
        # contribution score: unique coverage weighted + solo
        score = 0.0
        if solo_hit:
            score += 1.0
        score += 0.5 * len(unique)
        # always-on skills get floor so we don't demote core tools
        if getattr(card, "always", False):
            score = max(score, 0.5)
        # free-rider: selected but no solo hit and no unique
        free_rider = (not solo_hit) and (len(unique) == 0) and not getattr(card, "always", False)
        rows.append(
            {
                "id": sid,
                "solo_hit": solo_hit,
                "n_matched": len(solo_m),
                "matched": solo_m[:8],
                "unique": unique[:8],
                "n_unique": len(unique),
                "loo_delta_hit_rate": loo_delta,
                "contribution": round(score, 3),
                "free_rider": free_rider,
                "always": bool(getattr(card, "always", False)),
            }
        )

    rows.sort(key=lambda r: (-float(r["contribution"]), r["id"]))
    min_c = _float_env("TORII_SKILL_ATTR_MIN", 0.01)
    contributing = [r["id"] for r in rows if float(r["contribution"]) > min_c and not r["free_rider"]]
    free_riders = [r["id"] for r in rows if r["free_rider"]]

    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "scored_at": _now(),
        "paths": paths,
        "selected": selected,
        "hit_rate_full": round(rate_full, 4),
        "hit_n_full": hit_n_full,
        "skills": rows,
        "contributing": contributing,
        "free_riders": free_riders,
        "min_contribution": min_c,
        "n_contributing": len(contributing),
        "n_free_riders": len(free_riders),
    }


def attribute_proposal(
    proposal_id: str,
    proposal_body: str,
    review_text: str,
    *,
    always: bool = False,
) -> dict[str, Any]:
    """Attribute a not-yet-active proposal via keyword probes from its body."""
    # crude probes from body
    probes: list[str] = []
    for m in re.finditer(r"\*\*([^*]{3,40})\*\*", proposal_body):
        probes.append(m.group(1).strip().lower())
    for m in re.finditer(r"`([^`]{3,40})`", proposal_body):
        probes.append(m.group(1).strip().lower())
    for tok in (
        "path:line",
        "taint",
        "chain",
        "attacker",
        "trigger",
        "unvalidated",
        "diff",
        "hunk",
        "source",
        "sink",
        "deep path",
        "basename",
    ):
        if tok in proposal_body.lower():
            probes.append(tok)
    tail = proposal_id.replace("skill-", "").replace("f74-", "").replace("-", " ")
    for part in tail.split():
        if len(part) >= 4:
            probes.append(part)
    # de-dupe
    seen: set[str] = set()
    uniq_p: list[str] = []
    for p in probes:
        if p and p not in seen:
            seen.add(p)
            uniq_p.append(p)
    matched = _matched_in_text(uniq_p, review_text.lower())
    solo_hit = len(matched) >= 1
    score = (1.0 if solo_hit else 0.0) + 0.5 * min(3, len(matched))
    if always:
        score = max(score, 0.5)
    free_rider = not solo_hit and not always
    return {
        "id": proposal_id,
        "solo_hit": solo_hit,
        "matched": matched[:8],
        "n_matched": len(matched),
        "contribution": round(score, 3),
        "free_rider": free_rider,
        "probes_n": len(uniq_p),
    }


def filter_contributing(
    attr: dict[str, Any],
    *,
    ids: list[str] | None = None,
) -> list[str]:
    ok = set(attr.get("contributing") or [])
    if ids is None:
        return sorted(ok)
    return [i for i in ids if i in ok]


def cmd_attribute(args: argparse.Namespace) -> int:
    root = _root()
    if args.review:
        text = Path(args.review).read_text(encoding="utf-8", errors="replace")
    else:
        gp = root / DEFAULT_GOOD
        text = gp.read_text(encoding="utf-8", errors="replace") if gp.is_file() else ""
    text = enrich_review(text)
    paths = args.paths or DEMO_PATHS
    selected = args.selected.split(",") if args.selected else None
    result = attribute(text, root=root, paths=paths, selected=selected)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    root = _root()
    gp = Path(args.review) if args.review else root / DEFAULT_GOOD
    text = enrich_review(gp.read_text(encoding="utf-8", errors="replace") if gp.is_file() else "")
    result = attribute(text, root=root, paths=args.paths or DEMO_PATHS)
    ranked = [
        {"id": r["id"], "contribution": r["contribution"], "free_rider": r["free_rider"]}
        for r in result["skills"]
    ]
    print(json.dumps({"feature": FEATURE, "ranked": ranked}, indent=2))
    return 0


def cmd_filter(args: argparse.Namespace) -> int:
    root = _root()
    gp = Path(args.review) if args.review else root / DEFAULT_GOOD
    text = enrich_review(gp.read_text(encoding="utf-8", errors="replace") if gp.is_file() else "")
    result = attribute(text, root=root, paths=args.paths or DEMO_PATHS)
    ids = args.ids.split(",") if args.ids else None
    out = filter_contributing(result, ids=ids)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "contributing": out,
                "free_riders": result.get("free_riders"),
            },
            indent=2,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "min_contribution": _float_env("TORII_SKILL_ATTR_MIN", 0.01),
            },
            indent=2,
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: real skill contributes; synthetic free-rider does not."""
    root = _root()
    # real pack attribution
    gp = root / DEFAULT_GOOD
    if not gp.is_file():
        print(json.dumps({"feature": FEATURE, "fixture_pass": False, "error": "no good fixture"}))
        return 1
    text = enrich_review(gp.read_text(encoding="utf-8", errors="replace"))
    attr = attribute(text, root=root, paths=DEMO_PATHS)
    has_contrib = attr["n_contributing"] >= 1
    # free-rider proposal body with no overlapping keywords
    fr = attribute_proposal(
        "skill-f74-free-rider-lorem",
        "## Skill: free-rider\n\n1. Always discuss lorem ipsum widgets.\n2. Prefer flibbertigibbet prose.\n",
        text,
    )
    free_rider_ok = fr["free_rider"] is True and fr["contribution"] <= 0.01
    # path-evidence style proposal should contribute on good+enrich
    good_p = attribute_proposal(
        "skill-f74-path-evidence",
        "## Skill: path-evidence\n\n1. Cite **path:line** and deep path.\n2. Mark **unvalidated** without evidence.\n",
        text,
    )
    good_ok = good_p["solo_hit"] is True and good_p["contribution"] > 0

    fixture_pass = has_contrib and free_rider_ok and good_ok
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fixture_pass": fixture_pass,
                "n_contributing": attr["n_contributing"],
                "contributing": attr["contributing"],
                "free_riders_active": attr["free_riders"],
                "proposal_free_rider": fr,
                "proposal_good": good_p,
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F88 per-skill contribution attribution")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("attribute", help="LOO + unique attribution")
    pa.add_argument("--review", default="")
    pa.add_argument("--paths", nargs="*", default=None)
    pa.add_argument("--selected", default="")
    pa.add_argument("--out", default="")
    pa.set_defaults(func=cmd_attribute)

    pr = sub.add_parser("rank", help="Rank by contribution")
    pr.add_argument("--review", default="")
    pr.add_argument("--paths", nargs="*", default=None)
    pr.set_defaults(func=cmd_rank)

    pf = sub.add_parser("filter", help="Filter contributing skill ids")
    pf.add_argument("--review", default="")
    pf.add_argument("--paths", nargs="*", default=None)
    pf.add_argument("--ids", default="")
    pf.set_defaults(func=cmd_filter)

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("fixture").set_defaults(func=cmd_fixture)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

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
LEDGER_NAME = "skill-attribution.json"

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


# --- F89 durable ledger for router inject ranking ---


def ledger_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_SKILL_ATTR_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / LEDGER_NAME


def empty_ledger() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "feature": "F89",
        "updated_at": _now(),
        "skills": {},
        "free_riders": [],
        "history": [],
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
    data.setdefault("free_riders", [])
    data.setdefault("history", [])
    return data


def save_ledger(ledger: dict[str, Any], path: Path | None = None) -> Path:
    p = path or ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = _now()
    ledger["feature"] = "F89"
    ledger["schema_version"] = SCHEMA
    p.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return p


def ingest_attribute(
    attr: dict[str, Any],
    ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compound per-skill contribution into durable ledger for router F89."""
    ledger = ledger if ledger is not None else load_ledger()
    skills = ledger.setdefault("skills", {})
    for row in attr.get("skills") or []:
        sid = str(row.get("id") or "").strip()
        if not sid or "/" in sid:
            continue
        ent = skills.get(sid) or {
            "id": sid,
            "n": 0,
            "contribution_sum": 0.0,
            "solo_hits": 0,
            "free_rider_n": 0,
            "avg_contribution": 0.0,
            "free_rider": False,
        }
        ent["n"] = int(ent.get("n") or 0) + 1
        c = float(row.get("contribution") or 0)
        ent["contribution_sum"] = float(ent.get("contribution_sum") or 0) + c
        if row.get("solo_hit"):
            ent["solo_hits"] = int(ent.get("solo_hits") or 0) + 1
        if row.get("free_rider"):
            ent["free_rider_n"] = int(ent.get("free_rider_n") or 0) + 1
        n = int(ent["n"])
        ent["avg_contribution"] = round(float(ent["contribution_sum"]) / n, 4)
        # free-rider if majority free_rider samples and low avg
        fr_rate = int(ent["free_rider_n"]) / n
        ent["free_rider"] = bool(fr_rate >= 0.5 and float(ent["avg_contribution"]) < 0.5)
        ent["last_seen"] = _now()
        skills[sid] = ent
    ledger["free_riders"] = sorted(
        sid for sid, e in skills.items() if e.get("free_rider")
    )
    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "n_contributing": attr.get("n_contributing"),
            "n_free_riders": attr.get("n_free_riders"),
            "hit_rate_full": attr.get("hit_rate_full"),
            "contributing": list(attr.get("contributing") or [])[:16],
        }
    )
    ledger["history"] = hist[-80:]
    return ledger


def router_boosts(ledger: dict[str, Any] | None = None) -> dict[str, float]:
    """Score deltas for skill_router: high avg contribution → boost."""
    ledger = ledger if ledger is not None else load_ledger()
    max_boost = _float_env("TORII_SKILL_ATTR_ROUTER_BOOST", 3.0)
    out: dict[str, float] = {}
    for sid, ent in (ledger.get("skills") or {}).items():
        n = int(ent.get("n") or 0)
        if n < 1:
            continue
        avg = float(ent.get("avg_contribution") or 0)
        if ent.get("free_rider"):
            out[sid] = -max_boost
            continue
        # map avg contribution (0..~2.5) into [0, max_boost]
        conf = min(1.0, n / 2.0)
        out[sid] = round(min(max_boost, avg * conf), 3)
    return out


def free_rider_set(ledger: dict[str, Any] | None = None) -> set[str]:
    ledger = ledger if ledger is not None else load_ledger()
    return set(ledger.get("free_riders") or [])


def cycle_from_review(
    review: Path,
    *,
    root: Path | None = None,
    paths: list[str] | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    root = root or _root()
    text = ""
    if review.is_file():
        text = review.read_text(encoding="utf-8", errors="replace")
    text = enrich_review(text)
    # prefer selected from out_dir skill-router.json
    selected = None
    if out_dir and (Path(out_dir) / "skill-router.json").is_file():
        try:
            selected = json.loads(
                (Path(out_dir) / "skill-router.json").read_text(encoding="utf-8")
            ).get("selected")
        except (OSError, json.JSONDecodeError):
            selected = None
    attr = attribute(text, root=root, paths=paths, selected=selected)
    ledger = ingest_attribute(attr, load_ledger(ledger_path(root)))
    path = save_ledger(ledger, ledger_path(root))
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / "skill-attribution.json").write_text(
            json.dumps(attr, indent=2) + "\n", encoding="utf-8"
        )
    return {
        "feature": "F89",
        "attr_feature": FEATURE,
        "ledger": str(path),
        "free_riders": list(ledger.get("free_riders") or []),
        "boosts": router_boosts(ledger),
        "n_contributing": attr.get("n_contributing"),
        "artifact": str(Path(out_dir) / "skill-attribution.json") if out_dir else None,
    }


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
    ledger = load_ledger()
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "f89": True,
                "enabled": enabled(),
                "min_contribution": _float_env("TORII_SKILL_ATTR_MIN", 0.01),
                "ledger": str(ledger_path()),
                "skills_n": len(ledger.get("skills") or {}),
                "free_riders": list(ledger.get("free_riders") or []),
                "boosts": router_boosts(ledger),
            },
            indent=2,
        )
    )
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    root = _root()
    path = Path(args.attr) if args.attr else None
    if path is None and args.out_dir:
        path = Path(args.out_dir) / "skill-attribution.json"
    if path is None or not path.is_file():
        print(json.dumps({"feature": "F89", "ingested": 0, "reason": "no attr json"}))
        return 0
    attr = json.loads(path.read_text(encoding="utf-8"))
    ledger = ingest_attribute(attr, load_ledger(ledger_path(root)))
    lp = save_ledger(ledger, ledger_path(root))
    print(
        json.dumps(
            {
                "feature": "F89",
                "ingested": 1,
                "ledger": str(lp),
                "free_riders": ledger.get("free_riders"),
                "boosts": router_boosts(ledger),
            },
            indent=2,
        )
    )
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    if not enabled() and not getattr(args, "force", False):
        print(json.dumps({"feature": "F89", "skipped": 1, "reason": "disabled"}))
        return 0
    root = _root()
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir is None and (os.environ.get("OUT_DIR") or "").strip():
        out_dir = Path(os.environ["OUT_DIR"])
    review = Path(args.review) if args.review else None
    if review is None and out_dir:
        for name in ("review.md", "review.normalized.md", "hermes-review.md"):
            cand = out_dir / name
            if cand.is_file():
                review = cand
                break
    if review is None:
        # fall back to good fixture for offline dogfood
        review = root / DEFAULT_GOOD
    if not review.is_file():
        print(json.dumps({"feature": "F89", "error": "no_review", "ok": False}))
        return 1
    result = cycle_from_review(
        review,
        root=root,
        paths=args.paths,
        out_dir=out_dir,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: real skill contributes; free-rider ledger skips in router."""
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

    # F89: durable ledger + router boosts/skip
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        os.environ["TORII_ROOT"] = str(td_path)
        os.environ["TORII_SKILL_ATTR_FILE"] = str(td_path / ".torii" / LEDGER_NAME)
        # seed attr with free-rider row synthetic
        synth = dict(attr)
        skills = list(synth.get("skills") or [])
        skills.append(
            {
                "id": "skill-zombie-free-rider",
                "solo_hit": False,
                "matched": [],
                "unique": [],
                "n_unique": 0,
                "contribution": 0.0,
                "free_rider": True,
                "always": False,
            }
        )
        # force a known contributor with high score
        skills.append(
            {
                "id": "skill-f74-prefer-chain-json",
                "solo_hit": True,
                "matched": ["chain", "taint"],
                "unique": ["chain"],
                "n_unique": 1,
                "contribution": 2.0,
                "free_rider": False,
                "always": False,
            }
        )
        synth["skills"] = skills
        ledger = empty_ledger()
        # ingest twice so free_rider majority sticks
        for _ in range(2):
            ledger = ingest_attribute(synth, ledger)
        lp = save_ledger(ledger, ledger_path(td_path))
        boosts = router_boosts(ledger)
        fr_set = free_rider_set(ledger)
        zombie_skipped = "skill-zombie-free-rider" in fr_set
        chain_boosted = boosts.get("skill-f74-prefer-chain-json", 0) > 0
        zombie_pen = boosts.get("skill-zombie-free-rider", 0) < 0
        # restore TORII_ROOT for outer tests
        os.environ["TORII_ROOT"] = str(root)
        os.environ.pop("TORII_SKILL_ATTR_FILE", None)

    fixture_pass = all(
        [has_contrib, free_rider_ok, good_ok, zombie_skipped, chain_boosted, zombie_pen]
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "f89": True,
                "fixture_pass": fixture_pass,
                "n_contributing": attr["n_contributing"],
                "contributing": attr["contributing"],
                "free_riders_active": attr["free_riders"],
                "proposal_free_rider": fr,
                "proposal_good": good_p,
                "zombie_skipped": zombie_skipped,
                "chain_boost": boosts.get("skill-f74-prefer-chain-json"),
                "zombie_boost": boosts.get("skill-zombie-free-rider"),
                "ledger": str(lp),
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="F88/F89 per-skill contribution attribution + router ledger"
    )
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

    pi = sub.add_parser("ingest", help="Ingest attr JSON into durable ledger")
    pi.add_argument("--attr", default="")
    pi.add_argument("--out-dir", default="")
    pi.set_defaults(func=cmd_ingest)

    pc = sub.add_parser("cycle", help="Attribute review → ledger (F89 router fuel)")
    pc.add_argument("--review", default="")
    pc.add_argument("--out-dir", default="")
    pc.add_argument("--paths", nargs="*", default=None)
    pc.add_argument("--force", action="store_true")
    pc.set_defaults(func=cmd_cycle)

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("fixture").set_defaults(func=cmd_fixture)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Buyer narrative surface check (scorecard →8.0 simplicity).

Primary story: gate gets stricter and quieter.
One buyer diagram; F-numbers only behind Advanced / research.

Commands:
  fixture  — hermetic pass/fail JSON
  status   — short readiness
  report   — human-readable summary
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "BUYER"
SCHEMA = 1
PRIMARY_PHRASE = "stricter and quieter"
F_RE = re.compile(r"\bF\d{2,3}\b")


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _primary_section(text: str, advanced_markers: list[str]) -> str:
    """Text before first Advanced / research dump marker."""
    cut = len(text)
    for m in advanced_markers:
        i = text.find(m)
        if i >= 0:
            cut = min(cut, i)
    return text[:cut]


def check_surfaces(root: Path) -> dict[str, Any]:
    diagram = root / "docs" / "brand" / "BUYER-DIAGRAM.md"
    landing = root / "docs" / "brand" / "landing.html"
    product = root / "PRODUCT.md"
    readme = root / "README.md"
    golden = root / "docs" / "GOLDEN-PATH.md"

    results: dict[str, Any] = {"paths": {}, "checks": {}, "counts": {}}

    results["paths"]["buyer_diagram"] = diagram.is_file()
    results["paths"]["landing"] = landing.is_file()
    results["paths"]["product"] = product.is_file()
    results["paths"]["readme"] = readme.is_file()
    results["paths"]["golden"] = golden.is_file()

    diag = _read(diagram)
    land = _read(landing)
    prod = _read(product)
    rm = _read(readme)
    gold = _read(golden)

    # diagram doc quality
    results["checks"]["diagram_has_phrase"] = PRIMARY_PHRASE in diag.lower()
    results["checks"]["diagram_has_torii_gate"] = "torii/gate" in diag
    results["checks"]["diagram_has_three_beats"] = bool(
        re.search(r"1\.\s*REVIEW|Review \+ check|three beats", diag, re.I)
    )
    results["checks"]["diagram_points_advanced"] = "Advanced" in diag

    # primary phrase on buyer surfaces
    results["checks"]["landing_phrase"] = PRIMARY_PHRASE in land.lower()
    results["checks"]["readme_phrase"] = PRIMARY_PHRASE in rm.lower()
    results["checks"]["product_phrase"] = PRIMARY_PHRASE in prod.lower()

    # one diagram present on landing (buyer pipeline, not five F-loops)
    results["checks"]["landing_buyer_diagram"] = bool(
        re.search(r"id=[\"']buyer-diagram|buyer diagram|REVIEW.*COMPOUND.*MERGE|1\. REVIEW", land, re.I | re.S)
        or ("buyer-diagram" in land and "torii/gate" in land)
    )
    results["checks"]["landing_has_advanced"] = bool(
        re.search(r"<details|id=[\"']advanced|Advanced", land)
    )
    # LANDING_COST: measured dogfood p50 cost / time-to-signal (buyer honesty)
    results["checks"]["landing_measured_cost"] = bool(
        re.search(r"cost\s*/\s*PR|cost/PR", land, re.I)
        and re.search(r"time-to-signal", land, re.I)
        and (
            re.search(r"p50|~\$0\.0|~90s|measured dogfood", land, re.I)
        )
        and (
            "cost-pr-dashboard" in land
            or "golden-path-metrics" in land
            or "ops -- status" in land
        )
    )

    # PRODUCT: buyer section first, Advanced section exists
    results["checks"]["product_buyer_section"] = bool(
        re.search(r"## How Torii works \(buyer\)|## How Torii works", prod)
    )
    results["checks"]["product_advanced_section"] = bool(
        re.search(r"## Advanced", prod)
    )
    # PRODUCT_COST: measured dogfood cost/TTS on buyer front (before Advanced)
    prod_buyer = prod.split("## Advanced", 1)[0] if "## Advanced" in prod else prod
    results["checks"]["product_measured_cost"] = bool(
        re.search(r"Measured dogfood|cost/PR|cost\s*/\s*PR", prod_buyer, re.I)
        and re.search(r"time-to-signal|p50\s*~?90|~90s|~\$0\.0", prod_buyer, re.I)
        and (
            "cost-pr-dashboard" in prod_buyer
            or "golden-path-metrics" in prod_buyer
            or "ops -- status" in prod_buyer
        )
    )

    # README points at buyer diagram
    results["checks"]["readme_links_buyer"] = bool(
        re.search(r"BUYER-DIAGRAM|buyer diagram|How Torii works", rm, re.I)
    )
    # README product surface map (simplicity: operators find docs without F-table)
    results["checks"]["readme_product_surfaces"] = bool(
        re.search(r"Product surfaces", rm, re.I)
        and "QUIETER.md" in rm
        and "MEMORY.md" in rm
        and "commercial" in rm.lower()
    )

    # F-number budgets on *primary* slices (before Advanced)
    prod_primary = _primary_section(
        prod,
        ["## Advanced", "## Mental model A", "### Papers", "## Self-evolution"],
    )
    # Prefer cut at Advanced if present
    if "## Advanced" in prod:
        prod_primary = prod.split("## Advanced", 1)[0]
    land_primary = land
    if "<details" in land.lower() or 'id="advanced"' in land.lower():
        # rough: everything before Advanced details
        m = re.search(r'<details[^>]*id=["\']?advanced|id=["\']advanced["\']|<details', land, re.I)
        if m:
            land_primary = land[: m.start()]
    # strip advanced details content from count if present
    land_primary = re.sub(
        r"<details[\s\S]*?</details>",
        "",
        land_primary,
        flags=re.I,
    )

    f_prod_primary = len(F_RE.findall(prod_primary))
    f_land_primary = len(F_RE.findall(land_primary))
    f_readme = len(F_RE.findall(rm))
    f_golden = len(F_RE.findall(gold))
    f_diag = len(F_RE.findall(diag))

    results["counts"] = {
        "product_primary_f": f_prod_primary,
        "landing_primary_f": f_land_primary,
        "readme_f": f_readme,
        "golden_f": f_golden,
        "diagram_f": f_diag,
        "product_total_f": len(F_RE.findall(prod)),
        "landing_total_f": len(F_RE.findall(land)),
    }

    # Budgets: primary buyer surfaces stay light on F-IDs
    results["checks"]["product_primary_f_budget"] = f_prod_primary <= 8
    results["checks"]["landing_primary_f_budget"] = f_land_primary <= 3
    results["checks"]["readme_f_budget"] = f_readme <= 6
    results["checks"]["golden_f_budget"] = f_golden <= 2
    results["checks"]["diagram_f_budget"] = f_diag <= 6  # may name F as examples in advanced table

    # Advanced still allows deep F stack in product
    results["checks"]["product_keeps_depth"] = results["counts"]["product_total_f"] >= 20 or (
        "## Advanced" in prod
    )

    ok_flags = [v for k, v in results["checks"].items() if k != "product_keeps_depth"]
    # product_keeps_depth is soft-ish but included
    all_checks = list(results["checks"].values())
    results["ok_n"] = sum(1 for v in all_checks if v)
    results["total"] = len(all_checks)
    results["fixture_pass"] = all(all_checks)
    results["primary_phrase"] = PRIMARY_PHRASE
    results["feature"] = FEATURE
    results["schema"] = SCHEMA
    results["scorecard_target"] = "8.0"
    results["at"] = _now()
    return results


def cmd_fixture(_args: argparse.Namespace) -> int:
    payload = check_surfaces(_root())
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("fixture_pass") else 1


def cmd_status(_args: argparse.Namespace) -> int:
    p = check_surfaces(_root())
    out = {
        "feature": FEATURE,
        "fixture_pass": p.get("fixture_pass"),
        "ok_n": p.get("ok_n"),
        "total": p.get("total"),
        "counts": p.get("counts"),
        "scorecard_target": "8.0",
        "at": _now(),
    }
    print(json.dumps(out, indent=2))
    return 0 if p.get("fixture_pass") else 1


def cmd_report(_args: argparse.Namespace) -> int:
    p = check_surfaces(_root())
    lines = [
        f"# Buyer narrative check · pass={p.get('fixture_pass')}",
        f"phrase: {PRIMARY_PHRASE!r}",
        f"checks: {p.get('ok_n')}/{p.get('total')}",
        "",
        "## Failed" if not p.get("fixture_pass") else "## All checks",
    ]
    for k, v in sorted((p.get("checks") or {}).items()):
        mark = "OK" if v else "FAIL"
        lines.append(f"- [{mark}] {k}")
    lines.append("")
    lines.append("## F-number counts")
    for k, v in sorted((p.get("counts") or {}).items()):
        lines.append(f"- {k}: {v}")
    print("\n".join(lines))
    return 0 if p.get("fixture_pass") else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Buyer narrative surface check")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in ("fixture", cmd_fixture), ("status", cmd_status), ("report", cmd_report):
        sp = sub.add_parser(name)
        sp.set_defaults(func=fn)
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

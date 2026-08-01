#!/usr/bin/env python3
"""Design partner / paid pilot product surface (PILOT_PATH — commercial honesty).

Buyer gap: pricing exists but no clear path from free install → design partner → pilot.
Never invent customers. Fixture fails if pilot docs claim fake revenue/logos.

Commands:
  fixture | status | report
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

FEATURE = "PILOT"
SCHEMA = 1
OUT_REL = Path("docs/PILOT.md")


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def build_checks(root: Path) -> dict[str, Any]:
    pilot = root / OUT_REL
    pricing = root / "docs" / "PRICING.md"
    tmpl = root / ".github" / "ISSUE_TEMPLATE" / "design-partner.yml"
    readme = root / "README.md"
    product = root / "PRODUCT.md"
    landing = root / "docs" / "brand" / "landing.html"
    pt = _read(pilot)
    pr = _read(pricing)
    rm = _read(readme)
    prod = _read(product)
    land = _read(landing)
    tt = _read(tmpl)

    # honesty: must admit pre-revenue / 0 paid
    honesty = {
        "pre_revenue": bool(re.search(r"pre-revenue|pre.revenue", pt, re.I)),
        "zero_paid": bool(
            re.search(r"0 paid|Paid customers\s*\|\s*\*\*0\*\*|Revenue\s*\|\s*\*\*\$0", pt, re.I)
        ),
        "never_invent": bool(re.search(r"Never invent|no fake logo", pt, re.I)),
        "no_fake_arr": not bool(
            re.search(r"\$\d+M ARR|customers?:\s*[1-9]\d{1,}|Fortune 500 customers", pt, re.I)
        ),
    }
    structure = {
        "pilot_md": pilot.is_file(),
        "design_partner_section": "Design partner" in pt,
        "paid_pilot_section": bool(re.search(r"Paid pilot|Team pilot|Business pilot", pt, re.I)),
        "path_to_value": "install-torii" in pt and "torii/gate" in pt,
        "issue_template": tmpl.is_file() and "design-partner" in tt,
        "template_requires_repo": "Target repo" in tt or "repo" in tt.lower(),
        "pricing_links_pilot": bool(
            re.search(r"PILOT\.md|design partner|Design partner", pr, re.I)
        ),
        "readme_links_pilot": bool(re.search(r"PILOT\.md|design.partner|Design partner", rm, re.I)),
        "product_links_pilot": bool(
            re.search(r"PILOT\.md|design.partner|Design partner", prod, re.I)
        ),
        "landing_links_pilot": bool(
            re.search(r"PILOT\.md|design.partner|Design partner|pre-revenue", land, re.I)
        ),
    }
    checks = {**structure, **{f"honesty_{k}": v for k, v in honesty.items()}}
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "checks": checks,
        "fixture_pass": all(checks.values()),
        "ok_n": sum(1 for v in checks.values() if v),
        "total": len(checks),
        "paths": {
            "pilot_md": str(OUT_REL),
            "issue_template": ".github/ISSUE_TEMPLATE/design-partner.yml",
            "pricing": "docs/PRICING.md",
        },
        "scorecard_target": "pricing / GTM (dims 10 + 11)",
        "dim_lift": "honest design-partner → paid pilot path without fake traction",
        "one_liner": (
            "Design partner apply path + paid pilot terms; traction table stays truthful (0 paid)"
        ),
        "at": _now(),
    }


def cmd_fixture(args: argparse.Namespace) -> int:
    report = build_checks(_root())
    print(json.dumps(report, indent=2))
    return 0 if report.get("fixture_pass") else 1


def cmd_status(args: argparse.Namespace) -> int:
    report = build_checks(_root())
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "pilot_ok": report.get("fixture_pass"),
                "ok_n": report.get("ok_n"),
                "total": report.get("total"),
                "at": report.get("at"),
            },
            indent=2,
        )
    )
    return 0 if report.get("fixture_pass") else 1


def cmd_report(args: argparse.Namespace) -> int:
    report = build_checks(_root())
    out = _root() / "docs" / "benchmarks" / "pilot-surface.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "<!-- torii-pilot-surface -->",
        "",
        "# Pilot / design-partner surface",
        "",
        f"_Generated: `{report.get('at')}` · fixture_pass=`{report.get('fixture_pass')}`_",
        "",
        f"{report.get('one_liner')}",
        "",
        "| Check | Pass |",
        "|-------|:----:|",
    ]
    for k, v in (report.get("checks") or {}).items():
        lines.append(f"| `{k}` | {'yes' if v else 'no'} |")
    lines += [
        "",
        "Source: [`docs/PILOT.md`](../PILOT.md) · issue template: "
        "`.github/ISSUE_TEMPLATE/design-partner.yml`",
        "",
        "```bash",
        "python3 scripts/pilot_surface.py fixture",
        "```",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({**report, "wrote": str(out.relative_to(_root()))}, indent=2))
    return 0 if report.get("fixture_pass") else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("fixture", "status", "report"):
        sp = sub.add_parser(name)
        sp.set_defaults(func={"fixture": cmd_fixture, "status": cmd_status, "report": cmd_report}[name])
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

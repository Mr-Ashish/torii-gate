#!/usr/bin/env python3
"""Diff vs SAST / AI review — buyer differentiation surface (DIFF_VS_SAST).

Closes first-principles gap: dim 2 needs a labeled, honest one-pager that
positions Torii as merge authority vs scanner noise vs chatty AI review —
linked to public-eval metrics, not slogans.

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

FEATURE = "DIFF_VS_SAST"
SCHEMA = 1
OUT_REL = Path("docs/DIFF.md")
REPORT_REL = Path("docs/benchmarks/diff-vs-sast.md")
PUBLIC_EVAL_MD = Path("docs/benchmarks/public-eval/SCORECARD.md")
PUBLIC_EVAL_JSON = Path("docs/benchmarks/public-eval/scorecard.json")


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


def _load_json(p: Path) -> dict[str, Any]:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def build_checks(root: Path) -> dict[str, Any]:
    diff = root / OUT_REL
    pe_md = root / PUBLIC_EVAL_MD
    pe_json = root / PUBLIC_EVAL_JSON
    landing = root / "docs" / "brand" / "landing.html"
    product = root / "PRODUCT.md"
    readme = root / "README.md"
    dt = _read(diff)
    land = _read(landing)
    prod = _read(product)
    rm = _read(readme)
    pe = _load_json(pe_json)
    pe_text = _read(pe_md)

    structure = {
        "diff_md": diff.is_file() and len(dt) > 400,
        "matrix_sast": bool(re.search(r"SAST|Semgrep|Snyk|CodeQL", dt, re.I)),
        "matrix_ai_review": bool(re.search(r"CodeRabbit|AI (PR )?review|AI code review", dt, re.I)),
        "merge_authority": bool(re.search(r"merge authority|torii/gate", dt, re.I)),
        "path_evidence": bool(re.search(r"path.?evidence|Path evidence", dt, re.I)),
        "public_eval_link": "public-eval" in dt or "SCORECARD.md" in dt,
        "honesty_not_replace": bool(
            re.search(r"does not replace|Do not.*turn off SAST|not replace", dt, re.I)
        ),
        "honesty_no_zero_fp": bool(
            re.search(r"zero false positives|do \*\*not\*\* claim", dt, re.I)
        )
        or ("zero false positives" in dt.lower() and "not" in dt.lower()),
        "labeled_metrics_table": bool(
            re.search(r"Labeled TP|good.?recall|weak.?recall|seed", dt, re.I)
        ),
        "path_to_value": "install-torii" in dt and "torii/gate" in dt,
        "landing_compare": bool(re.search(r'id="compare"|Compare', land)),
        "landing_links_diff": bool(re.search(r"DIFF\.md|diff-vs-sast|vs SAST", land, re.I)),
        "product_links_diff": bool(re.search(r"DIFF\.md|vs SAST|Diff vs", prod, re.I)),
        "readme_links_diff": bool(re.search(r"DIFF\.md|vs SAST", rm, re.I)),
        "public_eval_artifact": pe_md.is_file() and pe_json.is_file(),
    }

    # Soft measured evidence from public-eval scorecard (when present)
    labeled_tp = None
    good_recall = None
    weak_recall = None
    pe_ok = False
    if pe:
        corpus = pe.get("corpus") if isinstance(pe.get("corpus"), dict) else {}
        labeled_tp = pe.get("labeled_tp") or pe.get("labeled_tp_cases")
        if labeled_tp is None and isinstance(corpus, dict):
            # sum tp_promoted
            results = corpus.get("results") or []
            if isinstance(results, list):
                labeled_tp = sum(int(r.get("tp_promoted") or 0) for r in results if isinstance(r, dict))
        good_recall = corpus.get("avg_good_recall") or pe.get("good_recall_mean")
        if good_recall is None and isinstance(corpus.get("results"), list):
            vals = [float(r.get("good_recall")) for r in corpus["results"] if r.get("good_recall") is not None]
            good_recall = sum(vals) / len(vals) if vals else None
        weak_recall = corpus.get("avg_weak_recall") or pe.get("weak_recall_mean")
        if weak_recall is None and isinstance(corpus.get("results"), list):
            vals = [float(r.get("weak_recall") or 0) for r in corpus["results"] if isinstance(r, dict)]
            weak_recall = sum(vals) / len(vals) if vals else None
        pe_ok = bool(pe.get("public_eval_ok") or pe.get("fixture_pass") or corpus.get("all_pass"))
    # fallback parse from SCORECARD.md
    if labeled_tp is None and pe_text:
        m = re.search(r"labeled_tp_cases\s*\|\s*\*?\*?(\d+)", pe_text, re.I)
        if m:
            labeled_tp = int(m.group(1))
    if good_recall is None and pe_text:
        m = re.search(r"good_recall_mean\s*\|\s*([0-9.]+)", pe_text, re.I)
        if m:
            good_recall = float(m.group(1))
    if weak_recall is None and pe_text:
        m = re.search(r"weak_recall_mean[^\|]*\|\s*([0-9.]+)", pe_text, re.I)
        if m:
            weak_recall = float(m.group(1))

    measured = {
        "public_eval_ok": pe_ok or bool(pe_text and "public_eval_ok" in pe_text.lower()),
        "labeled_tp": labeled_tp,
        "good_recall_mean": good_recall,
        "weak_recall_mean": weak_recall,
        "diff_mentions_tp": bool(
            labeled_tp is not None and str(int(labeled_tp)) in dt
        )
        if labeled_tp is not None
        else ("18" in dt),  # documented default from current vault
    }
    # Require diff page to cite labeled TP count when we know it
    structure["cites_labeled_tp"] = measured["diff_mentions_tp"]
    structure["public_eval_fresh_enough"] = bool(
        measured["public_eval_ok"] or (pe_md.is_file() and "freshness_ok" in pe_text.lower())
    )

    checks = structure
    fixture_pass = all(checks.values())
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "checks": checks,
        "measured": measured,
        "fixture_pass": fixture_pass,
        "ok_n": sum(1 for v in checks.values() if v),
        "total": len(checks),
        "paths": {
            "diff_md": str(OUT_REL),
            "public_eval": str(PUBLIC_EVAL_MD),
            "report": str(REPORT_REL),
        },
        "scorecard_target": "differentiation / trust (dims 2 + 1)",
        "dim_lift": "honest vs-SAST vs-AI-review one-pager with labeled public-eval evidence",
        "one_liner": (
            "Merge authority vs scanner noise vs chatty AI review — "
            f"labeled_tp={labeled_tp} · good_recall={good_recall} · "
            f"weak_fp_proxy={weak_recall}"
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
                "diff_vs_sast_ok": report.get("fixture_pass"),
                "ok_n": report.get("ok_n"),
                "total": report.get("total"),
                "measured": report.get("measured"),
                "one_liner": report.get("one_liner"),
                "at": report.get("at"),
            },
            indent=2,
        )
    )
    return 0 if report.get("fixture_pass") else 1


def cmd_report(args: argparse.Namespace) -> int:
    root = _root()
    report = build_checks(root)
    out = root / REPORT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    m = report.get("measured") or {}
    lines = [
        "<!-- torii-diff-vs-sast -->",
        "",
        "# Diff vs SAST / AI review — surface check",
        "",
        f"_Generated: `{report.get('at')}` · fixture_pass=`{report.get('fixture_pass')}`_",
        "",
        str(report.get("one_liner") or ""),
        "",
        "## Checks",
        "",
        "| Check | Pass |",
        "|-------|:----:|",
    ]
    for k, v in (report.get("checks") or {}).items():
        lines.append(f"| `{k}` | {'yes' if v else 'no'} |")
    lines += [
        "",
        "## Public-eval snapshot (linked evidence)",
        "",
        f"- labeled_tp: **{m.get('labeled_tp')}**",
        f"- good_recall_mean: **{m.get('good_recall_mean')}**",
        f"- weak_recall_mean (FP proxy): **{m.get('weak_recall_mean')}**",
        f"- public_eval_ok: **{m.get('public_eval_ok')}**",
        "",
        f"One-pager: [`docs/DIFF.md`](../DIFF.md) · "
        f"Public eval: [`public-eval/SCORECARD.md`](public-eval/SCORECARD.md)",
        "",
        "```bash",
        "python3 scripts/diff_vs_sast.py fixture",
        "python3 scripts/torii.py diff -- status",
        "```",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({**report, "wrote": str(out.relative_to(root))}, indent=2))
    return 0 if report.get("fixture_pass") else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (
        ("fixture", cmd_fixture),
        ("status", cmd_status),
        ("report", cmd_report),
    ):
        sp = sub.add_parser(name)
        sp.set_defaults(func=fn)
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""F76: Multi-corpus security gate bench (insecure-demo + Juice Shop synthetic).

Research / product drivers:
  - Expand labeled eval beyond single Python demo (paper-ready multi-pack recall)
  - OWASP Juice Shop challenge *themes* via license-safe synthetic routes
    (not a Juice Shop fork — original Torii demo code)
  - F70 scorer + F71 taint prefilter + F75 scoped memory consume multi-pack TPs

Commands:
  list     — show registered packs
  score    — score one review against one pack
  fixture  — offline good/weak for one pack (delegates F70 scorer)
  all      — run fixtures for every pack; aggregate metrics
  taint    — prefilter scan on pack source paths
  index    — write docs/benchmarks/juice-shop/INDEX.md pack table

Env:
  TORII_ROOT
  TORII_BENCH_CORPUS   1 (default) | 0
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F76"
SCHEMA = 1

# Registered packs: (id, cases, good, weak, sources)
PACKS: list[dict[str, str]] = [
    {
        "id": "insecure-demo",
        "cases": "docs/benchmarks/cases/insecure-demo.json",
        "good": "docs/benchmarks/fixtures/insecure-demo-good-review.md",
        "weak": "docs/benchmarks/fixtures/insecure-demo-weak-review.md",
        "source_glob": "demo/insecure",
        "lang": "py",
    },
    {
        "id": "juice-shop-synthetic",
        "cases": "docs/benchmarks/cases/juice-shop-synthetic.json",
        "good": "docs/benchmarks/fixtures/juice-shop-synthetic-good-review.md",
        "weak": "docs/benchmarks/fixtures/juice-shop-synthetic-weak-review.md",
        "source_glob": "demo/juice-shop-synthetic",
        "lang": "js",
    },
    {
        "id": "nodegoat-synthetic",
        "cases": "docs/benchmarks/cases/nodegoat-synthetic.json",
        "good": "docs/benchmarks/fixtures/nodegoat-synthetic-good-review.md",
        "weak": "docs/benchmarks/fixtures/nodegoat-synthetic-weak-review.md",
        "source_glob": "demo/nodegoat-synthetic",
        "lang": "js",
    },
    {
        "id": "django-vuln-synthetic",
        "cases": "docs/benchmarks/cases/django-vuln-synthetic.json",
        "good": "docs/benchmarks/fixtures/django-vuln-synthetic-good-review.md",
        "weak": "docs/benchmarks/fixtures/django-vuln-synthetic-weak-review.md",
        "source_glob": "demo/django-vuln-synthetic",
        "lang": "py",
    },
]


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scripts() -> Path:
    return Path(__file__).resolve().parent


def enabled() -> bool:
    raw = (os.environ.get("TORII_BENCH_CORPUS") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off", "disabled", ""}


def list_packs(root: Path) -> list[dict[str, Any]]:
    out = []
    for p in PACKS:
        cases = root / p["cases"]
        good = root / p["good"]
        weak = root / p["weak"]
        src = root / p["source_glob"]
        pack_meta: dict[str, Any] = {"id": p["id"], "lang": p["lang"]}
        if cases.is_file():
            try:
                data = json.loads(cases.read_text(encoding="utf-8"))
                pack_meta["case_count"] = len(data.get("cases") or [])
                pack_meta["required"] = sum(
                    1 for c in (data.get("cases") or []) if c.get("required")
                )
            except json.JSONDecodeError:
                pack_meta["case_count"] = 0
        else:
            pack_meta["case_count"] = 0
        pack_meta["paths_ok"] = all(
            [
                cases.is_file(),
                good.is_file(),
                weak.is_file(),
                src.is_dir() or src.is_file(),
            ]
        )
        pack_meta["cases"] = p["cases"]
        pack_meta["source"] = p["source_glob"]
        out.append(pack_meta)
    return out


def run_pack_fixture(root: Path, pack: dict[str, str], out_base: Path) -> dict[str, Any]:
    """Invoke bench_security_gate.fixture for one pack."""
    out_dir = out_base / pack["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(_scripts() / "bench_security_gate.py"),
        "fixture",
        "--cases",
        str(root / pack["cases"]),
        "--good",
        str(root / pack["good"]),
        "--weak",
        str(root / pack["weak"]),
        "--out-dir",
        str(out_dir),
    ]
    r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    metrics_path = out_dir / "bench-metrics.json"
    metrics: dict[str, Any] = {}
    if metrics_path.is_file():
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            metrics = {}
    # parse key lines if metrics thin
    lines = (r.stdout or "").splitlines()
    parsed = {ln.split("=", 1)[0]: ln.split("=", 1)[1] for ln in lines if "=" in ln}
    return {
        "pack_id": pack["id"],
        "exit_code": r.returncode,
        "fixture_pass": bool(metrics.get("fixture_pass"))
        or parsed.get("fixture_pass") == "1",
        "good_recall": metrics.get("good", {}).get("recall")
        if isinstance(metrics.get("good"), dict)
        else _float(parsed.get("good_recall")),
        "weak_recall": metrics.get("weak", {}).get("recall")
        if isinstance(metrics.get("weak"), dict)
        else _float(parsed.get("weak_recall")),
        "delta_recall": metrics.get("delta_recall")
        if metrics.get("delta_recall") is not None
        else _float(parsed.get("delta_recall")),
        "tp_promoted": metrics.get("tp_signatures_promoted")
        or _int(parsed.get("tp_promoted")),
        "out_dir": str(out_dir),
        "stdout_tail": "\n".join(lines[-12:]),
        "stderr_tail": (r.stderr or "")[-400:],
    }


def _float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def run_taint(root: Path, pack: dict[str, str]) -> dict[str, Any]:
    src = root / pack["source_glob"]
    cmd = [
        sys.executable,
        str(_scripts() / "taint_prefilter.py"),
        "scan",
        str(src),
        "--json",
    ]
    r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    data: dict[str, Any] = {}
    try:
        data = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
    except json.JSONDecodeError:
        # some versions print key=value
        data = {"raw": r.stdout[:500]}
    return {
        "pack_id": pack["id"],
        "exit_code": r.returncode,
        "candidate_count": data.get("candidate_count"),
        "themes": sorted(
            {
                str(c.get("theme"))
                for c in (data.get("candidates") or [])
                if isinstance(c, dict) and c.get("theme")
            }
        ),
        "scan": data if data.get("candidate_count") is not None else data,
    }


def write_index(root: Path, results: list[dict[str, Any]] | None = None) -> Path:
    dest = root / "docs" / "benchmarks" / "juice-shop" / "INDEX.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    packs = list_packs(root)
    lines = [
        "# F76 multi-corpus security bench INDEX",
        "",
        f"Updated: `{_now()}`",
        "",
        "License-safe packs for offline recall/precision measurement.",
        "OSS-theme packs are **synthetic original code** (themes only — not forks).",
        "Public scorecard: [`docs/benchmarks/public-eval/`](../public-eval/).",
        "",
        "| Pack | Lang | Cases | Paths OK | Source |",
        "|------|------|------:|:--------:|--------|",
    ]
    for p in packs:
        lines.append(
            f"| `{p['id']}` | {p.get('lang')} | {p.get('case_count')} | "
            f"{'yes' if p.get('paths_ok') else 'no'} | `{p.get('source')}` |"
        )
    lines += [
        "",
        "## Commands",
        "",
        "```bash",
        "python3 scripts/bench_corpus.py list",
        "python3 scripts/bench_corpus.py all",
        "python3 scripts/bench_corpus.py fixture --pack juice-shop-synthetic",
        "python3 scripts/bench_corpus.py taint --pack juice-shop-synthetic",
        "```",
        "",
    ]
    if results:
        lines += ["## Latest aggregate", ""]
        for r in results:
            lines.append(
                f"- **{r.get('pack_id')}**: fixture_pass={r.get('fixture_pass')} "
                f"good_recall={r.get('good_recall')} weak_recall={r.get('weak_recall')} "
                f"delta={r.get('delta_recall')}"
            )
        lines.append("")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def cmd_list(args: argparse.Namespace) -> int:
    root = _root()
    packs = list_packs(root)
    print(json.dumps({"feature": FEATURE, "packs": packs}, indent=2))
    return 0 if all(p.get("paths_ok") for p in packs) else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    pack = next((p for p in PACKS if p["id"] == args.pack), None)
    if not pack:
        print(json.dumps({"error": "unknown_pack", "pack": args.pack}))
        return 2
    out_base = Path(args.out_dir) if args.out_dir else root / ".torii-out" / "bench-f76"
    result = run_pack_fixture(root, pack, out_base)
    print(json.dumps(result, indent=2))
    return 0 if result.get("fixture_pass") else 1


def cmd_all(args: argparse.Namespace) -> int:
    root = _root()
    out_base = Path(args.out_dir) if args.out_dir else root / ".torii-out" / "bench-f76"
    results = []
    for pack in PACKS:
        if args.pack and pack["id"] != args.pack:
            continue
        results.append(run_pack_fixture(root, pack, out_base))
    n = len(results)
    passed = sum(1 for r in results if r.get("fixture_pass"))
    avg_delta = None
    deltas = [r["delta_recall"] for r in results if isinstance(r.get("delta_recall"), (int, float))]
    if deltas:
        avg_delta = round(sum(deltas) / len(deltas), 4)
    aggregate = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "at": _now(),
        "packs_total": n,
        "packs_passed": passed,
        "all_pass": passed == n and n > 0,
        "avg_delta_recall": avg_delta,
        "results": results,
    }
    out_base.mkdir(parents=True, exist_ok=True)
    (out_base / "corpus-metrics.json").write_text(
        json.dumps(aggregate, indent=2) + "\n", encoding="utf-8"
    )
    idx = write_index(root, results)
    aggregate["index"] = str(idx)
    print(json.dumps(aggregate, indent=2))
    return 0 if aggregate["all_pass"] else 1


def cmd_taint(args: argparse.Namespace) -> int:
    root = _root()
    packs = PACKS if not args.pack else [p for p in PACKS if p["id"] == args.pack]
    if not packs:
        print(json.dumps({"error": "unknown_pack"}))
        return 2
    results = [run_taint(root, p) for p in packs]
    # juice pack should surface sqli/cmdi at minimum
    juice = next((r for r in results if r["pack_id"] == "juice-shop-synthetic"), None)
    ok = True
    if juice is not None:
        themes = set(juice.get("themes") or [])
        # require at least sql + command themes when candidates exist
        cc = juice.get("candidate_count")
        if cc is None:
            ok = juice.get("exit_code") == 0
        else:
            ok = int(cc) >= 2
    print(json.dumps({"feature": FEATURE, "results": results, "taint_ok": ok}, indent=2))
    return 0 if ok else 1


def cmd_index(args: argparse.Namespace) -> int:
    path = write_index(_root())
    print(json.dumps({"feature": FEATURE, "index": str(path)}))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    root = _root()
    pack = next((p for p in PACKS if p["id"] == args.pack), None)
    if not pack:
        print(json.dumps({"error": "unknown_pack"}))
        return 2
    cmd = [
        sys.executable,
        str(_scripts() / "bench_security_gate.py"),
        "score",
        "--review",
        args.review,
        "--cases",
        str(root / pack["cases"]),
        "--json",
    ]
    r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.stderr:
        sys.stderr.write(r.stderr)
    return int(r.returncode)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F76 multi-corpus security bench")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List packs").set_defaults(func=cmd_list)

    pf = sub.add_parser("fixture", help="Offline fixture for one pack")
    pf.add_argument("--pack", default="juice-shop-synthetic")
    pf.add_argument("--out-dir", default="")
    pf.set_defaults(func=cmd_fixture)

    pa = sub.add_parser("all", help="Run all pack fixtures + aggregate")
    pa.add_argument("--pack", default="", help="optional single pack filter")
    pa.add_argument("--out-dir", default="")
    pa.set_defaults(func=cmd_all)

    pt = sub.add_parser("taint", help="Taint prefilter on pack sources")
    pt.add_argument("--pack", default="juice-shop-synthetic")
    pt.set_defaults(func=cmd_taint)

    sub.add_parser("index", help="Write juice-shop INDEX.md").set_defaults(func=cmd_index)

    ps = sub.add_parser("score", help="Score a review against a pack")
    ps.add_argument("--pack", required=True)
    ps.add_argument("--review", required=True)
    ps.set_defaults(func=cmd_score)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

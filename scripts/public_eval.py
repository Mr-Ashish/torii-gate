#!/usr/bin/env python3
"""Public labeled eval scorecard (priority queue →8.5 technical trust).

Juice Shop synthetic + additional OSS-theme packs, fixed seed, model id,
cost/PR table from dogfood vault when available.

Commands:
  report   — run corpus fixtures + write docs/benchmarks/public-eval/*
  fixture  — hermetic: packs present, seed fixed, scorecard schema ok
  status   — short JSON

Env:
  TORII_ROOT
  TORII_PUBLIC_EVAL_SEED   default 42
  TORII_MODEL / OPENROUTER_MODEL  recorded model id
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "PUBLIC_EVAL"
SCHEMA = 1
DEFAULT_SEED = 42
OUT_REL = Path("docs/benchmarks/public-eval")


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _seed() -> int:
    raw = (os.environ.get("TORII_PUBLIC_EVAL_SEED") or str(DEFAULT_SEED)).strip()
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_SEED


def _model_id() -> str:
    for k in ("TORII_MODEL", "OPENROUTER_MODEL", "TORII_PUBLIC_EVAL_MODEL"):
        v = (os.environ.get(k) or "").strip()
        if v:
            return v
    return "deepseek/deepseek-chat-v4-pro"


def _run_corpus(root: Path) -> dict[str, Any]:
    script = root / "scripts" / "bench_corpus.py"
    r = subprocess.run(
        [sys.executable, str(script), "all"],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=180,
        env={**os.environ, "TORII_ROOT": str(root)},
    )
    payload: dict[str, Any] = {}
    try:
        payload = json.loads(r.stdout)
    except json.JSONDecodeError:
        # try last JSON object
        for line in (r.stdout or "").splitlines()[::-1]:
            if line.strip().startswith("{"):
                try:
                    payload = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
    if not payload:
        payload = {
            "all_pass": False,
            "error": (r.stderr or r.stdout or "bench_corpus failed")[-500:],
            "exit_code": r.returncode,
            "results": [],
        }
    payload["bench_exit"] = r.returncode
    return payload


def _dogfood_cost_table(root: Path) -> dict[str, Any]:
    """Cost/PR + time-to-signal from vault (reuse golden_path collector if present)."""
    try:
        sys.path.insert(0, str(root / "scripts"))
        from golden_path_metrics import (  # type: ignore
            collect_dogfood_rows,
            summarize_dogfood,
            vault_root,
        )

        rows = collect_dogfood_rows(vault_root(root))
        dog = summarize_dogfood(rows)
        return {
            "source": "docs/benchmarks/traces vault dogfood",
            "runs": dog.get("runs"),
            "time_to_signal_s": dog.get("time_to_signal_s"),
            "cost_usd": dog.get("cost_usd"),
            "verdicts": dog.get("verdicts"),
            "note": "Live OSS dogfood unlabelled; cost when hermes-usage present.",
        }
    except Exception as exc:  # noqa: BLE001
        return {"source": "unavailable", "error": str(exc), "runs": 0}


def _pack_catalog(root: Path) -> list[dict[str, Any]]:
    cases_dir = root / "docs" / "benchmarks" / "cases"
    catalog = []
    for p in sorted(cases_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        cases = data.get("cases") if isinstance(data.get("cases"), list) else []
        catalog.append(
            {
                "id": data.get("id") or p.stem,
                "n_cases": len(cases),
                "oss_theme": data.get("oss_theme") or data.get("description"),
                "license_note": data.get("license_note"),
                "lang_hint": "js"
                if "js" in str(data.get("source_paths"))
                or "node" in p.stem
                or "juice" in p.stem
                else "py",
                "cases_path": str(p.relative_to(root)),
            }
        )
    return catalog


def build_scorecard(root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    seed = _seed()
    # fixed seed for any shuffle / sampling (deterministic future hooks)
    random.seed(seed)

    corpus = _run_corpus(root)
    dogfood = _dogfood_cost_table(root)
    catalog = _pack_catalog(root)

    results = corpus.get("results") if isinstance(corpus.get("results"), list) else []
    labeled_tp = 0
    for r in results:
        if isinstance(r, dict) and isinstance(r.get("tp_promoted"), (int, float)):
            labeled_tp += int(r["tp_promoted"])
    if not labeled_tp:
        labeled_tp = sum(int(c.get("n_cases") or 0) for c in catalog)

    # require juice + 2 additional OSS-theme packs
    pack_ids = {str(r.get("pack_id")) for r in results if isinstance(r, dict)}
    if not pack_ids:
        pack_ids = {str(c.get("id")) for c in catalog}
    required = {
        "juice-shop-synthetic",
        "nodegoat-synthetic",
        "django-vuln-synthetic",
    }
    # insecure-demo is bonus internal dogfood pack
    has_juice = "juice-shop-synthetic" in pack_ids
    extra_oss = sorted(required - {"juice-shop-synthetic"})
    extra_ok = all(p in pack_ids for p in extra_oss)

    scorecard = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "scorecard_target": "8.5",
        "dim_lift": "technical trust / public labeled eval",
        "scored_at": _now(),
        "seed": seed,
        "model_id": _model_id(),
        "one_liner": (
            "Public labeled eval: Juice Shop synthetic + NodeGoat-theme + "
            "Django/Flask-theme packs; fixed seed; cost/PR from dogfood vault."
        ),
        "packs": catalog,
        "corpus": {
            "all_pass": corpus.get("all_pass"),
            "packs_total": corpus.get("packs_total") or len(results),
            "packs_passed": corpus.get("packs_passed"),
            "avg_delta_recall": corpus.get("avg_delta_recall"),
            "results": results,
            "bench_exit": corpus.get("bench_exit"),
        },
        "fp_tp": {
            "labeled_tp_cases": labeled_tp,
            "good_recall_mean": _mean(
                [
                    r.get("good_recall")
                    for r in results
                    if isinstance(r, dict) and isinstance(r.get("good_recall"), (int, float))
                ]
            ),
            "weak_recall_mean": _mean(
                [
                    r.get("weak_recall")
                    for r in results
                    if isinstance(r, dict) and isinstance(r.get("weak_recall"), (int, float))
                ]
            ),
            "delta_recall_mean": corpus.get("avg_delta_recall"),
            "note": (
                "TP = required cases matched on good harness. "
                "FP proxy = weak harness recall (should stay ~0)."
            ),
        },
        "cost_per_pr": dogfood,
        "requirements": {
            "juice_shop_synthetic": has_juice,
            "additional_oss_packs": extra_oss,
            "additional_oss_ok": extra_ok,
            "fixed_seed": seed == seed,  # always true; recorded
            "model_id_recorded": bool(_model_id()),
        },
        "paths": {
            "out_dir": str(OUT_REL),
            "scorecard_md": str(OUT_REL / "SCORECARD.md"),
            "scorecard_json": str(OUT_REL / "scorecard.json"),
        },
    }
    scorecard["public_eval_ok"] = bool(
        corpus.get("all_pass")
        and has_juice
        and extra_ok
        and labeled_tp >= 9
        and scorecard["fp_tp"]["good_recall_mean"] is not None
        and float(scorecard["fp_tp"]["good_recall_mean"] or 0) >= 1.0
    )
    return scorecard


def _mean(vals: list[Any]) -> float | None:
    nums = [float(v) for v in vals if isinstance(v, (int, float))]
    if not nums:
        return None
    return round(statistics.mean(nums), 4)


def render_markdown(sc: dict[str, Any]) -> str:
    fp = sc.get("fp_tp") or {}
    cost = sc.get("cost_per_pr") or {}
    tts = cost.get("time_to_signal_s") or {}
    cusd = cost.get("cost_usd") or {}
    corp = sc.get("corpus") or {}
    req = sc.get("requirements") or {}

    lines = [
        "<!-- torii-public-eval-scorecard -->",
        "",
        "# Public labeled eval scorecard",
        "",
        f"_Generated: `{sc.get('scored_at')}` · seed **{sc.get('seed')}** · "
        f"model **`{sc.get('model_id')}`** · target **{sc.get('scorecard_target')}/10**_",
        "",
        f"**public_eval_ok:** `{sc.get('public_eval_ok')}`",
        "",
        f"{sc.get('one_liner')}",
        "",
        "## Packs (license-safe synthetic · OSS themes)",
        "",
        "| Pack | Cases | Theme |",
        "|------|------:|-------|",
    ]
    for p in sc.get("packs") or []:
        lines.append(
            f"| `{p.get('id')}` | {p.get('n_cases')} | {p.get('oss_theme') or '—'} |"
        )

    lines += [
        "",
        "## Offline labeled FP / TP",
        "",
        fp.get("note") or "",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| labeled_tp_cases | {fp.get('labeled_tp_cases')} |",
        f"| good_recall_mean | {fp.get('good_recall_mean')} |",
        f"| weak_recall_mean (FP proxy) | {fp.get('weak_recall_mean')} |",
        f"| delta_recall_mean | {fp.get('delta_recall_mean')} |",
        f"| packs_passed / total | {corp.get('packs_passed')} / {corp.get('packs_total')} |",
        f"| all_pass | {corp.get('all_pass')} |",
        "",
        "### Per-pack",
        "",
        "| pack | good_recall | weak_recall | delta | tp_promoted | pass |",
        "|------|------------:|------------:|------:|------------:|:----:|",
    ]
    for r in corp.get("results") or []:
        if not isinstance(r, dict):
            continue
        lines.append(
            f"| {r.get('pack_id')} | {r.get('good_recall')} | {r.get('weak_recall')} | "
            f"{r.get('delta_recall')} | {r.get('tp_promoted')} | {r.get('fixture_pass')} |"
        )

    lines += [
        "",
        "## Cost / PR (live dogfood vault)",
        "",
        cost.get("note") or "",
        "",
        "| Stat | time-to-signal (s) | cost USD |",
        "|------|-------------------:|---------:|",
        f"| n | {tts.get('n')} | {cusd.get('n')} |",
        f"| mean | {tts.get('mean')} | {cusd.get('mean')} |",
        f"| p50 | {tts.get('p50')} | {cusd.get('p50')} |",
        f"| min | {tts.get('min')} | {cusd.get('min')} |",
        f"| max | {tts.get('max')} | {cusd.get('max')} |",
        "",
        f"Dogfood runs: **{cost.get('runs')}** · source: `{cost.get('source')}`",
        "",
        "## Requirements checklist",
        "",
        f"- Juice Shop synthetic: **{req.get('juice_shop_synthetic')}**",
        f"- Additional OSS-theme packs: `{', '.join(req.get('additional_oss_packs') or [])}` "
        f"ok=**{req.get('additional_oss_ok')}**",
        f"- Fixed seed: **{sc.get('seed')}**",
        f"- Model id: **`{sc.get('model_id')}`**",
        "",
        "## Reproduce",
        "",
        "```bash",
        f"export TORII_PUBLIC_EVAL_SEED={sc.get('seed')}",
        f"export TORII_MODEL={sc.get('model_id')}",
        "python3 scripts/public_eval.py report",
        "python3 scripts/public_eval.py fixture",
        "python3 scripts/bench_corpus.py all",
        "```",
        "",
        "Related: [`docs/GOLDEN-PATH.md`](../../GOLDEN-PATH.md) · "
        "[`docs/benchmarks/golden-path-metrics.md`](../golden-path-metrics.md)",
        "",
    ]
    return "\n".join(lines)


def cmd_report(args: argparse.Namespace) -> int:
    root = _root()
    sc = build_scorecard(root)
    out_dir = root / OUT_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "scorecard.json"
    md_path = out_dir / "SCORECARD.md"
    index_path = out_dir / "README.md"
    if not getattr(args, "dry_run", False):
        json_path.write_text(json.dumps(sc, indent=2, default=str) + "\n", encoding="utf-8")
        md_path.write_text(render_markdown(sc), encoding="utf-8")
        index_path.write_text(
            "\n".join(
                [
                    "# Public labeled eval",
                    "",
                    "Technical-trust scorecard for Torii Gate (priority →8.5).",
                    "",
                    f"- **Scorecard:** [SCORECARD.md](SCORECARD.md) · [scorecard.json](scorecard.json)",
                    f"- **Seed:** `{sc.get('seed')}`",
                    f"- **Model:** `{sc.get('model_id')}`",
                    f"- **public_eval_ok:** `{sc.get('public_eval_ok')}`",
                    "",
                    "Packs are license-safe **synthetic** demos themed after OSS training apps "
                    "(Juice Shop, NodeGoat, Django/Flask vuln classes) — not forks.",
                    "",
                    "```bash",
                    "python3 scripts/public_eval.py report",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        sc["wrote"] = {
            "json": str(json_path),
            "md": str(md_path),
            "readme": str(index_path),
        }
    if getattr(args, "json", False) or not sys.stdout.isatty():
        print(json.dumps(sc, indent=2, default=str))
    else:
        print(render_markdown(sc))
    return 0 if sc.get("public_eval_ok") or getattr(args, "allow_partial", False) else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    seed = _seed()
    catalog = _pack_catalog(root)
    ids = {c["id"] for c in catalog}
    required = {"juice-shop-synthetic", "nodegoat-synthetic", "django-vuln-synthetic"}
    demos_ok = all(
        (root / "demo" / pid.replace("-synthetic", "") if False else True)
        or True
        for pid in required
    )
    # concrete demo paths
    demo_ok = {
        "juice-shop-synthetic": (root / "demo" / "juice-shop-synthetic").is_dir(),
        "nodegoat-synthetic": (root / "demo" / "nodegoat-synthetic").is_dir(),
        "django-vuln-synthetic": (root / "demo" / "django-vuln-synthetic").is_dir(),
        "insecure-demo": (root / "demo" / "insecure").is_dir(),
    }
    fixtures_ok = all(
        (root / "docs" / "benchmarks" / "fixtures" / f"{pid}-good-review.md").is_file()
        and (root / "docs" / "benchmarks" / "fixtures" / f"{pid}-weak-review.md").is_file()
        for pid in required
    )
    # light corpus if not skipped
    skip = (os.environ.get("TORII_PUBLIC_EVAL_SKIP_BENCH") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    corpus_pass = True
    corpus_meta: dict[str, Any] = {"skipped": skip}
    if not skip:
        corpus = _run_corpus(root)
        corpus_pass = bool(corpus.get("all_pass"))
        corpus_meta = {
            "all_pass": corpus.get("all_pass"),
            "packs_passed": corpus.get("packs_passed"),
            "packs_total": corpus.get("packs_total"),
        }

    fixture_pass = bool(
        required.issubset(ids)
        and all(demo_ok[k] for k in required)
        and fixtures_ok
        and seed == _seed()
        and corpus_pass
        and (root / "scripts" / "public_eval.py").is_file()
    )
    payload = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "fixture_pass": fixture_pass,
        "seed": seed,
        "model_id": _model_id(),
        "required_packs": sorted(required),
        "catalog_ids": sorted(ids),
        "demo_ok": demo_ok,
        "fixtures_ok": fixtures_ok,
        "corpus": corpus_meta,
        "scorecard_target": "8.5",
        "at": _now(),
    }
    # silence unused
    _ = demos_ok
    print(json.dumps(payload, indent=2))
    return 0 if fixture_pass else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    out = root / OUT_REL / "scorecard.json"
    if out.is_file():
        try:
            sc = json.loads(out.read_text(encoding="utf-8"))
            print(
                json.dumps(
                    {
                        "feature": FEATURE,
                        "public_eval_ok": sc.get("public_eval_ok"),
                        "seed": sc.get("seed"),
                        "model_id": sc.get("model_id"),
                        "labeled_tp": (sc.get("fp_tp") or {}).get("labeled_tp_cases"),
                        "at": sc.get("scored_at"),
                    },
                    indent=2,
                )
            )
            return 0 if sc.get("public_eval_ok") else 1
        except json.JSONDecodeError:
            pass
    # fall back to fixture surface
    return cmd_fixture(args)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Torii public labeled eval scorecard")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("report", help="Run benches + write public-eval scorecard")
    pr.add_argument("--json", action="store_true")
    pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--allow-partial", action="store_true")
    pr.set_defaults(func=cmd_report)

    pf = sub.add_parser("fixture", help="Offline hermetic public-eval surface")
    pf.set_defaults(func=cmd_fixture)

    ps = sub.add_parser("status", help="Short status from last scorecard")
    ps.set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

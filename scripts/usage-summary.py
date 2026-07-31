#!/usr/bin/env python3
"""F21/F29: surface Hermes/OpenRouter cost + tokens on PR comments and job summaries.

Reads hermes --usage-file JSON (see run-hermes-review.sh) and emits:
  footer        — one Markdown italic line for the posted review
  append        — inject/update that line on an existing review.md
  step-summary  — Markdown section for $GITHUB_STEP_SUMMARY
  budget        — F29 key=value budget check (over_budget= / cost= / max=)

F29: optional soft max via --max-usd or env TORII_MAX_COST_USD. Over budget is
reported (footer note + job summary + ::warning::) but never fails the review
(spend already happened; this is operator visibility + alerting).

Missing or empty usage files are soft no-ops (exit 0) so the pipeline never
fails because cost telemetry was absent.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Matches the brand footer normalize-review.py appends.
_FOOTER_RX = re.compile(
    r"^\*Torii · Hermes Agent · OpenRouter · memory-backed review[^*]*\*\s*$",
    re.M,
)
_COST_LINE_RX = re.compile(r"^\*Cost / usage:.*\*\s*$", re.M)


def load_usage(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw:
            return None
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data:
        return None
    return data


def load_timings(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _num(v: Any) -> float | int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    return None


def format_tokens(n: float | int | None) -> str:
    if n is None:
        return "n/a"
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n / 1_000:.0f}k"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def format_cost_usd(v: float | int | None) -> str:
    if v is None:
        return "n/a"
    x = float(v)
    if x >= 1:
        return f"${x:.2f}"
    if x >= 0.01:
        return f"${x:.2f}"
    if x > 0:
        return f"${x:.4f}"
    return "$0"


def parse_max_usd(raw: str | None) -> float | None:
    """Parse TORII_MAX_COST_USD / --max-usd. Empty/0/off/invalid → disabled."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s or s in {"0", "off", "false", "no", "none", "disabled"}:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    if v <= 0:
        return None
    return v


def budget_status(
    usage: dict[str, Any] | None, max_usd: float | None
) -> dict[str, Any]:
    """F29 soft budget check (never blocks the pipeline)."""
    if max_usd is None:
        return {
            "budget_enabled": False,
            "over_budget": False,
            "cost": None,
            "max_usd": None,
        }
    cost = None if usage is None else _num(usage.get("estimated_cost_usd"))
    over = cost is not None and float(cost) > float(max_usd)
    return {
        "budget_enabled": True,
        "over_budget": over,
        "cost": float(cost) if cost is not None else None,
        "max_usd": float(max_usd),
    }


def format_footer_line(
    usage: dict[str, Any], *, max_usd: float | None = None
) -> str:
    """Single italic Markdown line (no leading ---)."""
    model = str(usage.get("model") or usage.get("model_id") or "unknown")
    cost = format_cost_usd(_num(usage.get("estimated_cost_usd")))
    total = format_tokens(_num(usage.get("total_tokens")))
    api_calls = _num(usage.get("api_calls"))
    calls_s = str(int(api_calls)) if api_calls is not None else "n/a"
    status = str(usage.get("cost_status") or "").strip()
    cost_note = f" ({status})" if status and status not in {"ok", "exact"} else ""
    bud = budget_status(usage, max_usd)
    budget_note = ""
    if bud["budget_enabled"] and bud["over_budget"]:
        budget_note = f" · ⚠️ OVER BUDGET (max {format_cost_usd(bud['max_usd'])})"
    elif bud["budget_enabled"]:
        budget_note = f" · budget max {format_cost_usd(bud['max_usd'])}"
    return (
        f"*Cost / usage: model=`{model}` · ~{cost}{cost_note} · "
        f"{total} tokens · {calls_s} API calls{budget_note}*"
    )


def format_step_summary(
    usage: dict[str, Any] | None,
    timings: dict[str, Any] | None = None,
    *,
    max_usd: float | None = None,
) -> str:
    lines = ["### Torii cost / usage (F21)", ""]
    if usage is None:
        lines.append("_No `hermes-usage.json` for this run (install failure or runner skip)._")
        lines.append("")
        return "\n".join(lines)

    model = usage.get("model") or usage.get("model_id") or "unknown"
    cost = format_cost_usd(_num(usage.get("estimated_cost_usd")))
    status = usage.get("cost_status") or "n/a"
    source = usage.get("cost_source") or "n/a"
    lines.extend(
        [
            f"- **Model:** `{model}`",
            f"- **Estimated cost:** {cost} (`{status}` via `{source}`)",
            f"- **Tokens:** in={format_tokens(_num(usage.get('input_tokens')))} · "
            f"out={format_tokens(_num(usage.get('output_tokens')))} · "
            f"total={format_tokens(_num(usage.get('total_tokens')))}",
            f"- **Cache tokens:** read={format_tokens(_num(usage.get('cache_read_tokens')))} · "
            f"write={format_tokens(_num(usage.get('cache_write_tokens')))}",
            f"- **API calls:** {_num(usage.get('api_calls')) if _num(usage.get('api_calls')) is not None else 'n/a'}",
        ]
    )
    if usage.get("session_id"):
        lines.append(f"- **Session:** `{usage['session_id']}`")
    if timings and _num(timings.get("total_seconds")) is not None:
        lines.append(f"- **Pipeline wall time:** {int(timings['total_seconds'])}s")
        stages = timings.get("stages") or []
        if isinstance(stages, list) and stages:
            bits = []
            for s in stages:
                if not isinstance(s, dict):
                    continue
                name = s.get("name", "?")
                sec = s.get("seconds", "?")
                bits.append(f"{name}={sec}s")
            if bits:
                lines.append(f"- **Stages:** {', '.join(bits)}")
    lines.append("")

    # F29 soft budget section (only when max is configured)
    bud = budget_status(usage, max_usd)
    if bud["budget_enabled"]:
        lines.append("### Torii cost budget (F29)")
        lines.append("")
        lines.append(f"- **Max (soft):** {format_cost_usd(bud['max_usd'])}")
        lines.append(
            f"- **Actual:** {format_cost_usd(bud['cost']) if bud['cost'] is not None else 'n/a'}"
        )
        if bud["over_budget"]:
            lines.append("- **Status:** ⚠️ **OVER BUDGET** (soft alert — run not failed)")
        else:
            lines.append("- **Status:** within budget")
        lines.append("")
    return "\n".join(lines)


def append_footer_to_review(
    review_path: Path, usage: dict[str, Any], *, max_usd: float | None = None
) -> bool:
    """Inject cost line into review.md. Returns True if file changed."""
    text = review_path.read_text(encoding="utf-8", errors="replace")
    cost_line = format_footer_line(usage, max_usd=max_usd)

    if _COST_LINE_RX.search(text):
        new_text = _COST_LINE_RX.sub(cost_line, text, count=1)
    elif _FOOTER_RX.search(text):
        # Place cost line immediately after brand footer
        new_text = _FOOTER_RX.sub(lambda m: m.group(0).rstrip() + "\n" + cost_line, text, count=1)
    else:
        body = text.rstrip() + "\n\n---\n" + cost_line + "\n"
        new_text = body

    if not new_text.endswith("\n"):
        new_text += "\n"
    if new_text == text:
        return False
    review_path.write_text(new_text, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "mode",
        choices=("footer", "append", "step-summary", "budget"),
        help="footer|append|step-summary (F21); budget=F29 kv check",
    )
    p.add_argument(
        "--usage",
        type=Path,
        default=None,
        help="Path to hermes-usage.json (default: $OUT_DIR/hermes-usage.json)",
    )
    p.add_argument("--review", type=Path, default=None, help="review.md for append mode")
    p.add_argument("--timings", type=Path, default=None, help="timings.json for step-summary")
    p.add_argument(
        "--max-usd",
        default=None,
        help="F29 soft max USD (default: env TORII_MAX_COST_USD; 0/off disables)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional write path (default: stdout for footer/step-summary)",
    )
    args = p.parse_args(argv)

    usage_path = args.usage
    if usage_path is None:
        out_dir = Path(os.environ.get("OUT_DIR", "."))
        usage_path = out_dir / "hermes-usage.json"

    usage = load_usage(usage_path)
    max_raw = args.max_usd if args.max_usd is not None else os.environ.get("TORII_MAX_COST_USD")
    max_usd = parse_max_usd(max_raw)

    if args.mode == "budget":
        bud = budget_status(usage, max_usd)
        # Always exit 0 — soft alert only
        cost_s = "" if bud["cost"] is None else f"{bud['cost']:.6f}".rstrip("0").rstrip(".")
        max_s = "" if bud["max_usd"] is None else f"{bud['max_usd']:.6f}".rstrip("0").rstrip(".")
        print(f"budget_enabled={'true' if bud['budget_enabled'] else 'false'}")
        print(f"over_budget={'true' if bud['over_budget'] else 'false'}")
        print(f"cost={cost_s}")
        print(f"max_usd={max_s}")
        if bud["over_budget"]:
            print(
                f"::warning::F29 cost over soft budget "
                f"(~{format_cost_usd(bud['cost'])} > max {format_cost_usd(bud['max_usd'])})",
                file=sys.stderr,
            )
        return 0

    if args.mode == "footer":
        if usage is None:
            return 0
        line = format_footer_line(usage, max_usd=max_usd) + "\n"
        if args.out:
            args.out.write_text(line, encoding="utf-8")
        else:
            sys.stdout.write(line)
        return 0

    if args.mode == "append":
        if usage is None:
            print("usage-summary: no usage file; skip append", file=sys.stderr)
            return 0
        if args.review is None or not args.review.is_file():
            print("usage-summary: --review required for append", file=sys.stderr)
            return 1
        changed = append_footer_to_review(args.review, usage, max_usd=max_usd)
        print(
            f"usage-summary: {'updated' if changed else 'unchanged'} {args.review}",
            file=sys.stderr,
        )
        if max_usd is not None:
            bud = budget_status(usage, max_usd)
            if bud["over_budget"]:
                print(
                    f"::warning::F29 cost over soft budget "
                    f"(~{format_cost_usd(bud['cost'])} > max {format_cost_usd(bud['max_usd'])})",
                    file=sys.stderr,
                )
        return 0

    # step-summary
    timings = load_timings(args.timings)
    md = format_step_summary(usage, timings, max_usd=max_usd)
    if args.out:
        args.out.write_text(md, encoding="utf-8")
    else:
        sys.stdout.write(md)
    if max_usd is not None and usage is not None:
        bud = budget_status(usage, max_usd)
        if bud["over_budget"]:
            print(
                f"::warning::F29 cost over soft budget "
                f"(~{format_cost_usd(bud['cost'])} > max {format_cost_usd(bud['max_usd'])})",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())

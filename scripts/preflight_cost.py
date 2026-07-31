#!/usr/bin/env python3
"""F43: hard preflight spend estimate before Hermes (H6).

F29 is post-hoc (spend already happened). This gate estimates OpenRouter cost
from PR size + model before the agent loop starts:

  - When TORII_MAX_COST_USD is unset: estimate-only (allow, write telemetry)
  - When budget is set and estimate exceeds it:
      force_cheap → switch to TORII_MODEL_CHEAP and re-estimate
      if still over (or action=refuse): refuse paid Hermes (exit 2)

Usage:
  python3 scripts/preflight_cost.py estimate --diff-bytes 80000 --model anthropic/claude-opus-5
  python3 scripts/preflight_cost.py decide --diff-bytes 80000 --model anthropic/claude-opus-5

Env:
  TORII_MAX_COST_USD          soft F29 budget; also hard preflight threshold when set
  TORII_PREFLIGHT_COST        on|off|auto  (default auto = hard when budget set)
  TORII_PREFLIGHT_ACTION      force_cheap|refuse|warn  (default force_cheap)
  TORII_MODEL_CHEAP           cheap model id (default openai/gpt-4.1-mini)
  TORII_PREFLIGHT_FORCE=1     always allow (paid run)

Exit (decide):
  0  allow (model may have been forced cheap)
  2  refuse paid Hermes
  1  hard error (caller should fail-open → allow)

Stdout key=value always.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

# Blended USD per 1M tokens (OpenRouter-ish proxies — intentional overestimate).
# Not billing-grade; used only to refuse/force_cheap before spend.
_MODEL_USD_PER_MTOK: dict[str, float] = {
    "anthropic/claude-opus-5": 18.0,
    "anthropic/claude-opus-4": 18.0,
    "anthropic/claude-sonnet-4": 6.0,
    "anthropic/claude-sonnet-3.5": 6.0,
    "openai/gpt-5": 8.0,
    "openai/gpt-5-mini": 0.6,
    "openai/gpt-4.1": 4.0,
    "openai/gpt-4.1-mini": 0.4,
    "openai/gpt-4o": 5.0,
    "openai/gpt-4o-mini": 0.3,
    "google/gemini-2.5-pro": 5.0,
    "google/gemini-2.5-flash": 0.5,
}

DEFAULT_FULL_RATE = 12.0
DEFAULT_CHEAP_RATE = 0.5
DEFAULT_CHEAP_MODEL = "openai/gpt-4.1-mini"

# Prompt / SOUL / memory / tool overhead (tokens), independent of PR diff.
BASE_INPUT_TOKENS = 10_000
# Agent tool-loop overhead: assume modest tool use under F41 default 40.
DEFAULT_TOOL_TURNS = 8
TOKENS_PER_TOOL_TURN = 1_200
# Output summary tokens
BASE_OUTPUT_TOKENS = 2_500


def parse_max_usd(raw: str | None) -> float | None:
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


def parse_preflight_mode(raw: str | None, *, budget: float | None) -> str:
    """Return off|on|estimate.

    auto (default): hard gate when budget set, else estimate-only (on soft).
    We encode as: off | hard | estimate
    """
    if raw is None or str(raw).strip() == "":
        return "hard" if budget is not None else "estimate"
    s = str(raw).strip().lower()
    if s in {"0", "off", "false", "no", "none", "disabled"}:
        return "off"
    if s in {"estimate", "soft", "warn", "telemetry"}:
        return "estimate"
    if s in {"1", "on", "true", "yes", "hard", "auto"}:
        # auto with budget → hard; auto without → estimate
        if s == "auto":
            return "hard" if budget is not None else "estimate"
        return "hard"
    return "hard" if budget is not None else "estimate"


def parse_action(raw: str | None) -> str:
    if raw is None or str(raw).strip() == "":
        return "force_cheap"
    s = str(raw).strip().lower().replace("-", "_")
    if s in {"refuse", "block", "deny", "hard_refuse"}:
        return "refuse"
    if s in {"warn", "soft", "estimate_only"}:
        return "warn"
    if s in {"force_cheap", "cheap", "downgrade", "tier"}:
        return "force_cheap"
    return "force_cheap"


def model_rate_usd_per_mtok(model: str) -> float:
    m = (model or "").strip().lower()
    if not m:
        return DEFAULT_FULL_RATE
    if m in _MODEL_USD_PER_MTOK:
        return _MODEL_USD_PER_MTOK[m]
    # prefix / family heuristics
    if "mini" in m or "flash" in m or "nano" in m or "haiku" in m:
        return DEFAULT_CHEAP_RATE
    if "opus" in m:
        return 18.0
    if "sonnet" in m:
        return 6.0
    if "gpt-4.1" in m:
        return 4.0
    return DEFAULT_FULL_RATE


def estimate_tokens(
    *,
    diff_bytes: int = 0,
    file_count: int = 0,
    max_turns: int | None = None,
) -> dict[str, int]:
    try:
        diff_bytes = max(0, int(diff_bytes))
    except (TypeError, ValueError):
        diff_bytes = 0
    try:
        file_count = max(0, int(file_count))
    except (TypeError, ValueError):
        file_count = 0
    # ~4 chars/token for code diffs; floor small diffs
    diff_tokens = max(diff_bytes // 4, 0)
    file_tokens = file_count * 250
    turns = DEFAULT_TOOL_TURNS
    if max_turns is not None:
        try:
            mt = int(max_turns)
            if mt > 0:
                turns = min(DEFAULT_TOOL_TURNS, mt)
        except (TypeError, ValueError):
            pass
    tool_tokens = turns * TOKENS_PER_TOOL_TURN
    input_tokens = BASE_INPUT_TOKENS + diff_tokens + file_tokens + tool_tokens
    # Output scales lightly with input but caps
    output_tokens = BASE_OUTPUT_TOKENS + min(diff_tokens // 10, 4_000)
    total = input_tokens + output_tokens
    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": int(total),
        "tool_turns_assumed": int(turns),
    }


def estimate_cost_usd(
    *,
    model: str,
    diff_bytes: int = 0,
    file_count: int = 0,
    max_turns: int | None = None,
) -> dict[str, Any]:
    toks = estimate_tokens(
        diff_bytes=diff_bytes, file_count=file_count, max_turns=max_turns
    )
    rate = model_rate_usd_per_mtok(model)
    # Blended: weight input 70% / output 30% of total at same rate (proxy)
    usd = (toks["total_tokens"] / 1_000_000.0) * rate
    return {
        "model": model,
        "rate_usd_per_mtok": rate,
        "estimated_usd": round(usd, 6),
        **toks,
        "diff_bytes": int(diff_bytes or 0),
        "file_count": int(file_count or 0),
    }


def decide(
    *,
    model: str,
    diff_bytes: int = 0,
    file_count: int = 0,
    max_usd: float | None = None,
    mode: str = "hard",
    action: str = "force_cheap",
    cheap_model: str = DEFAULT_CHEAP_MODEL,
    max_turns: int | None = None,
    force_allow: bool = False,
) -> dict[str, Any]:
    """Return decision dict with action allow|force_cheap|refuse|warn|skip."""
    est = estimate_cost_usd(
        model=model,
        diff_bytes=diff_bytes,
        file_count=file_count,
        max_turns=max_turns,
    )
    out: dict[str, Any] = {
        **est,
        "max_usd": max_usd,
        "mode": mode,
        "policy": action,
        "cheap_model": cheap_model,
        "original_model": model,
        "decision": "allow",
        "reason": "ok",
        "forced_cheap": False,
        "refused": False,
        "over_estimate": False,
    }

    if force_allow:
        out["decision"] = "allow"
        out["reason"] = "force_allow"
        return out

    if mode == "off":
        out["decision"] = "allow"
        out["reason"] = "preflight_off"
        return out

    over = max_usd is not None and est["estimated_usd"] > float(max_usd)
    out["over_estimate"] = bool(over)

    if not over:
        out["decision"] = "allow"
        out["reason"] = "within_budget" if max_usd is not None else "no_budget"
        return out

    # Over estimate
    if mode == "estimate" or action == "warn":
        out["decision"] = "warn"
        out["reason"] = "over_estimate_warn"
        return out

    # hard mode
    if action == "refuse":
        out["decision"] = "refuse"
        out["reason"] = "over_estimate_refuse"
        out["refused"] = True
        return out

    # force_cheap
    if (model or "").strip() == (cheap_model or "").strip():
        out["decision"] = "refuse"
        out["reason"] = "over_estimate_already_cheap"
        out["refused"] = True
        return out

    cheap_est = estimate_cost_usd(
        model=cheap_model,
        diff_bytes=diff_bytes,
        file_count=file_count,
        max_turns=max_turns,
    )
    out["cheap_estimated_usd"] = cheap_est["estimated_usd"]
    out["model"] = cheap_model
    out["rate_usd_per_mtok"] = cheap_est["rate_usd_per_mtok"]
    out["estimated_usd"] = cheap_est["estimated_usd"]
    out["input_tokens"] = cheap_est["input_tokens"]
    out["output_tokens"] = cheap_est["output_tokens"]
    out["total_tokens"] = cheap_est["total_tokens"]
    out["forced_cheap"] = True

    if max_usd is not None and cheap_est["estimated_usd"] > float(max_usd):
        out["decision"] = "refuse"
        out["reason"] = "over_estimate_after_cheap"
        out["refused"] = True
        return out

    out["decision"] = "force_cheap"
    out["reason"] = "over_estimate_forced_cheap"
    out["over_estimate"] = False  # after downgrade within budget
    return out


def _kv(result: dict[str, Any]) -> None:
    order = [
        "decision",
        "reason",
        "model",
        "original_model",
        "estimated_usd",
        "max_usd",
        "over_estimate",
        "forced_cheap",
        "refused",
        "cheap_model",
        "cheap_estimated_usd",
        "rate_usd_per_mtok",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "diff_bytes",
        "file_count",
        "mode",
        "policy",
    ]
    for k in order:
        if k not in result:
            continue
        v = result[k]
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif v is None:
            v = ""
        print(f"{k}={v}")


def cmd_estimate(args: argparse.Namespace) -> int:
    est = estimate_cost_usd(
        model=args.model
        or os.environ.get("TORII_MODEL")
        or os.environ.get("OPENROUTER_MODEL")
        or "anthropic/claude-opus-5",
        diff_bytes=args.diff_bytes,
        file_count=args.file_count,
        max_turns=args.max_turns,
    )
    _kv(
        {
            **est,
            "decision": "estimate",
            "reason": "estimate_only",
            "original_model": est["model"],
            "max_usd": parse_max_usd(
                args.max_usd
                if args.max_usd is not None
                else os.environ.get("TORII_MAX_COST_USD")
            ),
            "over_estimate": False,
            "forced_cheap": False,
            "refused": False,
            "cheap_model": os.environ.get("TORII_MODEL_CHEAP") or DEFAULT_CHEAP_MODEL,
            "mode": "estimate",
            "policy": "n/a",
        }
    )
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    max_usd = parse_max_usd(
        args.max_usd if args.max_usd is not None else os.environ.get("TORII_MAX_COST_USD")
    )
    mode = parse_preflight_mode(
        args.mode if args.mode is not None else os.environ.get("TORII_PREFLIGHT_COST"),
        budget=max_usd,
    )
    action = parse_action(
        args.action if args.action is not None else os.environ.get("TORII_PREFLIGHT_ACTION")
    )
    model = (
        args.model
        or os.environ.get("TORII_MODEL")
        or os.environ.get("OPENROUTER_MODEL")
        or "anthropic/claude-opus-5"
    )
    cheap = (
        args.cheap_model
        or os.environ.get("TORII_MODEL_CHEAP")
        or DEFAULT_CHEAP_MODEL
    )
    force = args.force or os.environ.get("TORII_PREFLIGHT_FORCE", "").strip() in (
        "1",
        "true",
        "yes",
    )
    result = decide(
        model=model,
        diff_bytes=args.diff_bytes,
        file_count=args.file_count,
        max_usd=max_usd,
        mode=mode,
        action=action,
        cheap_model=cheap,
        max_turns=args.max_turns,
        force_allow=force,
    )
    _kv(result)
    if result.get("refused"):
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F43 preflight cost estimate before Hermes")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--model", default=None)
        sp.add_argument("--diff-bytes", type=int, default=0)
        sp.add_argument("--file-count", type=int, default=0)
        sp.add_argument("--max-turns", type=int, default=None)
        sp.add_argument("--max-usd", default=None)
        sp.add_argument("--cheap-model", default=None)
        sp.add_argument("--mode", default=None, help="off|on|auto|estimate|hard")
        sp.add_argument(
            "--action",
            default=None,
            help="force_cheap|refuse|warn",
        )
        sp.add_argument(
            "--force",
            action="store_true",
            help="Always allow (TORII_PREFLIGHT_FORCE)",
        )

    e = sub.add_parser("estimate", help="Print cost estimate key=value")
    add_common(e)
    e.set_defaults(func=cmd_estimate)

    d = sub.add_parser("decide", help="Decide allow/force_cheap/refuse (exit 2=refuse)")
    add_common(d)
    d.set_defaults(func=cmd_decide)

    args = p.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001
        print(f"decision=allow", file=sys.stderr)
        print(f"reason=error:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

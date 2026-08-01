#!/usr/bin/env python3
"""F108/F159: Shared soft-re-prompt budget + adaptive complementary slot.

Research drivers:
  - Agent cost guides (2026): multi-turn re-prompts double LLM spend; need kill
    switches / attempt caps before runaway loops.
  - Braintrust / Portal26: token budgets + retry ceilings per agent run.
  - Torii F49 zero-tool re-prompt + F106 memory utilization re-prompt can stack
    to 2× Hermes on DeepSeek (live F106 ~149s second pass).
  - Live F157: F106 consumes max_extra=1 so hub-archival util re-prompt never
    fires — complementary recovery kinds need one adaptive dual-recovery slot.

Product thesis:
  Soft re-prompts recover quality, but unbounded stacking burns budget.
  Default max_extra=1 blocks multi-kind runaway; **F159** grants at most one
  adaptive bonus when a complementary kind (memory util ↔ recovery/hub-archival)
  already used the base slot — dual recovery without opening the floodgates.

Commands:
  init     — write budget state file for a run
  allow    — decide if kind (f49|f106|f122|f137|f152|f157) may re-prompt
  consume  — record a successful/attempted re-prompt
  status   — show state
  fixture  — hermetic: max=1 allows first, blocks second; F159 adaptive dual

Env:
  TORII_REPROMPT_MAX_EXTRA     default 1 (0 = disable all soft re-prompts)
  TORII_REPROMPT_BUDGET        1 (default) | 0  — master toggle
  TORII_REPROMPT_ADAPTIVE      1 (default) | 0  — F159 complementary bonus slot
  TORII_REPROMPT_ADAPTIVE_BONUS default 1 — max adaptive extra (capped once)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F108"
FEATURE_ADAPTIVE = "F159"
SCHEMA = 1
STATE_NAME = "reprompt-budget.json"
# f122 = recovery skill util; f137 = scorecard util; f152 = recon-warm hub idle
# f157 = hub-archival util gap (partial recovery idle, F155/F156 slice)
KINDS = frozenset({"f49", "f106", "f122", "f137", "f152", "f157", "other"})

# F159: complementary dual-recovery families (memory util ↔ skill/hub recovery)
# When one family consumed the base slot, the other may grant one adaptive bonus.
_MEMORY_UTIL_KINDS = frozenset({"f106"})
_RECOVERY_SKILL_KINDS = frozenset({"f122", "f137", "f157"})
_RECON_WARM_KINDS = frozenset({"f152"})

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_REPROMPT_BUDGET") or "1").strip().lower()
    return raw not in _FALSEY


def max_extra() -> int:
    raw = (os.environ.get("TORII_REPROMPT_MAX_EXTRA") or "1").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 1


def adaptive_enabled() -> bool:
    """F159: grant complementary dual-recovery bonus slot (default on)."""
    raw = (os.environ.get("TORII_REPROMPT_ADAPTIVE") or "1").strip().lower()
    return raw not in _FALSEY


def adaptive_bonus() -> int:
    """F159: max adaptive extra slots (default 1, hard-capped at 2)."""
    raw = (os.environ.get("TORII_REPROMPT_ADAPTIVE_BONUS") or "1").strip()
    try:
        return max(0, min(2, int(raw)))
    except ValueError:
        return 1


def complementary_kinds(kind: str) -> frozenset[str]:
    """Kinds whose prior attempt may unlock an adaptive slot for `kind`."""
    k = (kind or "other").lower()
    if k in _RECOVERY_SKILL_KINDS:
        # hub-archival / recovery util after memory util (live F157 gap)
        return _MEMORY_UTIL_KINDS | _RECON_WARM_KINDS
    if k in _MEMORY_UTIL_KINDS:
        # reverse: recovery already ran, memory still needed
        return _RECOVERY_SKILL_KINDS | _RECON_WARM_KINDS
    if k in _RECON_WARM_KINDS:
        return _MEMORY_UTIL_KINDS | _RECOVERY_SKILL_KINDS
    return frozenset()


def ensure_adaptive_slot(state: dict[str, Any], *, kind: str) -> dict[str, Any]:
    """F159: if complementary kind used the base slot, expand max_extra once.

    Never expands for f49 (zero-tool owns its own path) or when adaptive off.
    Mutates state when expanding; safe to call on every allow.
    """
    kind = (kind or "other").lower()
    if kind not in KINDS:
        kind = "other"
    if not adaptive_enabled() or not enabled():
        return state
    if state.get("adaptive_expanded"):
        return state
    if kind == "f49":
        return state  # zero-tool re-prompt stays under base budget only
    max_n = int(state.get("max_extra") if state.get("max_extra") is not None else max_extra())
    used = int(state.get("used") or 0)
    if used < max_n:
        return state  # still have base remaining
    attempts = state.get("attempts") or []
    attempted = {
        str(a.get("kind") or "").lower()
        for a in attempts
        if isinstance(a, dict) and a.get("kind")
    }
    if kind in attempted:
        return state
    comps = complementary_kinds(kind)
    hit = comps & attempted
    if not hit:
        return state
    bonus = adaptive_bonus()
    if bonus <= 0:
        return state
    state["max_extra"] = max_n + bonus
    state["adaptive_expanded"] = True
    state["adaptive_feature"] = FEATURE_ADAPTIVE
    state["adaptive_reason"] = (
        f"complementary:{','.join(sorted(hit))}+need:{kind}"
    )
    state["adaptive_bonus"] = bonus
    state["remaining"] = max(0, int(state["max_extra"]) - used)
    return state


def default_state_path(out_dir: Path) -> Path:
    return Path(out_dir) / STATE_NAME


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return new_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return new_state()


def new_state(*, max_n: int | None = None) -> dict[str, Any]:
    m = max_extra() if max_n is None else max(0, int(max_n))
    return {
        "schema": SCHEMA,
        "feature": FEATURE,
        "feature_adaptive": FEATURE_ADAPTIVE if adaptive_enabled() else None,
        "enabled": enabled(),
        "max_extra": m,
        "base_max_extra": m,
        "used": 0,
        "remaining": m if enabled() else 0,
        "attempts": [],
        "blocked": [],
        "adaptive_expanded": False,
        "updated_at": _now(),
    }


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state = dict(state)
    state["updated_at"] = _now()
    state["remaining"] = max(0, int(state.get("max_extra") or 0) - int(state.get("used") or 0))
    if not state.get("enabled", True):
        state["remaining"] = 0
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def decide_allow(
    state: dict[str, Any],
    *,
    kind: str,
    apply_adaptive: bool = True,
) -> dict[str, Any]:
    kind = (kind or "other").lower()
    if kind not in KINDS:
        kind = "other"
    # F159: maybe expand max_extra before measuring remaining
    if apply_adaptive:
        ensure_adaptive_slot(state, kind=kind)
    on = bool(state.get("enabled", True)) and enabled()
    max_n = int(state.get("max_extra") if state.get("max_extra") is not None else max_extra())
    used = int(state.get("used") or 0)
    remaining = max(0, max_n - used) if on else 0
    adaptive = bool(state.get("adaptive_expanded"))
    out: dict[str, Any] = {
        "feature": FEATURE,
        "feature_adaptive": FEATURE_ADAPTIVE if adaptive_enabled() else None,
        "allow": 0,
        "enabled": on,
        "kind": kind,
        "max_extra": max_n,
        "base_max_extra": int(state.get("base_max_extra") or max_extra()),
        "used": used,
        "remaining": remaining,
        "adaptive_expanded": int(adaptive),
        "adaptive_reason": state.get("adaptive_reason") or "",
        "reason": "ok",
    }
    if not on:
        out["reason"] = "budget_off"
        return out
    if max_n <= 0:
        out["reason"] = "max_extra_zero"
        return out
    if remaining <= 0:
        out["reason"] = "budget_exhausted"
        return out
    # already consumed this kind? allow only once per kind naturally via used count
    attempts = state.get("attempts") or []
    if any(isinstance(a, dict) and a.get("kind") == kind for a in attempts):
        out["reason"] = "kind_already_attempted"
        return out
    out["allow"] = 1
    out["reason"] = (
        "adaptive_within_budget"
        if adaptive and used >= int(state.get("base_max_extra") or max_extra())
        else "within_budget"
    )
    return out


def consume(
    state: dict[str, Any],
    *,
    kind: str,
    recovered: bool = False,
    note: str = "",
) -> dict[str, Any]:
    kind = (kind or "other").lower()
    # F159: expand before decide so dual complementary recovery can consume
    ensure_adaptive_slot(state, kind=kind)
    dec = decide_allow(state, kind=kind, apply_adaptive=False)
    # always record attempt if not already, even if over budget (telemetry)
    attempts = list(state.get("attempts") or [])
    if not any(isinstance(a, dict) and a.get("kind") == kind for a in attempts):
        attempts.append(
            {
                "kind": kind,
                "at": _now(),
                "recovered": bool(recovered),
                "note": (note or "")[:120],
            }
        )
        if dec.get("allow") == 1 or int(state.get("used") or 0) < int(state.get("max_extra") or 0):
            state["used"] = int(state.get("used") or 0) + 1
        state["attempts"] = attempts
    else:
        # update recovered flag
        for a in attempts:
            if isinstance(a, dict) and a.get("kind") == kind:
                a["recovered"] = bool(recovered) or bool(a.get("recovered"))
                if note:
                    a["note"] = note[:120]
        state["attempts"] = attempts
    state["remaining"] = max(
        0, int(state.get("max_extra") or 0) - int(state.get("used") or 0)
    )
    return state


def record_blocked(state: dict[str, Any], *, kind: str, reason: str) -> dict[str, Any]:
    blocked = list(state.get("blocked") or [])
    blocked.append({"kind": kind, "reason": reason, "at": _now()})
    state["blocked"] = blocked[-20:]
    return state


def cmd_init(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    path = Path(args.state) if args.state else default_state_path(out_dir)
    max_n = int(args.max_extra) if args.max_extra is not None else max_extra()
    state = new_state(max_n=max_n)
    if not enabled():
        state["enabled"] = False
        state["remaining"] = 0
    save_state(path, state)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "path": str(path),
                "max_extra": state["max_extra"],
                "remaining": state["remaining"],
                "enabled": state["enabled"],
            },
            indent=2,
        )
    )
    return 0


def cmd_allow(args: argparse.Namespace) -> int:
    path = Path(args.state) if args.state else default_state_path(Path(args.out_dir))
    state = load_state(path)
    # soft re-init if missing
    if not path.is_file():
        state = new_state()
        save_state(path, state)
    # ensure base_max_extra stamped for pre-F159 state files
    if "base_max_extra" not in state:
        state["base_max_extra"] = int(state.get("max_extra") or max_extra())
    dec = decide_allow(state, kind=args.kind)
    # persist adaptive expand even when allow (so consume sees raised max)
    save_state(path, state)
    if dec.get("allow") != 1:
        state = record_blocked(state, kind=args.kind, reason=str(dec.get("reason")))
        save_state(path, state)
    # shell-friendly
    print(f"allow={dec['allow']}")
    print(f"enabled={int(bool(dec['enabled']))}")
    print(f"reason={dec['reason']}")
    print(f"kind={dec['kind']}")
    print(f"max_extra={dec['max_extra']}")
    print(f"used={dec['used']}")
    print(f"remaining={dec['remaining']}")
    print(f"adaptive_expanded={int(dec.get('adaptive_expanded') or 0)}")
    print(f"adaptive_reason={dec.get('adaptive_reason') or ''}")
    print(f"feature={FEATURE}")
    print(f"feature_adaptive={FEATURE_ADAPTIVE if adaptive_enabled() else ''}")
    if args.json:
        print(json.dumps(dec, indent=2), file=sys.stderr)
    return 0


def cmd_consume(args: argparse.Namespace) -> int:
    path = Path(args.state) if args.state else default_state_path(Path(args.out_dir))
    state = load_state(path)
    if not path.is_file():
        state = new_state()
    state = consume(
        state,
        kind=args.kind,
        recovered=bool(args.recovered),
        note=args.note or "",
    )
    save_state(path, state)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "kind": args.kind,
                "used": state.get("used"),
                "remaining": state.get("remaining"),
                "attempts": state.get("attempts"),
            },
            indent=2,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    path = Path(args.state) if args.state else (
        default_state_path(Path(args.out_dir)) if args.out_dir else None
    )
    if path and path.is_file():
        state = load_state(path)
    else:
        state = new_state()
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "env_max_extra": max_extra(),
                "state": state,
                "path": str(path) if path else None,
            },
            indent=2,
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        os.environ["TORII_REPROMPT_BUDGET"] = "1"
        os.environ["TORII_REPROMPT_MAX_EXTRA"] = "1"
        # F159 off for classic max=1 exhaust cases (f49 does not unlock adaptive)
        os.environ["TORII_REPROMPT_ADAPTIVE"] = "1"
        path = td_path / STATE_NAME
        state = new_state(max_n=1)
        save_state(path, state)

        d1 = decide_allow(load_state(path), kind="f49")
        state = consume(load_state(path), kind="f49", recovered=True)
        save_state(path, state)
        d2 = decide_allow(load_state(path), kind="f106")
        # kind already f49 used; f106 should be blocked by budget (f49 not complementary)
        d3 = decide_allow(load_state(path), kind="f49")  # same kind blocked
        d122 = decide_allow(load_state(path), kind="f122")  # also blocked at max=1

        # max=2 allows both kinds
        os.environ["TORII_REPROMPT_MAX_EXTRA"] = "2"
        path2 = td_path / "b2.json"
        st2 = new_state(max_n=2)
        save_state(path2, st2)
        a1 = decide_allow(load_state(path2), kind="f49")
        st2 = consume(load_state(path2), kind="f49")
        save_state(path2, st2)
        a2 = decide_allow(load_state(path2), kind="f106")
        st2 = consume(load_state(path2), kind="f106")
        save_state(path2, st2)
        a3 = decide_allow(load_state(path2), kind="other")

        # max=0 blocks all
        z = decide_allow(new_state(max_n=0), kind="f49")

        # disabled
        os.environ["TORII_REPROMPT_BUDGET"] = "0"
        off = decide_allow(new_state(max_n=5), kind="f49")
        os.environ["TORII_REPROMPT_BUDGET"] = "1"

        # max=2 also allows f122 as third would exhaust — use fresh max=2 for f122 after f49 only
        path3 = td_path / "b3.json"
        st3 = new_state(max_n=2)
        save_state(path3, st3)
        st3 = consume(load_state(path3), kind="f49")
        save_state(path3, st3)
        a122 = decide_allow(load_state(path3), kind="f122")

        # F159: f106 then f157 — adaptive bonus unlocks second recovery
        os.environ["TORII_REPROMPT_MAX_EXTRA"] = "1"
        os.environ["TORII_REPROMPT_ADAPTIVE"] = "1"
        os.environ["TORII_REPROMPT_ADAPTIVE_BONUS"] = "1"
        path_ad = td_path / "adaptive.json"
        st_ad = new_state(max_n=1)
        save_state(path_ad, st_ad)
        st_ad = consume(load_state(path_ad), kind="f106", recovered=True)
        save_state(path_ad, st_ad)
        d_f157 = decide_allow(load_state(path_ad), kind="f157")
        # persist expand from decide path
        st_ad2 = load_state(path_ad)
        ensure_adaptive_slot(st_ad2, kind="f157")
        save_state(path_ad, st_ad2)
        d_f157b = decide_allow(load_state(path_ad), kind="f157")
        st_ad = consume(load_state(path_ad), kind="f157", recovered=False)
        save_state(path_ad, st_ad)
        d_f152 = decide_allow(load_state(path_ad), kind="f152")  # adaptive only once
        # adaptive off: f106 then f157 blocked
        os.environ["TORII_REPROMPT_ADAPTIVE"] = "0"
        path_off = td_path / "adaptive-off.json"
        st_off = new_state(max_n=1)
        save_state(path_off, st_off)
        st_off = consume(load_state(path_off), kind="f106")
        save_state(path_off, st_off)
        d_f157_off = decide_allow(load_state(path_off), kind="f157")
        os.environ["TORII_REPROMPT_ADAPTIVE"] = "1"
        # reverse complementary: f157 then f106 adaptive
        path_rev = td_path / "adaptive-rev.json"
        st_rev = new_state(max_n=1)
        save_state(path_rev, st_rev)
        st_rev = consume(load_state(path_rev), kind="f157")
        save_state(path_rev, st_rev)
        d_f106_rev = decide_allow(load_state(path_rev), kind="f106")

        f159_ok = (
            int(d_f157.get("allow") or 0) == 1
            and "adaptive" in str(d_f157.get("reason") or "")
            or int(d_f157b.get("allow") or 0) == 1
        )
        # prefer the expanded path after ensure
        f159_ok = (
            int(d_f157b.get("allow") or 0) == 1
            and int(d_f157b.get("adaptive_expanded") or 0) == 1
            and int(d_f152.get("allow") or 0) == 0  # no second adaptive
            and int(d_f157_off.get("allow") or 0) == 0
            and d_f157_off.get("reason") == "budget_exhausted"
            and int(d_f106_rev.get("allow") or 0) == 1
        )

        ok = all(
            [
                d1.get("allow") == 1,
                d2.get("allow") == 0 and d2.get("reason") == "budget_exhausted",
                d3.get("allow") == 0,  # kind already or exhausted
                d122.get("allow") == 0,  # F122 blocked when budget used by f49
                a1.get("allow") == 1,
                a2.get("allow") == 1,
                a3.get("allow") == 0,  # exhausted after 2
                a122.get("allow") == 1,  # f122 allowed when slot remains
                z.get("allow") == 0,
                off.get("allow") == 0 and off.get("reason") == "budget_off",
                f159_ok,
            ]
        )
        out = {
            "feature": FEATURE,
            "feature_adaptive": FEATURE_ADAPTIVE,
            "fixture_pass": ok,
            "max1_first_allow": d1.get("allow"),
            "max1_second_block_reason": d2.get("reason"),
            "max2_both_allow": a1.get("allow") == 1 and a2.get("allow") == 1,
            "max0_block": z.get("reason"),
            "budget_off": off.get("reason"),
            "f159_ok": f159_ok,
            "f159_f106_then_f157_allow": d_f157b.get("allow"),
            "f159_adaptive_expanded": d_f157b.get("adaptive_expanded"),
            "f159_f157_reason": d_f157b.get("reason"),
            "f159_third_blocked": d_f152.get("reason"),
            "f159_off_blocks": d_f157_off.get("reason"),
            "f159_reverse_f106_allow": d_f106_rev.get("allow"),
            "scored_at": _now(),
        }
        print(json.dumps(out, indent=2))
        return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F108 shared re-prompt budget")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="create budget state for a run")
    pi.add_argument("--out-dir", required=True)
    pi.add_argument("--state", default="")
    pi.add_argument("--max-extra", type=int, default=None)
    pi.set_defaults(func=cmd_init)

    pa = sub.add_parser("allow", help="may this kind re-prompt?")
    pa.add_argument("--out-dir", default="")
    pa.add_argument("--state", default="")
    pa.add_argument("--kind", required=True, choices=sorted(KINDS))
    pa.add_argument("--json", action="store_true")
    pa.set_defaults(func=cmd_allow)

    pc = sub.add_parser("consume", help="record a re-prompt attempt")
    pc.add_argument("--out-dir", default="")
    pc.add_argument("--state", default="")
    pc.add_argument("--kind", required=True, choices=sorted(KINDS))
    pc.add_argument("--recovered", action="store_true")
    pc.add_argument("--note", default="")
    pc.set_defaults(func=cmd_consume)

    ps = sub.add_parser("status")
    ps.add_argument("--out-dir", default="")
    ps.add_argument("--state", default="")
    ps.set_defaults(func=cmd_status)

    pf = sub.add_parser("fixture")
    pf.set_defaults(func=cmd_fixture)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

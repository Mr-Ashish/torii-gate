#!/usr/bin/env python3
"""Shared TORII_MODEL aliases (MODEL_ALIAS_TOOLUSE / day-2 honesty).

Dogfood: deepseek-chat-v4-pro often yields 0 tool turns; deepseek-v4-pro uses tools.
Keep bash (run-hermes-review.sh) and Modal in sync with this map.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

FEATURE = "MODEL_ALIAS"
SCHEMA = 1

# Input slug → effective OpenRouter model id
ALIASES: dict[str, str] = {
    "deepseek/deepseek-chat-v4-pro": "deepseek/deepseek-v4-pro",
    "deepseek-chat-v4-pro": "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-chat-v4": "deepseek/deepseek-v4-pro",
    "deepseek-chat-v4": "deepseek/deepseek-v4-pro",
}

# Preferred dogfood / public-eval pin when operators say "DeepSeek V4 Pro"
PREFERRED_DEEPSEEK = "deepseek/deepseek-v4-pro"


def normalize_model(model: str | None) -> str:
    m = (model or "").strip()
    if not m:
        return m
    return ALIASES.get(m, m)


def from_env(*, default: str = PREFERRED_DEEPSEEK) -> str:
    raw = (
        os.environ.get("TORII_MODEL")
        or os.environ.get("OPENROUTER_MODEL")
        or default
    )
    return normalize_model(raw)


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: model_alias.py normalize <model> | from-env | fixture | map")
        return 0
    cmd = argv[0]
    if cmd == "normalize" and len(argv) >= 2:
        print(normalize_model(argv[1]))
        return 0
    if cmd == "from-env":
        print(from_env())
        return 0
    if cmd == "map":
        print(json.dumps(ALIASES, indent=2))
        return 0
    if cmd == "fixture":
        checks = {
            "chat_to_pro": normalize_model("deepseek/deepseek-chat-v4-pro")
            == PREFERRED_DEEPSEEK,
            "pro_stable": normalize_model(PREFERRED_DEEPSEEK) == PREFERRED_DEEPSEEK,
            "other_passthrough": normalize_model("openai/gpt-4.1-mini")
            == "openai/gpt-4.1-mini",
            "bash_case_present": False,
            "modal_alias_present": False,
        }
        root = os.environ.get("TORII_ROOT") or os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        hermes = os.path.join(root, "scripts", "run-hermes-review.sh")
        modal = os.path.join(root, "modal_app", "app.py")
        try:
            with open(hermes, encoding="utf-8") as f:
                ht = f.read()
            checks["bash_case_present"] = (
                "deepseek-chat-v4-pro" in ht and "deepseek/deepseek-v4-pro" in ht
            )
        except OSError:
            pass
        try:
            with open(modal, encoding="utf-8") as f:
                mt = f.read()
            checks["modal_alias_present"] = (
                "_normalize_model" in mt and "deepseek-chat-v4-pro" in mt
            )
        except OSError:
            pass
        ok = all(checks.values())
        print(
            json.dumps(
                {
                    "feature": FEATURE,
                    "schema": SCHEMA,
                    "fixture_pass": ok,
                    "checks": checks,
                    "preferred": PREFERRED_DEEPSEEK,
                    "scorecard_target": "JTBD / tool-use",
                    "dim_lift": "one alias map for Hermes + Modal + public-eval",
                },
                indent=2,
            )
        )
        return 0 if ok else 1
    print(f"unknown cmd: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

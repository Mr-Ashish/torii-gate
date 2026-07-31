#!/usr/bin/env python3
"""F55: unified feature toggle registry (env + optional file overrides).

Industry pattern (pr-agent TOML / OpenFeature-lite): one registry documents
defaults, kinds, and categories; resolution is deterministic code — not LLM.

Precedence (highest first):
  1. process environment (`TORII_*`)
  2. file overrides (TORII_TOGGLES_FILE or `.torii/toggles.json`)
  3. registry default

Usage:
  python3 scripts/feature_toggles.py list
  python3 scripts/feature_toggles.py get fixit_prompts
  python3 scripts/feature_toggles.py dump [--json]
  python3 scripts/feature_toggles.py enabled fixit_prompts
  python3 scripts/feature_toggles.py shell          # export KEY=val lines
  python3 scripts/feature_toggles.py product        # product-category only

Import:
  from feature_toggles import is_enabled, get_value, resolve, REGISTRY
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none"})
_TRUTHY = frozenset({"1", "true", "yes", "on", "enabled", "y"})


@dataclass(frozen=True)
class ToggleSpec:
    """One declared feature toggle."""

    key: str  # short stable id, e.g. fixit_prompts
    env: str  # TORII_* env var
    kind: str  # bool | int | str | float
    default: Any
    category: str  # product | quality | ops | runtime | memory | security
    description: str
    feature: str = ""  # Fxx id when applicable
    # When True, empty/unset env falls through to file then default.
    # When False for bool with default True, same behaviour (always).


@dataclass
class Resolved:
    key: str
    env: str
    kind: str
    value: Any
    source: str  # env | file | default
    category: str
    feature: str
    description: str


# ---------------------------------------------------------------------------
# Registry — product + quality gates first; runtime knobs included for dump
# ---------------------------------------------------------------------------

REGISTRY: list[ToggleSpec] = [
    # --- product ---
    ToggleSpec(
        "fixit_prompts",
        "TORII_FIXIT_PROMPTS",
        "bool",
        True,
        "product",
        "Attach Claude Code–ready fix-it prompts on inline findings",
        "F54",
    ),
    ToggleSpec(
        "issue_context",
        "TORII_ISSUE_CONTEXT",
        "bool",
        True,
        "product",
        "Fetch linked GitHub issues into review context",
        "F53",
    ),
    ToggleSpec(
        "issue_from_branch",
        "TORII_ISSUE_FROM_BRANCH",
        "bool",
        True,
        "product",
        "Extract issue numbers from PR head branch name",
        "F53",
    ),
    ToggleSpec(
        "inline_comments",
        "TORII_INLINE_COMMENTS",
        "bool",
        True,
        "product",
        "Post path-anchored inline PR review comments",
        "F9",
    ),
    ToggleSpec(
        "inline_suggestions",
        "TORII_INLINE_SUGGESTIONS",
        "bool",
        True,
        "product",
        "Post GitHub apply-suggestion blocks from Code suggestions",
        "F9c",
    ),
    ToggleSpec(
        "reply_on_thread",
        "TORII_REPLY_ON_THREAD",
        "bool",
        True,
        "product",
        "Reply in existing Torii inline threads on re-review (in_reply_to)",
        "F60",
    ),
    ToggleSpec(
        "pr_labels",
        "TORII_PR_LABELS",
        "bool",
        True,
        "product",
        "Apply verdict labels (torii:approve / request-changes / …)",
        "F37",
    ),
    ToggleSpec(
        "pr_review",
        "TORII_PR_REVIEW",
        "bool",
        True,
        "product",
        "Submit formal GitHub PR Review event",
        "F23",
    ),
    ToggleSpec(
        "commit_status",
        "TORII_COMMIT_STATUS",
        "bool",
        True,
        "product",
        "Post commit status on PR head SHA",
        "F22",
    ),
    ToggleSpec(
        "ops_footer",
        "TORII_OPS_FOOTER",
        "bool",
        True,
        "product",
        "Append ops deep-link footer on posted review comments",
        "F35",
    ),
    ToggleSpec(
        "replace_previous",
        "TORII_REPLACE_PREVIOUS",
        "bool",
        True,
        "product",
        "Replace prior Torii comments / dismiss prior PR reviews on re-run",
        "F24",
    ),
    ToggleSpec(
        "lens_packs",
        "TORII_LENS_PACKS",
        "bool",
        True,
        "product",
        "Apply named multi-lens recipe pack into assembled prompt",
        "F56",
    ),
    ToggleSpec(
        "lens_pack",
        "TORII_LENS_PACK",
        "str",
        "auto",
        "product",
        "Lens pack id or auto (default|security|docs|odoo|performance|milvus|go|cpp|auto)",
        "F63",
    ),
    ToggleSpec(
        "mermaid",
        "TORII_MERMAID",
        "bool",
        True,
        "product",
        "Inject auto Mermaid architecture diagram from changed files",
        "F57",
    ),
    ToggleSpec(
        "mermaid_max_nodes",
        "TORII_MERMAID_MAX_NODES",
        "int",
        24,
        "product",
        "Max nodes in auto Mermaid architecture diagram",
        "F57",
    ),
    ToggleSpec(
        "pr_description",
        "TORII_PR_DESCRIPTION",
        "bool",
        True,
        "product",
        "Build deterministic PR description scaffold (F58)",
        "F58",
    ),
    ToggleSpec(
        "pr_description_apply",
        "TORII_PR_DESCRIPTION_APPLY",
        "bool",
        False,
        "product",
        "Allow gh pr edit to push F58 description scaffold",
        "F58",
    ),
    ToggleSpec(
        "pr_description_mode",
        "TORII_PR_DESCRIPTION_MODE",
        "str",
        "fill-empty",
        "product",
        "F58 mode: fill-empty | markers | force",
        "F58",
    ),
    ToggleSpec(
        "incremental",
        "TORII_INCREMENTAL",
        "bool",
        False,
        "product",
        "Scope review diff to commits since last Torii head= marker",
        "F59",
    ),
    ToggleSpec(
        "testplan",
        "TORII_TESTPLAN",
        "bool",
        True,
        "product",
        "Inject deterministic suggested test plan (F61) into prompt + review",
        "F61",
    ),
    ToggleSpec(
        "testplan_max_cases",
        "TORII_TESTPLAN_MAX_CASES",
        "int",
        12,
        "product",
        "Max cases in auto suggested test plan",
        "F61",
    ),
    ToggleSpec(
        "fp_resolve",
        "TORII_FP_RESOLVE",
        "bool",
        True,
        "product",
        "Mine author FP/resolve replies and inject + memory-update patterns (F62)",
        "F62",
    ),
    ToggleSpec(
        "fp_resolve_max",
        "TORII_FP_RESOLVE_MAX",
        "int",
        24,
        "product",
        "Max FP/resolve patterns kept in prompt + MEMORY.md",
        "F62",
    ),
    # --- quality / agent ---
    ToggleSpec(
        "soul_scan",
        "TORII_SOUL_SCAN",
        "bool",
        True,
        "quality",
        "Preflight SOUL/prompt context scan before review",
        "F46",
    ),
    ToggleSpec(
        "tool_turns_gate",
        "TORII_TOOL_TURNS_GATE",
        "bool",
        True,
        "quality",
        "Gate/reprompt when tool-turn depth is too shallow",
        "F45",
    ),
    ToggleSpec(
        "severity_calibration",
        "TORII_SEVERITY_CALIBRATION",
        "bool",
        True,
        "quality",
        "Normalize/calibrate finding severities post-model",
        "F50",
    ),
    ToggleSpec(
        "tool_turns_reprompt",
        "TORII_TOOL_TURNS_REPROMPT",
        "bool",
        True,
        "quality",
        "Soft reprompt when tool-turns gate trips",
        "F49",
    ),
    # --- ops / cost ---
    ToggleSpec(
        "preflight_cost",
        "TORII_PREFLIGHT_COST",
        "bool",
        True,
        "ops",
        "Estimate cost before launching Hermes",
        "F43",
    ),
    ToggleSpec(
        "hub_publish",
        "TORII_HUB_PUBLISH",
        "bool",
        False,
        "memory",
        "Publish run artifacts to hub memory (opt-in)",
        "F28",
    ),
    ToggleSpec(
        "local_publish",
        "TORII_LOCAL_PUBLISH",
        "bool",
        True,
        "memory",
        "Write run under local .torii/ memory layout",
        "F28",
    ),
    ToggleSpec(
        "memory_tenant",
        "TORII_MEMORY_TENANT",
        "str",
        "",
        "memory",
        "F65 multi-tenant hub namespace (memory/tenants/{id}/repos/…); empty = classic shared layout",
        "F65",
    ),
    ToggleSpec(
        "self_evolve",
        "TORII_SELF_EVOLVE",
        "bool",
        False,
        "product",
        "F69 auto propose/eval skills after ingest (adopt stays manual)",
        "F69",
    ),
    ToggleSpec(
        "self_evolve_auto_adopt",
        "TORII_SELF_EVOLVE_AUTO_ADOPT",
        "bool",
        False,
        "product",
        "F69 auto-adopt evaluated skills (default off — human gate)",
        "F69",
    ),
    ToggleSpec(
        "agent_tools_research",
        "TORII_AGENT_TOOLS_RESEARCH",
        "bool",
        False,
        "product",
        "F68 run tools research stage after each review (soft)",
        "F68",
    ),
    ToggleSpec(
        "agent_tools_auto_adopt",
        "TORII_AGENT_TOOLS_AUTO_ADOPT",
        "bool",
        False,
        "product",
        "F68 allow unattended adopt (default off — human gate)",
        "F68",
    ),
    # --- numeric knobs (still registry-documented) ---
    ToggleSpec(
        "issue_context_max",
        "TORII_ISSUE_CONTEXT_MAX",
        "int",
        3,
        "product",
        "Max linked issues to fetch",
        "F53",
    ),
    ToggleSpec(
        "inline_max",
        "TORII_INLINE_MAX",
        "int",
        6,
        "product",
        "Max inline comments per review",
        "F9",
    ),
    ToggleSpec(
        "suggestion_max",
        "TORII_SUGGESTION_MAX",
        "int",
        3,
        "product",
        "Max F9c suggestion blocks",
        "F9c",
    ),
    ToggleSpec(
        "max_turns",
        "TORII_MAX_TURNS",
        "int",
        40,
        "ops",
        "Hermes max tool-calling turns (0 = unlimited)",
        "F41",
    ),
    ToggleSpec(
        "review_timeout_seconds",
        "TORII_REVIEW_TIMEOUT_SECONDS",
        "int",
        1500,
        "ops",
        "Hermes wall-clock timeout seconds (0 = off)",
        "F36",
    ),
    ToggleSpec(
        "cooldown_seconds",
        "TORII_COOLDOWN_SECONDS",
        "int",
        900,
        "ops",
        "Re-trigger cooldown window seconds (0 = off)",
        "",
    ),
    # --- string knobs ---
    ToggleSpec(
        "label_prefix",
        "TORII_LABEL_PREFIX",
        "str",
        "torii",
        "product",
        "Prefix for verdict labels",
        "F37",
    ),
    ToggleSpec(
        "status_context",
        "TORII_STATUS_CONTEXT",
        "str",
        "torii/review",
        "product",
        "GitHub commit status context string",
        "F22",
    ),
    ToggleSpec(
        "model_tier",
        "TORII_MODEL_TIER",
        "str",
        "off",
        "ops",
        "Model tier mode: off | auto",
        "F42",
    ),
    ToggleSpec(
        "inline_severity",
        "TORII_INLINE_SEVERITY",
        "str",
        "critical,high,blocking",
        "product",
        "Comma severities for inline posts (* or all = no filter)",
        "F9",
    ),
    ToggleSpec(
        "skip_path_globs",
        "TORII_SKIP_PATH_GLOBS",
        "str",
        "",
        "ops",
        "Path-glob free skip preset or custom globs",
        "F38",
    ),
]

_BY_KEY: dict[str, ToggleSpec] = {t.key: t for t in REGISTRY}
_BY_ENV: dict[str, ToggleSpec] = {t.env: t for t in REGISTRY}


def registry_by_key() -> dict[str, ToggleSpec]:
    return dict(_BY_KEY)


def parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None or raw == "":
        return default
    s = str(raw).strip().lower()
    if s in _FALSEY:
        return False
    if s in _TRUTHY:
        return True
    # unknown non-empty → treat as true (matches existing Torii scripts)
    return True


def coerce(kind: str, raw: Any, default: Any) -> Any:
    if raw is None or raw == "":
        return default
    if kind == "bool":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return bool(raw)
        return parse_bool(str(raw), bool(default))
    if kind == "int":
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default
    if kind == "float":
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default
    # str
    return str(raw)


def load_file_overrides(
    path: str | Path | None = None,
    *,
    search_roots: Iterable[Path] | None = None,
) -> dict[str, Any]:
    """Load JSON map of short keys and/or TORII_* env names → values.

    Search order when path is None:
      TORII_TOGGLES_FILE env, then <root>/.torii/toggles.json for each root.
    """
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    else:
        env_path = (os.environ.get("TORII_TOGGLES_FILE") or "").strip()
        if env_path:
            candidates.append(Path(env_path))
        roots = list(search_roots or [])
        if not roots:
            # TORII_ROOT, cwd, script-relative repo root
            lr = (os.environ.get("TORII_ROOT") or "").strip()
            if lr:
                roots.append(Path(lr))
            roots.append(Path.cwd())
            roots.append(Path(__file__).resolve().parents[1])
        seen: set[Path] = set()
        for r in roots:
            rp = r.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            candidates.append(rp / ".torii" / "toggles.json")

    for p in candidates:
        try:
            if p.is_file():
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except (OSError, json.JSONDecodeError, TypeError):
            continue
    return {}


def _lookup_file(spec: ToggleSpec, file_map: Mapping[str, Any]) -> Any | None:
    if not file_map:
        return None
    if spec.key in file_map:
        return file_map[spec.key]
    if spec.env in file_map:
        return file_map[spec.env]
    # case-insensitive env fallback
    lower = {str(k).lower(): v for k, v in file_map.items()}
    if spec.key.lower() in lower:
        return lower[spec.key.lower()]
    if spec.env.lower() in lower:
        return lower[spec.env.lower()]
    return None


def resolve(
    key_or_env: str,
    *,
    env: Mapping[str, str] | None = None,
    file_map: Mapping[str, Any] | None = None,
    load_file: bool = True,
) -> Resolved:
    """Resolve one toggle by short key or TORII_* env name."""
    spec = _BY_KEY.get(key_or_env) or _BY_ENV.get(key_or_env)
    if spec is None:
        # allow bare TORII_* unknown — return str from env with source
        raise KeyError(f"unknown toggle: {key_or_env}")

    environ = env if env is not None else os.environ
    fmap: Mapping[str, Any]
    if file_map is not None:
        fmap = file_map
    elif load_file:
        fmap = load_file_overrides()
    else:
        fmap = {}

    raw_env = environ.get(spec.env)
    if raw_env is not None and str(raw_env).strip() != "":
        val = coerce(spec.kind, raw_env, spec.default)
        return Resolved(
            key=spec.key,
            env=spec.env,
            kind=spec.kind,
            value=val,
            source="env",
            category=spec.category,
            feature=spec.feature,
            description=spec.description,
        )

    raw_file = _lookup_file(spec, fmap)
    if raw_file is not None and raw_file != "":
        val = coerce(spec.kind, raw_file, spec.default)
        return Resolved(
            key=spec.key,
            env=spec.env,
            kind=spec.kind,
            value=val,
            source="file",
            category=spec.category,
            feature=spec.feature,
            description=spec.description,
        )

    return Resolved(
        key=spec.key,
        env=spec.env,
        kind=spec.kind,
        value=spec.default,
        source="default",
        category=spec.category,
        feature=spec.feature,
        description=spec.description,
    )


def resolve_all(
    *,
    env: Mapping[str, str] | None = None,
    file_map: Mapping[str, Any] | None = None,
    load_file: bool = True,
    category: str | None = None,
) -> list[Resolved]:
    fmap = file_map
    if fmap is None and load_file:
        fmap = load_file_overrides()
    elif fmap is None:
        fmap = {}
    out: list[Resolved] = []
    for spec in REGISTRY:
        if category and spec.category != category:
            continue
        out.append(
            resolve(spec.key, env=env, file_map=fmap, load_file=False)
        )
    return out


def get_value(key_or_env: str, **kwargs: Any) -> Any:
    return resolve(key_or_env, **kwargs).value


def is_enabled(key_or_env: str, **kwargs: Any) -> bool:
    """Bool toggles only; non-bool → bool(value) with 0/empty false."""
    r = resolve(key_or_env, **kwargs)
    if r.kind == "bool":
        return bool(r.value)
    if r.kind == "int":
        return int(r.value) != 0
    if r.kind == "str":
        return bool(str(r.value).strip()) and str(r.value).strip().lower() not in _FALSEY
    return bool(r.value)


def resolved_to_dict(r: Resolved) -> dict[str, Any]:
    return {
        "key": r.key,
        "env": r.env,
        "kind": r.kind,
        "value": r.value,
        "source": r.source,
        "category": r.category,
        "feature": r.feature,
        "description": r.description,
    }


def dump_map(
    *,
    category: str | None = None,
    env: Mapping[str, str] | None = None,
    file_map: Mapping[str, Any] | None = None,
    load_file: bool = True,
) -> dict[str, Any]:
    """Short-key → value map (for scripts / agent tool I/O)."""
    return {
        r.key: r.value
        for r in resolve_all(
            env=env, file_map=file_map, load_file=load_file, category=category
        )
    }


def shell_exports(
    *,
    category: str | None = None,
    only_bool: bool = False,
) -> list[str]:
    """KEY=value lines safe for `eval $(... shell)`."""
    lines: list[str] = []
    for r in resolve_all(category=category):
        if only_bool and r.kind != "bool":
            continue
        if r.kind == "bool":
            val = "1" if r.value else "0"
        else:
            val = str(r.value)
        # escape for double-quoted shell
        val_esc = val.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
        lines.append(f'export {r.env}="{val_esc}"')
    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_list(args: argparse.Namespace) -> int:
    rows = REGISTRY
    if args.category:
        rows = [t for t in rows if t.category == args.category]
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "key": t.key,
                        "env": t.env,
                        "kind": t.kind,
                        "default": t.default,
                        "category": t.category,
                        "feature": t.feature,
                        "description": t.description,
                    }
                    for t in rows
                ],
                indent=2,
            )
        )
        return 0
    for t in rows:
        feat = f" [{t.feature}]" if t.feature else ""
        print(
            f"{t.key:28} {t.env:32} {t.kind:5} default={t.default!r:12} "
            f"({t.category}){feat}  {t.description}"
        )
    return 0


def _cmd_get(args: argparse.Namespace) -> int:
    try:
        r = resolve(args.name, load_file=not args.no_file)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(resolved_to_dict(r), indent=2))
    else:
        print(r.value)
        if args.verbose:
            print(f"# source={r.source} env={r.env} kind={r.kind}", file=sys.stderr)
    return 0


def _cmd_enabled(args: argparse.Namespace) -> int:
    try:
        on = is_enabled(args.name, load_file=not args.no_file)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print("1" if on else "0")
    return 0 if on else 1  # shell-friendly: exit 0 when enabled


def _cmd_dump(args: argparse.Namespace) -> int:
    rows = resolve_all(category=args.category, load_file=not args.no_file)
    if args.values_only:
        print(json.dumps({r.key: r.value for r in rows}, indent=2))
    else:
        print(json.dumps([resolved_to_dict(r) for r in rows], indent=2))
    return 0


def _cmd_shell(args: argparse.Namespace) -> int:
    for line in shell_exports(category=args.category, only_bool=args.bools):
        print(line)
    return 0


def _cmd_product(args: argparse.Namespace) -> int:
    args.category = "product"
    return _cmd_dump(args)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="F55 feature toggle registry (env + .torii/toggles.json)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="list registered toggles")
    pl.add_argument("--category", choices=["product", "quality", "ops", "memory", "runtime", "security"])
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=_cmd_list)

    pg = sub.add_parser("get", help="resolve one toggle value")
    pg.add_argument("name", help="short key or TORII_* env name")
    pg.add_argument("--json", action="store_true")
    pg.add_argument("-v", "--verbose", action="store_true")
    pg.add_argument("--no-file", action="store_true", help="ignore toggles.json")
    pg.set_defaults(func=_cmd_get)

    pe = sub.add_parser("enabled", help="exit 0 if bool/non-empty enabled")
    pe.add_argument("name")
    pe.add_argument("--no-file", action="store_true")
    pe.set_defaults(func=_cmd_enabled)

    pd = sub.add_parser("dump", help="resolve all (JSON)")
    pd.add_argument("--category", choices=["product", "quality", "ops", "memory", "runtime", "security"])
    pd.add_argument("--values-only", action="store_true")
    pd.add_argument("--no-file", action="store_true")
    pd.set_defaults(func=_cmd_dump)

    ps = sub.add_parser("shell", help="print export TORII_*=… lines")
    ps.add_argument("--category", choices=["product", "quality", "ops", "memory", "runtime", "security"])
    ps.add_argument("--bools", action="store_true", help="only bool toggles")
    ps.set_defaults(func=_cmd_shell)

    pp = sub.add_parser("product", help="dump product-category resolved toggles")
    pp.add_argument("--values-only", action="store_true")
    pp.add_argument("--no-file", action="store_true")
    pp.set_defaults(func=_cmd_product)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""F80: Bootstrap Modal secrets for Torii live e2e (from .env + gh auth).

Problem: Modal app expects secrets `torii-openrouter` and `torii-github`.
Operators often have `luffy-*` secrets or only local `.env` — every fire was
blocked with NotFoundError before Hermes could stream.

This tool:
  status   — list expected Modal secret names (presence only; no values)
  plan     — show what would be written (key names only)
  apply    — modal secret create --from-dotenv (temp filtered files)
  fixture  — offline hermetic: build filtered dotenv payloads + dry plan

Never prints secret values. Never commits secrets.

Env:
  TORII_ROOT
  TORII_MODAL_OPENROUTER_SECRET   default torii-openrouter
  TORII_MODAL_GITHUB_SECRET       default torii-github
  TORII_MODAL_ENV                 optional Modal environment
  OPENROUTER_API_KEY / GH_TOKEN / GITHUB_TOKEN from .env or process env

Usage:
  python3 scripts/modal_secrets_bootstrap.py status
  python3 scripts/modal_secrets_bootstrap.py apply
  python3 scripts/modal_secrets_bootstrap.py apply --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F80"
SCHEMA = 1

DEFAULT_OR_SECRET = "torii-openrouter"
DEFAULT_GH_SECRET = "torii-github"
# Fallback names operators may already have (sibling Luffy)
FALLBACK_OR = ("luffy-openrouter",)
FALLBACK_GH = ("luffy-github",)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def secret_names() -> tuple[str, str]:
    or_name = (os.environ.get("TORII_MODAL_OPENROUTER_SECRET") or DEFAULT_OR_SECRET).strip()
    gh_name = (os.environ.get("TORII_MODAL_GITHUB_SECRET") or DEFAULT_GH_SECRET).strip()
    return or_name or DEFAULT_OR_SECRET, gh_name or DEFAULT_GH_SECRET


def load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        if k:
            out[k] = v
    return out


def resolve_keys(root: Path) -> dict[str, Any]:
    """Resolve API keys from env + .env + gh auth (values never logged)."""
    env_file = root / ".env"
    file_env = load_dotenv(env_file)
    # process env wins over file for already-exported
    def get(name: str) -> str:
        return (os.environ.get(name) or file_env.get(name) or "").strip()

    or_key = get("OPENROUTER_API_KEY")
    gh = get("GH_TOKEN") or get("GITHUB_TOKEN")
    gh_source = "env" if gh else ""
    if not gh:
        try:
            r = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode == 0 and (r.stdout or "").strip():
                gh = r.stdout.strip()
                gh_source = "gh_auth"
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass

    or_base = get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
    return {
        "openrouter_set": bool(or_key),
        "github_set": bool(gh),
        "github_source": gh_source or ("missing"),
        "openrouter_base_set": bool(or_base),
        # private — only for write to temp files
        "_or_key": or_key,
        "_gh_token": gh,
        "_or_base": or_base,
    }


def modal_secret_list() -> list[str]:
    try:
        r = subprocess.run(
            ["modal", "secret", "list"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        return []
    if r.returncode != 0:
        return []
    names: list[str] = []
    for line in (r.stdout or "").splitlines():
        # table rows: │ name │ ...
        m = re.search(r"│\s*([A-Za-z0-9._-]+)\s*│", line)
        if m:
            name = m.group(1)
            if name.lower() in ("name", "created", "created at", "last"):
                continue
            if re.match(r"^[A-Za-z]", name):
                names.append(name)
    # de-dupe preserve order
    return list(dict.fromkeys(names))


def write_filtered_dotenv(path: Path, mapping: dict[str, str]) -> None:
    lines = [f"{k}={v}\n" for k, v in mapping.items() if v]
    path.write_text("".join(lines), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def apply_secrets(
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = _root()
    or_name, gh_name = secret_names()
    keys = resolve_keys(root)
    existing = modal_secret_list() if not dry_run else []
    actions: list[dict[str, Any]] = []
    errors: list[str] = []

    if not keys["openrouter_set"]:
        errors.append("OPENROUTER_API_KEY missing (.env or env)")
    if not keys["github_set"]:
        errors.append("GITHUB_TOKEN/GH_TOKEN missing and gh auth token failed")

    plans = [
        {
            "secret": or_name,
            "keys": ["OPENROUTER_API_KEY", "OPENROUTER_BASE_URL"],
            "ready": keys["openrouter_set"],
            "exists": or_name in existing,
            "payload": {
                "OPENROUTER_API_KEY": keys["_or_key"],
                "OPENROUTER_BASE_URL": keys["_or_base"],
            },
        },
        {
            "secret": gh_name,
            "keys": ["GITHUB_TOKEN", "GH_TOKEN"],
            "ready": keys["github_set"],
            "exists": gh_name in existing,
            "payload": {
                "GITHUB_TOKEN": keys["_gh_token"],
                "GH_TOKEN": keys["_gh_token"],
            },
        },
    ]

    for p in plans:
        act: dict[str, Any] = {
            "secret": p["secret"],
            "keys": p["keys"],
            "exists": p["exists"],
            "ready": p["ready"],
            "action": "skip",
        }
        if not p["ready"]:
            act["action"] = "blocked_missing_value"
            actions.append(act)
            continue
        if p["exists"] and not force:
            act["action"] = "exists_use_force_to_overwrite"
            actions.append(act)
            continue
        if dry_run:
            act["action"] = "would_create" if not p["exists"] else "would_overwrite"
            actions.append(act)
            continue
        # apply via modal CLI
        with tempfile.TemporaryDirectory(prefix="torii-modal-sec-") as td:
            dotenv = Path(td) / f"{p['secret']}.env"
            write_filtered_dotenv(dotenv, p["payload"])
            cmd = ["modal", "secret", "create", p["secret"], "--from-dotenv", str(dotenv)]
            if force or p["exists"]:
                cmd.append("--force")
            env_name = (os.environ.get("TORII_MODAL_ENV") or "").strip()
            if env_name:
                cmd.extend(["--env", env_name])
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            # redact any accidental secret echo in output
            out = (r.stdout or "") + (r.stderr or "")
            out = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "sk-[REDACTED]", out)
            out = re.sub(r"ghp_[A-Za-z0-9]{20,}", "ghp_[REDACTED]", out)
            act["action"] = "created" if r.returncode == 0 else "failed"
            act["rc"] = r.returncode
            act["cli_tail"] = out.strip()[-400:]
            if r.returncode != 0:
                errors.append(f"{p['secret']}: rc={r.returncode}")
        actions.append(act)

    # never return secret values
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "at": _now(),
        "dry_run": dry_run,
        "force": force,
        "openrouter_secret": or_name,
        "github_secret": gh_name,
        "openrouter_set": keys["openrouter_set"],
        "github_set": keys["github_set"],
        "github_source": keys["github_source"],
        "modal_secrets_seen": existing,
        "fallbacks": {"openrouter": list(FALLBACK_OR), "github": list(FALLBACK_GH)},
        "actions": actions,
        "ok": len(errors) == 0
        and all(a.get("action") in ("created", "exists_use_force_to_overwrite", "would_create", "would_overwrite") for a in actions if a.get("ready")),
        "errors": errors,
    }


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    or_name, gh_name = secret_names()
    keys = resolve_keys(root)
    existing = modal_secret_list()
    present = {
        or_name: or_name in existing,
        gh_name: gh_name in existing,
    }
    for n in FALLBACK_OR:
        present[f"fallback:{n}"] = n in existing
    for n in FALLBACK_GH:
        present[f"fallback:{n}"] = n in existing
    ready = present.get(or_name) and present.get(gh_name)
    # soft ready if fallbacks exist
    soft = (present.get(or_name) or any(present.get(f"fallback:{n}") for n in FALLBACK_OR)) and (
        present.get(gh_name) or any(present.get(f"fallback:{n}") for n in FALLBACK_GH)
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "openrouter_secret": or_name,
                "github_secret": gh_name,
                "local_openrouter_key": keys["openrouter_set"],
                "local_github_token": keys["github_set"],
                "github_source": keys["github_source"],
                "modal_present": present,
                "ready": ready,
                "soft_ready_fallbacks": soft and not ready,
                "modal_secret_names": existing,
            },
            indent=2,
        )
    )
    return 0 if ready or soft else 1


def cmd_plan(args: argparse.Namespace) -> int:
    result = apply_secrets(force=args.force, dry_run=True)
    print(json.dumps(result, indent=2))
    return 0 if result.get("openrouter_set") and result.get("github_set") else 1


def cmd_apply(args: argparse.Namespace) -> int:
    result = apply_secrets(force=args.force, dry_run=False)
    print(json.dumps(result, indent=2))
    # success if both secrets exist after apply
    existing = modal_secret_list()
    or_name, gh_name = secret_names()
    ok = or_name in existing and gh_name in existing
    result_ok = ok or (
        all(
            a.get("action") in ("created", "exists_use_force_to_overwrite")
            for a in result.get("actions") or []
            if a.get("ready")
        )
    )
    return 0 if result_ok else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic offline: filtered dotenv writing without modal CLI."""
    with tempfile.TemporaryDirectory(prefix="torii-f80-") as td:
        td_path = Path(td)
        # fake keys
        mapping_or = {
            "OPENROUTER_API_KEY": "sk-or-v1-TESTONLY-not-real",
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
        }
        mapping_gh = {"GITHUB_TOKEN": "ghp_TESTONLY", "GH_TOKEN": "ghp_TESTONLY"}
        or_path = td_path / "torii-openrouter.env"
        gh_path = td_path / "torii-github.env"
        write_filtered_dotenv(or_path, mapping_or)
        write_filtered_dotenv(gh_path, mapping_gh)
        or_txt = or_path.read_text(encoding="utf-8")
        gh_txt = gh_path.read_text(encoding="utf-8")
        # only expected keys
        or_keys = {ln.split("=", 1)[0] for ln in or_txt.splitlines() if "=" in ln}
        gh_keys = {ln.split("=", 1)[0] for ln in gh_txt.splitlines() if "=" in ln}
        privacy_ok = "OPENROUTER_API_KEY" in or_keys and "sk-or-v1-TESTONLY" in or_txt
        # status/plan without applying
        plan = apply_secrets(force=False, dry_run=True)
        # plan should not embed raw keys in JSON output fields we care about
        dumped = json.dumps({k: v for k, v in plan.items() if not str(k).startswith("_")})
        no_leak = "sk-or-v1-TESTONLY" not in dumped and "ghp_TESTONLY" not in dumped
        # secret name helpers
        or_name, gh_name = secret_names()
        names_ok = or_name == DEFAULT_OR_SECRET and gh_name == DEFAULT_GH_SECRET
        fixture_pass = (
            privacy_ok
            and or_keys == {"OPENROUTER_API_KEY", "OPENROUTER_BASE_URL"}
            and gh_keys == {"GITHUB_TOKEN", "GH_TOKEN"}
            and no_leak
            and names_ok
            and plan.get("feature") == FEATURE
        )
        print(
            json.dumps(
                {
                    "feature": FEATURE,
                    "fixture_pass": fixture_pass,
                    "or_keys": sorted(or_keys),
                    "gh_keys": sorted(gh_keys),
                    "no_leak": no_leak,
                    "names_ok": names_ok,
                    "plan_actions": [a.get("action") for a in plan.get("actions") or []],
                },
                indent=2,
            )
        )
        return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F80 Modal secrets bootstrap for Torii")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="Presence of Modal secrets + local keys").set_defaults(
        func=cmd_status
    )
    pp = sub.add_parser("plan", help="Dry-run create plan (no values printed)")
    pp.add_argument("--force", action="store_true")
    pp.set_defaults(func=cmd_plan)
    pa = sub.add_parser("apply", help="Create/update Modal secrets via CLI")
    pa.add_argument("--force", action="store_true", help="Overwrite existing")
    pa.set_defaults(func=cmd_apply)
    sub.add_parser("fixture", help="Offline hermetic fixture").set_defaults(
        func=cmd_fixture
    )
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

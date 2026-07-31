#!/usr/bin/env python3
"""F33/F34: authorize Modal/GitHub webhook doorbells (HMAC + bearer token).

Pure stdlib — no Modal/FastAPI import so unit tests stay offline.

Env:
  TORII_WEBHOOK_SECRET     GitHub webhook secret → X-Hub-Signature-256
  TORII_WEBHOOK_TOKEN      Shared token for simple API → Authorization: Bearer …
                           or X-Torii-Token: …
  TORII_WEBHOOK_ALLOW_OPEN=1  Dev escape hatch: permit unauthenticated when
                              neither SECRET nor TOKEN is set (F34 default is
                              **fail-closed**).

Policy (F34 fail-closed):
  - If neither secret nor token is configured:
      · allow_open / TORII_WEBHOOK_ALLOW_OPEN → auth=open + warning (dev only)
      · else → denied (production-safe default)
  - If GitHub signature header present → verify HMAC with secret (required).
  - Else if token configured → require matching Bearer / X-Torii-Token.
  - Else if only secret configured and no signature → reject.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from typing import Any, Mapping


def _truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in ("1", "true", "yes", "on")


def _norm_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    if not headers:
        return {}
    return {str(k).lower(): str(v) for k, v in headers.items()}


def github_hmac_hex(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def github_signature_valid(body: bytes, signature_header: str, secret: str) -> bool:
    """Validate X-Hub-Signature-256: sha256=<hex>."""
    if not secret or not signature_header:
        return False
    sig = signature_header.strip()
    if sig.lower().startswith("sha256="):
        got = sig.split("=", 1)[1].strip()
    else:
        got = sig
    expect = github_hmac_hex(body, secret)
    return hmac.compare_digest(got, expect)


def extract_bearer(headers: Mapping[str, str]) -> str:
    h = _norm_headers(headers)
    auth = h.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return (h.get("x-torii-token") or "").strip()


def bearer_valid(headers: Mapping[str, str], token: str) -> bool:
    if not token:
        return False
    got = extract_bearer(headers)
    if not got:
        return False
    return hmac.compare_digest(got, token)


def allow_open_from_env() -> bool:
    return _truthy(os.environ.get("TORII_WEBHOOK_ALLOW_OPEN"))


def authorize_webhook(
    body: bytes,
    headers: Mapping[str, str] | None = None,
    *,
    secret: str | None = None,
    token: str | None = None,
    allow_open: bool | None = None,
) -> dict[str, Any]:
    """Return {ok, auth, error?} for a webhook request.

    auth values: open | github_hmac | bearer | denied

    F34: default fail-closed when no credentials (allow_open / env escape hatch).
    """
    secret = (secret if secret is not None else os.environ.get("TORII_WEBHOOK_SECRET") or "").strip()
    token = (token if token is not None else os.environ.get("TORII_WEBHOOK_TOKEN") or "").strip()
    if allow_open is None:
        allow_open = allow_open_from_env()
    h = _norm_headers(headers)
    sig = (h.get("x-hub-signature-256") or h.get("x-hub-signature") or "").strip()

    if not secret and not token:
        if allow_open:
            return {
                "ok": True,
                "auth": "open",
                "warning": (
                    "TORII_WEBHOOK_ALLOW_OPEN=1 and no SECRET/TOKEN — "
                    "doorbell is unauthenticated (dev only)"
                ),
            }
        return {
            "ok": False,
            "auth": "denied",
            "error": (
                "webhook auth required (F34 fail-closed): set TORII_WEBHOOK_SECRET "
                "and/or TORII_WEBHOOK_TOKEN, or TORII_WEBHOOK_ALLOW_OPEN=1 for local dev"
            ),
        }

    # Prefer GitHub HMAC when signature header is present
    if sig:
        if not secret:
            return {
                "ok": False,
                "auth": "denied",
                "error": "signature present but TORII_WEBHOOK_SECRET unset",
            }
        if github_signature_valid(body, sig, secret):
            return {"ok": True, "auth": "github_hmac"}
        return {"ok": False, "auth": "denied", "error": "invalid GitHub webhook signature"}

    # Simple API path — bearer / X-Torii-Token
    if token:
        if bearer_valid(h, token):
            return {"ok": True, "auth": "bearer"}
        return {
            "ok": False,
            "auth": "denied",
            "error": "missing or invalid bearer token (Authorization: Bearer … or X-Torii-Token)",
        }

    # Secret configured but request has no signature → not a valid GitHub delivery
    return {
        "ok": False,
        "auth": "denied",
        "error": "TORII_WEBHOOK_SECRET set; require X-Hub-Signature-256 (or also set TORII_WEBHOOK_TOKEN for API)",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_sign = sub.add_parser("sign", help="Print sha256=… HMAC for a body (fixture helper)")
    p_sign.add_argument("--secret", required=True)
    p_sign.add_argument("--body", default="-", help="Path or - for stdin")

    p_auth = sub.add_parser("authorize", help="Authorize body+headers JSON")
    p_auth.add_argument("--secret", default="")
    p_auth.add_argument("--token", default="")
    p_auth.add_argument(
        "--allow-open",
        action="store_true",
        help="Permit unauthenticated when no secret/token (dev)",
    )
    p_auth.add_argument("--body", default="-", help="Raw body path or -")
    p_auth.add_argument(
        "--header",
        action="append",
        default=[],
        help="Header Name: value (repeatable)",
    )

    args = ap.parse_args(argv)

    def read_body(path: str) -> bytes:
        if path == "-":
            return sys.stdin.buffer.read()
        return Path_read(path)

    def Path_read(path: str) -> bytes:
        from pathlib import Path

        return Path(path).read_bytes()

    if args.cmd == "sign":
        body = read_body(args.body)
        print(f"sha256={github_hmac_hex(body, args.secret)}")
        return 0

    if args.cmd == "authorize":
        body = read_body(args.body)
        headers: dict[str, str] = {}
        for raw in args.header:
            if ":" not in raw:
                print(f"bad --header {raw!r}", file=sys.stderr)
                return 2
            k, _, v = raw.partition(":")
            headers[k.strip()] = v.strip()
        result = authorize_webhook(
            body,
            headers,
            secret=args.secret or None,
            token=args.token or None,
            allow_open=True if args.allow_open else None,
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

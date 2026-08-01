#!/usr/bin/env python3
"""F81: Optional LLM checker atop F78 deterministic second-agent critic.

Research drivers (2026):
  - QASecClaw: SAST + coding-LLM validation agent after discovery
  - VulAgent: hypothesis-validation multi-agent (maker ≠ checker model)
  - Prior Torii F78: tools-as-code panel; open gap was optional semantic pass

Product thesis:
  Keep F78 free/default. When TORII_LLM_CRITIC=1 and OPENROUTER_API_KEY is set,
  run a **bounded** OpenRouter chat completion that only returns structured JSON:
  recommended_verdict, confidence, issues[], endorse_demote. Schema-validated;
  on any failure → soft-skip (F78 remains source of truth).

Commands:
  run       — LLM critic on review (+ optional F78 panel JSON)
  fixture   — offline mock path (no API) + schema validation
  status    — enabled / key present / model

Env:
  TORII_LLM_CRITIC           0 (default) | 1
  TORII_LLM_CRITIC_MODEL     default deepseek/deepseek-v4-pro
  TORII_LLM_CRITIC_MAX_TOKENS  default 800
  TORII_LLM_CRITIC_TIMEOUT   default 90
  OPENROUTER_API_KEY / OPENROUTER_BASE_URL / TORII_MODEL
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F81"
SCHEMA = 1
DEFAULT_MODEL = "deepseek/deepseek-v4-pro"
DEFAULT_BASE = "https://openrouter.ai/api/v1"
MAX_REVIEW_CHARS = 6000
MAX_PANEL_CHARS = 2500

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})
_VERDICTS = frozenset({"APPROVE", "REQUEST_CHANGES", "COMMENT"})


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_LLM_CRITIC") or "0").strip().lower()
    return raw not in _FALSEY and raw != ""


def load_dotenv_key(root: Path | None = None) -> str:
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if key:
        return key
    env_path = (root or _root()) / ".env"
    if not env_path.is_file():
        return ""
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'").strip('"')
    return ""


def model_id() -> str:
    return (
        (os.environ.get("TORII_LLM_CRITIC_MODEL") or "").strip()
        or (os.environ.get("TORII_MODEL") or "").strip()
        or (os.environ.get("OPENROUTER_MODEL") or "").strip()
        or DEFAULT_MODEL
    )


def base_url() -> str:
    return (
        (os.environ.get("OPENROUTER_BASE_URL") or "").strip() or DEFAULT_BASE
    ).rstrip("/")


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def redact(s: str) -> str:
    s = re.sub(r"sk-or-v1-[A-Za-z0-9_-]{8,}", "[OPENROUTER_KEY_REDACTED]", s)
    s = re.sub(r"sk-[A-Za-z0-9_-]{12,}", "[KEY_REDACTED]", s)
    s = re.sub(r"ghp_[A-Za-z0-9]{20,}", "[GH_TOKEN_REDACTED]", s)
    s = re.sub(r"/Users/[^/\s]+", "/Users/[REDACTED]", s)
    return s


def build_messages(review: str, panel: dict[str, Any] | None) -> list[dict[str, str]]:
    review = redact(review)[:MAX_REVIEW_CHARS]
    panel_s = ""
    if panel:
        slim = {
            "maker_verdict": panel.get("maker_verdict"),
            "panel": panel.get("panel"),
            "decision": panel.get("decision"),
            "checkers": [
                {
                    "id": c.get("id"),
                    "ok": c.get("ok"),
                    "score": c.get("score"),
                }
                for c in (panel.get("checkers") or [])[:8]
            ],
        }
        panel_s = redact(json.dumps(slim, indent=2))[:MAX_PANEL_CHARS]

    system = (
        "You are Torii Gate's independent security review CHECKER (not the maker). "
        "You only validate evidence quality of an existing PR security review. "
        "Respond with a single JSON object only (no markdown fences). Schema:\n"
        "{\n"
        '  "recommended_verdict": "APPROVE"|"REQUEST_CHANGES"|"COMMENT",\n'
        '  "confidence": "low"|"medium"|"high",\n'
        '  "endorse_demote": true|false,\n'
        '  "path_evidence_adequate": true|false,\n'
        '  "issues": [{"severity":"high|medium|low","note":"..."}],\n'
        '  "summary": "one sentence"\n'
        "}\n"
        "Rules: prefer path-evidenced findings; never invent files; "
        "if APPROVE lacks path:line evidence, set endorse_demote=true and "
        "recommended_verdict COMMENT or REQUEST_CHANGES."
    )
    user = "### Review under check\n\n" + review
    if panel_s:
        user += "\n\n### Deterministic F78 panel (JSON)\n\n" + panel_s
    user += "\n\nReturn JSON only."
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_llm_json(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    # strip fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    # find first object
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


def validate_schema(obj: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    issues: list[str] = []
    if not isinstance(obj, dict):
        return False, ["not_object"], {}
    verdict = str(obj.get("recommended_verdict") or "").upper().replace(" ", "_")
    if verdict in ("REQUEST-CHANGES", "CHANGES_REQUESTED"):
        verdict = "REQUEST_CHANGES"
    if verdict not in _VERDICTS:
        issues.append(f"bad_verdict:{verdict}")
        verdict = "COMMENT"
    conf = str(obj.get("confidence") or "low").lower()
    if conf not in ("low", "medium", "high"):
        conf = "low"
        issues.append("bad_confidence")
    endorse = bool(obj.get("endorse_demote"))
    path_ok = bool(obj.get("path_evidence_adequate"))
    raw_issues = obj.get("issues") if isinstance(obj.get("issues"), list) else []
    clean_issues = []
    for it in raw_issues[:8]:
        if not isinstance(it, dict):
            continue
        clean_issues.append(
            {
                "severity": str(it.get("severity") or "medium")[:12],
                "note": redact(str(it.get("note") or ""))[:240],
            }
        )
    summary = redact(str(obj.get("summary") or ""))[:400]
    out = {
        "recommended_verdict": verdict,
        "confidence": conf,
        "endorse_demote": endorse,
        "path_evidence_adequate": path_ok,
        "issues": clean_issues,
        "summary": summary,
    }
    # schema ok even if we normalized
    return True, issues, out


def call_openrouter(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    model: str,
    timeout: int,
    max_tokens: int,
) -> dict[str, Any]:
    url = f"{base_url()}/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
        # Prefer structured JSON when provider supports it (ignored if unsupported)
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Mr-Ashish/torii-gate",
            "X-Title": "Torii Gate F81 LLM Critic",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        return {
            "ok": False,
            "error": f"http_{e.code}",
            "detail": redact(err_body),
        }
    except Exception as e:
        return {"ok": False, "error": "request_failed", "detail": redact(str(e))[:200]}

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": "bad_json_response"}

    try:
        msg = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return {"ok": False, "error": "missing_content", "detail": list(payload.keys())}

    # Some models (reasoning) put text in content=None + reasoning/refusal fields
    content = msg.get("content")
    if content is None or (isinstance(content, str) and not content.strip()):
        for alt in ("reasoning_content", "reasoning", "refusal", "output_text"):
            if msg.get(alt):
                content = msg.get(alt)
                break
    if isinstance(content, list):
        # OpenAI-style multipart
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") in ("text", "output_text"):
                parts.append(str(part.get("text") or part.get("content") or ""))
            elif isinstance(part, str):
                parts.append(part)
        content = "\n".join(parts)

    parsed = parse_llm_json(str(content or ""))
    if not parsed:
        return {
            "ok": False,
            "error": "parse_failed",
            "raw_preview": redact(str(content))[:300],
            "message_keys": list(msg.keys()) if isinstance(msg, dict) else [],
        }
    ok, norm_issues, clean = validate_schema(parsed)
    return {
        "ok": ok,
        "model": model,
        "result": clean,
        "normalize_notes": norm_issues,
        "usage": payload.get("usage") or {},
    }


def mock_critic(review: str, panel: dict[str, Any] | None) -> dict[str, Any]:
    """Offline deterministic stand-in for fixture / no-key path."""
    low = review.lower()
    # Deep path (dir/file.ext) or path:line counts; bare "app.py" alone is weak
    has_deep_path = bool(
        re.search(
            r"[\w.-]+(?:/[\w.-]+)+\.(?:py|js|ts|tsx|go|java)(?::\d+)?",
            review,
        )
    )
    has_path_line = bool(
        re.search(r"[\w./-]+\.(?:py|js|ts|go|java):\d+", review)
    )
    has_path = has_deep_path or has_path_line
    maker = "UNKNOWN"
    if panel and panel.get("maker_verdict"):
        maker = str(panel["maker_verdict"])
    elif re.search(r"\*\*Verdict:\*\*\s*APPROVE", review, re.I):
        maker = "APPROVE"
    elif re.search(r"\*\*Verdict:\*\*\s*REQUEST", review, re.I):
        maker = "REQUEST_CHANGES"
    # weak narrative APPROVE → demote
    endorse = maker == "APPROVE" and not has_path
    if maker == "APPROVE" and re.search(r"(?i)looks fine|no major issues|no security", review):
        endorse = True
        has_path = False
    verdict = "COMMENT" if endorse else (
        "REQUEST_CHANGES" if "request" in maker.lower() else maker if maker in _VERDICTS else "COMMENT"
    )
    if "sql injection" in low and has_path:
        verdict = "REQUEST_CHANGES"
    clean = {
        "recommended_verdict": verdict,
        "confidence": "medium" if has_path else "low",
        "endorse_demote": endorse,
        "path_evidence_adequate": has_path,
        "issues": (
            [{"severity": "medium", "note": "APPROVE without path evidence"}]
            if endorse
            else []
        ),
        "summary": "mock checker: path=" + ("yes" if has_path else "no"),
    }
    return {
        "ok": True,
        "model": "mock://f81",
        "result": clean,
        "normalize_notes": [],
        "usage": {},
        "mock": True,
    }


def run_critic(
    review: str,
    *,
    panel: dict[str, Any] | None = None,
    force_mock: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    root = root or _root()
    if force_mock or (os.environ.get("TORII_LLM_CRITIC_MOCK") or "").strip() in (
        "1",
        "true",
        "yes",
    ):
        out = mock_critic(review, panel)
        out.update({"feature": FEATURE, "at": _now(), "skipped": False})
        return out

    if not enabled() and not force_mock:
        return {
            "feature": FEATURE,
            "at": _now(),
            "skipped": True,
            "reason": "TORII_LLM_CRITIC disabled",
            "ok": False,
        }

    key = load_dotenv_key(root)
    if not key:
        return {
            "feature": FEATURE,
            "at": _now(),
            "skipped": True,
            "reason": "no_OPENROUTER_API_KEY",
            "ok": False,
        }

    messages = build_messages(review, panel)
    api = call_openrouter(
        messages,
        api_key=key,
        model=model_id(),
        timeout=_int_env("TORII_LLM_CRITIC_TIMEOUT", 90),
        max_tokens=_int_env("TORII_LLM_CRITIC_MAX_TOKENS", 800),
    )
    api.update({"feature": FEATURE, "at": _now(), "skipped": False})
    return api


def to_checker_result(api: dict[str, Any]) -> dict[str, Any]:
    """Shape for F78 CheckerResult-compatible dict."""
    if api.get("skipped"):
        return {
            "id": "f81_llm",
            "name": "LLM checker (F81, skipped)",
            "ok": True,  # soft — do not fail panel
            "score": 0.5,
            "detail": {"skipped": True, "reason": api.get("reason")},
            "error": "",
        }
    if not api.get("ok"):
        return {
            "id": "f81_llm",
            "name": "LLM checker (F81)",
            "ok": True,  # soft-fail: F78 remains authority
            "score": 0.4,
            "detail": {"error": api.get("error"), "detail": api.get("detail")},
            "error": str(api.get("error") or "")[:200],
        }
    res = api.get("result") or {}
    path_ok = bool(res.get("path_evidence_adequate"))
    conf = {"low": 0.45, "medium": 0.7, "high": 0.9}.get(
        str(res.get("confidence") or "low"), 0.5
    )
    score = conf if path_ok else conf * 0.6
    return {
        "id": "f81_llm",
        "name": "LLM checker (F81)",
        "ok": path_ok or str(res.get("recommended_verdict")) != "APPROVE",
        "score": round(min(1.0, score), 4),
        "detail": res,
        "error": "",
        "model": api.get("model"),
    }


def cmd_run(args: argparse.Namespace) -> int:
    root = _root()
    review_path = Path(args.review)
    text = review_path.read_text(encoding="utf-8", errors="replace")
    panel = None
    if args.panel:
        panel = json.loads(Path(args.panel).read_text(encoding="utf-8"))
    elif args.out_dir:
        p = Path(args.out_dir) / "second-agent-critic.json"
        if p.is_file():
            panel = json.loads(p.read_text(encoding="utf-8"))

    # allow force when CLI run even if default disabled
    if not enabled() and not args.force and not args.mock:
        # still allow explicit run with --force
        os.environ["TORII_LLM_CRITIC"] = "1"

    result = run_critic(
        text,
        panel=panel,
        force_mock=args.mock,
        root=root,
    )
    result["checker"] = to_checker_result(result)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        # strip any accidental key material
        safe = json.loads(redact(json.dumps(result)))
        out.write_text(json.dumps(safe, indent=2) + "\n", encoding="utf-8")
        result["wrote"] = str(out)
    print(json.dumps(result, indent=2))
    if result.get("skipped"):
        return 0
    return 0 if result.get("ok") else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    good = root / "docs/benchmarks/fixtures/insecure-demo-good-review.md"
    weak = root / "docs/benchmarks/fixtures/insecure-demo-weak-review.md"
    g = run_critic(good.read_text(encoding="utf-8"), force_mock=True, root=root)
    w = run_critic(weak.read_text(encoding="utf-8"), force_mock=True, root=root)
    g_res = g.get("result") or {}
    w_res = w.get("result") or {}
    # good should not endorse demote; weak APPROVE should
    good_ok = g.get("ok") and g_res.get("path_evidence_adequate") is True
    weak_ok = w.get("ok") and (
        w_res.get("endorse_demote") is True
        or w_res.get("recommended_verdict") != "APPROVE"
    )
    # schema validation
    ok1, _, _ = validate_schema(
        {
            "recommended_verdict": "REQUEST_CHANGES",
            "confidence": "high",
            "endorse_demote": False,
            "path_evidence_adequate": True,
            "issues": [],
            "summary": "ok",
        }
    )
    ok2, issues2, clean2 = validate_schema(
        {"recommended_verdict": "LGTM", "confidence": "nope"}
    )
    schema_ok = ok1 and clean2.get("recommended_verdict") == "COMMENT"
    # messages have no secrets
    msgs = build_messages("test sk-or-v1-deadbeefdeadbeef /Users/ashish/secret", None)
    blob = json.dumps(msgs)
    privacy_ok = "deadbeef" not in blob and "/Users/ashish" not in blob

    fixture_pass = good_ok and weak_ok and schema_ok and privacy_ok
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fixture_pass": fixture_pass,
                "good_path_ok": g_res.get("path_evidence_adequate"),
                "weak_endorse_demote": w_res.get("endorse_demote"),
                "weak_verdict": w_res.get("recommended_verdict"),
                "schema_ok": schema_ok,
                "privacy_ok": privacy_ok,
                "good_checker": to_checker_result(g),
                "weak_checker": to_checker_result(w),
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    key = load_dotenv_key(root)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "api_key_set": bool(key),
                "model": model_id(),
                "base_url": base_url(),
                "max_tokens": _int_env("TORII_LLM_CRITIC_MAX_TOKENS", 800),
                "timeout": _int_env("TORII_LLM_CRITIC_TIMEOUT", 90),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F81 optional LLM critic atop F78")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="Run LLM critic on a review")
    pr.add_argument("--review", required=True)
    pr.add_argument("--panel", default="", help="F78 second-agent-critic.json")
    pr.add_argument("--out-dir", default="")
    pr.add_argument("--out", default="")
    pr.add_argument("--mock", action="store_true")
    pr.add_argument("--force", action="store_true", help="run even if toggle off")
    pr.set_defaults(func=cmd_run)

    sub.add_parser("fixture", help="Offline mock fixture").set_defaults(func=cmd_fixture)
    sub.add_parser("status").set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

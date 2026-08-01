#!/usr/bin/env python3
"""F71: Deterministic source→sink prefilter + federated sanitized signals.

Research drivers (2026):
  - SemTaint (arXiv 2601.10865): static-led multi-agent taint specs (sources,
    sinks, call edges) — modular reusable specifications compound across analyses
  - deepsec (Vercel Labs): cheap regex prefilter → AI investigation → revalidation
  - SAST-Genius / Semgrep Assistant Memories: hybrid SAST+LLM + compound learning
  - Torii thesis: tools-as-code over long SOUL prose; federated intelligence
    without leaking private source (aggregate patterns, not raw code)

Product: a deterministic pipeline stage that (1) extracts candidate source/sink
flows from changed files, (2) injects them as trusted agent context, and
(3) exports privacy-safe federated signals (theme/CWE/keywords only) so every
org benefits without raw path or code leakage.

Commands:
  scan      — scan files/dirs → candidates JSON
  score     — score scan hits against labeled cases pack
  inject    — write trusted prompt section
  federate  — merge local TP + prefilter into sanitized aggregate
  fixture   — offline e2e on demo/insecure (+ optional federation privacy check)

Env:
  TORII_ROOT
  TORII_TAINT_PREFILTER       1 (default) | 0/off
  TORII_FEDERATED_SIGNALS_FILE  override path for federated-signals.json
  TORII_TP_SIGNATURES_FILE      optional TP input for federate
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F71"
SCHEMA = 1
FED_FILENAME = "federated-signals.json"
CAND_FILENAME = "taint-candidates.json"
DEFAULT_CASES = "docs/benchmarks/cases/insecure-demo.json"
DEFAULT_DEMO = "demo/insecure"

# ---------------------------------------------------------------------------
# Source / sink catalog (modular specs — SemTaint-inspired, deterministic)
# ---------------------------------------------------------------------------

# Each rule: id, theme, cwe, kind (source|sink|both), languages, patterns
RULES: list[dict[str, Any]] = [
    # Sources
    {
        "id": "src-flask-request",
        "kind": "source",
        "theme": "untrusted_input",
        "cwe": ["CWE-20"],
        "tags": ["source", "web", "flask"],
        "langs": ["py"],
        "patterns": [
            r"\brequest\.args\b",
            r"\brequest\.form\b",
            r"\brequest\.data\b",
            r"\brequest\.json\b",
            r"\brequest\.get_json\b",
            r"\brequest\.values\b",
            r"\brequest\.cookies\b",
            r"\brequest\.headers\b",
        ],
    },
    {
        "id": "src-cli-env",
        "kind": "source",
        "theme": "untrusted_input",
        "cwe": ["CWE-20"],
        "tags": ["source", "cli", "env"],
        "langs": ["py"],
        "patterns": [
            r"\bsys\.argv\b",
            r"\binput\s*\(",
            r"\bos\.environ\b",
            r"\bos\.getenv\s*\(",
        ],
    },
    # Sinks — injection / RCE / deserial / secrets
    {
        "id": "sink-sqli",
        "kind": "sink",
        "theme": "sql_injection",
        "cwe": ["CWE-89"],
        "tags": ["sink", "sqli", "injection"],
        "langs": ["py"],
        "patterns": [
            r"""\.execute\s*\(\s*f["']""",
            r"""\.execute\s*\(\s*["'][^"']*%[sd]""",
            r"""\.execute\s*\(\s*["'][^"']*\+""",
            r"""\.execute\s*\(\s*.*\.format\s*\(""",
            r"""\bcursor\.execute\s*\(\s*f""",
            r"""\bcur\.execute\s*\(\s*f""",
        ],
        "keywords": ["sql injection", "sqli", "f-string", "execute(f", "cwe-89"],
    },
    {
        "id": "sink-pickle",
        "kind": "sink",
        "theme": "insecure_deserialization",
        "cwe": ["CWE-502"],
        "tags": ["sink", "pickle", "deserialize"],
        "langs": ["py"],
        "patterns": [
            r"\bpickle\.loads\s*\(",
            r"\bpickle\.load\s*\(",
            r"\byaml\.load\s*\((?!.*Loader\s*=)",
            r"\bmarshal\.loads\s*\(",
        ],
        "keywords": ["pickle", "deserialize", "unsafe load", "cwe-502", "pickle.loads"],
    },
    {
        "id": "sink-cmdi",
        "kind": "sink",
        "theme": "command_injection",
        "cwe": ["CWE-78"],
        "tags": ["sink", "rce", "shell"],
        "langs": ["py"],
        "patterns": [
            r"\bsubprocess\.(?:check_output|run|Popen|call|check_call)\s*\([^)]*shell\s*=\s*True",
            r"\bos\.system\s*\(",
            r"\bos\.popen\s*\(",
            r"\bcommands\.getoutput\s*\(",
        ],
        "keywords": [
            "command injection",
            "shell=true",
            "subprocess",
            "rce",
            "cwe-78",
        ],
    },
    {
        "id": "sink-code-exec",
        "kind": "sink",
        "theme": "code_execution",
        "cwe": ["CWE-94", "CWE-95"],
        "tags": ["sink", "eval", "exec"],
        "langs": ["py"],
        "patterns": [
            r"\beval\s*\(",
            r"\bexec\s*\(",
            r"\bcompile\s*\([^)]*['\"]exec['\"]",
        ],
        "keywords": ["eval", "exec", "code injection", "cwe-94"],
    },
    {
        "id": "sink-secret-expose",
        "kind": "sink",
        "theme": "secrets_exposure",
        "cwe": ["CWE-200", "CWE-798"],
        "tags": ["sink", "secrets", "api_key"],
        "langs": ["py"],
        "patterns": [
            r"""return\s*\{[^}]*os\.environ""",
            r"""return\s*\{[^}]*os\.getenv""",
            r"""["'](?:api[_-]?key|secret|password|token|OPENROUTER)["']\s*:""",
            r"""=\s*["']sk-[A-Za-z0-9_-]{8,}["']""",
            r"""=\s*["']sk-or-v1-[A-Za-z0-9_-]{8,}["']""",
        ],
        "keywords": [
            "secret",
            "api key",
            "api_key",
            "credential",
            "exposure",
            "openrouter",
        ],
    },
    # JS/TS light coverage
    {
        "id": "sink-js-sqli",
        "kind": "sink",
        "theme": "sql_injection",
        "cwe": ["CWE-89"],
        "tags": ["sink", "sqli"],
        "langs": ["js", "ts"],
        "patterns": [
            r"""\.(?:query|execute)\s*\(\s*[`"'].*\$\{""",
            r"""\.(?:query|execute)\s*\(\s*["'][^"']*\+""",
        ],
        "keywords": ["sql injection", "sqli", "cwe-89"],
    },
    {
        "id": "sink-js-cmdi",
        "kind": "sink",
        "theme": "command_injection",
        "cwe": ["CWE-78"],
        "tags": ["sink", "rce"],
        "langs": ["js", "ts"],
        "patterns": [
            r"\bchild_process\.(?:exec|execSync|spawn)\s*\(",
            r"\beval\s*\(",
        ],
        "keywords": ["command injection", "child_process", "rce", "cwe-78"],
    },
    # F76: Juice Shop–theme JS sinks (XSS, hardcoded secrets, express sources)
    {
        "id": "src-js-express",
        "kind": "source",
        "theme": "untrusted_input",
        "cwe": ["CWE-20"],
        "tags": ["source", "web", "express"],
        "langs": ["js", "ts"],
        "patterns": [
            r"\breq\.query\b",
            r"\breq\.body\b",
            r"\breq\.params\b",
            r"\breq\.headers\b",
            r"\breq\.cookies\b",
        ],
    },
    {
        "id": "sink-js-xss",
        "kind": "sink",
        "theme": "xss",
        "cwe": ["CWE-79"],
        "tags": ["sink", "xss"],
        "langs": ["js", "ts"],
        "patterns": [
            r"\binnerHTML\s*=",
            r"\bdocument\.write\s*\(",
            r"\.send\s*\(\s*`[^`]*\$\{",
            r'res\.type\s*\(\s*["\']html["\']\s*\)',
            r"\.send\s*\(\s*`[^`]*<(?:div|script)",
        ],
        "keywords": ["xss", "reflected", "cwe-79", "unsanitized", "html"],
    },
    {
        "id": "sink-js-hardcoded-secret",
        "kind": "sink",
        "theme": "secrets_exposure",
        "cwe": ["CWE-798", "CWE-321"],
        "tags": ["sink", "secrets", "jwt"],
        "langs": ["js", "ts"],
        "patterns": [
            r'(?:JWT_SECRET|API_KEY|SECRET|PASSWORD)\s*=\s*["\'][^"\']{8,}["\']',
            r'=\s*["\']sk-[A-Za-z0-9_-]{8,}["\']',
            r"hardcoded-secret",
        ],
        "keywords": ["hardcoded", "jwt", "secret", "api key", "cwe-798"],
    },
]


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_TAINT_PREFILTER") or "").strip().lower()
    if raw in ("0", "off", "false", "no"):
        return False
    if raw in ("1", "on", "true", "yes"):
        return True
    try:
        from feature_toggles import is_enabled  # type: ignore

        return bool(is_enabled("taint_prefilter"))
    except Exception:
        return True


def default_fed_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_FEDERATED_SIGNALS_FILE") or "").strip()
    if env:
        return Path(env)
    r = root or _root()
    # Prefer durable .torii, fall back to memory/federation
    torii = r / ".torii" / FED_FILENAME
    if torii.parent.is_dir() or not (r / "memory").is_dir():
        return torii
    return r / "memory" / "federation" / FED_FILENAME


def _lang_for(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    return {
        "py": "py",
        "js": "js",
        "jsx": "js",
        "ts": "ts",
        "tsx": "ts",
        "mjs": "js",
        "cjs": "js",
    }.get(ext, ext or "unknown")


def _iter_files(paths: list[Path], *, max_files: int = 200) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and _lang_for(child) in (
                    "py",
                    "js",
                    "ts",
                    "unknown",
                ):
                    if child.suffix.lower() in (
                        ".py",
                        ".js",
                        ".jsx",
                        ".ts",
                        ".tsx",
                        ".mjs",
                        ".cjs",
                    ):
                        out.append(child)
                if len(out) >= max_files:
                    return out
    return out[:max_files]


@dataclass
class Hit:
    rule_id: str
    kind: str
    theme: str
    cwe: list[str]
    tags: list[str]
    path: str
    line: int
    snippet: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class FlowCandidate:
    """Co-located source+sink within same function/window (cheap taint heuristic)."""

    id: str
    theme: str
    cwe: list[str]
    path: str
    source_line: int
    sink_line: int
    source_rule: str
    sink_rule: str
    confidence: str
    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def scan_text(
    text: str,
    *,
    path: str = "unknown",
    lang: str = "py",
) -> tuple[list[Hit], list[FlowCandidate]]:
    """Scan one file. Returns (all hits, source→sink flow candidates)."""
    hits: list[Hit] = []
    lines = text.splitlines()
    compiled: list[tuple[dict[str, Any], list[re.Pattern[str]]]] = []
    for rule in RULES:
        langs = rule.get("langs") or []
        if langs and lang not in langs and lang != "unknown":
            continue
        pats = [re.compile(p) for p in (rule.get("patterns") or [])]
        if pats:
            compiled.append((rule, pats))

    for i, line in enumerate(lines, start=1):
        for rule, pats in compiled:
            for pat in pats:
                if pat.search(line):
                    snippet = line.strip()[:160]
                    hits.append(
                        Hit(
                            rule_id=str(rule["id"]),
                            kind=str(rule["kind"]),
                            theme=str(rule["theme"]),
                            cwe=list(rule.get("cwe") or []),
                            tags=list(rule.get("tags") or []),
                            path=path,
                            line=i,
                            snippet=snippet,
                            keywords=list(rule.get("keywords") or []),
                        )
                    )
                    break  # one hit per rule per line

    # Function windows (Python): def ... until next def/class or EOF
    windows: list[tuple[int, int]] = []
    if lang == "py":
        starts = [i for i, ln in enumerate(lines, start=1) if re.match(r"^\s*(async\s+)?def\s+\w+", ln)]
        if not starts:
            windows = [(1, len(lines))]
        else:
            for idx, s in enumerate(starts):
                e = starts[idx + 1] - 1 if idx + 1 < len(starts) else len(lines)
                windows.append((s, e))
    else:
        # JS: function / => blocks — coarse full-file window
        windows = [(1, len(lines))]

    sources = [h for h in hits if h.kind == "source"]
    sinks = [h for h in hits if h.kind == "sink"]
    flows: list[FlowCandidate] = []
    seen: set[tuple[str, int, int]] = set()

    for s0, s1 in windows:
        win_src = [h for h in sources if s0 <= h.line <= s1]
        win_snk = [h for h in sinks if s0 <= h.line <= s1]
        # If no explicit source in window but sink present, still surface sink
        # (secrets / pickle often have request.data as source in same fn)
        for snk in win_snk:
            if win_src:
                src = min(win_src, key=lambda h: abs(h.line - snk.line))
                key = (snk.theme, src.line, snk.line)
                if key in seen:
                    continue
                seen.add(key)
                conf = "high" if abs(src.line - snk.line) <= 12 else "medium"
                kws = list(dict.fromkeys((snk.keywords or []) + (src.keywords or [])))
                flows.append(
                    FlowCandidate(
                        id=f"{snk.theme}:{Path(path).name}:{snk.line}",
                        theme=snk.theme,
                        cwe=list(snk.cwe),
                        path=path,
                        source_line=src.line,
                        sink_line=snk.line,
                        source_rule=src.rule_id,
                        sink_rule=snk.rule_id,
                        confidence=conf,
                        keywords=kws[:12],
                        tags=list(dict.fromkeys((snk.tags or []) + ["flow"])),
                    )
                )
            else:
                key = (snk.theme, 0, snk.line)
                if key in seen:
                    continue
                seen.add(key)
                flows.append(
                    FlowCandidate(
                        id=f"{snk.theme}:{Path(path).name}:{snk.line}",
                        theme=snk.theme,
                        cwe=list(snk.cwe),
                        path=path,
                        source_line=0,
                        sink_line=snk.line,
                        source_rule="",
                        sink_rule=snk.rule_id,
                        confidence="low",
                        keywords=list(snk.keywords or [])[:12],
                        tags=list(dict.fromkeys((snk.tags or []) + ["sink_only"])),
                    )
                )

    return hits, flows


def scan_paths(
    paths: list[Path],
    *,
    root: Path | None = None,
    max_files: int = 200,
    max_bytes: int = 400_000,
) -> dict[str, Any]:
    root = root or _root()
    files = _iter_files(paths, max_files=max_files)
    all_hits: list[dict[str, Any]] = []
    all_flows: list[dict[str, Any]] = []
    for fp in files:
        try:
            raw = fp.read_bytes()
        except OSError:
            continue
        if len(raw) > max_bytes:
            raw = raw[:max_bytes]
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            continue
        try:
            rel = str(fp.resolve().relative_to(root.resolve()))
        except ValueError:
            rel = str(fp)
        lang = _lang_for(fp)
        hits, flows = scan_text(text, path=rel, lang=lang)
        all_hits.extend(asdict(h) for h in hits)
        all_flows.extend(asdict(f) for f in flows)

    # Prefer flows; if empty, promote sink hits as candidates
    candidates = all_flows
    if not candidates:
        for h in all_hits:
            if h.get("kind") == "sink":
                candidates.append(
                    {
                        "id": f"{h['theme']}:{Path(str(h['path'])).name}:{h['line']}",
                        "theme": h["theme"],
                        "cwe": h.get("cwe") or [],
                        "path": h["path"],
                        "source_line": 0,
                        "sink_line": h["line"],
                        "source_rule": "",
                        "sink_rule": h["rule_id"],
                        "confidence": "low",
                        "keywords": h.get("keywords") or [],
                        "tags": list(h.get("tags") or []) + ["sink_only"],
                    }
                )

    return {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "scanned_at": _now(),
        "file_count": len(files),
        "hit_count": len(all_hits),
        "candidate_count": len(candidates),
        "files": [str(f) for f in files],
        "hits": all_hits,
        "candidates": candidates,
    }


# ---------------------------------------------------------------------------
# Score vs labeled cases
# ---------------------------------------------------------------------------


def load_cases(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_scan(scan: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    cases = [c for c in (pack.get("cases") or []) if isinstance(c, dict)]
    cands = scan.get("candidates") or []
    themes = {(c.get("theme") or "").lower() for c in cands}
    # also match via keywords in candidate keywords + hit snippets
    blob_parts: list[str] = []
    for c in cands:
        blob_parts.append(str(c.get("theme") or ""))
        blob_parts.extend(str(k) for k in (c.get("keywords") or []))
        blob_parts.append(str(c.get("path") or ""))
    for h in scan.get("hits") or []:
        blob_parts.append(str(h.get("snippet") or ""))
        blob_parts.append(str(h.get("theme") or ""))
    blob = " ".join(blob_parts).lower()

    results = []
    tp = fp = fn = 0
    for case in cases:
        cid = str(case.get("id") or "")
        theme = str(case.get("theme") or "").lower()
        must = [str(m).lower() for m in (case.get("must_match_any") or [])]
        path_subs = [str(p).lower() for p in (case.get("path_substrings") or [])]
        theme_hit = theme and theme in themes
        kw_hit = any(m in blob for m in must) if must else False
        path_hit = True
        if path_subs:
            path_hit = any(
                any(ps in str(c.get("path") or "").lower() for ps in path_subs)
                for c in cands
            ) or any(
                any(ps in str(h.get("path") or "").lower() for ps in path_subs)
                for h in (scan.get("hits") or [])
            )
        matched = bool((theme_hit or kw_hit) and path_hit)
        required = bool(case.get("required", True))
        if matched:
            tp += 1
            status = "tp"
        else:
            if required:
                fn += 1
            status = "fn"
        results.append(
            {
                "case_id": cid,
                "theme": theme,
                "matched": matched,
                "status": status,
                "required": required,
                "theme_hit": theme_hit,
                "kw_hit": kw_hit,
            }
        )

    required_n = sum(1 for c in cases if c.get("required", True))
    recall = (tp / required_n) if required_n else 1.0
    return {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "required": required_n,
        "recall": round(recall, 4),
        "passed": fn == 0 and required_n > 0,
        "candidate_count": len(cands),
        "cases": results,
    }


# ---------------------------------------------------------------------------
# Prompt inject
# ---------------------------------------------------------------------------


def render_prefilter_section(scan: dict[str, Any], *, max_n: int = 20) -> str:
    cands = scan.get("candidates") or []
    if not cands:
        return ""
    lines = [
        "<!-- torii-f71-taint-prefilter -->",
        "## Deterministic source→sink prefilter (F71)",
        "",
        "Static-led candidate flows (regex/source-sink catalog). Treat as investigation "
        "leads — confirm path evidence and dataflow before blocking. Prefer these over "
        "unrelated style nits.",
        "",
    ]
    for c in cands[:max_n]:
        cwe = c.get("cwe") or []
        cwe_s = ",".join(cwe) if isinstance(cwe, list) else str(cwe)
        src = c.get("source_line") or 0
        snk = c.get("sink_line") or 0
        flow = f"L{src}→L{snk}" if src else f"sink@L{snk}"
        lines.append(
            f"- `{c.get('id')}` theme={c.get('theme')} cwe={cwe_s or 'n/a'} "
            f"path=`{c.get('path')}` {flow} conf={c.get('confidence')}"
        )
    lines.append("")
    return "\n".join(lines)


def inject_into_prompt(prompt_path: Path, scan: dict[str, Any]) -> bool:
    section = render_prefilter_section(scan)
    if not section:
        return False
    text = prompt_path.read_text(encoding="utf-8", errors="replace") if prompt_path.is_file() else ""
    marker = "<!-- torii-f71-taint-prefilter -->"
    if marker in text:
        text = re.sub(
            rf"{re.escape(marker)}[\s\S]*?(?=\n<!--|\Z)",
            section.rstrip() + "\n",
            text,
            count=1,
        )
    else:
        text = text.rstrip() + "\n\n" + section
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Federated sanitized signals (privacy-safe aggregate)
# ---------------------------------------------------------------------------

_PRIVATE_PATH_RX = re.compile(
    r"(?:/Users/|/home/|/private/|C:\\\\|owner--|[\w.-]+--[\w.-]+/)",
    re.I,
)
_CODE_LIKE_RX = re.compile(
    r"(?:def |class |import |from |function |const |let |var |=>|\{|\})",
)


def sanitize_path_hint(path: str) -> str:
    """Keep only basename — never org/repo trees or absolute paths."""
    if not path:
        return ""
    base = Path(str(path).replace("\\", "/")).name
    # strip anything that still looks multi-segment
    base = base.split("/")[-1]
    return base[:128]


def sanitize_keywords(kws: list[Any], *, max_n: int = 10) -> list[str]:
    out: list[str] = []
    for k in kws:
        s = str(k).strip().lower()
        if not s or len(s) > 64:
            continue
        # drop raw code-ish / secrets
        if _CODE_LIKE_RX.search(s) and len(s) > 24:
            continue
        if re.search(r"sk-[a-z0-9_-]{8,}", s, re.I):
            continue
        if "/" in s and s.count("/") >= 2:
            continue
        out.append(s[:48])
        if len(out) >= max_n:
            break
    # unique preserve order
    return list(dict.fromkeys(out))


def signal_from_tp(sig: dict[str, Any]) -> dict[str, Any] | None:
    theme = str(sig.get("theme") or sig.get("id") or "").strip().lower()
    if not theme:
        return None
    cwe = sig.get("cwe") or []
    if not isinstance(cwe, list):
        cwe = [str(cwe)]
    path_hints = [
        sanitize_path_hint(p)
        for p in (sig.get("path_globs") or sig.get("path_substrings") or [])
    ]
    path_hints = [p for p in path_hints if p]
    return {
        "id": re.sub(r"[^a-z0-9._-]+", "-", theme)[:64],
        "theme": theme,
        "cwe": [str(c) for c in cwe][:6],
        "tags": [str(t) for t in (sig.get("tags") or []) if str(t)][:8],
        "keywords": sanitize_keywords(list(sig.get("keywords") or [])),
        "path_basenames": list(dict.fromkeys(path_hints))[:6],
        "hits": int(sig.get("hits") or 1),
        "source": "tp_signature",
    }


def signal_from_candidate(c: dict[str, Any]) -> dict[str, Any] | None:
    theme = str(c.get("theme") or "").strip().lower()
    if not theme or theme == "untrusted_input":
        # sources alone are not federated findings
        if theme == "untrusted_input":
            return None
    if not theme:
        return None
    cwe = c.get("cwe") or []
    if not isinstance(cwe, list):
        cwe = [str(cwe)]
    return {
        "id": re.sub(r"[^a-z0-9._-]+", "-", theme)[:64],
        "theme": theme,
        "cwe": [str(x) for x in cwe][:6],
        "tags": [str(t) for t in (c.get("tags") or []) if str(t)][:8],
        "keywords": sanitize_keywords(list(c.get("keywords") or [])),
        "path_basenames": [sanitize_path_hint(str(c.get("path") or ""))][:1],
        "hits": 1,
        "source": "taint_prefilter",
        "confidence": str(c.get("confidence") or "medium"),
    }


def load_json_list(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        items = data.get(key) or data.get("signatures") or data.get("rules") or []
        return [x for x in items if isinstance(x, dict)]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def merge_signals(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for s in existing + incoming:
        sid = str(s.get("id") or s.get("theme") or "")
        if not sid:
            continue
        if sid not in by_id:
            by_id[sid] = dict(s)
            by_id[sid]["hits"] = int(s.get("hits") or 1)
            by_id[sid]["tenants"] = int(s.get("tenants") or 1)
            continue
        cur = by_id[sid]
        cur["hits"] = int(cur.get("hits") or 0) + int(s.get("hits") or 1)
        cur["tenants"] = int(cur.get("tenants") or 1) + 1
        # merge keywords / cwe / basenames (sanitized)
        cur["keywords"] = sanitize_keywords(
            list(cur.get("keywords") or []) + list(s.get("keywords") or []),
            max_n=12,
        )
        cwe = list(cur.get("cwe") or []) + [str(x) for x in (s.get("cwe") or [])]
        cur["cwe"] = list(dict.fromkeys(cwe))[:8]
        bases = list(cur.get("path_basenames") or []) + list(s.get("path_basenames") or [])
        cur["path_basenames"] = list(dict.fromkeys(b for b in bases if b))[:8]
        tags = list(cur.get("tags") or []) + list(s.get("tags") or [])
        cur["tags"] = list(dict.fromkeys(str(t) for t in tags if t))[:10]
    # sort by hits desc
    out = sorted(by_id.values(), key=lambda x: (-int(x.get("hits") or 0), str(x.get("id"))))
    return out


def assert_privacy(signals: list[dict[str, Any]]) -> list[str]:
    """Return list of privacy violations (empty = clean)."""
    issues: list[str] = []
    for s in signals:
        blob = json.dumps(s, ensure_ascii=False)
        if _PRIVATE_PATH_RX.search(blob):
            issues.append(f"private_path in {s.get('id')}")
        if "snippet" in s or "code" in s:
            issues.append(f"raw_code_field in {s.get('id')}")
        for p in s.get("path_basenames") or []:
            if "/" in str(p) or "\\" in str(p):
                issues.append(f"multi_segment_path in {s.get('id')}: {p}")
        for k in s.get("keywords") or []:
            if re.search(r"sk-[a-z0-9_-]{10,}", str(k), re.I):
                issues.append(f"secret_keyword in {s.get('id')}")
    return issues


def federate(
    *,
    tp_path: Path | None,
    scan: dict[str, Any] | None,
    dest: Path,
    tenant: str = "",
) -> dict[str, Any]:
    incoming: list[dict[str, Any]] = []
    if tp_path and tp_path.is_file():
        for sig in load_json_list(tp_path, "signatures"):
            s = signal_from_tp(sig)
            if s:
                if tenant:
                    s["tenant_hash"] = _tenant_hash(tenant)
                incoming.append(s)
    if scan:
        for c in scan.get("candidates") or []:
            s = signal_from_candidate(c)
            if s:
                if tenant:
                    s["tenant_hash"] = _tenant_hash(tenant)
                incoming.append(s)

    existing = load_json_list(dest, "signals")
    merged = merge_signals(existing, incoming)
    issues = assert_privacy(merged)
    if issues:
        # hard-strip offenders
        merged = [s for s in merged if not any(s.get("id", "") in i for i in issues)]
        # re-check
        issues = assert_privacy(merged)

    payload = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "updated_at": _now(),
        "count": len(merged),
        "privacy": "basename_theme_cwe_keywords_only",
        "privacy_ok": len(issues) == 0,
        "privacy_issues": issues,
        "signals": merged,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _tenant_hash(tenant: str) -> str:
    """Non-reversible short token — no raw tenant string in aggregate."""
    import hashlib

    t = re.sub(r"[^A-Za-z0-9._-]+", "-", (tenant or "").strip())[:64]
    if not t:
        return ""
    return hashlib.sha256(t.encode()).hexdigest()[:12]


def render_federated_section(signals: list[dict[str, Any]], *, max_n: int = 16) -> str:
    if not signals:
        return ""
    lines = [
        "<!-- torii-f71-federated-signals -->",
        "## Federated security signals (F71 privacy-safe)",
        "",
        "Cross-org aggregate patterns (theme/CWE/keywords only — no private source).",
        "Use as prior: raise path-evidenced matches; never invent file paths from this list.",
        "",
    ]
    for s in signals[:max_n]:
        kws = ", ".join(str(k) for k in (s.get("keywords") or [])[:6])
        cwe = ",".join(str(c) for c in (s.get("cwe") or [])[:4])
        lines.append(
            f"- `{s.get('id')}` theme={s.get('theme')} cwe={cwe or 'n/a'} "
            f"hits={s.get('hits') or 1} tenants≈{s.get('tenants') or 1} keywords=[{kws}]"
        )
    lines.append("")
    return "\n".join(lines)


def inject_federated_into_prompt(prompt_path: Path, signals: list[dict[str, Any]]) -> bool:
    section = render_federated_section(signals)
    if not section:
        return False
    text = prompt_path.read_text(encoding="utf-8", errors="replace") if prompt_path.is_file() else ""
    marker = "<!-- torii-f71-federated-signals -->"
    if marker in text:
        text = re.sub(
            rf"{re.escape(marker)}[\s\S]*?(?=\n<!--|\Z)",
            section.rstrip() + "\n",
            text,
            count=1,
        )
    else:
        text = text.rstrip() + "\n\n" + section
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_scan(args: argparse.Namespace) -> int:
    root = _root()
    paths = [Path(p) for p in (args.paths or [])]
    if not paths:
        paths = [root / DEFAULT_DEMO]
    # resolve relative to cwd or root
    resolved = []
    for p in paths:
        if p.is_absolute():
            resolved.append(p)
        elif p.exists():
            resolved.append(p.resolve())
        elif (root / p).exists():
            resolved.append(root / p)
        else:
            resolved.append(p)
    scan = scan_paths(resolved, root=root, max_files=int(args.max_files))
    out = Path(args.out) if args.out else None
    text = json.dumps(scan, indent=2) + "\n"
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    if args.json or not out:
        sys.stdout.write(text)
    else:
        print(f"candidates={scan['candidate_count']} hits={scan['hit_count']} files={scan['file_count']} -> {out}")
    return 0 if scan["candidate_count"] >= 0 else 1


def cmd_score(args: argparse.Namespace) -> int:
    root = _root()
    if args.scan:
        scan = json.loads(Path(args.scan).read_text(encoding="utf-8"))
    else:
        paths = [Path(p) for p in (args.paths or [str(root / DEFAULT_DEMO)])]
        resolved = []
        for p in paths:
            if (root / p).exists():
                resolved.append(root / p)
            else:
                resolved.append(Path(p))
        scan = scan_paths(resolved, root=root)
    cases_path = Path(args.cases) if args.cases else root / DEFAULT_CASES
    if not cases_path.is_file() and (root / DEFAULT_CASES).is_file():
        cases_path = root / DEFAULT_CASES
    pack = load_cases(cases_path)
    report = score_scan(scan, pack)
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    if report["passed"] or args.soft:
        return 0
    return 1


def cmd_inject(args: argparse.Namespace) -> int:
    root = _root()
    if args.scan:
        scan = json.loads(Path(args.scan).read_text(encoding="utf-8"))
    else:
        paths = [Path(p) for p in (args.paths or [str(root / DEFAULT_DEMO)])]
        resolved = [(root / p) if (root / p).exists() else Path(p) for p in paths]
        scan = scan_paths(resolved, root=root)
    prompt = Path(args.prompt)
    ok = inject_into_prompt(prompt, scan)
    if args.federated:
        fed_path = Path(args.federated) if args.federated not in ("1", "true", "yes") else default_fed_path(root)
        if args.federated in ("1", "true", "yes"):
            fed_path = default_fed_path(root)
        sigs = load_json_list(fed_path, "signals")
        if sigs:
            inject_federated_into_prompt(prompt, sigs)
    print(json.dumps({"injected": ok, "candidates": scan.get("candidate_count", 0)}))
    return 0 if ok else 1


def cmd_federate(args: argparse.Namespace) -> int:
    root = _root()
    tp = Path(args.tp_signatures) if args.tp_signatures else None
    if tp is None:
        env = (os.environ.get("TORII_TP_SIGNATURES_FILE") or "").strip()
        cand = Path(env) if env else root / ".torii" / "tp-signatures.json"
        tp = cand if cand.is_file() else None
    scan = None
    if args.scan:
        scan = json.loads(Path(args.scan).read_text(encoding="utf-8"))
    elif args.paths or args.include_scan:
        paths = [Path(p) for p in (args.paths or [str(root / DEFAULT_DEMO)])]
        resolved = [(root / p) if (root / p).exists() else Path(p) for p in paths]
        scan = scan_paths(resolved, root=root)
    dest = Path(args.out) if args.out else default_fed_path(root)
    tenant = (args.tenant or os.environ.get("TORII_MEMORY_TENANT") or "").strip()
    payload = federate(tp_path=tp, scan=scan, dest=dest, tenant=tenant)
    # also write out_dir copy when requested
    if args.out_dir:
        od = Path(args.out_dir)
        od.mkdir(parents=True, exist_ok=True)
        (od / FED_FILENAME).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": payload["count"], "privacy_ok": payload["privacy_ok"], "path": str(dest)}))
    return 0 if payload["privacy_ok"] else 2


def cmd_fixture(args: argparse.Namespace) -> int:
    """Offline e2e: prefilter scores full recall on insecure-demo + federation privacy."""
    root = _root()
    demo = root / DEFAULT_DEMO
    cases = root / DEFAULT_CASES
    scan = scan_paths([demo], root=root)
    pack = load_cases(cases)
    score = score_scan(scan, pack)

    with __import__("tempfile").TemporaryDirectory() as td:
        td_path = Path(td)
        # fabricate TP with private-looking paths to prove sanitization
        tp_path = td_path / "tp-signatures.json"
        tp_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "signatures": [
                        {
                            "id": "sqli-search",
                            "theme": "sql_injection",
                            "cwe": ["CWE-89"],
                            "tags": ["sqli"],
                            "keywords": ["sql injection", "execute(f", "cwe-89"],
                            "path_globs": [
                                "/Users/secret/org/demo/insecure/app.py",
                                "Mr-Ashish--odoo/models/foo.py",
                                "app.py",
                            ],
                            "hits": 2,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        fed_dest = td_path / FED_FILENAME
        payload = federate(tp_path=tp_path, scan=scan, dest=fed_dest, tenant="Acme-Corp")
        issues = assert_privacy(payload.get("signals") or [])
        # ensure basenames only
        for s in payload.get("signals") or []:
            for b in s.get("path_basenames") or []:
                if "/" in b or "Users" in b or "--" in b:
                    issues.append(f"leaked_path:{b}")

        # inject into temp prompt
        prompt = td_path / "prompt.md"
        prompt.write_text("# review\n", encoding="utf-8")
        inject_into_prompt(prompt, scan)
        inject_federated_into_prompt(prompt, payload.get("signals") or [])
        body = prompt.read_text(encoding="utf-8")
        has_pre = "torii-f71-taint-prefilter" in body
        has_fed = "torii-f71-federated-signals" in body

    result = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "fixture_pass": bool(
            score.get("passed")
            and score.get("recall", 0) >= 1.0
            and not issues
            and has_pre
            and has_fed
            and payload.get("count", 0) >= 1
        ),
        "score": score,
        "federated_count": payload.get("count"),
        "privacy_ok": not issues and payload.get("privacy_ok"),
        "privacy_issues": issues,
        "inject_prefilter": has_pre,
        "inject_federated": has_fed,
        "candidate_count": scan.get("candidate_count"),
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if result["fixture_pass"] else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F71 taint prefilter + federated signals")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("scan", help="scan paths for source→sink candidates")
    ps.add_argument("paths", nargs="*", help="files or dirs (default demo/insecure)")
    ps.add_argument("--out", default="", help="write JSON to path")
    ps.add_argument("--json", action="store_true", help="always print JSON")
    ps.add_argument("--max-files", type=int, default=200)
    ps.set_defaults(func=cmd_scan)

    po = sub.add_parser("score", help="score scan vs labeled cases")
    po.add_argument("paths", nargs="*", help="optional paths to scan")
    po.add_argument("--scan", default="", help="existing scan JSON")
    po.add_argument("--cases", default="", help="cases pack JSON")
    po.add_argument("--out", default="")
    po.add_argument("--soft", action="store_true", help="exit 0 even if recall < 1")
    po.set_defaults(func=cmd_score)

    pi = sub.add_parser("inject", help="inject prefilter (+ optional federated) into prompt")
    pi.add_argument("--prompt", required=True)
    pi.add_argument("paths", nargs="*")
    pi.add_argument("--scan", default="")
    pi.add_argument(
        "--federated",
        nargs="?",
        const="1",
        default="",
        help="also inject federated signals (optional path)",
    )
    pi.set_defaults(func=cmd_inject)

    pf = sub.add_parser("federate", help="sanitize+merge TP/prefilter into federated signals")
    pf.add_argument("--tp-signatures", default="")
    pf.add_argument("--scan", default="")
    pf.add_argument("--include-scan", action="store_true", help="scan default demo paths")
    pf.add_argument("paths", nargs="*")
    pf.add_argument("--out", default="")
    pf.add_argument("--out-dir", default="")
    pf.add_argument("--tenant", default="")
    pf.set_defaults(func=cmd_federate)

    px = sub.add_parser("fixture", help="offline e2e: recall + privacy + inject")
    px.add_argument("--out", default="")
    px.set_defaults(func=cmd_fixture)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

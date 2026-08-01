#!/usr/bin/env python3
"""F72: Full-chain revalidation — deterministic maker/checker gate.

Research drivers (2026):
  - VulAgent: hypothesis-validation multi-agent (discovery ≠ confirmation)
  - QASecClaw: SAST+LLM contextual review for FP reduction
  - Argus: multi-agent full-chain vuln detection (source→sink evidence)
  - deepsec: AI investigation → revalidation before final call
  - Loop Engineering: Maker/Checker split — implementer cannot mark work done

Product thesis: F70 dual-pass critic scores path/FP/TP; F71 surfaces
source→sink candidates. Missing was a **separate checker** that revalidates
review findings against static chain evidence and demotes narrative-only claims.

Confidence ladder (checker, not maker):
  full_chain   — path + theme/CWE + taint candidate (source→sink) on same path
  theme_path   — path + theme/CWE keywords (no static candidate match)
  path_only    — path evidence without security theme
  unvalidated  — narrative / no path (demote)
  likely_fp    — matches durable FP rule

Commands:
  revalidate  — check review.md (+ optional taint scan JSON or scan paths)
  score       — revalidate + score vs labeled cases pack
  inject      — write checker brief into prompt (require full-chain for block)
  fixture     — offline e2e: good vs weak fixtures + scorecard
  scorecard   — print Loop-Ready-style readiness metrics from a revalidate JSON

Env:
  TORII_ROOT
  TORII_CHAIN_REVALIDATE   1 (default) | 0/off
  TORII_TP_SIGNATURES_FILE
  TORII_FP_RULES_FILE
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

FEATURE = "F72"
SCHEMA = 1
DEFAULT_CASES = "docs/benchmarks/cases/insecure-demo.json"
DEFAULT_GOOD = "docs/benchmarks/fixtures/insecure-demo-good-review.md"
DEFAULT_WEAK = "docs/benchmarks/fixtures/insecure-demo-weak-review.md"
DEFAULT_DEMO = "demo/insecure"

# Hypothesis catalog — CWE/theme signatures the checker expects evidence for
HYPOTHESES: list[dict[str, Any]] = [
    {
        "id": "hyp-sqli",
        "theme": "sql_injection",
        "cwe": ["CWE-89"],
        "keywords": [
            "sql injection",
            "sqli",
            "cwe-89",
            "execute(f",
            "f-string",
            "string-formatted",
            "cur.execute",
        ],
    },
    {
        "id": "hyp-pickle",
        "theme": "insecure_deserialization",
        "cwe": ["CWE-502"],
        "keywords": [
            "pickle",
            "deserialize",
            "deserialization",
            "cwe-502",
            "pickle.loads",
            "unsafe load",
        ],
    },
    {
        "id": "hyp-cmdi",
        "theme": "command_injection",
        "cwe": ["CWE-78"],
        "keywords": [
            "command injection",
            "shell=true",
            "shell = true",
            "subprocess",
            "cwe-78",
            "os command",
            "rce",
            "shell injection",
        ],
    },
    {
        "id": "hyp-secrets",
        "theme": "secrets_exposure",
        "cwe": ["CWE-200", "CWE-798"],
        "keywords": [
            "secret",
            "api key",
            "api_key",
            "credential",
            "openrouter",
            "exposure",
            "exposes",
            "hardcoded",
        ],
    },
    {
        "id": "hyp-xss",
        "theme": "xss",
        "cwe": ["CWE-79"],
        "keywords": ["xss", "cross-site", "cwe-79", "innerhtml", "unescaped"],
    },
    {
        "id": "hyp-ssrf",
        "theme": "ssrf",
        "cwe": ["CWE-918"],
        "keywords": ["ssrf", "cwe-918", "server-side request", "url open"],
    },
    {
        "id": "hyp-path-trav",
        "theme": "path_traversal",
        "cwe": ["CWE-22"],
        "keywords": ["path traversal", "directory traversal", "cwe-22", "../"],
    },
    {
        "id": "hyp-code-exec",
        "theme": "code_execution",
        "cwe": ["CWE-94", "CWE-95"],
        "keywords": ["eval(", "exec(", "code injection", "cwe-94"],
    },
]

_PATH_RX = re.compile(
    r"(?:"
    r"`([^`\n]+?\.(?:py|js|ts|tsx|go|java|rb|php|rs|c|cpp|h|jsx|vue|sql))(?::(\d{1,7}))?`"
    r"|"
    r"\b([\w./-]+?\.(?:py|js|ts|tsx|go|java|rb|php|rs|c|cpp|h|jsx|vue|sql))(?::(\d{1,7}))?\b"
    r")"
)
_FINDING_SPLIT = re.compile(r"(?m)^(?:\d+\.|[-*]|###)\s+")
_VERDICT_RX = re.compile(
    r"\*\*Verdict:\*\*\s*(APPROVE|REQUEST\s*CHANGES|COMMENT|LGTM|CHANGES\s*REQUESTED)\b",
    re.I,
)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def enabled() -> bool:
    raw = (os.environ.get("TORII_CHAIN_REVALIDATE") or "").strip().lower()
    if raw in ("0", "off", "false", "no"):
        return False
    if raw in ("1", "on", "true", "yes"):
        return True
    try:
        from feature_toggles import is_enabled  # type: ignore

        return bool(is_enabled("chain_revalidate"))
    except Exception:
        return True


def normalize_verdict(raw: str) -> str:
    v = re.sub(r"\s+", " ", (raw or "").strip().upper())
    if v in ("REQUEST CHANGES", "REQUEST_CHANGES", "REQUEST-CHANGES", "CHANGES REQUESTED"):
        return "REQUEST_CHANGES"
    if v in ("LGTM",):
        return "APPROVE"
    if v in ("APPROVE", "COMMENT"):
        return v
    return "UNKNOWN"


def parse_verdict(text: str) -> str:
    m = _VERDICT_RX.search(text or "")
    if not m:
        return "UNKNOWN"
    return normalize_verdict(m.group(1))


def extract_path_hits(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in _PATH_RX.finditer(text or ""):
        path = (m.group(1) or m.group(3) or "").strip().strip("`")
        line_s = m.group(2) or m.group(4)
        if not path:
            continue
        key = f"{path}:{line_s or ''}"
        if key in seen:
            continue
        seen.add(key)
        line: int | None = None
        if line_s:
            try:
                line = int(line_s)
            except ValueError:
                line = None
        hits.append({"path": path, "line": line})
    return hits


def extract_finding_chunks(text: str) -> list[str]:
    body = text or ""
    regions: list[str] = []
    for hdr in (
        r"###\s+Blocking\b",
        r"###\s+Security audit\b",
        r"###\s+Key findings\b",
    ):
        m = re.search(hdr, body, re.I)
        if not m:
            continue
        start = m.end()
        nxt = re.search(r"(?m)^###\s+", body[start:])
        end = start + nxt.start() if nxt else len(body)
        regions.append(body[start:end])
    blob = "\n".join(regions) if regions else body
    parts = _FINDING_SPLIT.split(blob)
    chunks = [p.strip() for p in parts if p and len(p.strip()) > 24]
    # Filter pure boilerplate
    out: list[str] = []
    for c in chunks:
        low = _norm(c)
        if low in ("none", "n/a", "no major issues spotted.", "no issues"):
            continue
        if low.startswith("none ") or low == "none":
            continue
        out.append(c)
    return out[:40]


def match_hypotheses(chunk: str) -> list[dict[str, Any]]:
    low = _norm(chunk)
    hits: list[dict[str, Any]] = []
    for h in HYPOTHESES:
        matched_kws = [k for k in (h.get("keywords") or []) if k.lower() in low]
        cwe_hit = any(str(c).lower() in low for c in (h.get("cwe") or []))
        if matched_kws or cwe_hit:
            hits.append(
                {
                    "id": h["id"],
                    "theme": h["theme"],
                    "cwe": list(h.get("cwe") or []),
                    "matched_keywords": matched_kws[:8],
                    "cwe_hit": cwe_hit,
                }
            )
    return hits


def _basename(p: str) -> str:
    return Path(str(p).replace("\\", "/")).name.lower()


def _path_overlap(finding_paths: list[dict[str, Any]], cand_path: str) -> bool:
    cp = str(cand_path or "").lower().replace("\\", "/")
    cb = _basename(cp)
    for hp in finding_paths:
        p = str(hp.get("path") or "").lower().replace("\\", "/")
        if not p:
            continue
        if p in cp or cp in p or _basename(p) == cb:
            return True
        # shared suffix segments
        if p.endswith(cb) or cp.endswith(_basename(p)):
            return True
    return False


def match_taint_candidates(
    finding_paths: list[dict[str, Any]],
    hyp_hits: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    themes = {str(h.get("theme") or "").lower() for h in hyp_hits}
    cwes = set()
    for h in hyp_hits:
        for c in h.get("cwe") or []:
            cwes.add(str(c).upper())
    out: list[dict[str, Any]] = []
    for c in candidates or []:
        if not isinstance(c, dict):
            continue
        cpath = str(c.get("path") or "")
        if finding_paths and not _path_overlap(finding_paths, cpath):
            # allow theme-only match when no path on finding (weaker)
            path_ok = False
        else:
            path_ok = True if finding_paths else bool(cpath)
        ctheme = str(c.get("theme") or "").lower()
        ccwe = {str(x).upper() for x in (c.get("cwe") or [])}
        theme_ok = (ctheme in themes) if themes else False
        cwe_ok = bool(cwes & ccwe) if cwes else False
        if path_ok and (theme_ok or cwe_ok):
            out.append(
                {
                    "id": c.get("id"),
                    "theme": ctheme,
                    "path": cpath,
                    "source_line": c.get("source_line"),
                    "sink_line": c.get("sink_line"),
                    "confidence": c.get("confidence"),
                    "source_rule": c.get("source_rule"),
                    "sink_rule": c.get("sink_rule"),
                }
            )
    return out[:8]


def load_fp_rules(path: Path | None = None) -> list[dict[str, Any]]:
    if path is None:
        env = (os.environ.get("TORII_FP_RULES_FILE") or "").strip()
        path = Path(env) if env else _root() / ".torii" / "fp-rules.json"
    if not path.is_file():
        # also try memory path used by F64
        alt = _root() / "memory" / "fp-rules.json"
        path = alt if alt.is_file() else path
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        return [x for x in (data.get("rules") or []) if isinstance(x, dict)]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def load_scan(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def scan_demo_or_paths(paths: list[Path] | None = None) -> dict[str, Any]:
    """Soft import F71 scanner; empty dict if unavailable."""
    root = _root()
    try:
        sys.path.insert(0, str(root / "scripts"))
        from taint_prefilter import scan_paths  # type: ignore
    except Exception:
        return {}
    targets = paths or []
    if not targets:
        demo = root / DEFAULT_DEMO
        if demo.is_dir():
            targets = [demo]
    if not targets:
        return {}
    try:
        return scan_paths(targets, root=root)
    except Exception:
        return {}


@dataclass
class FindingCheck:
    index: int
    status: str
    has_path: bool
    paths: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    taint_matches: list[dict[str, Any]] = field(default_factory=list)
    demote_reason: str = ""
    keep_for_blocking: bool = False
    preview: str = ""


def revalidate(
    review_text: str,
    *,
    scan: dict[str, Any] | None = None,
    fp_rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Checker pass: revalidate maker findings against hypothesis + chain evidence."""
    chunks = extract_finding_chunks(review_text)
    candidates = list((scan or {}).get("candidates") or [])
    fp_rules = fp_rules if fp_rules is not None else load_fp_rules()
    verdict = parse_verdict(review_text)
    # Document-level paths: later bullets often omit the file named in summary/item 1
    global_paths = extract_path_hits(review_text)

    findings: list[FindingCheck] = []
    counts = {
        "full_chain": 0,
        "theme_path": 0,
        "path_only": 0,
        "unvalidated": 0,
        "likely_fp": 0,
    }

    for i, ch in enumerate(chunks):
        low = _norm(ch)
        local_paths = extract_path_hits(ch)
        # Inherit review-level paths for security hypotheses (common review style)
        hyps = match_hypotheses(ch)
        paths = local_paths if local_paths else (global_paths if hyps else [])
        has_path = bool(paths)
        taint = match_taint_candidates(paths, hyps, candidates)
        # Theme-aligned taint when document path inheritance still missed
        if not taint and hyps and candidates:
            themes = {str(h.get("theme") or "").lower() for h in hyps}
            for c in candidates:
                if not isinstance(c, dict):
                    continue
                if str(c.get("theme") or "").lower() not in themes:
                    continue
                # Prefer path overlap with local/global; else accept sole-theme match
                cpath = str(c.get("path") or "")
                if paths or global_paths:
                    if not _path_overlap(paths or global_paths, cpath):
                        continue
                taint.append(
                    {
                        "id": c.get("id"),
                        "theme": c.get("theme"),
                        "path": cpath,
                        "source_line": c.get("source_line"),
                        "sink_line": c.get("sink_line"),
                        "confidence": c.get("confidence"),
                        "source_rule": c.get("source_rule"),
                        "sink_rule": c.get("sink_rule"),
                    }
                )
            taint = taint[:8]

        demoted = False
        demote_reason = ""
        for rule in fp_rules:
            rpath = str(rule.get("path") or "").lower()
            if rpath and rpath in low:
                demoted = True
                demote_reason = f"fp_rule:{rpath}"
                break

        if demoted:
            status = "likely_fp"
            keep = False
        elif taint and hyps:
            # Static source→sink (or sink-only) candidate confirms the hypothesis chain
            status = "full_chain"
            keep = True
        elif has_path and hyps:
            status = "theme_path"
            keep = True
        elif hyps and not has_path:
            # Hypothesis without path: still demote — checker needs path evidence
            status = "unvalidated"
            keep = False
        elif has_path:
            status = "path_only"
            keep = False
        else:
            status = "unvalidated"
            keep = False

        counts[status] = counts.get(status, 0) + 1
        findings.append(
            FindingCheck(
                index=i,
                status=status,
                has_path=has_path,
                paths=paths[:5],
                hypotheses=hyps,
                taint_matches=taint,
                demote_reason=demote_reason,
                keep_for_blocking=keep,
                preview=ch[:180].replace("\n", " "),
            )
        )

    total = len(findings) or 1
    validated = counts["full_chain"] + counts["theme_path"]
    full_chain_rate = round(counts["full_chain"] / total, 4)
    validated_rate = round(validated / total, 4)
    precision_proxy = validated_rate  # checker-confirmed / all chunks
    demoted_n = counts["unvalidated"] + counts["likely_fp"] + counts["path_only"]

    # Scorecard (Loop Engineering readiness-inspired, product-scoped)
    # full_chain weight high; theme_path medium; unvalidated hurts
    score_raw = (
        50.0 * full_chain_rate
        + 30.0 * (counts["theme_path"] / total)
        + 20.0 * (1.0 if verdict == "REQUEST_CHANGES" and validated > 0 else 0.0)
        - 15.0 * (counts["unvalidated"] / total)
    )
    scorecard_pct = round(max(0.0, min(100.0, score_raw)), 1)

    # Blocking recommendation from checker (independent of maker verdict)
    if counts["full_chain"] >= 1 or (counts["theme_path"] >= 2 and validated >= 2):
        checker_verdict = "REQUEST_CHANGES"
    elif validated == 0:
        checker_verdict = "APPROVE" if verdict in ("APPROVE", "UNKNOWN", "COMMENT") else "COMMENT"
    else:
        checker_verdict = "COMMENT"

    return {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "pass": "chain_revalidate",
        "role": "checker",  # maker/checker split
        "scanned_at": _now(),
        "verdict_maker": verdict,
        "verdict_checker": checker_verdict,
        "chunk_count": len(chunks),
        "candidate_count": len(candidates),
        "counts": counts,
        "full_chain_rate": full_chain_rate,
        "validated_rate": validated_rate,
        "precision_proxy": precision_proxy,
        "demoted": demoted_n,
        "scorecard_pct": scorecard_pct,
        "findings": [asdict(f) for f in findings],
        "blocking_findings": [
            asdict(f) for f in findings if f.keep_for_blocking
        ],
    }


def score_against_cases(report: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    """Measure whether checker-kept findings cover ground-truth cases."""
    # Build blob from validated findings only
    kept = report.get("blocking_findings") or [
        f
        for f in (report.get("findings") or [])
        if f.get("keep_for_blocking")
        or f.get("status") in ("full_chain", "theme_path")
    ]
    blob_parts: list[str] = []
    for f in kept:
        blob_parts.append(str(f.get("preview") or ""))
        for h in f.get("hypotheses") or []:
            blob_parts.append(str(h.get("theme") or ""))
            blob_parts.extend(str(k) for k in (h.get("matched_keywords") or []))
            blob_parts.extend(str(c) for c in (h.get("cwe") or []))
        for p in f.get("paths") or []:
            blob_parts.append(str(p.get("path") or ""))
        for t in f.get("taint_matches") or []:
            blob_parts.append(str(t.get("theme") or ""))
            blob_parts.extend(
                str(x)
                for x in (
                    t.get("sink_rule"),
                    t.get("source_rule"),
                    t.get("id"),
                )
                if x
            )
    blob = " ".join(blob_parts).lower()

    cases = [c for c in (pack.get("cases") or []) if isinstance(c, dict)]
    tp = fn = 0
    results = []
    for case in cases:
        required = bool(case.get("required", True))
        must = [str(m).lower() for m in (case.get("must_match_any") or [])]
        theme = str(case.get("theme") or "").lower()
        hit = any(m in blob for m in must) if must else (theme and theme in blob)
        if not hit and theme and theme in blob:
            hit = True
        status = "tp" if hit else "fn"
        if required:
            if hit:
                tp += 1
            else:
                fn += 1
        results.append(
            {
                "case_id": case.get("id"),
                "theme": theme,
                "matched": hit,
                "status": status,
                "required": required,
            }
        )
    required_n = sum(1 for c in cases if c.get("required", True))
    recall = (tp / required_n) if required_n else 0.0
    return {
        "tp": tp,
        "fn": fn,
        "required": required_n,
        "recall": round(recall, 4),
        "passed": fn == 0 and required_n > 0,
        "cases": results,
    }


# ---------------------------------------------------------------------------
# Prompt inject — checker brief (maker must leave chain evidence)
# ---------------------------------------------------------------------------


def render_checker_section(scan: dict[str, Any] | None = None) -> str:
    cands = (scan or {}).get("candidates") or []
    lines = [
        "<!-- torii-f72-chain-revalidate -->",
        "## Full-chain evidence gate (F72 checker)",
        "",
        "Maker/Checker split: your draft findings are the **maker** output. A separate",
        "deterministic **checker** revalidates them. For each security finding you raise:",
        "",
        "1. **Hypothesis** — name CWE/theme (e.g. CWE-89 SQL injection).",
        "2. **Path evidence** — concrete `file.ext` (line if known).",
        "3. **Chain** — source→sink or sink with untrusted input (prefer F71 candidates).",
        "",
        "Findings without path + theme will be demoted as `unvalidated` and must not alone",
        "drive REQUEST CHANGES. Prefer silence over narrative-only claims.",
        "",
    ]
    if cands:
        lines.append("Static candidates available for chain confirmation:")
        for c in cands[:12]:
            cwe = c.get("cwe") or []
            cwe_s = ",".join(cwe) if isinstance(cwe, list) else str(cwe)
            src = c.get("source_line") or 0
            snk = c.get("sink_line") or 0
            flow = f"L{src}→L{snk}" if src else f"sink@L{snk}"
            lines.append(
                f"- `{c.get('id')}` theme={c.get('theme')} cwe={cwe_s or 'n/a'} "
                f"path=`{c.get('path')}` {flow}"
            )
        lines.append("")
    return "\n".join(lines)


def inject_into_prompt(prompt_path: Path, scan: dict[str, Any] | None = None) -> bool:
    section = render_checker_section(scan)
    if not section:
        return False
    text = (
        prompt_path.read_text(encoding="utf-8", errors="replace")
        if prompt_path.is_file()
        else ""
    )
    marker = "<!-- torii-f72-chain-revalidate -->"
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
    prompt_path.write_text(
        text if text.endswith("\n") else text + "\n", encoding="utf-8"
    )
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_revalidate(args: argparse.Namespace) -> int:
    review = Path(args.review).read_text(encoding="utf-8", errors="replace")
    scan: dict[str, Any] = {}
    if args.scan:
        scan = load_scan(Path(args.scan))
    elif args.paths:
        scan = scan_demo_or_paths([Path(p) for p in args.paths])
    elif args.auto_scan:
        scan = scan_demo_or_paths()
    report = revalidate(review, scan=scan, fp_rules=load_fp_rules(Path(args.fp_rules) if args.fp_rules else None))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        c = report["counts"]
        print(f"feature={FEATURE} role=checker")
        print(
            f"chunks={report['chunk_count']} full_chain={c['full_chain']} "
            f"theme_path={c['theme_path']} path_only={c['path_only']} "
            f"unvalidated={c['unvalidated']} likely_fp={c['likely_fp']}"
        )
        print(
            f"full_chain_rate={report['full_chain_rate']} "
            f"validated_rate={report['validated_rate']} "
            f"precision_proxy={report['precision_proxy']} "
            f"scorecard_pct={report['scorecard_pct']}"
        )
        print(
            f"verdict_maker={report['verdict_maker']} "
            f"verdict_checker={report['verdict_checker']}"
        )
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    review = Path(args.review).read_text(encoding="utf-8", errors="replace")
    pack = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    scan: dict[str, Any] = {}
    if args.scan:
        scan = load_scan(Path(args.scan))
    elif args.paths:
        scan = scan_demo_or_paths([Path(p) for p in args.paths])
    elif args.auto_scan:
        scan = scan_demo_or_paths()
    report = revalidate(review, scan=scan)
    scored = score_against_cases(report, pack)
    out = {**report, "case_score": scored}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out if args.json else {
        "recall": scored["recall"],
        "tp": scored["tp"],
        "fn": scored["fn"],
        "passed": scored["passed"],
        "full_chain_rate": report["full_chain_rate"],
        "precision_proxy": report["precision_proxy"],
        "scorecard_pct": report["scorecard_pct"],
        "verdict_checker": report["verdict_checker"],
    }, indent=2))
    return 0 if scored["passed"] or args.soft else 1


def cmd_inject(args: argparse.Namespace) -> int:
    scan = load_scan(Path(args.scan)) if args.scan else (
        scan_demo_or_paths() if args.auto_scan else {}
    )
    if args.print_only:
        print(render_checker_section(scan), end="")
        return 0
    ok = inject_into_prompt(Path(args.prompt), scan)
    print(f"injected={int(ok)} prompt={args.prompt}")
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Offline e2e: good fixture high full_chain; weak low; recall on good."""
    root = _root()
    cases_path = Path(args.cases) if args.cases else root / DEFAULT_CASES
    good_path = Path(args.good) if args.good else root / DEFAULT_GOOD
    weak_path = Path(args.weak) if args.weak else root / DEFAULT_WEAK
    out_dir = Path(args.out_dir) if args.out_dir else root / ".torii-out" / "bench-f72"
    out_dir.mkdir(parents=True, exist_ok=True)

    pack = json.loads(cases_path.read_text(encoding="utf-8"))
    good = good_path.read_text(encoding="utf-8", errors="replace")
    weak = weak_path.read_text(encoding="utf-8", errors="replace")
    scan = scan_demo_or_paths([root / DEFAULT_DEMO])

    good_r = revalidate(good, scan=scan)
    weak_r = revalidate(weak, scan=scan)
    good_score = score_against_cases(good_r, pack)
    weak_score = score_against_cases(weak_r, pack)

    # Also inject into a temp prompt to verify marker
    prompt = out_dir / "prompt-snippet.md"
    prompt.write_text("# test prompt\n", encoding="utf-8")
    inject_ok = inject_into_prompt(prompt, scan)
    inject_text = prompt.read_text(encoding="utf-8")
    inject_has_marker = "<!-- torii-f72-chain-revalidate -->" in inject_text

    delta_full = round(
        float(good_r["full_chain_rate"]) - float(weak_r["full_chain_rate"]), 4
    )
    delta_prec = round(
        float(good_r["precision_proxy"]) - float(weak_r["precision_proxy"]), 4
    )
    delta_score = round(
        float(good_r["scorecard_pct"]) - float(weak_r["scorecard_pct"]), 1
    )

    fixture_pass = (
        good_score["passed"]
        and float(good_r["full_chain_rate"]) >= 0.5
        and float(good_r["precision_proxy"]) > float(weak_r["precision_proxy"])
        and good_r["verdict_checker"] == "REQUEST_CHANGES"
        and inject_ok
        and inject_has_marker
    )

    result = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "fixture_pass": fixture_pass,
        "good": {
            "full_chain_rate": good_r["full_chain_rate"],
            "precision_proxy": good_r["precision_proxy"],
            "scorecard_pct": good_r["scorecard_pct"],
            "verdict_checker": good_r["verdict_checker"],
            "counts": good_r["counts"],
            "case_score": good_score,
        },
        "weak": {
            "full_chain_rate": weak_r["full_chain_rate"],
            "precision_proxy": weak_r["precision_proxy"],
            "scorecard_pct": weak_r["scorecard_pct"],
            "verdict_checker": weak_r["verdict_checker"],
            "counts": weak_r["counts"],
            "case_score": weak_score,
        },
        "delta_full_chain_rate": delta_full,
        "delta_precision_proxy": delta_prec,
        "delta_scorecard_pct": delta_score,
        "inject_ok": inject_ok,
        "inject_marker": inject_has_marker,
        "candidate_count": good_r["candidate_count"],
    }
    (out_dir / "fixture-result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "good-revalidate.json").write_text(
        json.dumps(good_r, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "weak-revalidate.json").write_text(
        json.dumps(weak_r, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if fixture_pass else 1


def cmd_scorecard(args: argparse.Namespace) -> int:
    """Loop-Engineering-inspired readiness print from a revalidate JSON."""
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    checks = [
        ("has_findings", int(data.get("chunk_count") or 0) > 0),
        ("full_chain_rate>=0.5", float(data.get("full_chain_rate") or 0) >= 0.5),
        ("validated_rate>=0.5", float(data.get("validated_rate") or 0) >= 0.5),
        (
            "checker_blocks_on_chain",
            data.get("verdict_checker") == "REQUEST_CHANGES"
            and int((data.get("counts") or {}).get("full_chain") or 0) > 0,
        ),
        ("maker_checker_split", data.get("role") == "checker"),
        ("no_all_unvalidated", int((data.get("counts") or {}).get("unvalidated") or 0)
         < max(1, int(data.get("chunk_count") or 1))),
    ]
    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    pct = round(100.0 * passed / total, 1) if total else 0.0
    out = {
        "feature": FEATURE,
        "scorecard": "chain_revalidate_ready",
        "passed": passed,
        "total": total,
        "pct": pct,
        "level": "L3" if pct >= 90 else "L2" if pct >= 70 else "L1" if pct >= 50 else "L0",
        "checks": [{"id": i, "ok": ok} for i, ok in checks],
        "scorecard_pct_product": data.get("scorecard_pct"),
    }
    print(json.dumps(out, indent=2))
    return 0 if pct >= 70 else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="F72 full-chain revalidation (maker/checker)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("revalidate", help="Revalidate a review against chain evidence")
    r.add_argument("review", help="Path to review.md")
    r.add_argument("--scan", help="taint-candidates.json from F71")
    r.add_argument("--paths", nargs="*", help="Paths to scan with F71")
    r.add_argument("--auto-scan", action="store_true", help="Scan demo/insecure")
    r.add_argument("--fp-rules", help="fp-rules.json path")
    r.add_argument("--out", help="Write full JSON report")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_revalidate)

    s = sub.add_parser("score", help="Revalidate + score vs labeled cases")
    s.add_argument("review")
    s.add_argument("--cases", default=None)
    s.add_argument("--scan")
    s.add_argument("--paths", nargs="*")
    s.add_argument("--auto-scan", action="store_true")
    s.add_argument("--out")
    s.add_argument("--json", action="store_true")
    s.add_argument("--soft", action="store_true")
    s.set_defaults(func=cmd_score)

    i = sub.add_parser("inject", help="Inject checker brief into prompt")
    i.add_argument("--prompt", required=False, help="Prompt path")
    i.add_argument("--scan")
    i.add_argument("--auto-scan", action="store_true")
    i.add_argument("--print-only", action="store_true")
    i.set_defaults(func=cmd_inject)

    f = sub.add_parser("fixture", help="Offline good/weak e2e scorecard")
    f.add_argument("--cases")
    f.add_argument("--good")
    f.add_argument("--weak")
    f.add_argument("--out-dir")
    f.set_defaults(func=cmd_fixture)

    sc = sub.add_parser("scorecard", help="Readiness scorecard from report JSON")
    sc.add_argument("report", help="revalidate JSON path")
    sc.set_defaults(func=cmd_scorecard)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # default cases path for score
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "cases", None) is None and args.cmd == "score":
        args.cases = str(_root() / DEFAULT_CASES)
    if args.cmd == "inject" and not args.print_only and not args.prompt:
        print("inject requires --prompt or --print-only", file=sys.stderr)
        return 2
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

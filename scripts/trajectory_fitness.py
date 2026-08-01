#!/usr/bin/env python3
"""F73: Trajectory fitness + paper-ready eval-trace vault.

Research drivers (2026):
  - Hermes Agent Self-Evolution: multi-dim fitness (correctness / procedure /
    conciseness) + GEPA that *reads execution traces* to propose mutations
  - Loop Engineering loop-verifier: independent checker with evidence checklist
    (default REJECT until proven)
  - H9 trajectory packaging for offline eval / research paper corpora

Product thesis:
  F69 packages trajectories; F70 scores review vs labels; F71/F72 score chain
  evidence. Missing was a **deterministic fitness scorer on the agent loop
  itself** (tool use, path cites, procedure structure) and a **versioned
  paper-safe trace vault** under docs/benchmarks/traces/ with INDEX.

Composite fitness (mirrors Hermes FitnessScore weights, no LLM judge):
  0.40 * path_evidence
  + 0.25 * procedure
  + 0.20 * tool_use
  + 0.15 * chain_quality
  - length_penalty

Commands:
  score     — multi-dim fitness from review + optional agent-loop / chain JSON
  archive   — write versioned vault dir + slim summary + update INDEX.md
  inject    — procedure/fitness rubric into review prompt
  fixture   — offline good vs weak (+ optional showcase agent-loop)
  promote   — soft-append fitness signal into evolution ledger
  pack      — score + archive convenience

Env:
  TORII_ROOT
  TORII_TRAJECTORY_FITNESS   1 (default) | 0/off
  TORII_TRACE_VAULT          1 (default) | 0/off — archive to docs vault
  TORII_TRACE_VAULT_ROOT     override vault root
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F73"
SCHEMA = 1
MARKER = "<!-- torii-f73-trajectory-fitness -->"
DEFAULT_GOOD = "docs/benchmarks/fixtures/insecure-demo-good-review.md"
DEFAULT_WEAK = "docs/benchmarks/fixtures/insecure-demo-weak-review.md"
DEFAULT_SHOWCASE_LOOP = (
    "docs/showcase/devmemory-dogfood-luffy/agent-loop/agent-loop.json"
)
INDEX_NAME = "INDEX.md"
SUMMARY_NAME = "summary.json"
FITNESS_NAME = "fitness.json"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

_PATH_RX = re.compile(
    r"(?:"
    r"`([^`\n]+?\.(?:py|js|ts|tsx|go|java|rb|php|rs|c|cpp|h|jsx|vue|sql))(?::(\d{1,7}))?`"
    r"|"
    r"\b([\w./-]+?\.(?:py|js|ts|tsx|go|java|rb|php|rs|c|cpp|h|jsx|vue|sql))(?::(\d{1,7}))?\b"
    r")"
)
_VERDICT_RX = re.compile(
    r"\*\*Verdict:\*\*\s*(APPROVE|REQUEST\s*CHANGES|COMMENT|LGTM|CHANGES\s*REQUESTED)\b",
    re.I,
)
_THEME_RX = re.compile(
    r"(sql\s*injection|sqli|cwe-89|pickle|deserializ|cwe-502|command\s*injection|"
    r"shell\s*=\s*true|cwe-78|secret|api[_\s-]?key|cwe-798|xss|cwe-79|path\s*traversal|"
    r"ssrf|rce|injection)",
    re.I,
)
_TRIGGER_RX = re.compile(
    r"(trigger|exploit|poc|repro|attacker|crafted|payload|GET\s+/|POST\s+/)",
    re.I,
)

# Large blobs: keep slim summary; raw may be gitignored via vault rules
_LARGE_SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".zip", ".gz", ".tar", ".db", ".sqlite"}
_LARGE_MAX_BYTES = 400_000  # skip copying files larger than this into vault


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")


def _truthy_env(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSEY


def enabled() -> bool:
    return _truthy_env("TORII_TRAJECTORY_FITNESS", True)


def vault_enabled() -> bool:
    return _truthy_env("TORII_TRACE_VAULT", True)


def vault_root(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_TRACE_VAULT_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    r = root or _root()
    return r / "docs" / "benchmarks" / "traces"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


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


def extract_path_hits(text: str) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for m in _PATH_RX.finditer(text or ""):
        path = (m.group(1) or m.group(3) or "").strip().strip("`")
        if not path or path in seen:
            continue
        seen.add(path)
        hits.append(path)
    return hits


def load_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Fitness scoring
# ---------------------------------------------------------------------------


@dataclass
class FitnessScore:
    """Multi-dimensional trajectory fitness (deterministic)."""

    tool_use: float = 0.0
    path_evidence: float = 0.0
    procedure: float = 0.0
    chain_quality: float = 0.0
    conciseness: float = 1.0
    length_penalty: float = 0.0
    composite: float = 0.0
    level: str = "L0"
    verdict: str = "UNKNOWN"
    path_hits: list[str] = field(default_factory=list)
    tool_call_turns: int = 0
    theme_hits: int = 0
    trigger_hits: int = 0
    review_chars: int = 0
    feedback: list[str] = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)
    feature: str = FEATURE
    schema_version: int = SCHEMA
    scored_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _level_from_composite(c: float) -> str:
    if c >= 0.85:
        return "L3"
    if c >= 0.65:
        return "L2"
    if c >= 0.40:
        return "L1"
    return "L0"


def score_tool_use(loop: dict[str, Any], review: str) -> tuple[float, int, list[str]]:
    """Score tool depth from agent-loop package or review 'What I checked'."""
    fb: list[str] = []
    turns = 0
    if loop:
        turns = int(
            loop.get("tool_call_turns")
            or loop.get("tool_turns")
            or 0
        )
        if not turns and isinstance(loop.get("steps"), list):
            turns = sum(
                1
                for s in loop["steps"]
                if isinstance(s, dict)
                and (
                    s.get("kind") in ("assistant_tool_calls", "tool", "tool_call")
                    or s.get("tool_calls")
                    or s.get("tool_name")
                )
            )
    # Review-side proxy when no loop: deep workspace vs skim
    checked = ""
    m = re.search(r"(?is)###?\s*What I checked\s*\n(.+?)(?:\n###|\Z)", review or "")
    if m:
        checked = m.group(1)
    deep_words = len(
        re.findall(
            r"\b(workspace|rg|grep|read|sed|cat|open|inspect|symbol|hunk|diff)\b",
            checked,
            re.I,
        )
    )
    skim = bool(re.search(r"\bskim|diff only|no deep\b", checked, re.I))

    if turns >= 5:
        score = 1.0
    elif turns >= 3:
        score = 0.85
    elif turns >= 1:
        score = 0.65
    elif deep_words >= 2 and not skim:
        score = 0.55
        fb.append("no agent-loop; inferred moderate depth from What I checked")
    elif skim or (checked and deep_words == 0):
        score = 0.15
        fb.append("shallow What I checked / skim-only")
    else:
        score = 0.35
        fb.append("no tool-turn evidence; neutral tool_use")
    return _clamp(score), turns, fb


def score_path_evidence(review: str) -> tuple[float, list[str], list[str]]:
    hits = extract_path_hits(review)
    fb: list[str] = []
    n = len(hits)
    # Prefer repo-relative paths (dir/file.ext) over bare basenames
    deep = [h for h in hits if "/" in h or "\\" in h]
    n_deep = len(deep)
    if n_deep >= 2:
        score = 1.0
    elif n_deep == 1 and n >= 2:
        score = 0.9
    elif n_deep == 1:
        score = 0.75
    elif n >= 2:
        score = 0.45
        fb.append("path cites are basename-only (prefer dir/file)")
    elif n == 1:
        score = 0.3
        fb.append("single basename-only path cite")
    else:
        score = 0.1
        fb.append("no path evidence in review")
    return _clamp(score), hits, fb


def score_procedure(review: str) -> tuple[float, str, int, int, list[str]]:
    fb: list[str] = []
    verdict = parse_verdict(review)
    themes = len(_THEME_RX.findall(review or ""))
    triggers = len(_TRIGGER_RX.findall(review or ""))
    has_blocking = bool(re.search(r"(?im)^###?\s*Blocking\b", review or ""))
    has_summary = bool(re.search(r"(?im)^###?\s*Summary\b", review or ""))
    has_security = bool(re.search(r"(?im)^###?\s*Security\b", review or ""))
    has_checked = bool(re.search(r"(?im)^###?\s*What I checked\b", review or ""))
    has_confidence = bool(re.search(r"\*\*Confidence:\*\*", review or "", re.I))
    has_score = bool(re.search(r"\*\*Score:\*\*", review or "", re.I))

    pts = 0.0
    max_pts = 8.0
    if verdict != "UNKNOWN":
        pts += 1.5
    else:
        fb.append("missing Verdict")
    if has_summary:
        pts += 1.0
    if has_blocking:
        pts += 1.0
    if has_security or themes:
        pts += 1.0
    if has_checked:
        pts += 1.0
    if has_confidence:
        pts += 0.5
    if has_score:
        pts += 0.5
    if themes >= 2:
        pts += 1.0
    elif themes == 1:
        pts += 0.5
    if triggers >= 1:
        pts += 0.5
    else:
        fb.append("no trigger/exploit scenario language")

    score = _clamp(pts / max_pts)
    return score, verdict, themes, triggers, fb


def score_chain_quality(chain: dict[str, Any], review: str) -> tuple[float, list[str]]:
    fb: list[str] = []
    if chain:
        counts = chain.get("counts") or {}
        total = int(counts.get("total") or chain.get("finding_count") or 0)
        full = int(counts.get("full_chain") or 0)
        theme = int(counts.get("theme_path") or 0)
        unval = int(counts.get("unvalidated") or 0)
        rate = chain.get("full_chain_rate")
        if rate is None and total:
            rate = full / total
        elif rate is None:
            rate = 0.0
        proxy = float(chain.get("precision_proxy") or 0.0)
        score = _clamp(0.6 * float(rate) + 0.4 * proxy)
        if unval and total and unval / total > 0.5:
            fb.append("majority findings unvalidated by chain checker")
        if full + theme == 0 and total:
            fb.append("no full_chain/theme_path from F72")
        return score, fb
    # Fallback: theme+path co-presence
    paths = extract_path_hits(review)
    themes = len(_THEME_RX.findall(review or ""))
    if paths and themes >= 2:
        return 0.7, ["chain JSON absent; inferred from path+theme"]
    if paths and themes:
        return 0.5, ["chain JSON absent; weak theme signal"]
    if themes:
        return 0.25, ["chain JSON absent; theme without path"]
    return 0.15, ["chain JSON absent; no theme/path"]


def score_length(review: str) -> tuple[float, float, int]:
    n = len(review or "")
    # Ideal band ~800–6000 chars for a PR review
    if n < 200:
        penalty = 0.25
        conc = 0.4
    elif n < 400:
        penalty = 0.1
        conc = 0.7
    elif n <= 8000:
        penalty = 0.0
        conc = 1.0
    elif n <= 16000:
        penalty = 0.1
        conc = 0.75
    else:
        penalty = 0.25
        conc = 0.5
    return conc, penalty, n


def _load_scorecard_ops(root: Path | None = None) -> dict[str, Any]:
    """F134: soft load product scorecard + federated scorecard skill themes."""
    root = root or _root()
    out: dict[str, Any] = {
        "brand_ready": None,
        "scorecard_skills_n": 0,
        "fed_n": 0,
    }
    for cand in (
        root / ".torii" / "product-scorecard.json",
    ):
        if cand.is_file():
            try:
                sc = json.loads(cand.read_text(encoding="utf-8"))
                out["brand_ready"] = sc.get("brand_ready")
                out["level"] = sc.get("level")
                m = sc.get("metrics") or {}
                out["dual_triple"] = m.get("dual_compound_triple_ready")
                break
            except (OSError, json.JSONDecodeError):
                pass
    fed = root / "memory" / "federation" / "scorecard-skill-signals.json"
    if fed.is_file():
        try:
            doc = json.loads(fed.read_text(encoding="utf-8"))
            out["fed_n"] = int(doc.get("count") or len(doc.get("signals") or []))
            out["scorecard_skills_n"] = len(doc.get("skill_ids") or [])
            out["privacy_ok"] = doc.get("privacy_ok")
        except (OSError, json.JSONDecodeError):
            pass
    # active scorecard skills on disk
    active = root / "agent" / "skills" / "active"
    if active.is_dir():
        n = sum(
            1
            for p in active.glob("skill-prefer-*.md")
            if any(
                x in p.stem
                for x in (
                    "scorecard",
                    "demote-eval",
                    "memory-util",
                    "workflow",
                    "hub-gap",
                    "dual-compound",
                )
            )
        )
        out["active_scorecard_n"] = n
        out["scorecard_skills_n"] = max(int(out.get("scorecard_skills_n") or 0), n)
    return out


def compute_fitness(
    review: str,
    *,
    loop: dict[str, Any] | None = None,
    chain: dict[str, Any] | None = None,
    root: Path | None = None,
) -> FitnessScore:
    loop = loop or {}
    chain = chain or {}
    feedback: list[str] = []

    tool_s, turns, fb = score_tool_use(loop, review)
    feedback.extend(fb)
    path_s, paths, fb = score_path_evidence(review)
    feedback.extend(fb)
    proc_s, verdict, themes, triggers, fb = score_procedure(review)
    feedback.extend(fb)
    chain_s, fb = score_chain_quality(chain, review)
    feedback.extend(fb)
    conc, pen, nchars = score_length(review)

    # F134: soft blend scorecard ops readiness into procedure/tool dims (capped)
    ops = _load_scorecard_ops(root or _root())
    ops_bonus = 0.0
    if ops.get("brand_ready") is True:
        ops_bonus += 0.04
        feedback.append("f134_scorecard_brand_ready")
    n_sc = int(ops.get("scorecard_skills_n") or ops.get("active_scorecard_n") or 0)
    if n_sc >= 1:
        ops_bonus += min(0.06, 0.02 * n_sc)
        feedback.append(f"f134_scorecard_skills_n={n_sc}")
    if ops.get("dual_triple") is True:
        ops_bonus += 0.02
        feedback.append("f134_dual_compound_triple")
    # F136: mid-run scorecard skill util (tool_hit) soft-blend when present
    sc_util_path = None
    for cand in (
        (root or _root()) / ".torii-out" / "scorecard-skill-util.json",
        Path(os.environ.get("OUT_DIR") or "") / "scorecard-skill-util.json"
        if (os.environ.get("OUT_DIR") or "").strip()
        else None,
    ):
        if cand and cand.is_file():
            sc_util_path = cand
            break
    if sc_util_path is not None:
        try:
            scu = json.loads(sc_util_path.read_text(encoding="utf-8"))
            if scu.get("utilization_gap"):
                ops_bonus = max(0.0, ops_bonus - 0.03)
                feedback.append("f136_scorecard_util_gap")
            elif int(scu.get("tool_hit_n") or 0) >= 1:
                ops_bonus += 0.03
                feedback.append(
                    f"f136_scorecard_util_rate={scu.get('util_rate')}"
                )
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    # apply half to procedure, half to tool_use (ops discipline)
    if ops_bonus > 0:
        proc_s = _clamp(proc_s + ops_bonus * 0.5)
        tool_s = _clamp(tool_s + ops_bonus * 0.5)

    raw = (
        0.40 * path_s
        + 0.25 * proc_s
        + 0.20 * tool_s
        + 0.15 * chain_s
    )
    composite = _clamp(raw - pen)
    level = _level_from_composite(composite)

    return FitnessScore(
        tool_use=round(tool_s, 4),
        path_evidence=round(path_s, 4),
        procedure=round(proc_s, 4),
        chain_quality=round(chain_s, 4),
        conciseness=round(conc, 4),
        length_penalty=round(pen, 4),
        composite=round(composite, 4),
        level=level,
        verdict=verdict,
        path_hits=paths,
        tool_call_turns=turns,
        theme_hits=themes,
        trigger_hits=triggers,
        review_chars=nchars,
        feedback=feedback,
        signals={
            "weights": {
                "path_evidence": 0.40,
                "procedure": 0.25,
                "tool_use": 0.20,
                "chain_quality": 0.15,
            },
            "raw_before_penalty": round(raw, 4),
            "f134_ops_bonus": round(ops_bonus, 4),
            "f134_scorecard": {
                k: ops.get(k)
                for k in (
                    "brand_ready",
                    "scorecard_skills_n",
                    "active_scorecard_n",
                    "fed_n",
                    "dual_triple",
                )
            },
        },
        scored_at=_now(),
    )


# ---------------------------------------------------------------------------
# Inject rubric
# ---------------------------------------------------------------------------


def render_rubric_section() -> str:
    return f"""{MARKER}
## Trajectory fitness rubric (F73 — procedure contract)

Independent fitness scorer (Hermes-style multi-dim, deterministic) will grade this run:

| Dimension | Weight | Expectation |
|-----------|--------|-------------|
| path_evidence | 0.40 | Cite concrete `path` or `path:line` for every blocking finding |
| procedure | 0.25 | Verdict + Blocking + Security + What I checked + trigger scenario |
| tool_use | 0.20 | ≥1 workspace/diff tool read on multi-file or security-sensitive PRs |
| chain_quality | 0.15 | Prefer full-chain (path + theme + source→sink) over narrative |

**Default stance:** low fitness until path evidence + procedure structure are present.
Do not claim "looks fine" without path cites when the diff touches auth, SQL, shell, or pickle.
"""


def inject_into_prompt(prompt_path: Path) -> bool:
    if not enabled():
        return False
    section = render_rubric_section()
    text = (
        prompt_path.read_text(encoding="utf-8", errors="replace")
        if prompt_path.is_file()
        else ""
    )
    if MARKER in text:
        text = re.sub(
            rf"{re.escape(MARKER)}[\s\S]*?(?=\n<!--|\Z)",
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
# Archive / vault
# ---------------------------------------------------------------------------


def _short_sha(s: str, n: int = 7) -> str:
    h = hashlib.sha256((s or "x").encode()).hexdigest()
    return h[:n]


def _safe_label(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", (s or "run").strip())[:48]
    return s.strip("-") or "run"


def _redact_text(s: str) -> str:
    patterns = [
        (re.compile(r"sk-or-v1-[A-Za-z0-9_-]{10,}"), "[OPENROUTER_KEY_REDACTED]"),
        (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[API_KEY_REDACTED]"),
        (re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.I), "Bearer [REDACTED]"),
        (re.compile(r"(OPENROUTER_API_KEY=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"/Users/[^/\s]+"), "/Users/[REDACTED]"),
        (re.compile(r"/home/[^/\s]+"), "/home/[REDACTED]"),
    ]
    out = s
    for rx, repl in patterns:
        out = rx.sub(repl, out)
    return out


def _copy_slim(src: Path, dest: Path) -> bool:
    if not src.is_file():
        return False
    if src.suffix.lower() in _LARGE_SKIP_SUFFIX:
        return False
    try:
        size = src.stat().st_size
    except OSError:
        return False
    if size > _LARGE_MAX_BYTES:
        # write stub pointer
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            f"[omitted large file: {src.name} bytes={size}]\n", encoding="utf-8"
        )
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        text = src.read_text(encoding="utf-8", errors="replace")
        dest.write_text(_redact_text(text), encoding="utf-8")
        return True
    except Exception:
        try:
            shutil.copy2(src, dest)
            return True
        except Exception:
            return False


def make_run_id(
    *,
    label: str = "run",
    pr: str = "",
    repo: str = "",
    model: str = "",
    extra: str = "",
) -> str:
    slug = _now_slug()
    parts = [slug]
    if repo:
        parts.append(_safe_label(repo.replace("/", "-")))
    if pr:
        parts.append(f"PR{_safe_label(str(pr))}")
    parts.append(_safe_label(label))
    seed = f"{slug}|{repo}|{pr}|{model}|{extra}|{label}"
    parts.append(_short_sha(seed))
    return "-".join(parts)


def archive_run(
    *,
    out_dir: Path | None = None,
    review_path: Path | None = None,
    fitness: FitnessScore | None = None,
    label: str = "run",
    repo: str = "",
    pr: str = "",
    model: str = "",
    root: Path | None = None,
    include_agent_loop: bool = True,
) -> dict[str, Any]:
    """Write paper-safe vault entry + update INDEX.md."""
    root = root or _root()
    vroot = vault_root(root)
    vroot.mkdir(parents=True, exist_ok=True)

    out_dir = Path(out_dir) if out_dir else None
    if review_path is None and out_dir:
        # common names
        for cand in (
            out_dir / "review.md",
            out_dir / f"review-{pr}.md" if pr else None,
        ):
            if cand and cand.is_file():
                review_path = cand
                break
    review_text = ""
    if review_path and review_path.is_file():
        review_text = review_path.read_text(encoding="utf-8", errors="replace")

    loop: dict[str, Any] = {}
    if out_dir:
        loop = load_json(out_dir / "agent-loop" / "agent-loop.json")
        chain = load_json(out_dir / "chain-revalidate.json")
    else:
        chain = {}

    if fitness is None:
        fitness = compute_fitness(review_text, loop=loop, chain=chain)

    model = model or os.environ.get("TORII_MODEL") or os.environ.get(
        "OPENROUTER_MODEL"
    ) or (loop.get("model") if loop else "") or "unknown"
    repo = repo or os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY") or ""
    pr = str(pr or os.environ.get("PR_NUMBER") or "")

    run_id = make_run_id(label=label, pr=pr, repo=repo, model=str(model))
    dest = vroot / run_id
    dest.mkdir(parents=True, exist_ok=True)

    artifacts: list[str] = []
    # slim review
    if review_text:
        (dest / "review.md").write_text(
            _redact_text(review_text), encoding="utf-8"
        )
        artifacts.append("review.md")

    fit_dict = fitness.to_dict()
    (dest / FITNESS_NAME).write_text(
        json.dumps(fit_dict, indent=2) + "\n", encoding="utf-8"
    )
    artifacts.append(FITNESS_NAME)

    # optional copies from out_dir
    if out_dir and out_dir.is_dir():
        for name in (
            "timings.json",
            "hermes-usage.json",
            "meta.env",
            "prompt.md",
            "context.md",
            "chain-revalidate.json",
            "taint-candidates.json",
        ):
            if _copy_slim(out_dir / name, dest / name):
                artifacts.append(name)
        if include_agent_loop:
            al = out_dir / "agent-loop"
            if al.is_dir():
                for name in (
                    "agent-loop.json",
                    "agent-loop.md",
                    "usage.json",
                    "messages.json",
                ):
                    if _copy_slim(al / name, dest / "agent-loop" / name):
                        artifacts.append(f"agent-loop/{name}")
                # agent.log may be huge — slim head
                logp = al / "agent.log"
                if logp.is_file():
                    try:
                        raw = logp.read_text(encoding="utf-8", errors="replace")
                        slim = _redact_text(raw[:80_000])
                        if len(raw) > 80_000:
                            slim += f"\n\n[truncated tail omitted bytes={len(raw)}]\n"
                        (dest / "agent-loop").mkdir(parents=True, exist_ok=True)
                        (dest / "agent-loop" / "agent.log").write_text(
                            slim, encoding="utf-8"
                        )
                        artifacts.append("agent-loop/agent.log")
                    except Exception:
                        pass

    summary = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "run_id": run_id,
        "archived_at": _now(),
        "repo": repo or None,
        "pr_number": pr or None,
        "model": model,
        "label": label,
        "fitness": {
            "composite": fitness.composite,
            "level": fitness.level,
            "tool_use": fitness.tool_use,
            "path_evidence": fitness.path_evidence,
            "procedure": fitness.procedure,
            "chain_quality": fitness.chain_quality,
            "verdict": fitness.verdict,
            "tool_call_turns": fitness.tool_call_turns,
        },
        "artifacts": artifacts,
        "git_safe": True,
        "notes": "Redacted slim vault entry for eval/paper; large blobs omitted/truncated",
    }
    (dest / SUMMARY_NAME).write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    artifacts.append(SUMMARY_NAME)

    def _rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(root.resolve()))
        except Exception:
            return str(p)

    rel = _rel(dest)

    # meta pointer
    (dest / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "feature": FEATURE,
                "path": rel,
                "summary": SUMMARY_NAME,
                "fitness": FITNESS_NAME,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    index_path = vroot / INDEX_NAME
    _update_index(index_path, summary, rel=rel)

    # pointer for orchestrator
    if out_dir:
        try:
            (out_dir / "latest-vault-dir.txt").write_text(str(dest) + "\n", encoding="utf-8")
            (out_dir / FITNESS_NAME).write_text(
                json.dumps(fit_dict, indent=2) + "\n", encoding="utf-8"
            )
        except Exception:
            pass

    return {
        "ok": True,
        "run_id": run_id,
        "path": str(dest),
        "rel": rel,
        "summary": summary,
        "fitness": fit_dict,
    }


def _update_index(index_path: Path, summary: dict[str, Any], rel: str) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Torii eval-trace vault INDEX\n\n"
        "Paper/eval-safe slim traces (redacted). Large raw logs may be gitignored; "
        "always keep INDEX + summary.json + fitness.json.\n\n"
        "| Date (UTC) | Repo | PR | Model | Fitness | Level | Path |\n"
        "|------------|------|----|-------|---------|-------|------|\n"
    )
    fit = summary.get("fitness") or {}
    row = (
        f"| {summary.get('archived_at', '')} "
        f"| {summary.get('repo') or '-'} "
        f"| {summary.get('pr_number') or '-'} "
        f"| {summary.get('model') or '-'} "
        f"| {fit.get('composite', '-')} "
        f"| {fit.get('level', '-')} "
        f"| `{rel}` |\n"
    )
    if index_path.is_file():
        text = index_path.read_text(encoding="utf-8", errors="replace")
        if "| Date (UTC) |" not in text:
            text = header
        # append if not duplicate run_id
        run_id = summary.get("run_id") or ""
        if run_id and run_id in text:
            return
        if not text.endswith("\n"):
            text += "\n"
        text += row
    else:
        text = header + row
    index_path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Promote into evolution ledger (soft signal)
# ---------------------------------------------------------------------------


def promote_to_evolution(
    fitness: FitnessScore,
    *,
    root: Path | None = None,
    run_id: str = "",
    repo: str = "",
    pr: str = "",
) -> dict[str, Any]:
    root = root or _root()
    evo = root / "memory" / "evolution"
    evo.mkdir(parents=True, exist_ok=True)
    ledger_path = evo / "ledger.json"
    if ledger_path.is_file():
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            ledger = {}
    else:
        ledger = {
            "schema_version": 1,
            "feature": "F69",
            "trajectories": [],
            "proposals": [],
            "adopted": [],
        }
    ledger.setdefault("fitness_signals", [])
    signal = {
        "at": _now(),
        "feature": FEATURE,
        "run_id": run_id,
        "repo": repo,
        "pr": pr,
        "composite": fitness.composite,
        "level": fitness.level,
        "tool_use": fitness.tool_use,
        "path_evidence": fitness.path_evidence,
        "procedure": fitness.procedure,
        "chain_quality": fitness.chain_quality,
        "verdict": fitness.verdict,
        "feedback": fitness.feedback[:8],
        "low_fitness": fitness.composite < 0.5,
        "high_fitness": fitness.composite >= 0.85,
    }
    signals = ledger["fitness_signals"]
    if not isinstance(signals, list):
        signals = []
    signals.append(signal)
    # keep last 100
    ledger["fitness_signals"] = signals[-100:]
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "ledger": str(ledger_path), "signal": signal}


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_score(args: argparse.Namespace) -> int:
    review_path = Path(args.review)
    if not review_path.is_file():
        print(json.dumps({"error": f"missing review: {review_path}"}))
        return 2
    review = review_path.read_text(encoding="utf-8", errors="replace")
    loop = load_json(Path(args.loop) if args.loop else None)
    chain = load_json(Path(args.chain) if args.chain else None)
    if args.out_dir:
        od = Path(args.out_dir)
        if not loop:
            loop = load_json(od / "agent-loop" / "agent-loop.json")
        if not chain:
            chain = load_json(od / "chain-revalidate.json")
    fit = compute_fitness(review, loop=loop, chain=chain)
    out = fit.to_dict()
    if args.min_composite is not None:
        out["passed"] = fit.composite >= float(args.min_composite)
    print(json.dumps(out, indent=2))
    if args.min_composite is not None and fit.composite < float(args.min_composite):
        return 1
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    if not vault_enabled() and not args.force:
        print(json.dumps({"ok": False, "skipped": True, "reason": "TORII_TRACE_VAULT off"}))
        return 0
    out_dir = Path(args.out_dir) if args.out_dir else None
    review = Path(args.review) if args.review else None
    loop = load_json(Path(args.loop) if args.loop else None)
    chain = load_json(Path(args.chain) if args.chain else None)
    review_text = ""
    if review and review.is_file():
        review_text = review.read_text(encoding="utf-8", errors="replace")
    elif out_dir:
        for cand in sorted(out_dir.glob("review*.md")):
            review_text = cand.read_text(encoding="utf-8", errors="replace")
            review = cand
            break
    if out_dir:
        if not loop:
            loop = load_json(out_dir / "agent-loop" / "agent-loop.json")
        if not chain:
            chain = load_json(out_dir / "chain-revalidate.json")
    fit = compute_fitness(review_text, loop=loop, chain=chain)
    result = archive_run(
        out_dir=out_dir,
        review_path=review,
        fitness=fit,
        label=args.label or "run",
        repo=args.repo or "",
        pr=args.pr or "",
        model=args.model or "",
        include_agent_loop=not args.no_loop,
    )
    if args.promote:
        result["promote"] = promote_to_evolution(
            fit,
            run_id=result.get("run_id", ""),
            repo=args.repo or "",
            pr=args.pr or "",
        )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def cmd_inject(args: argparse.Namespace) -> int:
    path = Path(args.prompt)
    ok = inject_into_prompt(path)
    print(json.dumps({"ok": ok, "path": str(path), "marker": MARKER, "enabled": enabled()}))
    return 0 if ok else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    good_p = root / DEFAULT_GOOD
    weak_p = root / DEFAULT_WEAK
    loop_p = root / DEFAULT_SHOWCASE_LOOP
    good = good_p.read_text(encoding="utf-8")
    weak = weak_p.read_text(encoding="utf-8")
    loop = load_json(loop_p) if loop_p.is_file() else {}

    chain: dict[str, Any] = {}
    try:
        import subprocess as _sp

        r = _sp.run(
            [
                sys.executable,
                str(root / "scripts" / "chain_revalidate.py"),
                "revalidate",
                str(good_p),
                "--auto-scan",
                "--json",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        if r.returncode == 0 and r.stdout.strip():
            chain = json.loads(r.stdout)
    except Exception:
        chain = {}

    fit_good = compute_fitness(good, loop=loop, chain=chain)
    fit_weak = compute_fitness(weak, loop={}, chain={})

    # inject check
    import tempfile

    inject_ok = False
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "prompt.md"
        p.write_text("# prompt\n", encoding="utf-8")
        os.environ.setdefault("TORII_TRAJECTORY_FITNESS", "1")
        inject_ok = inject_into_prompt(p) and MARKER in p.read_text(encoding="utf-8")

    delta = round(fit_good.composite - fit_weak.composite, 4)
    # Archive good as fixture sample when requested
    archived = None
    if args.archive:
        archived = archive_run(
            review_path=good_p,
            fitness=fit_good,
            label="fixture-insecure-good",
            repo="torii/demo",
            pr="0",
            model="fixture",
            include_agent_loop=False,
        )
        # also drop a minimal agent-loop pointer if showcase exists
        if loop and archived.get("path"):
            dest = Path(archived["path"])
            (dest / "agent-loop").mkdir(exist_ok=True)
            (dest / "agent-loop" / "agent-loop.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "note": "showcase loop reference for fixture",
                        "tool_call_turns": loop.get("tool_call_turns"),
                        "model": loop.get("model"),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    fixture_pass = (
        fit_good.composite >= 0.55
        and fit_weak.composite < fit_good.composite
        and delta >= 0.15
        and fit_good.path_evidence >= 0.6
        and fit_weak.path_evidence <= 0.5
        and inject_ok
    )
    out = {
        "feature": FEATURE,
        "fixture_pass": fixture_pass,
        "good": fit_good.to_dict(),
        "weak": fit_weak.to_dict(),
        "delta_composite": delta,
        "inject_ok": inject_ok,
        "chain_used": bool(chain),
        "loop_used": bool(loop),
        "archived": archived,
    }
    print(json.dumps(out, indent=2))
    return 0 if fixture_pass else 1


def cmd_promote(args: argparse.Namespace) -> int:
    fit_path = Path(args.fitness) if args.fitness else None
    if fit_path and fit_path.is_file():
        data = load_json(fit_path)
        fit = FitnessScore(
            tool_use=float(data.get("tool_use") or 0),
            path_evidence=float(data.get("path_evidence") or 0),
            procedure=float(data.get("procedure") or 0),
            chain_quality=float(data.get("chain_quality") or 0),
            conciseness=float(data.get("conciseness") or 1),
            length_penalty=float(data.get("length_penalty") or 0),
            composite=float(data.get("composite") or 0),
            level=str(data.get("level") or "L0"),
            verdict=str(data.get("verdict") or "UNKNOWN"),
            feedback=list(data.get("feedback") or []),
            scored_at=str(data.get("scored_at") or _now()),
        )
    else:
        review = Path(args.review).read_text(encoding="utf-8", errors="replace")
        fit = compute_fitness(review)
    result = promote_to_evolution(
        fit, run_id=args.run_id or "", repo=args.repo or "", pr=args.pr or ""
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    """Score + archive + optional promote (post-review hook)."""
    ns = argparse.Namespace(
        out_dir=args.out_dir,
        review=args.review,
        loop=args.loop,
        chain=args.chain,
        label=args.label or "e2e",
        repo=args.repo,
        pr=args.pr,
        model=args.model,
        promote=args.promote,
        no_loop=args.no_loop,
        force=True,
    )
    return cmd_archive(ns)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F73 trajectory fitness + trace vault")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("score", help="score review fitness")
    ps.add_argument("review", help="path to review.md")
    ps.add_argument("--loop", help="agent-loop.json")
    ps.add_argument("--chain", help="chain-revalidate.json")
    ps.add_argument("--out-dir", help="torii out dir (auto-load loop/chain)")
    ps.add_argument("--min-composite", type=float, default=None)
    ps.set_defaults(func=cmd_score)

    pa = sub.add_parser("archive", help="archive slim vault entry + INDEX")
    pa.add_argument("--out-dir", help="torii out dir")
    pa.add_argument("--review", help="review.md path")
    pa.add_argument("--loop", help="agent-loop.json")
    pa.add_argument("--chain", help="chain-revalidate.json")
    pa.add_argument("--label", default="run")
    pa.add_argument("--repo", default="")
    pa.add_argument("--pr", default="")
    pa.add_argument("--model", default="")
    pa.add_argument("--promote", action="store_true")
    pa.add_argument("--no-loop", action="store_true")
    pa.add_argument("--force", action="store_true")
    pa.set_defaults(func=cmd_archive)

    pi = sub.add_parser("inject", help="inject fitness rubric into prompt")
    pi.add_argument("prompt", help="prompt.md path")
    pi.set_defaults(func=cmd_inject)

    pf = sub.add_parser("fixture", help="offline good vs weak fitness e2e")
    pf.add_argument("--archive", action="store_true", help="also vault the good fixture")
    pf.set_defaults(func=cmd_fixture)

    pp = sub.add_parser("promote", help="append fitness signal to evolution ledger")
    pp.add_argument("--fitness", help="fitness.json")
    pp.add_argument("--review", help="review.md if no fitness.json")
    pp.add_argument("--run-id", default="")
    pp.add_argument("--repo", default="")
    pp.add_argument("--pr", default="")
    pp.set_defaults(func=cmd_promote)

    pk = sub.add_parser("pack", help="score+archive (+ optional promote)")
    pk.add_argument("--out-dir", required=True)
    pk.add_argument("--review", default="")
    pk.add_argument("--loop", default="")
    pk.add_argument("--chain", default="")
    pk.add_argument("--label", default="e2e")
    pk.add_argument("--repo", default="")
    pk.add_argument("--pr", default="")
    pk.add_argument("--model", default="")
    pk.add_argument("--promote", action="store_true")
    pk.add_argument("--no-loop", action="store_true")
    pk.set_defaults(func=cmd_pack)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

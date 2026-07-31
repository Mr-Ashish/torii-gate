#!/usr/bin/env python3
"""F61: deterministic suggested test plan from PR files + optional unified diff.

Pure code — no LLM. Builds prioritized, concrete scenarios for authors and for
the review ``### Suggested test plan`` section. Improves D3 actionability when
model findings are soft/empty.

Usage:
  python3 scripts/testplan_generation.py generate --pr-json pr.json
  python3 scripts/testplan_generation.py generate --pr-json pr.json --diff pr.diff
  python3 scripts/testplan_generation.py section --pr-json pr.json --diff pr.diff
  python3 scripts/testplan_generation.py apply --review review.md --pr-json pr.json
  python3 scripts/testplan_generation.py plan --pr-json pr.json   # JSON

Env:
  TORII_TESTPLAN=1 (default) | 0/off
  TORII_TESTPLAN_MAX_CASES=12
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Toggle
# ---------------------------------------------------------------------------


def _truthy(val: str | None, default: bool = True) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() not in ("0", "false", "no", "off", "disabled")


def enabled(raw: str | None = None) -> bool:
    try:
        from feature_toggles import is_enabled  # type: ignore

        return bool(is_enabled("testplan"))
    except Exception:
        v = raw if raw is not None else os.environ.get("TORII_TESTPLAN")
        return _truthy(v, default=True)


def max_cases() -> int:
    try:
        from feature_toggles import get_value  # type: ignore

        v = get_value("testplan_max_cases")
        if v is not None:
            return max(1, int(v))
    except Exception:
        pass
    raw = (os.environ.get("TORII_TESTPLAN_MAX_CASES") or "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return 12


# ---------------------------------------------------------------------------
# File / symbol helpers
# ---------------------------------------------------------------------------

_TEST_PATH_RE = re.compile(
    r"(?:^|/)(?:tests?|testing|__tests__|spec|testdata)(?:/|$)"
    r"|(?:_test|_spec|Test|Spec)\.[^/]+$"
    r"|test_[^/]+\.[^/]+$"
    r"|[^/]+_test\.[^/]+$",
    re.I,
)

_GO_FUNC = re.compile(r"^\+\s*func\s+(?:\([^)]+\)\s*)?(\w+)\s*\(", re.M)
_PY_DEF = re.compile(r"^\+\s*def\s+(\w+)\s*\(", re.M)
_PY_CLASS = re.compile(r"^\+\s*class\s+(\w+)\s*[\(:]", re.M)
_JS_FN = re.compile(
    r"^\+\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", re.M
)
_JS_ARROW = re.compile(
    r"^\+\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
    re.M,
)
_RUST_FN = re.compile(r"^\+\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*[<\(]", re.M)
_TYPE_DECL = re.compile(
    r"^\+\s*(?:type|struct|interface|enum)\s+(\w+)\b", re.M
)

_DIFF_FILE_RE = re.compile(r"^\+\+\+\s+b/(.+)$", re.M)
_HUNK_HEADER = re.compile(r"^@@ .+ @@(?:\s+(.*))?$", re.M)

_SECURITY_HINTS = (
    "security",
    "auth",
    "permission",
    "acl",
    "csrf",
    "oauth",
    "credential",
    "secret",
    "token",
    "password",
    "crypto",
    "tls",
    "ssl",
    "sanitize",
    "escape",
    "inject",
)
_MIGRATION_HINTS = ("migration", "migrate", "alembic", "schema/versions")
_CONFIG_EXTS = (".yml", ".yaml", ".toml", ".ini", ".cfg", ".json", ".env.example")
_HOT_PATH_HINTS = (
    "writebuffer",
    "interceptor",
    "handler",
    "proxy",
    "gateway",
    "delegator",
    "wal",
    "streaming",
    "query",
    "insert",
    "rpc",
    "grpc",
)


@dataclass
class TestCase:
    priority: str  # P0 | P1 | P2
    kind: str  # unit | integration | e2e | negative | security | migration | config | smoke
    target: str  # path or symbol
    scenario: str
    rationale: str
    source: str = "heuristic"  # heuristic | symbol | gap | path


@dataclass
class TestPlan:
    cases: list[TestCase] = field(default_factory=list)
    prod_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    has_prod_without_tests: bool = False
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases": [asdict(c) for c in self.cases],
            "prod_files": self.prod_files,
            "test_files": self.test_files,
            "symbols": self.symbols,
            "has_prod_without_tests": self.has_prod_without_tests,
            "summary": self.summary,
            "n_cases": len(self.cases),
        }


def is_test_path(path: str) -> bool:
    p = path.replace("\\", "/")
    return bool(_TEST_PATH_RE.search(p))


def is_prod_path(path: str) -> bool:
    if not path or path.endswith("/"):
        return False
    if is_test_path(path):
        return False
    # skip pure docs/license/lock
    name = Path(path).name.lower()
    if name in ("readme.md", "license", "license.md", "changelog.md"):
        return False
    if name.endswith((".md", ".txt", ".lock", ".sum")) and "test" not in name:
        # keep CODEOWNERS-like out; docs alone are low risk
        if path.lower().endswith((".md", ".rst", ".txt")):
            return False
    return True


def parse_paths_from_pr(data: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    files = data.get("files") if isinstance(data, dict) else data
    if not isinstance(files, list):
        return []
    out: list[dict[str, Any]] = []
    for f in files:
        if isinstance(f, str):
            out.append({"path": f, "additions": None, "deletions": None})
            continue
        if not isinstance(f, dict):
            continue
        path = f.get("path") or f.get("filename") or f.get("name")
        if not path:
            continue
        out.append(
            {
                "path": str(path).replace("\\", "/").lstrip("./"),
                "additions": f.get("additions"),
                "deletions": f.get("deletions"),
            }
        )
    return out


def pair_test_for(prod: str, test_paths: list[str]) -> str | None:
    """Best-effort matching test file for a production path."""
    stem = Path(prod).stem
    parent = str(Path(prod).parent).replace("\\", "/")
    candidates = []
    for t in test_paths:
        t_stem = Path(t).stem.replace("_test", "").replace("test_", "").replace("_spec", "")
        t_parent = str(Path(t).parent).replace("\\", "/")
        score = 0
        if stem == t_stem or stem in Path(t).stem or t_stem in stem:
            score += 3
        if parent and (parent in t_parent or t_parent in parent):
            score += 2
        if Path(prod).suffix and Path(t).suffix == Path(prod).suffix:
            score += 1
        if score:
            candidates.append((score, t))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][1]


def extract_symbols_from_diff(diff: str) -> dict[str, list[str]]:
    """Map path → new symbols introduced on + lines."""
    by_file: dict[str, list[str]] = {}
    current: str | None = None
    # process per-file chunks
    chunks = re.split(r"(?=^diff --git )", diff, flags=re.M)
    if len(chunks) <= 1 and "+++" in diff:
        chunks = [diff]
    for chunk in chunks:
        m = _DIFF_FILE_RE.search(chunk)
        if m:
            current = m.group(1).strip()
        elif current is None:
            # bare +++ without diff --git
            m2 = re.search(r"^\+\+\+\s+b/(.+)$", chunk, re.M)
            if m2:
                current = m2.group(1).strip()
        if not current:
            continue
        if is_test_path(current):
            continue
        found: list[str] = []
        for rx in (
            _GO_FUNC,
            _PY_DEF,
            _PY_CLASS,
            _JS_FN,
            _JS_ARROW,
            _RUST_FN,
            _TYPE_DECL,
        ):
            for sm in rx.finditer(chunk):
                name = sm.group(1)
                if name and not name.startswith("Test") and name not in (
                    "init",
                    "main",
                    "setUp",
                    "tearDown",
                ):
                    found.append(name)
        # hunk context function names (@@ ... @@ func Foo)
        for hm in _HUNK_HEADER.finditer(chunk):
            ctx = (hm.group(1) or "").strip()
            for pat in (
                r"func\s+(?:\([^)]+\)\s*)?(\w+)",
                r"def\s+(\w+)",
                r"fn\s+(\w+)",
                r"class\s+(\w+)",
            ):
                cm = re.search(pat, ctx)
                if cm:
                    found.append(cm.group(1))
        if found:
            # unique preserve order
            seen: set[str] = set()
            uniq: list[str] = []
            for n in found:
                if n not in seen:
                    seen.add(n)
                    uniq.append(n)
            by_file[current] = uniq
    return by_file


def _path_has_any(path: str, hints: Iterable[str]) -> bool:
    pl = path.lower()
    return any(h in pl for h in hints)


def build_plan(
    *,
    files: list[dict[str, Any]] | None = None,
    pr_json: dict[str, Any] | list[Any] | None = None,
    diff: str | None = None,
    title: str = "",
    body: str = "",
    limit: int | None = None,
) -> TestPlan:
    if files is None:
        files = parse_paths_from_pr(pr_json or {})
    limit = limit if limit is not None else max_cases()
    paths = [f["path"] for f in files if f.get("path")]
    prod = [p for p in paths if is_prod_path(p)]
    tests = [p for p in paths if is_test_path(p)]
    plan = TestPlan(prod_files=prod, test_files=tests)

    symbols_by_file: dict[str, list[str]] = {}
    if diff:
        symbols_by_file = extract_symbols_from_diff(diff)
        for syms in symbols_by_file.values():
            plan.symbols.extend(syms)
        # unique preserve order
        seen_s: set[str] = set()
        uniq_syms: list[str] = []
        for s in plan.symbols:
            if s not in seen_s:
                seen_s.add(s)
                uniq_syms.append(s)
        plan.symbols = uniq_syms

    cases: list[TestCase] = []
    seen_keys: set[str] = set()

    def add(c: TestCase) -> None:
        key = f"{c.priority}|{c.kind}|{c.target}|{c.scenario[:60]}"
        if key in seen_keys:
            return
        seen_keys.add(key)
        cases.append(c)

    # Gap: production code without any tests in the PR
    if prod and not tests:
        plan.has_prod_without_tests = True
        for p in prod[:4]:
            add(
                TestCase(
                    priority="P0",
                    kind="unit",
                    target=p,
                    scenario=(
                        f"Add unit coverage for new behavior in `{p}` "
                        f"(happy path + one edge: empty/nil/error return)."
                    ),
                    rationale="Production path changed with no test files in this PR",
                    source="gap",
                )
            )
    elif prod and tests:
        # check unpaired prod files
        unpaired = []
        for p in prod:
            if pair_test_for(p, tests) is None:
                unpaired.append(p)
        if unpaired and len(unpaired) >= max(1, len(prod) // 2):
            plan.has_prod_without_tests = True
            for p in unpaired[:3]:
                add(
                    TestCase(
                        priority="P0",
                        kind="unit",
                        target=p,
                        scenario=(
                            f"Add or extend tests for `{p}` — no paired test "
                            f"file appears in this PR."
                        ),
                        rationale="Unpaired production change",
                        source="gap",
                    )
                )

    # Symbol-driven cases
    for fpath, syms in symbols_by_file.items():
        paired = pair_test_for(fpath, tests)
        for sym in syms[:3]:
            tgt = f"{fpath}::{sym}"
            if paired:
                add(
                    TestCase(
                        priority="P0",
                        kind="unit",
                        target=tgt,
                        scenario=(
                            f"In `{paired}`, assert `{sym}` behavior for the "
                            f"new branch introduced in this PR (table-driven "
                            f"if multi-case)."
                        ),
                        rationale=f"New/changed symbol `{sym}` in `{fpath}`",
                        source="symbol",
                    )
                )
            else:
                add(
                    TestCase(
                        priority="P0",
                        kind="unit",
                        target=tgt,
                        scenario=(
                            f"Unit-test `{sym}` in `{fpath}`: cover the new "
                            f"code path and at least one failure/empty input."
                        ),
                        rationale=f"New/changed symbol `{sym}` without paired test file",
                        source="symbol",
                    )
                )

    # Existing tests in PR → run them
    if tests:
        add(
            TestCase(
                priority="P0",
                kind="smoke",
                target=", ".join(tests[:4]),
                scenario=(
                    "Run the added/updated tests in this PR locally or in CI "
                    "and confirm green on the head commit."
                ),
                rationale="PR already touches test files",
                source="path",
            )
        )

    # Security-sensitive paths
    sec_files = [p for p in prod if _path_has_any(p, _SECURITY_HINTS)]
    title_body = f"{title}\n{body}".lower()
    if sec_files or any(h in title_body for h in _SECURITY_HINTS):
        target = sec_files[0] if sec_files else (prod[0] if prod else "security surface")
        add(
            TestCase(
                priority="P0",
                kind="security",
                target=target,
                scenario=(
                    "Negative authz/credential case: invalid, expired, or "
                    "cross-tenant input is rejected; no secret material in logs."
                ),
                rationale="Security-sensitive path or title signal",
                source="heuristic",
            )
        )

    # Migration
    mig = [p for p in paths if _path_has_any(p, _MIGRATION_HINTS)]
    if mig:
        add(
            TestCase(
                priority="P0",
                kind="migration",
                target=mig[0],
                scenario=(
                    "Apply migration on a populated fixture DB, verify schema/"
                    "data, then exercise rollback (or documented irreversible note)."
                ),
                rationale="Migration path in PR",
                source="path",
            )
        )

    # Config / YAML
    cfg = [
        p
        for p in paths
        if p.lower().endswith(_CONFIG_EXTS) or "/configs/" in p.lower()
    ]
    if cfg:
        add(
            TestCase(
                priority="P1",
                kind="config",
                target=cfg[0],
                scenario=(
                    f"Validate `{cfg[0]}` parses (schema/linter) and defaults "
                    f"remain backward-compatible for unset keys."
                ),
                rationale="Config/workflow file changed",
                source="path",
            )
        )

    # Hot-path / concurrency-ish modules (milvus-style)
    hot = [p for p in prod if _path_has_any(p, _HOT_PATH_HINTS)]
    if hot:
        add(
            TestCase(
                priority="P1",
                kind="integration",
                target=hot[0],
                scenario=(
                    f"Integration: exercise the changed hot path in `{hot[0]}` "
                    f"under concurrent or multi-request load if the surface is "
                    f"shared (race / double-call / partial failure)."
                ),
                rationale="Hot-path module heuristic",
                source="heuristic",
            )
        )
        add(
            TestCase(
                priority="P1",
                kind="negative",
                target=hot[0],
                scenario=(
                    f"Negative path on `{hot[0]}`: early-return / skip / error "
                    f"branch when preconditions fail (nil config, empty batch, "
                    f"disabled feature flag)."
                ),
                rationale="Hot paths often add skip/early-return branches",
                source="heuristic",
            )
        )

    # Title/body claim-to-test (skip parse, raise limit, fix, etc.)
    claim_patterns = [
        (
            r"skip\s+\w+",
            "P0",
            "Assert the skip/early-exit branch: when the precondition is false, "
            "heavy work is not invoked (spy/mock call count = 0).",
        ),
        (
            r"raise|increase|ceiling|limit|max\b",
            "P1",
            "Boundary test at old limit −1, old limit, new limit, new limit +1 "
            "(expect reject only past new ceiling).",
        ),
        (
            r"fix|bug|race|nil|npe|panic",
            "P0",
            "Regression test that fails on base and passes on head for the "
            "reported bug trigger.",
        ),
        (
            r"deprecat|remov|break",
            "P1",
            "Compatibility: callers still on the old API get a clear error or "
            "shim; document migration in the test name.",
        ),
    ]
    for pat, pri, scenario in claim_patterns:
        if re.search(pat, title_body, re.I):
            tgt = prod[0] if prod else (tests[0] if tests else "PR claim")
            add(
                TestCase(
                    priority=pri,
                    kind="unit",
                    target=tgt,
                    scenario=scenario,
                    rationale=f"Title/body claim matched /{pat}/",
                    source="heuristic",
                )
            )

    # Docs-only
    if not prod and not tests and paths:
        add(
            TestCase(
                priority="P2",
                kind="smoke",
                target=paths[0],
                scenario="Proofread rendered docs/links; no runtime test required.",
                rationale="Docs/non-code PR",
                source="path",
            )
        )

    # Always: smoke the intended behavior if we still have room
    if prod:
        add(
            TestCase(
                priority="P2",
                kind="e2e",
                target=prod[0],
                scenario=(
                    "End-to-end happy path that exercises the user-visible "
                    "behavior described in the PR title/summary once."
                ),
                rationale="Baseline behavioral smoke",
                source="heuristic",
            )
        )

    # Sort: P0 before P1 before P2, keep stable
    order = {"P0": 0, "P1": 1, "P2": 2}
    cases.sort(key=lambda c: (order.get(c.priority, 9), c.kind, c.target))
    plan.cases = cases[:limit]

    n0 = sum(1 for c in plan.cases if c.priority == "P0")
    n1 = sum(1 for c in plan.cases if c.priority == "P1")
    gap = "prod-without-tests; " if plan.has_prod_without_tests else ""
    plan.summary = (
        f"{len(plan.cases)} case(s) ({n0} P0, {n1} P1); "
        f"{gap}{len(prod)} prod / {len(tests)} test file(s); "
        f"{len(plan.symbols)} symbol(s) from diff"
    )
    return plan


# ---------------------------------------------------------------------------
# Render / apply
# ---------------------------------------------------------------------------


def render_section(plan: TestPlan, *, include_marker: bool = True) -> str:
    parts: list[str] = ["### Suggested test plan"]
    if include_marker:
        parts.append("<!-- torii-testplan -->")
    parts.extend(
        [
            "",
            f"_Auto-generated (F61, deterministic). {plan.summary}. "
            "Authors: treat P0 as merge-blocking coverage gaps; model may refine._",
            "",
        ]
    )
    if not plan.cases:
        parts.append("None — no actionable test scenarios derived from files/diff.")
        parts.append("")
        return "\n".join(parts)

    parts.extend(
        [
            "| Pri | Kind | Target | Scenario |",
            "|-----|------|--------|----------|",
        ]
    )
    for c in plan.cases:
        tgt = c.target.replace("|", "\\|")
        scen = c.scenario.replace("|", "\\|").replace("\n", " ")
        parts.append(f"| {c.priority} | {c.kind} | `{tgt}` | {scen} |")
    parts.append("")
    if plan.prod_files:
        parts.append("<details><summary>Prod files considered</summary>")
        parts.append("")
        for p in plan.prod_files[:40]:
            parts.append(f"- `{p}`")
        parts.append("")
        parts.append("</details>")
        parts.append("")
    return "\n".join(parts)


def render_markdown(plan: TestPlan) -> str:
    """Standalone testplan.md artifact (not necessarily review-section shaped)."""
    lines = [
        "# Suggested test plan (F61)",
        "",
        plan.summary,
        "",
    ]
    if plan.symbols:
        lines.append("## Symbols from diff")
        lines.append("")
        for s in plan.symbols[:40]:
            lines.append(f"- `{s}`")
        lines.append("")
    lines.append("## Cases")
    lines.append("")
    for i, c in enumerate(plan.cases, 1):
        lines.append(f"{i}. **{c.priority}** `{c.kind}` — `{c.target}`")
        lines.append(f"   - {c.scenario}")
        lines.append(f"   - _{c.rationale}_ ({c.source})")
        lines.append("")
    return "\n".join(lines)


def apply_to_review(review: str, section: str, *, force: bool = False) -> str:
    """Insert or replace ### Suggested test plan in a review body.

    If the model already wrote a non-empty plan with the marker or a filled
    table, leave it unless force=True. Soft-inject when missing or placeholder.
    """
    has_marker = "<!-- torii-testplan -->" in review
    has_heading = bool(re.search(r"^### Suggested test plan\s*$", review, re.M))

    placeholder = re.compile(
        r"### Suggested test plan\s*\n(?:<!-- torii-testplan -->\s*\n)?"
        r"(?:None\b[^\n]*|_?n/?a_?|_\s*none\s*_|\s*)\s*(?=\n### |\n## |\Z)",
        re.I | re.S,
    )

    if has_heading or has_marker:
        # Replace only if empty/placeholder or force
        if force or placeholder.search(review) or (
            has_heading
            and not re.search(
                r"### Suggested test plan[\s\S]*?\| Pri \|", review, re.I
            )
        ):
            pat = re.compile(
                r"### Suggested test plan\n.*?(?=\n### |\n## |\Z)",
                re.DOTALL,
            )
            if pat.search(review):
                return pat.sub(section.rstrip() + "\n\n", review, count=1)
        return review

    # Insert before ### Tests & risk, else after Suggestions, else before footer
    for anchor in (
        "### Tests & risk\n",
        "### What I checked\n",
        "### Nits\n",
    ):
        idx = review.find(anchor)
        if idx >= 0:
            return review[:idx] + section.rstrip() + "\n\n" + review[idx:]
    m = re.search(r"\n---\n\*Torii", review)
    if m:
        return review[: m.start()] + "\n" + section + review[m.start() :]
    return review.rstrip() + "\n\n" + section


def apply_to_prompt(prompt: str, section: str) -> str:
    """Inject trusted auto testplan into assembled prompt."""
    if "{{SUGGESTED_TESTPLAN}}" in prompt:
        return prompt.replace("{{SUGGESTED_TESTPLAN}}", section.rstrip())
    marker = "## Changed files summary\n"
    idx = prompt.find(marker)
    block = (
        "\n## Suggested test plan (auto, F61)\n\n"
        + section
        + "\nUse this as a **starting checklist** under **### Suggested test plan** "
        "and **### Tests & risk**. You may refine scenarios with evidence from the "
        "diff/tools; do not drop P0 items without saying why they are already covered.\n"
    )
    if idx >= 0:
        rest = prompt[idx + len(marker) :]
        m = re.search(r"\n## ", rest)
        if m:
            at = idx + len(marker) + m.start()
            return prompt[:at] + block + prompt[at:]
    # before Required Markdown template
    req = prompt.find("## Required Markdown template")
    if req >= 0:
        return prompt[:req] + block + "\n" + prompt[req:]
    return prompt.rstrip() + "\n" + block


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_pr(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _load_diff(path: Path | None) -> str | None:
    if not path or not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _plan_from_args(args: argparse.Namespace) -> TestPlan:
    pr = _load_pr(args.pr_json) if getattr(args, "pr_json", None) else None
    diff = _load_diff(getattr(args, "diff", None))
    title = ""
    body = ""
    if isinstance(pr, dict):
        title = str(pr.get("title") or "")
        body = str(pr.get("body") or "")
    if getattr(args, "title", None):
        title = args.title
    files = None
    if getattr(args, "files", None) and args.files.is_file():
        # reuse simple parse: lines with `path`
        text = args.files.read_text(encoding="utf-8", errors="replace")
        paths = re.findall(r"`([^`]+)`", text)
        files = [{"path": p} for p in paths]
    return build_plan(
        files=files,
        pr_json=pr,
        diff=diff,
        title=title,
        body=body,
        limit=getattr(args, "max_cases", None) or max_cases(),
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F61 deterministic suggested test plan")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--pr-json", type=Path, help="assemble pr.json")
        sp.add_argument("--diff", type=Path, help="unified diff (pr.diff)")
        sp.add_argument("--files", type=Path, help="files.txt from assemble")
        sp.add_argument("--title", default=None, help="override PR title")
        sp.add_argument("--max-cases", type=int, default=None)

    for name, help_ in (
        ("generate", "print full markdown artifact"),
        ("section", "print ### Suggested test plan section"),
        ("plan", "print JSON plan"),
    ):
        sp = sub.add_parser(name, help=help_)
        add_common(sp)
        sp.add_argument("--out", type=Path, default=None)
        sp.add_argument("--force", action="store_true", help="ignore TORII_TESTPLAN=0")

    pa = sub.add_parser("apply", help="inject section into review.md")
    add_common(pa)
    pa.add_argument("--review", type=Path, required=True)
    pa.add_argument("--force", action="store_true")
    pa.add_argument(
        "--force-replace",
        action="store_true",
        help="replace even non-empty model plan",
    )

    args = p.parse_args(argv)
    if args.cmd != "apply" and not args.force and not enabled():
        sys.stderr.write("testplan disabled (TORII_TESTPLAN=0)\n")
        return 0
    if args.cmd == "apply" and not args.force and not enabled():
        return 0

    plan = _plan_from_args(args)

    if args.cmd == "plan":
        text = json.dumps(plan.to_dict(), indent=2) + "\n"
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    if args.cmd == "generate":
        text = render_markdown(plan)
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    if args.cmd == "section":
        text = render_section(plan)
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    if args.cmd == "apply":
        section = render_section(plan)
        raw = args.review.read_text(encoding="utf-8", errors="replace")
        out = apply_to_review(
            raw, section, force=bool(getattr(args, "force_replace", False))
        )
        args.review.write_text(out, encoding="utf-8")
        sys.stdout.write(f"wrote {args.review} ({plan.summary})\n")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

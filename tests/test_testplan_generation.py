#!/usr/bin/env python3
"""F61: deterministic suggested test plan."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "testplan_generation.py"
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("testplan_generation", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["testplan_generation"] = _mod
_spec.loader.exec_module(_mod)


MILVUS_PR = {
    "title": "torii-eval: #51991 skip insert body parsing without functions",
    "body": "enhance: skip insert body parsing without functions",
    "files": [
        {
            "path": "internal/flushcommon/writebuffer/write_buffer_test.go",
            "additions": 13,
            "deletions": 1,
        },
        {
            "path": "internal/streamingnode/server/wal/interceptors/shard/function_materializer.go",
            "additions": 2,
            "deletions": 9,
        },
        {
            "path": "internal/util/function/manager.go",
            "additions": 26,
            "deletions": 7,
        },
        {
            "path": "internal/util/function/manager_test.go",
            "additions": 46,
            "deletions": 17,
        },
    ],
}

SAMPLE_DIFF = """diff --git a/internal/util/function/manager.go b/internal/util/function/manager.go
--- a/internal/util/function/manager.go
+++ b/internal/util/function/manager.go
@@ -10,6 +10,12 @@ package function
+func (m *Manager) SkipParseIfNoFunctions(schema *Schema) bool {
+	if schema == nil || len(schema.Functions) == 0 {
+		return true
+	}
+	return false
+}
+
 func (m *Manager) Process(row Row) error {
"""


class ClassifyPaths(unittest.TestCase):
    def test_go_tests(self):
        self.assertTrue(_mod.is_test_path("internal/util/function/manager_test.go"))
        self.assertFalse(_mod.is_test_path("internal/util/function/manager.go"))

    def test_py_tests(self):
        self.assertTrue(_mod.is_test_path("tests/test_foo.py"))
        self.assertTrue(_mod.is_test_path("pkg/test_bar.py"))
        self.assertFalse(_mod.is_test_path("pkg/bar.py"))


class Symbols(unittest.TestCase):
    def test_extract_go_func(self):
        by = _mod.extract_symbols_from_diff(SAMPLE_DIFF)
        self.assertIn("internal/util/function/manager.go", by)
        self.assertIn("SkipParseIfNoFunctions", by["internal/util/function/manager.go"])


class BuildPlan(unittest.TestCase):
    def test_milvus_skip_claim(self):
        plan = _mod.build_plan(pr_json=MILVUS_PR, diff=SAMPLE_DIFF)
        self.assertGreaterEqual(len(plan.cases), 2)
        self.assertTrue(any(c.priority == "P0" for c in plan.cases))
        blob = " ".join(c.scenario for c in plan.cases).lower()
        self.assertTrue(
            "skip" in blob or "skipparse" in blob.lower() or "symbol" in " ".join(c.source for c in plan.cases)
        )
        # symbol case present
        self.assertTrue(
            any("SkipParseIfNoFunctions" in c.target for c in plan.cases),
            plan.cases,
        )

    def test_prod_without_tests_p0(self):
        pr = {
            "title": "add feature",
            "files": [{"path": "pkg/core/engine.go", "additions": 40}],
        }
        plan = _mod.build_plan(pr_json=pr)
        self.assertTrue(plan.has_prod_without_tests)
        self.assertTrue(any(c.priority == "P0" and c.source == "gap" for c in plan.cases))

    def test_security_heuristic(self):
        pr = {
            "title": "Azure credential broker",
            "files": [
                {"path": "pkg/auth/credential_broker.go", "additions": 80},
                {"path": "pkg/auth/credential_broker_test.go", "additions": 40},
            ],
        }
        plan = _mod.build_plan(pr_json=pr)
        kinds = {c.kind for c in plan.cases}
        self.assertIn("security", kinds)

    def test_max_cases(self):
        pr = {
            "title": "fix race nil panic raise limit skip parse",
            "files": [
                {"path": f"internal/hot/writebuffer/mod{i}.go", "additions": 10}
                for i in range(8)
            ],
        }
        plan = _mod.build_plan(pr_json=pr, limit=5)
        self.assertLessEqual(len(plan.cases), 5)


class RenderApply(unittest.TestCase):
    def test_section_marker(self):
        plan = _mod.build_plan(pr_json=MILVUS_PR, diff=SAMPLE_DIFF)
        sec = _mod.render_section(plan)
        self.assertIn("### Suggested test plan", sec)
        self.assertIn("<!-- torii-testplan -->", sec)
        self.assertIn("| Pri |", sec)

    def test_apply_inserts_before_tests_risk(self):
        review = """## Torii

### Summary
hello

### Blocking
- None

### Tests & risk
- none

---
*Torii · Hermes*
"""
        plan = _mod.build_plan(pr_json=MILVUS_PR, diff=SAMPLE_DIFF)
        sec = _mod.render_section(plan)
        out = _mod.apply_to_review(review, sec)
        self.assertIn("<!-- torii-testplan -->", out)
        self.assertLess(
            out.find("### Suggested test plan"), out.find("### Tests & risk")
        )

    def test_apply_skips_filled_plan(self):
        review = """## Torii

### Suggested test plan
<!-- torii-testplan -->

| Pri | Kind | Target | Scenario |
|-----|------|--------|----------|
| P0 | unit | `a.go` | custom model plan |

### Tests & risk
- yes
"""
        plan = _mod.build_plan(pr_json=MILVUS_PR)
        sec = _mod.render_section(plan)
        out = _mod.apply_to_review(review, sec)
        self.assertIn("custom model plan", out)

    def test_apply_to_prompt(self):
        prompt = "## Changed files summary\n\n- a\n\n## Required Markdown template\n"
        plan = _mod.build_plan(pr_json=MILVUS_PR, diff=SAMPLE_DIFF)
        sec = _mod.render_section(plan)
        out = _mod.apply_to_prompt(prompt, sec)
        self.assertIn("Suggested test plan (auto, F61)", out)
        self.assertIn("<!-- torii-testplan -->", out)


class CLI(unittest.TestCase):
    def _run(self, *args, env=None):
        e = os.environ.copy()
        if env:
            e.update(env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=e,
        )

    def test_section_cli(self):
        with tempfile.TemporaryDirectory() as td:
            prp = Path(td) / "pr.json"
            prp.write_text(json.dumps(MILVUS_PR), encoding="utf-8")
            cp = self._run("section", "--pr-json", str(prp), "--force")
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertIn("### Suggested test plan", cp.stdout)

    def test_plan_json_cli(self):
        with tempfile.TemporaryDirectory() as td:
            prp = Path(td) / "pr.json"
            prp.write_text(json.dumps(MILVUS_PR), encoding="utf-8")
            cp = self._run("plan", "--pr-json", str(prp), "--force")
            self.assertEqual(cp.returncode, 0, cp.stderr)
            data = json.loads(cp.stdout)
            self.assertIn("cases", data)
            self.assertGreaterEqual(data["n_cases"], 1)

    def test_apply_cli(self):
        with tempfile.TemporaryDirectory() as td:
            prp = Path(td) / "pr.json"
            prp.write_text(json.dumps(MILVUS_PR), encoding="utf-8")
            rev = Path(td) / "review.md"
            rev.write_text(
                "## R\n\n### Tests & risk\n- x\n\n---\n*Torii*\n", encoding="utf-8"
            )
            cp = self._run(
                "apply",
                "--review",
                str(rev),
                "--pr-json",
                str(prp),
                "--force",
            )
            self.assertEqual(cp.returncode, 0, cp.stderr)
            body = rev.read_text(encoding="utf-8")
            self.assertIn("torii-testplan", body)


if __name__ == "__main__":
    unittest.main()

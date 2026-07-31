#!/usr/bin/env python3
"""F57: mermaid architecture from changed files."""

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
SCRIPT = ROOT / "scripts" / "mermaid_architecture.py"
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("mermaid_architecture", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["mermaid_architecture"] = _mod
_spec.loader.exec_module(_mod)


class GroupAndRender(unittest.TestCase):
    def test_odoo_groups(self):
        paths = [
            "addons/account/tools/dict_to_xml.py",
            "odoo/tools/xml_utils.py",
            "odoo/addons/test_testing_utilities/tests/test_xml_tools.py",
        ]
        g = _mod.build_groups(paths)
        self.assertIn("addons/account", g)
        self.assertIn("odoo/tools", g)
        mm = _mod.render_mermaid(paths)
        self.assertIn("flowchart LR", mm)
        self.assertIn("dict_to_xml.py", mm)
        self.assertIn("subgraph", mm)

    def test_parse_files_txt(self):
        txt = "Total: +1 / -0 across 1 files\n\n- `src/foo.py` (+1/-0)\n"
        self.assertEqual(_mod.parse_files_txt(txt), ["src/foo.py"])

    def test_parse_pr_json(self):
        data = {"files": [{"path": "a/b.py", "additions": 1}, {"filename": "c.py"}]}
        self.assertEqual(_mod.parse_pr_json(data), ["a/b.py", "c.py"])

    def test_section_marker(self):
        sec = _mod.render_section(["pkg/mod.py"])
        self.assertIn("### Architecture diagram", sec)
        self.assertIn("<!-- torii-mermaid -->", sec)
        self.assertIn("```mermaid", sec)

    def test_empty_paths(self):
        mm = _mod.render_mermaid([])
        self.assertIn("No changed files", mm)

    def test_apply_to_review_inserts_after_walkthrough(self):
        review = """## Torii

### Summary
hello

### Walkthrough
- change

### Blocking
- None
"""
        sec = _mod.render_section(["x/y.py"])
        out = _mod.apply_to_review(review, sec)
        self.assertIn("<!-- torii-mermaid -->", out)
        self.assertLess(out.find("### Walkthrough"), out.find("### Architecture diagram"))
        self.assertLess(out.find("### Architecture diagram"), out.find("### Blocking"))

    def test_apply_to_prompt_placeholder(self):
        prompt = "before\n{{ARCHITECTURE_DIAGRAM}}\nafter\n"
        sec = _mod.render_section(["a.py"])
        out = _mod.apply_to_prompt(prompt, sec)
        self.assertNotIn("{{ARCHITECTURE_DIAGRAM}}", out)
        self.assertIn("```mermaid", out)

    def test_max_nodes_truncation(self):
        paths = [f"pkg/file_{i}.py" for i in range(50)]
        mm = _mod.render_mermaid(paths, max_n=5, max_per_group=2)
        self.assertIn("truncated", mm)


class CLI(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )

    def test_render_cli(self):
        cp = self._run("render", "--paths", "foo/bar.py", "foo/baz.py")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("flowchart LR", cp.stdout)

    def test_apply_review_cli(self):
        with tempfile.TemporaryDirectory() as td:
            rev = Path(td) / "review.md"
            rev.write_text("### Summary\nok\n\n### Walkthrough\n- x\n\n### Blocking\n- None\n")
            pr = Path(td) / "pr.json"
            pr.write_text(json.dumps({"files": [{"path": "lib/a.py"}]}))
            cp = self._run(
                "apply",
                "--review",
                str(rev),
                "--pr-json",
                str(pr),
                "--force",
            )
            self.assertEqual(cp.returncode, 0, cp.stderr)
            body = rev.read_text()
            self.assertIn("torii-mermaid", body)


class Enabled(unittest.TestCase):
    def test_off(self):
        os.environ["TORII_MERMAID"] = "0"
        try:
            # may use feature_toggles which reads env
            self.assertFalse(_mod.enabled("0"))
        finally:
            os.environ.pop("TORII_MERMAID", None)


if __name__ == "__main__":
    unittest.main()

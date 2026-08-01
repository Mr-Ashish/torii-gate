"""Tests for F75 scoped memory recall (Mem0 multi-scope over TP/FP)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "scoped_memory_recall.py"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {**os.environ, "TORII_SCOPED_MEMORY": "1"}
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


class ScopedMemoryRecallTests(unittest.TestCase):
    def test_fixture_offline_e2e(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["path_matched"])
        self.assertTrue(data["privacy_ok"])
        self.assertTrue(data["inject_ok"])
        self.assertTrue(data["has_conflict"])
        self.assertLessEqual(data["metrics"]["tp_returned"], 4)

    def test_path_ranks_relevant_tp_higher(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            torii = td_path / ".torii"
            torii.mkdir()
            (torii / "tp-signatures.json").write_text(
                json.dumps(
                    {
                        "signatures": [
                            {
                                "id": "sqli",
                                "theme": "sql_injection",
                                "keywords": ["sql"],
                                "path_globs": ["demo/insecure/app.py"],
                                "hits": 2,
                            },
                            {
                                "id": "xss",
                                "theme": "xss",
                                "keywords": ["xss"],
                                "path_globs": ["other/widget.js"],
                                "hits": 20,
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (torii / "fp-rules.json").write_text(
                json.dumps({"rules": []}) + "\n", encoding="utf-8"
            )
            store = torii / "scoped-memory.json"
            env = {
                "TORII_ROOT": str(td_path),
                "TORII_TP_SIGNATURES_FILE": str(torii / "tp-signatures.json"),
                "TORII_FP_RULES_FILE": str(torii / "fp-rules.json"),
                "TORII_SCOPED_MEMORY_FILE": str(store),
                "TORII_FEDERATED_SIGNALS_FILE": str(torii / "missing-fed.json"),
            }
            r = _run(
                [
                    "recall",
                    "--files",
                    "demo/insecure/app.py",
                    "--refresh",
                    "--tp-max",
                    "2",
                ],
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertGreaterEqual(len(data["tp"]), 1)
            top = data["tp"][0]
            self.assertIn("sqli", str(top.get("raw_id") or top.get("id")))
            self.assertGreater(top.get("path_match") or 0, 0)

    def test_fp_path_suppresses_theme_tp(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            torii = td_path / ".torii"
            torii.mkdir()
            (torii / "tp-signatures.json").write_text(
                json.dumps(
                    {
                        "signatures": [
                            {
                                "id": "sqli",
                                "theme": "sql_injection",
                                "keywords": ["sql"],
                                "path_globs": [],  # theme-only
                                "hits": 3,
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (torii / "fp-rules.json").write_text(
                json.dumps(
                    {
                        "rules": [
                            {
                                "kind": "false_positive",
                                "path": "demo/insecure/app.py",
                                "reason": "sql is parameterized false positive",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            store = torii / "scoped-memory.json"
            env = {
                "TORII_ROOT": str(td_path),
                "TORII_TP_SIGNATURES_FILE": str(torii / "tp-signatures.json"),
                "TORII_FP_RULES_FILE": str(torii / "fp-rules.json"),
                "TORII_SCOPED_MEMORY_FILE": str(store),
                "TORII_FEDERATED_SIGNALS_FILE": str(torii / "nofed.json"),
            }
            r = _run(
                ["recall", "--files", "demo/insecure/app.py", "--refresh"],
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertGreaterEqual(len(data.get("conflicts") or []), 1)
            # theme-only TP may be suppressed
            self.assertTrue(
                data["metrics"]["suppress_count"] >= 1
                or any(c.get("resolution") == "prefer_fp" for c in data["conflicts"])
            )

    def test_inject_marker_and_replace_f70(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            torii = td_path / ".torii"
            torii.mkdir()
            (torii / "tp-signatures.json").write_text(
                json.dumps(
                    {
                        "signatures": [
                            {
                                "id": "a",
                                "theme": "sql_injection",
                                "keywords": ["sql"],
                                "path_globs": ["a.py"],
                                "hits": 1,
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (torii / "fp-rules.json").write_text('{"rules":[]}\n', encoding="utf-8")
            prompt = td_path / "prompt.md"
            prompt.write_text(
                "# p\n\n<!-- torii-f70-tp-signatures -->\n## bulk\n- x\n\n",
                encoding="utf-8",
            )
            env = {
                "TORII_ROOT": str(td_path),
                "TORII_TP_SIGNATURES_FILE": str(torii / "tp-signatures.json"),
                "TORII_FP_RULES_FILE": str(torii / "fp-rules.json"),
                "TORII_SCOPED_MEMORY_FILE": str(torii / "scoped-memory.json"),
                "TORII_FEDERATED_SIGNALS_FILE": str(torii / "nofed.json"),
                "TORII_SCOPED_REPLACE_TP": "1",
            }
            r = _run(
                [
                    "inject",
                    "--prompt",
                    str(prompt),
                    "--files",
                    "a.py",
                    "--refresh",
                ],
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            body = prompt.read_text(encoding="utf-8")
            self.assertIn("<!-- torii-f75-scoped-memory -->", body)
            self.assertIn("superseded by F75", body)

    def test_status_enabled(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F75")
        self.assertTrue(data["enabled"])


if __name__ == "__main__":
    unittest.main()

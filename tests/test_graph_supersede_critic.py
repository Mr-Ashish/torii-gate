"""F101: dual-pass demotes graph-superseded TP themes."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class GraphSupersedeCriticTests(unittest.TestCase):
    def test_superseded_theme_demoted(self):
        import memory_temporal_graph as mtg  # type: ignore
        from bench_security_gate import dual_pass_critic  # type: ignore

        tp = [
            {
                "id": "sqli-v1",
                "theme": "sql_injection",
                "kind": "tp",
                "keywords": ["sql injection", "sqli"],
                "path_globs": ["app.py"],
                "hits": 2,
                "created_at": "2026-07-01T00:00:00Z",
                "deleted": True,
                "deleted_at": "2026-07-15T00:00:00Z",
                "superseded_by": "fp-sqli",
                "effective_score": 0.9,
            },
            {
                "id": "cmdi-hot",
                "theme": "command_injection",
                "kind": "tp",
                "keywords": ["command injection", "shell=true"],
                "path_globs": ["run.py"],
                "hits": 3,
                "effective_score": 0.8,
                "created_at": "2026-07-20T00:00:00Z",
            },
        ]
        fp = [
            {
                "id": "fp-sqli",
                "theme": "sql_injection",
                "kind": "fp",
                "path": "app.py",
                "created_at": "2026-07-15T00:00:00Z",
            }
        ]
        g = mtg.build_graph(tp, fp)
        idx = mtg.superseded_index(g)
        self.assertGreaterEqual(idx["count"], 1)

        # Active store may drop deleted TP; graph still demotes sqli theme-only text
        active_tp = [t for t in tp if not t.get("deleted")]
        review_sqli = """
## Finding: SQL injection
**Path:** `app.py`
User input causes sql injection via f-string sqli.
"""
        r = dual_pass_critic(review_sqli, tp_signatures=active_tp, memory_graph=g)
        self.assertTrue(r.get("graph_supersede_aware"))
        self.assertGreaterEqual(int(r.get("superseded_tp") or 0), 1, r)
        self.assertTrue(
            any(f.get("status") == "superseded_tp" for f in r.get("findings") or []),
            r,
        )

        review_cmdi = """
## Finding: command injection
**Path:** `run.py`
Uses shell=true command injection with user args.
"""
        r2 = dual_pass_critic(review_cmdi, tp_signatures=active_tp, memory_graph=g)
        self.assertGreaterEqual(int(r2.get("confirmed_tp") or 0), 1, r2)
        self.assertEqual(int(r2.get("superseded_tp") or 0), 0)

    def test_toggle_off(self):
        import memory_temporal_graph as mtg  # type: ignore
        from bench_security_gate import dual_pass_critic  # type: ignore

        tp = [
            {
                "id": "sqli-v1",
                "theme": "sql_injection",
                "keywords": ["sql injection"],
                "path_globs": ["app.py"],
                "deleted": True,
                "superseded_by": "fp-x",
                "effective_score": 0.9,
            }
        ]
        fp = [{"id": "fp-x", "theme": "sql_injection", "path": "app.py", "kind": "fp"}]
        g = mtg.build_graph(tp, fp)
        review = "## Finding\n**Path:** `app.py`\nsql injection here\n"
        old = os.environ.get("TORII_GRAPH_SUPERSEDE")
        try:
            os.environ["TORII_GRAPH_SUPERSEDE"] = "0"
            r = dual_pass_critic(
                review,
                tp_signatures=[
                    {
                        "id": "sqli-live",
                        "theme": "sql_injection",
                        "keywords": ["sql injection"],
                        "effective_score": 0.9,
                    }
                ],
                memory_graph=g,
            )
            self.assertEqual(int(r.get("superseded_tp") or 0), 0)
        finally:
            if old is None:
                os.environ.pop("TORII_GRAPH_SUPERSEDE", None)
            else:
                os.environ["TORII_GRAPH_SUPERSEDE"] = old


if __name__ == "__main__":
    unittest.main()

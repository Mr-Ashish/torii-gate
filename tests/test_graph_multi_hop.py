"""F102: multi-hop co_path expansion for supersede index + query."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SCRIPT = ROOT / "scripts" / "memory_temporal_graph.py"


class GraphMultiHopTests(unittest.TestCase):
    def test_fixture_multi_hop(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "fixture"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "TORII_MEMORY_GRAPH": "1", "TORII_GRAPH_MULTI_HOP": "1"},
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data.get("multi_hop_ok"), data)

    def test_neighborhood_expands(self):
        import memory_temporal_graph as mtg  # type: ignore

        tp = [
            {
                "id": "sqli-app",
                "theme": "sql_injection",
                "kind": "tp",
                "path_globs": ["app.py"],
                "deleted": True,
                "superseded_by": "fp1",
                "created_at": "2026-07-01T00:00:00Z",
                "deleted_at": "2026-07-10T00:00:00Z",
            },
            {
                "id": "sqli-db",
                "theme": "sql_injection",
                "kind": "tp",
                "path_globs": ["app.py", "db.py"],
                "hits": 1,
                "created_at": "2026-07-11T00:00:00Z",
            },
        ]
        fp = [{"id": "fp1", "theme": "sql_injection", "kind": "fp", "path": "app.py"}]
        g = mtg.build_graph(tp, fp)
        seeds = mtg.path_seed_nodes(g, ["app.py"])
        self.assertGreaterEqual(len(seeds), 1)
        neigh = mtg.expand_neighborhood(g, seeds, hops=2)
        self.assertGreaterEqual(len(neigh), len(seeds))
        idx = mtg.superseded_index(g, paths=["db.py"], multi_hop=True, hops=2)
        # db.py seeds sqli-db; hop reaches app.py cluster + supersede theme
        self.assertTrue(idx["hop"]["multi_hop"])
        self.assertIn("sql_injection", idx["themes"])

    def test_dual_pass_path_hop(self):
        import memory_temporal_graph as mtg  # type: ignore
        from bench_security_gate import dual_pass_critic  # type: ignore

        tp = [
            {
                "id": "sqli-old",
                "theme": "sql_injection",
                "kind": "tp",
                "keywords": ["sql injection"],
                "path_globs": ["legacy.py"],
                "deleted": True,
                "superseded_by": "fp-leg",
                "effective_score": 0.9,
            },
        ]
        fp = [{"id": "fp-leg", "theme": "sql_injection", "kind": "fp", "path": "legacy.py"}]
        g = mtg.build_graph(tp, fp)
        # Finding on legacy.py — multi-hop index still demotes theme
        review = "## Finding\n**Path:** `legacy.py`\nsql injection in helper\n"
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
        self.assertGreaterEqual(int(r.get("superseded_tp") or 0), 1, r)


if __name__ == "__main__":
    unittest.main()

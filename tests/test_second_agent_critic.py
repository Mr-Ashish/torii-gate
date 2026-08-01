"""Tests for F78 multi-checker second-agent critic."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "second_agent_critic.py"
GOOD = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-good-review.md"
WEAK = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-weak-review.md"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {
        **os.environ,
        "TORII_SECOND_CRITIC": "1",
        "TORII_SECOND_CRITIC_DEMOTE": "0",  # never rewrite fixtures
        "TORII_LLM_CRITIC": "0",  # F81 off in unit tests unless mock
        "TORII_LLM_CRITIC_MOCK": "1",
    }
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


class SecondAgentCriticTests(unittest.TestCase):
    def test_fixture_offline(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertGreater(data["delta"], 0.1)
        self.assertTrue(data["inject_ok"])

    def test_good_higher_than_weak(self):
        rg = _run(["run", "--review", str(GOOD), "--force"])
        rw = _run(["run", "--review", str(WEAK), "--force"])
        self.assertEqual(rg.returncode, 0, rg.stderr + rg.stdout)
        self.assertEqual(rw.returncode, 0, rw.stderr + rw.stdout)
        g = json.loads(rg.stdout)
        w = json.loads(rw.stdout)
        self.assertGreater(
            float(g["panel"]["composite"]),
            float(w["panel"]["composite"]),
        )
        # weak APPROVE should recommend demote
        self.assertEqual(w["maker_verdict"], "APPROVE")
        self.assertTrue(w["decision"]["demoted"] or w["decision"]["recommended_verdict"] != "APPROVE")

    def test_inject_marker(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = Path(td) / "prompt.md"
            prompt.write_text("# p\n", encoding="utf-8")
            r = _run(["inject", "--prompt", str(prompt)])
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            body = prompt.read_text(encoding="utf-8")
            self.assertIn("<!-- torii-f78-second-agent-critic -->", body)
            self.assertIn("maker", body.lower())

    def test_demote_rewrites_copy_not_source(self):
        with tempfile.TemporaryDirectory() as td:
            review = Path(td) / "review.md"
            review.write_text(WEAK.read_text(encoding="utf-8"), encoding="utf-8")
            r = _run(
                ["run", "--review", str(review), "--demote", "--force"],
                env={"TORII_SECOND_CRITIC_DEMOTE": "1"},
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            if data["decision"]["demoted"]:
                body = review.read_text(encoding="utf-8")
                self.assertIn("torii-f78-demote", body)
                self.assertNotIn("**Verdict:** APPROVE", body)
            # source fixture unchanged
            self.assertIn("APPROVE", WEAK.read_text(encoding="utf-8"))

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F78")
        self.assertTrue(data["enabled"])
        self.assertEqual(data.get("feature_hub_gap"), "F127")
        self.assertEqual(data.get("feature_scorecard_hub_gap"), "F139")
        # F141 may be present when status updated
        if data.get("feature_memory_util"):
            self.assertEqual(data.get("feature_memory_util"), "F141")

    def test_f128_demote_eval(self):
        """F128: paper demote-rate pack demotes weak + hub-gap APPROVE."""
        with tempfile.TemporaryDirectory() as td:
            r = _run(["demote-eval", "--out-dir", td])
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertEqual(data.get("feature"), "F128")
            self.assertTrue(data.get("eval_pass"), data)
            self.assertTrue(data.get("weak_demote_ok"), data)
            self.assertGreaterEqual(float(data.get("demote_rate") or 0), 0.5)
            self.assertTrue(
                data.get("scorecard_hub_gap_demote_ok")
                or data.get("scorecard_hub_gap_soft_ok"),
                data,
            )
            paper = data.get("paper") or {}
            self.assertEqual(paper.get("metric"), "critic_approve_demote_rate")
            art = Path(td) / "critic-demote-eval.json"
            self.assertTrue(art.is_file())

    def test_f127_hub_gap_demotes_approve(self):
        """F127: high hub gap + idle recovery demotes maker APPROVE."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # hub signals with high gap pressure
            fed = root / "memory" / "federation"
            fed.mkdir(parents=True)
            (fed / "recovery-util-signals.json").write_text(
                json.dumps(
                    {
                        "signals": [
                            {
                                "id": "recovery-util-gap",
                                "theme": "recovery-util-gap",
                                "tags": ["recovery_util", "utilization_gap"],
                                "hits": 8,
                                "tenants": 3,
                                "util_rate_bin": "gap",
                                "source": "recovery_skill_util",
                            },
                            {
                                "id": "recovery-util-ok",
                                "theme": "recovery-util-ok",
                                "tags": ["recovery_util"],
                                "hits": 1,
                                "util_rate_bin": "full",
                                "source": "recovery_skill_util",
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            od = root / "out"
            od.mkdir()
            (od / "skill-router.json").write_text(
                json.dumps(
                    {
                        "selected": ["skill-prefer-memory-cli-early"],
                        "always_selected": ["skill-prefer-memory-cli-early"],
                        "inject_chars": 600,
                    }
                ),
                encoding="utf-8",
            )
            (od / "skill-hits.json").write_text(
                json.dumps(
                    {
                        "hits": [
                            {
                                "id": "skill-prefer-memory-cli-early",
                                "tool_hit": False,
                                "hit": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            review = root / "approve.md"
            review.write_text(
                "## Review\n**Verdict:** APPROVE\n\n### Summary\nok\n\n"
                "### Blocking\nnone\n\n### What I checked\n`app.py:1` ok\n",
                encoding="utf-8",
            )
            env = {
                "TORII_ROOT": str(root),
                "TORII_HUB_GAP_CRITIC": "1",
                "TORII_HUB_GAP_PRESSURE_THR": "0.2",
                "TORII_RECOVERY_HUB_COMPOUND": "1",
                "TORII_SECOND_CRITIC_MIN_PATH": "0.1",
            }
            r = _run(
                ["run", "--review", str(review), "--out-dir", str(od), "--force"],
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            ids = [c["id"] for c in data.get("checkers") or []]
            self.assertIn("f127_hub_gap", ids)
            hubc = next(c for c in data["checkers"] if c["id"] == "f127_hub_gap")
            self.assertFalse(hubc["ok"], hubc)
            self.assertTrue(
                data["decision"]["demoted"]
                or data["decision"]["recommended_verdict"] != "APPROVE",
                data["decision"],
            )
            reasons = " ".join(data["decision"].get("reasons") or [])
            self.assertIn("hub_gap", reasons)

    def test_f139_scorecard_hub_gap_demotes_approve(self):
        """F139: high scorecard hub gap + idle scorecard ops demotes APPROVE."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fed = root / "memory" / "federation"
            fed.mkdir(parents=True)
            sc_sid = "skill-prefer-product-scorecard"
            (fed / "scorecard-util-signals.json").write_text(
                json.dumps(
                    {
                        "signals": [
                            {
                                "id": "scorecard-util-gap",
                                "theme": "scorecard-util-gap",
                                "tags": [
                                    "scorecard_util",
                                    "utilization_gap",
                                    "f136",
                                ],
                                "hits": 8,
                                "tenants": 3,
                                "util_rate_bin": "gap",
                                "source": "scorecard_skill_util",
                            },
                            {
                                "id": "scorecard-util-ok",
                                "theme": "scorecard-util-ok",
                                "tags": ["scorecard_util", "util_ok"],
                                "hits": 1,
                                "util_rate_bin": "full",
                                "source": "scorecard_skill_util",
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            od = root / "out"
            od.mkdir()
            (od / "skill-router.json").write_text(
                json.dumps(
                    {
                        "selected": [sc_sid],
                        "always_selected": [],
                        "inject_chars": 600,
                    }
                ),
                encoding="utf-8",
            )
            (od / "skill-hits.json").write_text(
                json.dumps(
                    {
                        "hits": [
                            {
                                "id": sc_sid,
                                "tool_hit": False,
                                "hit": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            review = root / "approve.md"
            review.write_text(
                "## Review\n**Verdict:** APPROVE\n\n### Summary\nok\n\n"
                "### Blocking\nnone\n\n### What I checked\n`app.py:1` ok\n",
                encoding="utf-8",
            )
            env = {
                "TORII_ROOT": str(root),
                "TORII_SCORECARD_HUB_GAP_CRITIC": "1",
                "TORII_SCORECARD_HUB_GAP_THR": "0.2",
                "TORII_SCORECARD_HUB_COMPOUND": "1",
                "TORII_SECOND_CRITIC_MIN_PATH": "0.1",
            }
            r = _run(
                ["run", "--review", str(review), "--out-dir", str(od), "--force"],
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            ids = [c["id"] for c in data.get("checkers") or []]
            self.assertIn("f139_scorecard_hub_gap", ids)
            sch = next(
                c for c in data["checkers"] if c["id"] == "f139_scorecard_hub_gap"
            )
            self.assertFalse(sch["ok"], sch)
            self.assertTrue(
                data["decision"]["demoted"]
                or data["decision"]["recommended_verdict"] != "APPROVE",
                data["decision"],
            )
            reasons = " ".join(data["decision"].get("reasons") or [])
            self.assertIn("scorecard_hub_gap", reasons)

    def test_f141_memory_util_demotes_approve(self):
        """F141: memory inject unused demotes maker APPROVE."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            od = root / "out"
            od.mkdir()
            (od / "memory-tool-audit.json").write_text(
                json.dumps(
                    {
                        "score": 0.15,
                        "hit_count": 0,
                        "inject_offered": True,
                        "utilization_gap": True,
                        "tool_call_turns": 4,
                        "tools_used": [],
                    }
                ),
                encoding="utf-8",
            )
            review = root / "approve.md"
            review.write_text(
                "## Review\n**Verdict:** APPROVE\n\n### Summary\nok\n\n"
                "### Blocking\nnone\n\n### What I checked\n`app.py:1` ok\n",
                encoding="utf-8",
            )
            env = {
                "TORII_ROOT": str(root),
                "TORII_MEMORY_UTIL_CRITIC": "1",
                "TORII_SECOND_CRITIC_MIN_PATH": "0.1",
            }
            r = _run(
                ["run", "--review", str(review), "--out-dir", str(od), "--force"],
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            ids = [c["id"] for c in data.get("checkers") or []]
            self.assertIn("f141_memory_util", ids)
            memc = next(c for c in data["checkers"] if c["id"] == "f141_memory_util")
            self.assertFalse(memc["ok"], memc)
            self.assertTrue(
                data["decision"]["demoted"]
                or data["decision"]["recommended_verdict"] != "APPROVE",
                data["decision"],
            )
            reasons = " ".join(data["decision"].get("reasons") or [])
            self.assertIn("memory_tool", reasons)


if __name__ == "__main__":
    unittest.main()

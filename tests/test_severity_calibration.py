#!/usr/bin/env python3
"""F50/H20: severity_calibration gate tests."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "severity_calibration.py"
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("severity_calibration", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


F49_PR2_SAMPLE = """## 🏴‍☠️ Torii Review — PR #2

**Verdict:** APPROVE
**Confidence:** high
**Score:** 95/100
**Review effort:** 2/5

### Summary
Fixes getFieldsSpec crash and format:false alias for integer/float fields.

### Blocking
- None

### Key findings
None — no high-confidence defects in new code.

### Suggestions
- Consider adding comments in extractProps about why format aliasing was added.
- Slightly enhance test coverage by explicitly testing `format: false` in float field extractProps to confirm float widget correctness alongside integer.

### Tests & risk
- Relevant tests added/updated: yes
- Coverage: Fixes are covered for model spec retrieval and some widget extractProps paths; slight enhancement suggested for full float widget coverage.
- Risk: low
- Rollback: easy
"""

CLEAN_APPROVE = """## 🏴‍☠️ Torii Review — PR #3

**Verdict:** APPROVE
**Confidence:** high
**Score:** 92/100
**Review effort:** 2/5

### Summary
Unicode scrub is correct and fully tested.

### Blocking
- None

### Suggestions
- None

### Tests & risk
- Relevant tests added/updated: yes
- Coverage: str/bytes/lxml paths covered by new unit tests.
- Risk: low
- Rollback: easy
"""

TESTS_NO_APPROVE = """## 🏴‍☠️ Torii Review — PR #9

**Verdict:** APPROVE
**Confidence:** medium
**Score:** 88/100
**Review effort:** 3/5

### Blocking
- None

### Suggestions
- None

### Tests & risk
- Relevant tests added/updated: no
- Coverage: production path changed with no new tests.
- Risk: medium
- Rollback: easy
"""


class DetectTests(unittest.TestCase):
    def test_f49_pr2_gap(self):
        g = _mod.detect_test_gap(F49_PR2_SAMPLE)
        self.assertTrue(g["hit"])
        self.assertIn("missing_tests", g["match"])

    def test_clean_approve_no_gap(self):
        g = _mod.detect_test_gap(CLEAN_APPROVE)
        self.assertFalse(g["hit"])

    def test_tests_no_line(self):
        g = _mod.detect_test_gap(TESTS_NO_APPROVE)
        self.assertTrue(g["hit"])
        self.assertEqual(g["match"], "tests_no_line")


class DecideTests(unittest.TestCase):
    def test_upgrade_approve_with_gap(self):
        d = _mod.decide(F49_PR2_SAMPLE)
        self.assertEqual(d["gate"], 1)
        self.assertEqual(d["action"], "upgrade_request_changes")
        self.assertEqual(d["reason"], "approve_with_test_gap")

    def test_clean_no_gate(self):
        d = _mod.decide(CLEAN_APPROVE)
        self.assertEqual(d["gate"], 0)
        self.assertEqual(d["reason"], "no_test_gap_signal")

    def test_gate_off(self):
        d = _mod.decide(F49_PR2_SAMPLE, gate_on=False)
        self.assertEqual(d["gate"], 0)
        self.assertEqual(d["reason"], "gate_off")

    def test_already_request_changes_annotate(self):
        body = F49_PR2_SAMPLE.replace("APPROVE", "REQUEST CHANGES")
        d = _mod.decide(body)
        self.assertEqual(d["gate"], 1)
        self.assertEqual(d["action"], "annotate_only")


class ApplyTests(unittest.TestCase):
    def test_upgrade_and_cap(self):
        d = _mod.decide(F49_PR2_SAMPLE)
        new, mut = _mod.apply_to_review(F49_PR2_SAMPLE, decision=d)
        self.assertTrue(mut["mutated"])
        self.assertEqual(mut["verdict_before"], "APPROVE")
        self.assertEqual(mut["verdict_after"], "REQUEST_CHANGES")
        self.assertIn("**Verdict:** REQUEST CHANGES", new)
        self.assertIn("**Score:** 69/100", new)
        self.assertIn("Severity calibration (F50", new)
        self.assertTrue(mut["score_capped"])
        self.assertTrue(mut["banner_added"])

    def test_idempotent_banner(self):
        d = _mod.decide(F49_PR2_SAMPLE)
        once, _ = _mod.apply_to_review(F49_PR2_SAMPLE, decision=d)
        twice, mut2 = _mod.apply_to_review(once, decision=d)
        # Second apply: verdict already REQUEST_CHANGES → annotate_only or skip
        self.assertEqual(once.count("Severity calibration (F50"), 1)
        # re-decide on mutated body
        d2 = _mod.decide(once)
        thrice, _ = _mod.apply_to_review(once, decision=d2)
        self.assertEqual(thrice.count("Severity calibration (F50"), 1)
        self.assertIn("REQUEST CHANGES", thrice)

    def test_cli_apply(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            review = td_path / "review.md"
            env = td_path / "severity-calibration.env"
            review.write_text(F49_PR2_SAMPLE, encoding="utf-8")
            rc = _mod.main(
                [
                    "apply",
                    "--review",
                    str(review),
                    "--out",
                    str(review),
                    "--env-out",
                    str(env),
                ]
            )
            self.assertEqual(rc, 0)
            body = review.read_text(encoding="utf-8")
            self.assertIn("REQUEST CHANGES", body)
            env_txt = env.read_text(encoding="utf-8")
            self.assertIn("gate=1", env_txt)
            self.assertIn("mutated=1", env_txt)


if __name__ == "__main__":
    unittest.main()

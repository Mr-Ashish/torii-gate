#!/usr/bin/env python3
"""Phase 1: review-to-openui converter tests."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "review-to-openui.py"
SHOWCASE = ROOT / "docs" / "showcase" / "e2e-odoo-pr3-opus5-agentic-loop"

SAMPLE = """<!-- torii-review pr=1 -->
## Torii Review — PR #1

**Verdict:** REQUEST CHANGES
**Score:** 42/100
**Review effort:** 3/5

### Summary
Something is wrong with the bytes path.

### Blocking
- **file.py — bad codec.** Use surrogateescape instead.

### Key findings

| Severity | File | Issue | Trigger scenario |
|----------|------|-------|------------------|
| critical | `a.py` | broken decode | latin-1 payload |
| high | `b.py` | test fails | run suite |

### Security audit
`No` — clean.
"""


class ReviewToOpenUITests(unittest.TestCase):
    def test_cli_sample(self):
        with tempfile.TemporaryDirectory() as td:
            rev = Path(td) / "review.md"
            out = Path(td) / "out.openui"
            rev.write_text(SAMPLE)
            cp = subprocess.run(
                [sys.executable, str(SCRIPT), "--review", str(rev), "-o", str(out)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, cp.stderr)
            text = out.read_text()
            self.assertIn("root = Stack(", text)
            self.assertIn("REQUEST CHANGES", text)
            self.assertIn("findingsTable", text)
            self.assertIn("blockingCallout", text)
            self.assertTrue(text.startswith("root = "))

    def test_showcase_fixture(self):
        rev = SHOWCASE / "review.md"
        if not rev.is_file():
            self.skipTest("showcase review missing")
        usage = SHOWCASE / "hermes-usage.json"
        timings = SHOWCASE / "timings.json"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "showcase.openui"
            cmd = [
                sys.executable,
                str(SCRIPT),
                "--review",
                str(rev),
                "-o",
                str(out),
                "--title",
                "Torii Review — Odoo PR #3",
            ]
            if usage.is_file():
                cmd.extend(["--usage", str(usage)])
            if timings.is_file():
                cmd.extend(["--timings", str(timings)])
            cp = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            text = out.read_text()
            self.assertIn("root = Stack(", text)
            self.assertIn("Callout(", text)
            self.assertIn("costCard", text)  # usage present
            self.assertIn("stagesTable", text)

    def test_module_build(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        # import by path
        import importlib.util

        spec = importlib.util.spec_from_file_location("r2o", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)
        out = mod.build_openui(SAMPLE)
        self.assertIn('Callout("error"', out)


if __name__ == "__main__":
    unittest.main()

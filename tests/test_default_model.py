#!/usr/bin/env python3
"""F26: default TORII_MODEL is a single source of truth across script + ops docs."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run-hermes-review.sh"
DEFAULT = "anthropic/claude-opus-5"


def _script_default() -> str:
    text = SCRIPT.read_text()
    m = re.search(r'^DEFAULT_TORII_MODEL="([^"]+)"', text, re.M)
    if not m:
        raise AssertionError("DEFAULT_TORII_MODEL not found in run-hermes-review.sh")
    return m.group(1)


class DefaultModelAlignmentTests(unittest.TestCase):
    def test_script_default_is_opus(self):
        self.assertEqual(_script_default(), DEFAULT)

    def test_ops_docs_do_not_claim_mini_as_script_default(self):
        bad_snippets = (
            "default in scripts: `openai/gpt-5-mini`",
            "script default `openai/gpt-5-mini`",
            "default in scripts: openai/gpt-5-mini",
        )
        for rel in ("docs/OPERATIONS.md", "USAGE.md", "DEV.md"):
            text = (ROOT / rel).read_text()
            for snip in bad_snippets:
                self.assertNotIn(snip, text, msg=f"{rel} still claims mini default")

    def test_ops_docs_mention_true_default(self):
        ops = (ROOT / "docs" / "OPERATIONS.md").read_text()
        usage = (ROOT / "USAGE.md").read_text()
        self.assertIn(DEFAULT, ops)
        self.assertIn(DEFAULT, usage)

    def test_env_example_does_not_force_mini(self):
        env = (ROOT / ".env.example").read_text()
        # Must not actively set mini as the only example without noting default
        self.assertNotRegex(
            env,
            r"(?m)^TORII_MODEL=openai/gpt-5-mini\s*$",
            msg=".env.example must not force mini as active default assignment",
        )
        self.assertIn("claude-opus-5", env)

    def test_workflow_defers_empty_model_to_script(self):
        wf = (ROOT / ".github" / "workflows" / "torii-review-reusable.yml").read_text()
        # Old pattern re-hardcoded a second default
        self.assertNotIn(
            'export TORII_MODEL="${TORII_MODEL:-anthropic/claude-opus-5}"',
            wf,
        )
        self.assertIn("F26", wf)


if __name__ == "__main__":
    unittest.main()

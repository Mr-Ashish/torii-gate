"""Install UX: 5-min path, --minimal, doctor text defaults, one CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(ROOT)},
        timeout=kwargs.pop("timeout", 180),
        **kwargs,
    )


class InstallUxTests(unittest.TestCase):
    def test_install_md(self):
        p = ROOT / "docs" / "INSTALL.md"
        self.assertTrue(p.is_file())
        t = p.read_text(encoding="utf-8")
        self.assertIn("torii/gate", t)
        self.assertIn("torii.py", t)
        self.assertIn("--minimal", t)

    def test_fixture(self):
        r = _run([sys.executable, str(ROOT / "scripts" / "install_ux_check.py"), "fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)

    def test_doctor_json(self):
        r = _run([sys.executable, str(ROOT / "scripts" / "torii.py"), "doctor", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertIn("doctor_pass", data)
        self.assertEqual(data.get("install_doc"), "docs/INSTALL.md")

    def test_doctor_text_helper(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "torii_cli", ROOT / "scripts" / "torii.py"
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        text = mod.render_doctor_text(
            {
                "doctor_pass": True,
                "scored_at": "now",
                "results": [{"check": "memory", "ok": True}],
                "recovery_ok": True,
                "recovery_active": ["skill-prefer-product-cli"],
                "recovery_hub_gap_ok": True,
                "hub_archival_loop_ok": True,
                "refine_loop_ok": True,
            }
        )
        self.assertIn("PASS", text)
        self.assertIn("torii/gate", text)
        self.assertIn("doctor --json", text)

    def test_minimal_flag_in_script(self):
        sh = (ROOT / "scripts" / "install-torii.sh").read_text(encoding="utf-8")
        self.assertIn("--minimal", sh)
        self.assertIn("MINIMAL_EXCLUDE", sh)
        self.assertNotIn("torii_memory.py help &&", sh)


if __name__ == "__main__":
    unittest.main()

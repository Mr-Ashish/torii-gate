#!/usr/bin/env python3
"""F30: memory-health.sh record/summary + local publish status when skipped."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MH = ROOT / "scripts" / "memory-health.sh"
PUB_LOCAL = ROOT / "scripts" / "publish-run-local.sh"
PRELOAD = ROOT / "scripts" / "preload-hub-memory.sh"


class MemoryHealthTests(unittest.TestCase):
    def test_record_and_summary(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            env = os.environ.copy()
            env["OUT_DIR"] = str(out)
            subprocess.check_call(
                ["bash", str(MH), "record", "MEMORY_SOURCE=local"], env=env
            )
            subprocess.check_call(
                ["bash", str(MH), "record", "LOCAL_PUBLISH=failed"], env=env
            )
            health = (out / "memory-health.env").read_text()
            self.assertIn("MEMORY_SOURCE=local", health)
            self.assertIn("LOCAL_PUBLISH=failed", health)
            # overwrite key
            subprocess.check_call(
                ["bash", str(MH), "record", "LOCAL_PUBLISH=ok"], env=env
            )
            health = (out / "memory-health.env").read_text()
            self.assertIn("LOCAL_PUBLISH=ok", health)
            self.assertNotIn("LOCAL_PUBLISH=failed", health)
            cp = subprocess.run(
                ["bash", str(MH), "summary"],
                capture_output=True,
                text=True,
                env=env,
                check=True,
            )
            self.assertIn("Torii memory health (F30)", cp.stdout)
            self.assertIn("local", cp.stdout)
            self.assertIn("ok", cp.stdout)

    def test_warn_if_bad(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            env = os.environ.copy()
            env["OUT_DIR"] = str(out)
            subprocess.check_call(
                ["bash", str(MH), "record", "LOCAL_PUBLISH=failed"], env=env
            )
            cp = subprocess.run(
                ["bash", str(MH), "warn-if-bad"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(cp.returncode, 0)
            self.assertIn("::warning::", cp.stderr + cp.stdout)

    def test_local_publish_no_token_warns(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            env = {
                **os.environ,
                "OUT_DIR": str(out),
                "REPO": "acme/widgets",
                "TORII_MEMORY_MODE": "local",
                "TORII_LOCAL_PUBLISH": "1",
            }
            # clear tokens
            for k in ("GITHUB_TOKEN", "GH_TOKEN", "TORII_LOCAL_TOKEN"):
                env.pop(k, None)
                env[k] = ""
            cp = subprocess.run(
                ["bash", str(PUB_LOCAL)],
                capture_output=True,
                text=True,
                env=env,
                cwd=str(ROOT),
            )
            self.assertNotEqual(cp.returncode, 0)
            combined = cp.stdout + cp.stderr
            self.assertIn("::warning::", combined)
            self.assertIn("LOCAL_PUBLISH=no_token", (out / "memory-health.env").read_text())

    def test_local_publish_skipped_records(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            env = {
                **os.environ,
                "OUT_DIR": str(out),
                "TORII_LOCAL_PUBLISH": "0",
                "TORII_MEMORY_MODE": "local",
            }
            cp = subprocess.run(
                ["bash", str(PUB_LOCAL)],
                capture_output=True,
                text=True,
                env=env,
                cwd=str(ROOT),
            )
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertIn("LOCAL_PUBLISH=skipped", (out / "memory-health.env").read_text())

    def test_preload_records_seed(self):
        with tempfile.TemporaryDirectory() as td:
            hermes = Path(td) / "h"
            hermes.mkdir()
            out = Path(td) / "out"
            out.mkdir()
            bin_dir = Path(td) / "bin"
            bin_dir.mkdir()
            curl = bin_dir / "curl"
            curl.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "sys.stdout.write('404')\n"
            )
            curl.chmod(0o755)
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
                "REPO": "acme/widgets",
                "HERMES_HOME": str(hermes),
                "OUT_DIR": str(out),
                "TORII_MEMORY_MODE": "local",
            }
            env.pop("TORII_HUB_PUBLISH", None)
            cp = subprocess.run(
                ["bash", str(PRELOAD)],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(cp.returncode, 0, cp.stderr)
            health = (out / "memory-health.env").read_text()
            self.assertIn("MEMORY_SOURCE=seed", health)


if __name__ == "__main__":
    unittest.main()

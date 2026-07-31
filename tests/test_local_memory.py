#!/usr/bin/env python3
"""F28: repo-local .torii/ ingest, hub skip, preload preference."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "scripts" / "hub-ingest-run.py"
PRELOAD = ROOT / "scripts" / "preload-hub-memory.sh"
PUBLISH_HUB = ROOT / "scripts" / "publish-run-to-hub.sh"


def _sample_run(**overrides):
    base = {
        "schema_version": 1,
        "source_repo": "acme/widgets",
        "pr_number": "7",
        "run_id": "123",
        "run_attempt": "1",
        "trace_id": "pr7-run123-a1",
        "model": "anthropic/claude-opus-5",
        "status": "success",
        "verdict": "REQUEST CHANGES",
        "review_md": "## Review\n\n**Verdict:** REQUEST CHANGES\n\n### Summary\nok\n",
        "memory_block": "## Review run pr7-run123-a1\n- Verdict: REQUEST CHANGES\n",
        "timings": {"total_seconds": 12},
        "meta": {},
    }
    base.update(overrides)
    return base


class LocalIngestTests(unittest.TestCase):
    def test_local_layout_writes_dot_torii(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            payload = {"run": _sample_run()}
            env = os.environ.copy()
            env["CLIENT_PAYLOAD"] = json.dumps(payload)
            env["TORII_INGEST_LAYOUT"] = "local"
            env["TORII_MEMORY_ROOT"] = str(target)
            env["TORII_MEMORY_PATH"] = ".torii"
            subprocess.check_call([sys.executable, str(INGEST)], env=env, cwd=str(target))
            mem = target / ".torii" / "MEMORY.md"
            self.assertTrue(mem.exists(), "MEMORY.md under .torii/")
            self.assertIn("REQUEST CHANGES", mem.read_text())
            run_meta = target / ".torii" / "runs" / "pr7-run123-a1" / "meta.json"
            self.assertTrue(run_meta.exists())
            meta = json.loads(run_meta.read_text())
            self.assertEqual(meta.get("layout"), "local")
            self.assertIsNone(meta.get("slug"))
            review = target / ".torii" / "runs" / "pr7-run123-a1" / "review.md"
            summary = target / ".torii" / "runs" / "pr7-run123-a1" / "summary.md"
            self.assertTrue(review.exists())
            self.assertTrue(summary.exists())
            # no hub tree
            self.assertFalse((target / "memory" / "repos").exists())

    def test_local_no_slug_required(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            # minimal repo id still ok
            env = os.environ.copy()
            env["CLIENT_PAYLOAD"] = json.dumps(
                {"run": _sample_run(source_repo="solo-repo-no-slash")}
            )
            env["TORII_INGEST_LAYOUT"] = "local"
            env["TORII_MEMORY_ROOT"] = str(target)
            subprocess.check_call([sys.executable, str(INGEST)], env=env)
            self.assertTrue((target / ".torii" / "MEMORY.md").exists())

    def test_hub_layout_still_uses_slug(self):
        with tempfile.TemporaryDirectory() as td:
            hub = Path(td)
            env = os.environ.copy()
            env["CLIENT_PAYLOAD"] = json.dumps({"run": _sample_run()})
            env["HUB_ROOT"] = str(hub)
            env["TORII_INGEST_LAYOUT"] = "hub"
            subprocess.check_call([sys.executable, str(INGEST)], env=env)
            mem = hub / "memory" / "repos" / "acme--widgets" / "MEMORY.md"
            self.assertTrue(mem.exists())


class HubPublishGateTests(unittest.TestCase):
    def test_hub_skipped_when_mode_local(self):
        env = os.environ.copy()
        env["TORII_MEMORY_MODE"] = "local"
        # Ensure explicit publish not set
        env.pop("TORII_HUB_PUBLISH", None)
        env["GITHUB_TOKEN"] = "fake"
        env["GH_TOKEN"] = "fake"
        r = subprocess.run(
            ["bash", str(PUBLISH_HUB)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        combined = r.stdout + r.stderr
        self.assertIn("skip hub publish", combined)
        self.assertNotIn("Hub publish mode=", combined)

    def test_hub_runs_when_publish_explicit(self):
        """With TORII_HUB_PUBLISH=1 but missing payload tooling path still past gate."""
        env = os.environ.copy()
        env["TORII_MEMORY_MODE"] = "local"
        env["TORII_HUB_PUBLISH"] = "1"
        env["GITHUB_TOKEN"] = "fake"
        env["OUT_DIR"] = "/nonexistent-out-dir-for-gate-test"
        r = subprocess.run(
            ["bash", str(PUBLISH_HUB)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )
        # Should not early-exit with "skip hub publish" from mode
        combined = r.stdout + r.stderr
        self.assertNotIn("TORII_HUB_PUBLISH=0", combined)
        # May fail later building payload — that's fine; we only assert gate opened
        self.assertNotIn("skip hub publish", combined)


class PreloadPreferenceTests(unittest.TestCase):
    def test_local_wins_over_hub(self):
        """curl to local path 200 → MEMORY_SOURCE=local; hub never required."""
        with tempfile.TemporaryDirectory() as td:
            hermes = Path(td) / "hermes"
            hermes.mkdir()
            (hermes / "memories").mkdir()
            local_body = "# Local memory\n\nfrom .torii\n"
            hub_body = "# Hub memory\n\nfrom hub\n"

            calls = []

            def fake_curl(cmd, *a, **kw):
                # curl -sS -L -o TMP -w %{http_code} ... URL
                # find -o dest and URL
                out_file = None
                url = cmd[-1] if cmd else ""
                for i, c in enumerate(cmd):
                    if c == "-o" and i + 1 < len(cmd):
                        out_file = cmd[i + 1]
                calls.append(url)
                if ".torii/MEMORY.md" in url or "%2Ftorii" in url:
                    Path(out_file).write_text(local_body)
                    # curl writes http code to stdout when -w used; script captures HTTP=
                    # Our mock: run real can't work; use subprocess replacement
                return mock.DEFAULT

            # Simpler: implement a small wrapper script env via PATH
            bin_dir = Path(td) / "bin"
            bin_dir.mkdir()
            curl_sh = bin_dir / "curl"
            curl_sh.write_text(
                f"""#!/usr/bin/env bash
# minimal curl stub for preload tests
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -w|-H|-L|-sS) shift; [[ "$1" == *http* ]] && shift || true; shift 2>/dev/null || true ;;
    http*) url="$1"; shift ;;
    *) shift ;;
  esac
done
# parse remaining
for a in "$@"; do
  case "$a" in http*) url="$a" ;; esac
done
# re-scan argv from BASH_ARGV not available; use last arg pattern
url="${{url:-}}"
# Actually re-read: the script passes URL as last positional after HDR
# Fall through: inspect full command line
full="$* $out"
# Write body based on URL in process list — use env from parent via file
if [[ -n "${{out:-}}" ]]; then
  if [[ "$*" == *".torii/MEMORY.md"* ]] || [[ "$*" == *"%2E%6Cuffy"* ]]; then
    printf '%s' {json.dumps(local_body)} >"$out"
  elif [[ "$*" == *"memory/repos"* ]]; then
    printf '%s' {json.dumps(hub_body)} >"$out"
  else
    printf '%s' {json.dumps(local_body)} >"$out"
  fi
fi
# http code on stdout for -w (script uses -w "%{{http_code}}")
echo -n 200
"""
            )
            # The stub above is fragile. Use a cleaner Python curl shim.
            curl_sh.write_text(
                """#!/usr/bin/env python3
import sys
from pathlib import Path
args = sys.argv[1:]
out = None
url = None
i = 0
while i < len(args):
    a = args[i]
    if a == "-o" and i + 1 < len(args):
        out = args[i + 1]
        i += 2
        continue
    if a.startswith("http"):
        url = a
    i += 1
if url is None:
    for a in args:
        if a.startswith("http"):
            url = a
body = ""
code = "404"
if url and ".torii/MEMORY.md" in url:
    body = "# Local memory\\n\\nfrom .torii\\n"
    code = "200"
elif url and "memory/repos" in url:
    body = "# Hub memory\\n\\nfrom hub\\n"
    code = "200"
if out and code == "200":
    Path(out).write_text(body)
sys.stdout.write(code)
"""
            )
            curl_sh.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            env["REPO"] = "acme/widgets"
            env["HERMES_HOME"] = str(hermes)
            env["TORII_MEMORY_MODE"] = "both"  # hub available but local must win
            env["TORII_HUB_PUBLISH"] = "1"
            env["GITHUB_TOKEN"] = "fake"
            r = subprocess.run(
                ["bash", str(PRELOAD)],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            combined = r.stdout + r.stderr
            self.assertIn("MEMORY_SOURCE=local", combined)
            dest = hermes / "memories" / "MEMORY.md"
            self.assertTrue(dest.exists())
            self.assertIn("from .torii", dest.read_text())
            self.assertNotIn("from hub", dest.read_text())

    def test_hub_skipped_when_mode_local(self):
        with tempfile.TemporaryDirectory() as td:
            hermes = Path(td) / "hermes"
            hermes.mkdir()
            bin_dir = Path(td) / "bin"
            bin_dir.mkdir()
            curl_sh = bin_dir / "curl"
            curl_sh.write_text(
                """#!/usr/bin/env python3
import sys
from pathlib import Path
args = sys.argv[1:]
out = None
url = None
for i, a in enumerate(args):
    if a == "-o" and i + 1 < len(args):
        out = args[i + 1]
    if a.startswith("http"):
        url = a
code = "404"
if url and "memory/repos" in url:
    if out:
        Path(out).write_text("# should not load\\n")
    code = "200"
# local always 404
sys.stdout.write(code if (url and "memory/repos" in (url or "")) else "404")
"""
            )
            # Fix: always 404 for local, 200 for hub — but mode local must not fetch hub
            curl_sh.write_text(
                """#!/usr/bin/env python3
import sys
from pathlib import Path
args = sys.argv[1:]
out = None
url = None
for i, a in enumerate(args):
    if a == "-o" and i + 1 < len(args):
        out = args[i + 1]
    if isinstance(a, str) and a.startswith("http"):
        url = a
# Always 404 — assert hub path never requested
if url and "memory/repos" in url:
    Path(out or "/tmp/x").write_text("HUB_SHOULD_NOT_BE_CALLED")
    sys.stdout.write("200")
    sys.exit(0)
sys.stdout.write("404")
"""
            )
            curl_sh.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            env["REPO"] = "acme/widgets"
            env["HERMES_HOME"] = str(hermes)
            env["TORII_MEMORY_MODE"] = "local"
            env.pop("TORII_HUB_PUBLISH", None)
            env["GITHUB_TOKEN"] = "fake"
            r = subprocess.run(
                ["bash", str(PRELOAD)],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            combined = r.stdout + r.stderr
            self.assertIn("HUB_MEMORY=skipped", combined)
            self.assertIn("MEMORY_SOURCE=seed", combined)
            dest = hermes / "memories" / "MEMORY.md"
            # no file written from remote
            if dest.exists():
                self.assertNotIn("HUB_SHOULD_NOT_BE_CALLED", dest.read_text())


if __name__ == "__main__":
    unittest.main()

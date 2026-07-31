#!/usr/bin/env python3
"""F55: feature toggle registry resolution + CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "feature_toggles.py"
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("feature_toggles", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["feature_toggles"] = _mod  # required before dataclass exec
_spec.loader.exec_module(_mod)


class ParseBool(unittest.TestCase):
    def test_default_when_empty(self):
        self.assertTrue(_mod.parse_bool(None, True))
        self.assertFalse(_mod.parse_bool(None, False))
        self.assertTrue(_mod.parse_bool("", True))

    def test_falsey(self):
        for v in ("0", "false", "OFF", "no", "disabled"):
            self.assertFalse(_mod.parse_bool(v, True), v)

    def test_truthy(self):
        for v in ("1", "true", "YES", "on"):
            self.assertTrue(_mod.parse_bool(v, False), v)


class ResolvePrecedence(unittest.TestCase):
    def test_default(self):
        r = _mod.resolve("fixit_prompts", env={}, file_map={}, load_file=False)
        self.assertTrue(r.value)
        self.assertEqual(r.source, "default")
        self.assertEqual(r.env, "TORII_FIXIT_PROMPTS")

    def test_env_wins_over_file(self):
        r = _mod.resolve(
            "fixit_prompts",
            env={"TORII_FIXIT_PROMPTS": "0"},
            file_map={"fixit_prompts": True},
            load_file=False,
        )
        self.assertFalse(r.value)
        self.assertEqual(r.source, "env")

    def test_file_when_env_unset(self):
        r = _mod.resolve(
            "fixit_prompts",
            env={},
            file_map={"TORII_FIXIT_PROMPTS": 0},
            load_file=False,
        )
        self.assertFalse(r.value)
        self.assertEqual(r.source, "file")

    def test_file_short_key(self):
        r = _mod.resolve(
            "issue_context",
            env={},
            file_map={"issue_context": False},
            load_file=False,
        )
        self.assertFalse(r.value)
        self.assertEqual(r.source, "file")

    def test_env_by_full_name(self):
        r = _mod.resolve(
            "TORII_INLINE_MAX",
            env={"TORII_INLINE_MAX": "12"},
            file_map={},
            load_file=False,
        )
        self.assertEqual(r.value, 12)
        self.assertEqual(r.kind, "int")

    def test_unknown_key(self):
        with self.assertRaises(KeyError):
            _mod.resolve("not_a_real_toggle", env={}, file_map={}, load_file=False)

    def test_is_enabled_bool(self):
        self.assertTrue(
            _mod.is_enabled("fixit_prompts", env={}, file_map={}, load_file=False)
        )
        self.assertFalse(
            _mod.is_enabled(
                "fixit_prompts",
                env={"TORII_FIXIT_PROMPTS": "off"},
                file_map={},
                load_file=False,
            )
        )

    def test_hub_publish_default_off(self):
        r = _mod.resolve("hub_publish", env={}, file_map={}, load_file=False)
        self.assertFalse(r.value)
        self.assertEqual(r.category, "memory")


class FileLoad(unittest.TestCase):
    def test_load_json_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "toggles.json"
            p.write_text(
                json.dumps({"fixit_prompts": False, "inline_max": 9}),
                encoding="utf-8",
            )
            fmap = _mod.load_file_overrides(p)
            self.assertEqual(fmap["fixit_prompts"], False)
            r = _mod.resolve(
                "inline_max", env={}, file_map=fmap, load_file=False
            )
            self.assertEqual(r.value, 9)
            self.assertEqual(r.source, "file")

    def test_search_torii_dir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".torii").mkdir()
            (root / ".torii" / "toggles.json").write_text(
                json.dumps({"ops_footer": False}),
                encoding="utf-8",
            )
            fmap = _mod.load_file_overrides(search_roots=[root])
            self.assertIn("ops_footer", fmap)
            r = _mod.resolve(
                "ops_footer", env={}, file_map=fmap, load_file=False
            )
            self.assertFalse(r.value)


class DumpAndProduct(unittest.TestCase):
    def test_dump_map_product(self):
        m = _mod.dump_map(
            category="product", env={}, file_map={}, load_file=False
        )
        self.assertIn("fixit_prompts", m)
        self.assertIn("issue_context", m)
        self.assertTrue(m["fixit_prompts"])

    def test_registry_unique_keys(self):
        keys = [t.key for t in _mod.REGISTRY]
        envs = [t.env for t in _mod.REGISTRY]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(envs), len(set(envs)))


class CLI(unittest.TestCase):
    def _run(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        e = os.environ.copy()
        if env:
            e.update(env)
        # avoid accidental file overrides from developer machine
        e.pop("TORII_TOGGLES_FILE", None)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=e,
        )

    def test_list_json(self):
        cp = self._run("list", "--json", "--category", "product")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        keys = {row["key"] for row in data}
        self.assertIn("fixit_prompts", keys)

    def test_get_env_override(self):
        cp = self._run(
            "get",
            "fixit_prompts",
            "--no-file",
            env={"TORII_FIXIT_PROMPTS": "0"},
        )
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(cp.stdout.strip().lower(), "false")

    def test_enabled_exit_codes(self):
        cp = self._run(
            "enabled",
            "fixit_prompts",
            "--no-file",
            env={"TORII_FIXIT_PROMPTS": "1"},
        )
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(cp.stdout.strip(), "1")
        cp2 = self._run(
            "enabled",
            "fixit_prompts",
            "--no-file",
            env={"TORII_FIXIT_PROMPTS": "0"},
        )
        self.assertEqual(cp2.returncode, 1)
        self.assertEqual(cp2.stdout.strip(), "0")

    def test_dump_values(self):
        cp = self._run("dump", "--values-only", "--no-file", "--category", "product")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        self.assertIsInstance(data["inline_max"], int)

    def test_shell_exports(self):
        cp = self._run("shell", "--bools", "--category", "product")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("export TORII_FIXIT_PROMPTS=", cp.stdout)


if __name__ == "__main__":
    unittest.main()

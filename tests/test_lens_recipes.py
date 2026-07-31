#!/usr/bin/env python3
"""F56: named lens recipe packs."""

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
SCRIPT = ROOT / "scripts" / "lens_recipes.py"
PACKS = ROOT / "agent" / "packs"
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("lens_recipes", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["lens_recipes"] = _mod
_spec.loader.exec_module(_mod)


class PackLoad(unittest.TestCase):
    def test_list_builtin_packs(self):
        packs = _mod.list_packs(PACKS)
        ids = {p["id"] for p in packs}
        self.assertIn("default", ids)
        self.assertIn("security", ids)
        self.assertIn("odoo", ids)
        self.assertIn("docs", ids)
        self.assertIn("performance", ids)
        self.assertIn("milvus", ids)
        self.assertIn("go", ids)
        self.assertIn("cpp", ids)

    def test_get_odoo(self):
        pack = _mod.get_pack("odoo", PACKS)
        self.assertEqual(pack["id"], "odoo")
        lids = [x["id"] for x in pack["lenses"]]
        self.assertIn("security", lids)
        self.assertTrue(pack["extra_focus"])

    def test_unknown(self):
        with self.assertRaises(KeyError):
            _mod.get_pack("not-a-pack", PACKS)


class RenderApply(unittest.TestCase):
    def test_render_contains_pack_id(self):
        pack = _mod.get_pack("security", PACKS)
        md = _mod.render_full(pack)
        self.assertIn("**Lens pack:** `security`", md)
        self.assertIn("<!-- torii-lens-pack:security -->", md)
        self.assertIn("| security |", md)
        self.assertIn("Pack focus:", md)

    def test_apply_to_prompt_rewrites_sections(self):
        template = (ROOT / "agent" / "review-prompt.md").read_text(encoding="utf-8")
        pack = _mod.get_pack("docs", PACKS)
        out = _mod.apply_to_prompt(template, pack)
        self.assertIn("**Lens pack:** `docs`", out)
        self.assertIn("<!-- torii-lens-pack:docs -->", out)
        self.assertIn("| correctness |", out)
        # order: docs puts correctness first
        idx_pass = out.find("### Multi-lens pass")
        idx_check = out.find("### Multi-lens checklist")
        idx_sugg = out.find("### Suggestions")
        self.assertGreater(idx_pass, 0)
        self.assertGreater(idx_check, idx_pass)
        self.assertGreater(idx_sugg, idx_check)
        # default 7 lenses still present as rows for docs pack
        self.assertEqual(out.count("| ok / concern / n/a |"), 7)

    def test_apply_file(self):
        template = (ROOT / "agent" / "review-prompt.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "prompt.md"
            p.write_text(template)
            os.environ["TORII_LENS_PACK"] = "odoo"
            os.environ["TORII_LENS_PACKS"] = "1"
            os.environ.pop("TORII_TOGGLES_FILE", None)
            # force packs dir via env
            os.environ["TORII_LENS_PACKS_DIR"] = str(PACKS)
            try:
                info = _mod.apply_file(p, packs_dir=PACKS, pack_id="odoo")
            finally:
                os.environ.pop("TORII_LENS_PACK", None)
                os.environ.pop("TORII_LENS_PACKS_DIR", None)
            self.assertTrue(info["enabled"])
            self.assertEqual(info["pack"], "odoo")
            body = p.read_text()
            self.assertIn("torii-lens-pack:odoo", body)
            self.assertIn("bare sudo()", body)


class ActivePack(unittest.TestCase):
    def test_active_from_env(self):
        os.environ["TORII_LENS_PACK"] = "Security"
        try:
            # avoid F55 file/env noise: clear may still use feature_toggles
            self.assertEqual(_mod.active_pack_id("Security"), "security")
        finally:
            os.environ.pop("TORII_LENS_PACK", None)


class AutoSelect(unittest.TestCase):
    def test_milvus_paths(self):
        pack = _mod.select_pack_for_paths(
            [
                "internal/flushcommon/writebuffer/write_buffer.go",
                "internal/util/function/manager.go",
            ],
            PACKS,
        )
        self.assertEqual(pack["id"], "milvus")

    def test_go_generic(self):
        pack = _mod.select_pack_for_paths(
            ["pkg/server/handler.go", "cmd/api/main.go"],
            PACKS,
        )
        self.assertEqual(pack["id"], "go")

    def test_cpp_paths(self):
        pack = _mod.select_pack_for_paths(
            ["src/engine/query.cpp", "include/engine/query.h"],
            PACKS,
        )
        self.assertEqual(pack["id"], "cpp")

    def test_docs_paths(self):
        pack = _mod.select_pack_for_paths(
            ["docs/guide.md", "README.md"],
            PACKS,
        )
        self.assertEqual(pack["id"], "docs")

    def test_unknown_falls_default(self):
        pack = _mod.select_pack_for_paths(
            ["random/file.xyz"],
            PACKS,
        )
        self.assertEqual(pack["id"], "default")

    def test_resolve_auto(self):
        os.environ["TORII_LENS_PACK"] = "auto"
        os.environ.pop("TORII_TOGGLES_FILE", None)
        try:
            pack = _mod.resolve_active(
                PACKS,
                paths=["internal/streamingnode/server/wal/interceptor.go"],
            )
            self.assertEqual(pack["id"], "milvus")
        finally:
            os.environ.pop("TORII_LENS_PACK", None)


class CLI(unittest.TestCase):
    def _run(self, *args, env=None):
        e = os.environ.copy()
        e["TORII_LENS_PACKS_DIR"] = str(PACKS)
        e.pop("TORII_TOGGLES_FILE", None)
        if env:
            e.update(env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--packs-dir", str(PACKS), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=e,
        )

    def test_list_json(self):
        cp = self._run("list", "--json")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        self.assertGreaterEqual(len(data), 5)

    def test_resolve(self):
        cp = self._run("resolve", env={"TORII_LENS_PACK": "docs"})
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(cp.stdout.strip(), "docs")

    def test_select_milvus(self):
        cp = self._run(
            "select",
            "--paths",
            "internal/flushcommon/writebuffer/x.go",
            env={"TORII_LENS_PACK": "auto"},
        )
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(cp.stdout.strip(), "milvus")


if __name__ == "__main__":
    unittest.main()

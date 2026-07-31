from pathlib import Path
import importlib.util
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "torii_gate_status", ROOT / "scripts" / "torii_gate_status.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["torii_gate_status"] = mod
spec.loader.exec_module(mod)


def test_approve_opens_gate():
    text = """**Verdict:** APPROVE
**Security audit:** No
**Score:** 90
"""
    d = mod.gate_decision(mod.parse_verdict_text(text))
    assert d["block"] is False
    assert d["state"] == "success"


def test_request_changes_closes_gate():
    text = """**Verdict:** REQUEST CHANGES
**Security audit:** XSS: reflected in q param
"""
    d = mod.gate_decision(mod.parse_verdict_text(text))
    assert d["block"] is True
    assert d["state"] == "failure"


def test_security_concern_closes_even_if_comment():
    text = """**Verdict:** COMMENT
**Security audit:** SQL injection in search handler
"""
    d = mod.gate_decision(mod.parse_verdict_text(text))
    assert d["block"] is True


def test_default_pack_is_security(monkeypatch):
    monkeypatch.delenv("TORII_LENS_PACK", raising=False)
    sys.path.insert(0, str(ROOT / "scripts"))
    # re-import clean
    if "feature_toggles" in sys.modules:
        del sys.modules["feature_toggles"]
    if "lens_recipes" in sys.modules:
        del sys.modules["lens_recipes"]
    from lens_recipes import active_pack_id

    assert active_pack_id() == "security"

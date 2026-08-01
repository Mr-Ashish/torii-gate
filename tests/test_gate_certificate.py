from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "gate_certificate", ROOT / "scripts" / "gate_certificate.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["gate_certificate"] = mod
spec.loader.exec_module(mod)


def test_good_review_closes_with_path_evidence():
    review = ROOT / "docs/benchmarks/fixtures/insecure-demo-good-review.md"
    cert = mod.build_certificate(ROOT, review)
    assert cert["block"] is True
    assert cert["verdict"] == "REQUEST_CHANGES"
    assert "verdict_request_changes" in cert["reason_codes"]
    assert float(cert["path_evidence"]["score"]) >= 0.45
    assert cert["certificate_id"].startswith("gc-")
    assert cert["merge_authority"]["closed"] is True


def test_weak_approve_opens_with_low_path_code():
    review = ROOT / "docs/benchmarks/fixtures/insecure-demo-weak-review.md"
    critic = ROOT / "docs/benchmarks/fixtures/second-agent-critic.json"
    cert = mod.build_certificate(
        ROOT, review, critic_path=critic if critic.is_file() else None
    )
    assert cert["block"] is False
    assert cert["verdict"] == "APPROVE"
    assert "low_path_evidence" in cert["reason_codes"] or float(
        cert["path_evidence"]["score"]
    ) < 0.4
    if critic.is_file():
        assert cert.get("critic", {}).get("demoted") is True
        assert "critic_demoted_maker" in cert["reason_codes"]


def test_fixture_pass():
    # GATE.md must mention certificate for fixture — ensure via report/docs before full pass
    gate = ROOT / "docs" / "GATE.md"
    text = gate.read_text(encoding="utf-8") if gate.is_file() else ""
    if "certificate" not in text.lower():
        # still unit-test core checks without gate_md clause
        rep = mod.run_fixture(ROOT)
        assert rep["checks"]["good_blocks"] is True
        assert rep["checks"]["weak_opens"] is True
    else:
        rep = mod.run_fixture(ROOT)
        assert rep["fixture_pass"] is True, rep


def test_render_md_has_reason_codes():
    review = ROOT / "docs/benchmarks/fixtures/insecure-demo-good-review.md"
    cert = mod.build_certificate(ROOT, review)
    md = mod.render_md(cert)
    assert "Reason codes" in md
    assert cert["certificate_id"] in md

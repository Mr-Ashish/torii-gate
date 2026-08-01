#!/usr/bin/env python3
"""Install UX surface check (priority queue dim 7).

5-minute path, one CLI, doctor defaults, minimal pack flag.

Commands:
  fixture | status | report
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "INSTALL_UX"
SCHEMA = 1


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def check(root: Path) -> dict[str, Any]:
    install_md = root / "docs" / "INSTALL.md"
    install_sh = root / "scripts" / "install-torii.sh"
    torii = root / "scripts" / "torii.py"
    golden = root / "docs" / "GOLDEN-PATH.md"
    pack_readme = root / "pack" / "README.md"

    im = _read(install_md)
    sh = _read(install_sh)
    tp = _read(torii)
    gd = _read(golden)

    checks: dict[str, bool] = {
        "install_md_exists": install_md.is_file(),
        "install_md_5min": bool(re.search(r"5.?minute|five minute", im, re.I)),
        "install_md_torii_gate": "torii/gate" in im,
        "install_md_one_cli": ("torii.py" in im)
        and (("One CLI" in im) or ("one front door" in im.lower())),
        "install_md_doctor": "doctor" in im,
        "install_md_status_day2": bool(
            re.search(r"status\s+--text|status --text", im)
            and ("one-screen" in im.lower() or "day-2" in im.lower())
        ),
        "install_md_deeper_self_evolve": "SELF-EVOLVE" in im,
        "install_md_deeper_federation": "FEDERATION" in im,
        "install_md_deeper_memory": "MEMORY.md" in im,
        # ENT_INSTALL_TENANT: enterprise light + quieter checklist on install
        "install_md_enterprise_tenant": bool(
            re.search(r"--tenant|TORII_MEMORY_TENANT|Enterprise light", im, re.I)
            and ("enterprise/" in im or "enterprise -- status" in im)
        ),
        "install_md_quieter_checklist": bool(
            re.search(r"quieter checklist|Own-repo quieter|quieter -- status", im, re.I)
            and "torii/gate" in im
        ),
        # LANDING_COST / day-2 cost visibility (dim 7 + ops)
        "install_md_cost_pr_day2": bool(
            re.search(r"Cost\s*/\s*PR|cost/PR", im, re.I)
            and (
                "cost-pr-dashboard" in im
                or "ops_dashboard" in im
                or "ops -- status" in im
                or "torii.py ops" in im
            )
        ),
        "install_sh_minimal": "--minimal" in sh and "MINIMAL_EXCLUDE" in sh,
        "install_sh_next_steps_one_cli": "One CLI" in sh
        or "torii.py help|doctor" in sh
        or "torii.py help|status|doctor" in sh,
        "install_sh_no_dual_tip": "torii_memory.py help &&" not in sh,
        # INSTALL_COST_TIP: day-2 cost visibility from install Next steps
        "install_sh_cost_tip": bool(
            re.search(r"cost/PR|cost-pr-dashboard|ops -- status", sh, re.I)
            and "ops" in sh
        ),
        # STATUS_DAY2: one-screen status tip from install Next steps
        "install_sh_status_tip": bool(
            re.search(r"status\s+--text|status --text", sh)
            and ("one-screen" in sh.lower() or "Day-2" in sh)
        ),
        "install_sh_tenant_flag": bool(
            re.search(r"--tenant", sh)
            and "TORII_MEMORY_TENANT" in sh
            and "tenant_id=" in sh
        ),
        "install_sh_enterprise_tip": bool(
            re.search(r"enterprise light|enterprise -- status", sh, re.I)
        ),
        "install_sh_quieter_tip": bool(
            re.search(r"quieter -- status|Quieter chart", sh, re.I)
        ),
        "pack_readme_cost": bool(
            re.search(r"cost/PR|cost-pr-dashboard|ops -- status", _read(pack_readme), re.I)
        )
        if pack_readme.is_file()
        else False,
        "torii_doctor_text": "render_doctor_text" in tp,
        "torii_status_text": "render_status_text" in tp,
        "torii_doctor_json_flag": '"--json"' in tp or "'--json'" in tp,
        "golden_links_install": "INSTALL.md" in gd or "docs/INSTALL" in gd,
        "install_script_exists": install_sh.is_file(),
    }

    # dry-run minimal install into temp-like path under .torii-out
    dry_ok = False
    dry_detail = ""
    try:
        dest = root / ".torii-out" / "install-ux-minimal-dry"
        dest.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["bash", str(install_sh), "--minimal", "--dry-run", "--dest", str(dest)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = (r.stdout or "") + (r.stderr or "")
        dry_ok = r.returncode == 0 and ("minimal" in out.lower() or "DRY" in out or "dry-run" in out)
        dry_detail = out[-300:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        dry_detail = str(exc)
    checks["minimal_dry_run"] = dry_ok

    # doctor --json still works
    doctor_json_ok = False
    try:
        r = subprocess.run(
            [sys.executable, str(torii), "doctor", "--json"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "TORII_ROOT": str(root)},
        )
        data = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
        doctor_json_ok = "doctor_pass" in data
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        doctor_json_ok = False
    checks["doctor_json"] = doctor_json_ok

    ok_n = sum(1 for v in checks.values() if v)
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "fixture_pass": all(checks.values()),
        "ok_n": ok_n,
        "total": len(checks),
        "checks": checks,
        "dry_detail_tail": dry_detail[-200:] if dry_detail else "",
        "scorecard_target": "install",
        "dim_lift": "install UX (dim 7)",
        "at": _now(),
        "paths": {
            "install_md": "docs/INSTALL.md",
            "install_sh": "scripts/install-torii.sh",
            "pack_readme": str(pack_readme.relative_to(root)) if pack_readme.is_file() else None,
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Install UX check")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("fixture", "status", "report"):
        sp = sub.add_parser(name)
        sp.set_defaults(cmd=name)
    args = p.parse_args(argv)
    payload = check(_root())
    if args.cmd == "report":
        lines = [
            f"# Install UX · pass={payload['fixture_pass']}",
            f"checks: {payload['ok_n']}/{payload['total']}",
            "",
        ]
        for k, v in sorted(payload["checks"].items()):
            lines.append(f"- [{'OK' if v else 'FAIL'}] {k}")
        print("\n".join(lines))
    else:
        print(json.dumps(payload, indent=2))
    return 0 if payload.get("fixture_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())

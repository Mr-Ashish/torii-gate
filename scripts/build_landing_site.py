#!/usr/bin/env python3
"""Build a deployable static site from docs/brand/landing.html (DEPLOYED_LANDING).

Buyer gap #7: landing must be a real URL, not only a path inside the monorepo.
This script writes docs/brand/site/ for GitHub Pages (or any static host):

  index.html     — landing with relative doc links rewritten to github.com blob URLs
  .nojekyll      — allow _paths on Pages
  README.md      — how to enable Pages + expected public URL

Commands:
  build | fixture | status

Env:
  TORII_ROOT
  TORII_LANDING_REPO_URL   default https://github.com/Mr-Ashish/torii-gate
  TORII_LANDING_BLOB_REF   default main
  TORII_LANDING_PAGES_URL  default https://mr-ashish.github.io/torii-gate/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

FEATURE = "DEPLOYED_LANDING"
SCHEMA = 1
SITE_REL = Path("docs/brand/site")
LANDING_REL = Path("docs/brand/landing.html")
DEFAULT_REPO = "https://github.com/Mr-Ashish/torii-gate"
DEFAULT_PAGES = "https://mr-ashish.github.io/torii-gate/"


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_url() -> str:
    return (os.environ.get("TORII_LANDING_REPO_URL") or DEFAULT_REPO).rstrip("/")


def blob_base() -> str:
    ref = (os.environ.get("TORII_LANDING_BLOB_REF") or "main").strip() or "main"
    return f"{repo_url()}/blob/{ref}/"


def pages_url() -> str:
    return (os.environ.get("TORII_LANDING_PAGES_URL") or DEFAULT_PAGES).rstrip("/") + "/"


def rewrite_landing_html(html: str, *, blob: str, root: Path | None = None) -> str:
    """Rewrite relative paths from docs/brand/ to github blob URLs for static deploy."""
    root = root or _root()

    def repl_href(m: re.Match[str]) -> str:
        q = m.group(1)
        href = m.group(2)
        # leave absolute / anchors / mailto
        if href.startswith(("http://", "https://", "#", "mailto:", "data:")):
            return m.group(0)
        # from docs/brand/: ../X -> docs/X ; ../../X -> repo root (or docs/ if only there)
        if href.startswith("../../"):
            rel = href[len("../../") :]
            target = rel
            if not (root / rel).exists() and (root / "docs" / rel).exists():
                target = f"docs/{rel}"
        elif href.startswith("../"):
            rel = href[len("../") :]
            target = f"docs/{rel}"
        elif href.startswith("./"):
            target = f"docs/brand/{href[2:]}"
        else:
            # bare relative in brand dir
            target = f"docs/brand/{href}"
        # strip query/hash for path; reattach hash
        path, frag = target, ""
        if "#" in path:
            path, frag = path.split("#", 1)
            frag = "#" + frag
        url = urljoin(blob if blob.endswith("/") else blob + "/", path) + frag
        return f"href={q}{url}{q}"

    out = re.sub(r'href=(["\'])([^"\']+)\1', repl_href, html)
    # base for github pages project site (assets relative to /torii-gate/)
    if "<base " not in out.lower():
        out = out.replace(
            "<head>",
            '<head>\n<base href="./" />\n'
            f'<!-- torii-deployed-landing · {FEATURE} · blob={blob} -->',
            1,
        )
    # canonical pages note
    if "torii-deployed-landing" not in out:
        out = out.replace(
            "</body>",
            f'<!-- {FEATURE} pages={pages_url()} -->\n</body>',
            1,
        )
    return out


def build(root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    landing = root / LANDING_REL
    site = root / SITE_REL
    if not landing.is_file():
        return {
            "feature": FEATURE,
            "ok": False,
            "error": "missing_landing",
            "path": str(LANDING_REL),
        }
    raw = landing.read_text(encoding="utf-8")
    blob = blob_base()
    html = rewrite_landing_html(raw, blob=blob, root=root)
    site.mkdir(parents=True, exist_ok=True)
    index = site / "index.html"
    index.write_text(html, encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")
    pages = pages_url()
    (site / "README.md").write_text(
        "\n".join(
            [
                "# Torii Gate — deployed landing site",
                "",
                f"**Public URL (GitHub Pages):** [{pages}]({pages})",
                "",
                "Built from `docs/brand/landing.html` via:",
                "",
                "```bash",
                "python3 scripts/build_landing_site.py build",
                "```",
                "",
                "Enable Pages: repo **Settings → Pages → GitHub Actions** "
                "(workflow `.github/workflows/pages-landing.yml`).",
                "",
                f"Source HTML is rewritten so doc links open on `{blob}`.",
                "",
                f"_Built: `{_now()}` · feature **{FEATURE}**_",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Buyer GTM: primary CTA is design-partner apply, not incubator/Hub71 detours
    primary_slice = html.split("<details")[0] if "<details" in html else html
    checks = {
        "index_exists": index.is_file(),
        "has_torii_gate": "torii/gate" in html,
        "has_stricter_quieter": "stricter and quieter" in html.lower(),
        "no_f_compound_marketing": not re.search(
            r"\bF18[5-9]\b|\bF186\b", primary_slice
        ),
        "blob_links": blob.rstrip("/") in html or "github.com/" in html,
        "nojekyll": (site / ".nojekyll").is_file(),
        "workflow": (root / ".github" / "workflows" / "pages-landing.yml").is_file(),
        "design_partner_cta": "design-partner.yml" in html
        or "template=design-partner" in html,
        "no_hub71_primary_cta": "hub71.com" not in primary_slice.lower(),
        "no_wrong_repo_control_plane": "luffy-pr-review-agent" not in html,
        "install_cta": "INSTALL.md" in html or "install-torii" in html.lower(),
        "proof_packet_link": "PILOT-PROOF" in html,
    }
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "ok": all(checks.values()),
        "checks": checks,
        "pages_url": pages,
        "blob_base": blob,
        "wrote": {
            "index": str(index.relative_to(root)),
            "nojekyll": str((site / ".nojekyll").relative_to(root)),
            "readme": str((site / "README.md").relative_to(root)),
        },
        "bytes": index.stat().st_size if index.is_file() else 0,
        "at": _now(),
        "one_liner": (
            "Static site from landing.html for GitHub Pages — buyer URL, not monorepo path only"
        ),
    }


def cmd_build(args: argparse.Namespace) -> int:
    report = build(_root())
    if getattr(args, "json", False) or not sys.stdout.isatty():
        print(json.dumps(report, indent=2))
    else:
        print(f"# {FEATURE} build ok={report.get('ok')}")
        print(f"pages: {report.get('pages_url')}")
        for k, v in (report.get("wrote") or {}).items():
            print(f"  {k}: {v}")
        for k, v in (report.get("checks") or {}).items():
            print(f"  check {k}: {v}")
    return 0 if report.get("ok") else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    report = build(root)
    readme = (root / "README.md").read_text(encoding="utf-8", errors="replace")
    product = (root / "PRODUCT.md").read_text(encoding="utf-8", errors="replace")
    pages = pages_url()
    surface = {
        "build_ok": bool(report.get("ok")),
        "site_index": (root / SITE_REL / "index.html").is_file(),
        "workflow": (root / ".github" / "workflows" / "pages-landing.yml").is_file(),
        "readme_pages_url": pages.rstrip("/") in readme
        or "github.io/torii-gate" in readme
        or "Pages" in readme
        and "landing" in readme.lower(),
        "product_pages_url": "github.io/torii-gate" in product
        or pages.rstrip("/") in product
        or ("deployed landing" in product.lower() or "GitHub Pages" in product),
        "script_present": (root / "scripts" / "build_landing_site.py").is_file(),
    }
    # strengthen readme check
    surface["readme_pages_url"] = bool(
        re.search(r"github\.io/torii-gate|Pages.*landing|deployed landing", readme, re.I)
    )
    fixture_pass = all(surface.values()) and bool(report.get("ok"))
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "schema": SCHEMA,
                "fixture_pass": fixture_pass,
                "checks": surface,
                "build": {
                    "ok": report.get("ok"),
                    "pages_url": report.get("pages_url"),
                    "checks": report.get("checks"),
                },
                "scorecard_target": "GTM / distribution (dim 11)",
                "dim_lift": "buyer landing is a public URL via GitHub Pages",
                "at": _now(),
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    index = root / SITE_REL / "index.html"
    wf = root / ".github" / "workflows" / "pages-landing.yml"
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "pages_url": pages_url(),
                "site_built": index.is_file(),
                "workflow": wf.is_file(),
                "bytes": index.stat().st_size if index.is_file() else 0,
                "at": _now(),
            },
            indent=2,
        )
    )
    return 0 if index.is_file() and wf.is_file() else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    pb = sub.add_parser("build", help="Write docs/brand/site/")
    pb.add_argument("--json", action="store_true")
    pb.set_defaults(func=cmd_build)
    pf = sub.add_parser("fixture", help="Hermetic deployable landing surface")
    pf.set_defaults(func=cmd_fixture)
    ps = sub.add_parser("status", help="Short status")
    ps.set_defaults(func=cmd_status)
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

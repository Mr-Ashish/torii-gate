"""Torii public-eval — synthetic Django/Flask-style vulnerable views.

Original demo code for gate benchmarks. DO NOT deploy.
Themes inspired by common OSS training-app classes (not a project fork).
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.request import urlopen

from flask import Flask, redirect, request, render_template_string

app = Flask(__name__)
BASE = Path(__file__).resolve().parent


@app.get("/fetch")
def fetch_url():
    # dj-ssrf: intentional SSRF — server fetches attacker-controlled URL
    url = request.args.get("url", "http://127.0.0.1/")
    with urlopen(url, timeout=3) as resp:  # noqa: S310 — intentional vuln
        return {"body": resp.read(2000).decode("utf-8", errors="replace")}


@app.get("/download")
def download():
    # dj-path: intentional path traversal
    name = request.args.get("name", "readme.txt")
    target = BASE / "files" / name  # missing resolve/safeguard vs ..
    return target.read_text(encoding="utf-8", errors="replace")


@app.get("/go")
def open_redirect():
    # dj-redirect: intentional open redirect
    next_url = request.args.get("next", "/")
    return redirect(next_url)  # no allowlist


@app.get("/page")
def ssti():
    # dj-ssti: intentional server-side template injection
    title = request.args.get("title", "home")
    # vulnerable: user input in template string
    tpl = f"<h1>{title}</h1><p>welcome</p>"
    return render_template_string(tpl)


@app.get("/config")
def config_leak():
    # dj-secret: debug config / secret exposure pattern
    return {
        "DEBUG": True,
        "SECRET_KEY": os.environ.get("DJANGO_SECRET", "django-insecure-demo-key-do-not-use"),
    }

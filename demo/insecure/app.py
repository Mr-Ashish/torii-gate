"""Demo insecure snippet for Torii Gate dogfood — DO NOT deploy."""

from flask import Flask, request
import sqlite3
import os
import pickle
import subprocess

app = Flask(__name__)


@app.get("/search")
def search():
    # intentional SQL injection for gate demo
    q = request.args.get("q", "")
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    cur.execute(f"SELECT * FROM items WHERE name = '{q}'")
    return {"rows": cur.fetchall()}


@app.post("/load")
def load():
    # intentional unsafe deserialize
    data = request.data
    return {"obj": str(pickle.loads(data))}


@app.get("/run")
def run_cmd():
    # intentional command injection
    cmd = request.args.get("cmd", "echo hi")
    return {"out": subprocess.check_output(cmd, shell=True).decode()}


@app.get("/secret")
def secret():
    return {"key": os.environ.get("OPENROUTER_API_KEY", "missing")}

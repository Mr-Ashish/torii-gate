/**
 * Torii public-eval — synthetic NodeGoat-style vulnerable routes.
 * Original demo code for gate benchmarks. DO NOT deploy.
 */
"use strict";

const express = require("express");
const fs = require("fs");
const path = require("path");
const http = require("http");
const { MongoClient } = require("mongodb"); // pattern only — not connected in bench

const app = express();
app.use(express.json());

// ng-nosql: intentional NoSQL operator injection into find filter
app.post("/api/users/login", (req, res) => {
  const { userName, password } = req.body || {};
  // vulnerable: attacker can send password: { "$gt": "" }
  const filter = { userName, password };
  // pattern: db.collection("users").find(filter)
  res.json({ ok: true, filter, note: "nosql injection demo" });
});

// ng-path: intentional path traversal on profile avatar
app.get("/api/profile/avatar", (req, res) => {
  const name = req.query.file || "default.png";
  // vulnerable: join without sanitizing .. segments
  const filePath = path.join(__dirname, "uploads", name);
  try {
    const data = fs.readFileSync(filePath);
    res.type("application/octet-stream").send(data);
  } catch (e) {
    res.status(404).send(String(e));
  }
});

// ng-ssrf: intentional server-side request forgery
app.get("/api/stock", (req, res) => {
  const url = req.query.url || "http://127.0.0.1/";
  // vulnerable: fetch arbitrary URL from server
  http
    .get(url, (r) => {
      let body = "";
      r.on("data", (c) => (body += c));
      r.on("end", () => res.type("text").send(body.slice(0, 2000)));
    })
    .on("error", (e) => res.status(500).send(String(e)));
});

// ng-idor: intentional missing ownership on allocations
app.get("/api/allocations/:userId", (req, res) => {
  const userId = req.params.userId;
  // vulnerable: no session check — any caller reads any userId
  res.json({ userId, allocations: [{ symbol: "ACME", shares: 100 }] });
});

module.exports = { app };

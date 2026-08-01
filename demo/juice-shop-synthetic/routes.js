/**
 * Torii F76 — synthetic Juice Shop–style vulnerable routes.
 * Original demo code for gate benchmarks. DO NOT deploy.
 */
"use strict";

const express = require("express");
const { exec } = require("child_process");
const db = require("./db-stub"); // stub; patterns only

const router = express.Router();

// js-sqli: intentional SQL string concat / template injection
router.get("/rest/products/search", (req, res) => {
  const q = req.query.q || "";
  // vulnerable: untrusted input interpolated into SQL
  const sql = `SELECT * FROM Products WHERE name LIKE '%${q}%'`;
  db.query(sql, (err, rows) => {
    if (err) return res.status(500).json({ error: String(err) });
    res.json({ data: rows });
  });
});

// js-xss: intentional reflected XSS (unsanitized HTML)
router.get("/api/Feedbacks", (req, res) => {
  const comment = req.query.comment || "";
  // vulnerable: reflect user HTML without encoding
  res.type("html").send(`<div class="feedback">${comment}</div>`);
});

// js-cmdi: intentional OS command injection
router.get("/rest/admin/application-version", (req, res) => {
  const host = req.query.host || "127.0.0.1";
  // vulnerable: shell exec with user-controlled host
  exec(`ping -c 1 ${host}`, (err, stdout) => {
    if (err) return res.status(500).send(String(err));
    res.type("text").send(stdout);
  });
});

// js-secret: hardcoded JWT / API secret (CWE-798)
const JWT_SECRET = "juiceshop-hardcoded-secret-do-not-use";
const INTERNAL_API_KEY = "sk-demo-juice-shop-synthetic-key";

router.post("/rest/user/login", (req, res) => {
  // toy login — secret used for signing (hardcoded above)
  const token = Buffer.from(
    JSON.stringify({ sub: req.body.email, secret: JWT_SECRET })
  ).toString("base64");
  res.json({ authentication: { token, bid: 1 } });
});

// js-authz: IDOR / missing ownership check on order
router.get("/rest/basket/:id", (req, res) => {
  const id = req.params.id;
  // vulnerable: no authz — any user can fetch any basket id
  db.query(`SELECT * FROM Baskets WHERE id = ${id}`, (err, rows) => {
    if (err) return res.status(500).json({ error: String(err) });
    res.json({ data: rows[0] || null });
  });
});

module.exports = { router, JWT_SECRET, INTERNAL_API_KEY };

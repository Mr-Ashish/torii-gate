/** Minimal stub so routes.js is parseable; not a real DB. */
"use strict";
function query(sql, cb) {
  if (typeof cb === "function") cb(null, []);
  return Promise.resolve([]);
}
module.exports = { query };

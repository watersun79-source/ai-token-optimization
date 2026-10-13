#!/usr/bin/env node
// Deterministic JSON validator parity test; no API/network calls.
const fs = require("node:fs");
const path = require("node:path");
const fixturePath = path.join(__dirname, "..", "tests", "fixtures", "json_validator_cases.json");
const fixtures = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
const TOP = new Set(["checks", "error_count", "answer", "confidence", "search_used"]);
const CHECK = new Set(["label", "expected", "actual", "correct"]);
const CONFIDENCE = new Set(["low", "medium", "high"]);
function sameArray(a, b) { return a.length === b.length && a.every((x, i) => x === b[i]); }
function sortedDiff(a, b) { return [...a].filter(x => !b.has(x)).sort(); }
function extractJson(raw) {
  let candidate = raw.trim();
  if (candidate.startsWith("```")) {
    candidate = candidate.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  }
  return JSON.parse(candidate);
}
function validate(value) {
  const errors = [];
  if (value === null || typeof value !== "object" || Array.isArray(value)) return ["root_must_be_object"];
  const keys = Object.keys(value);
  const missing = sortedDiff(TOP, new Set(keys));
  const extra = sortedDiff(new Set(keys), TOP);
  if (missing.length) errors.push("missing_fields:" + missing.join(","));
  if (extra.length) errors.push("unexpected_fields:" + extra.join(","));
  if (missing.length) return errors;
  let checks = value.checks;
  if (!Array.isArray(checks) || checks.length === 0) { errors.push("checks_must_be_nonempty_array"); checks = []; }
  let counted = 0;
  checks.forEach((check, i) => {
    const prefix = `checks[${i}]`;
    if (check === null || typeof check !== "object" || Array.isArray(check)) { errors.push(prefix + "_must_be_object"); return; }
    const absent = sortedDiff(CHECK, new Set(Object.keys(check)));
    const unexpected = sortedDiff(new Set(Object.keys(check)), CHECK);
    if (absent.length) { errors.push(prefix + "_missing_fields:" + absent.join(",")); return; }
    if (unexpected.length) errors.push(prefix + "_unexpected_fields:" + unexpected.join(","));
    if (typeof check.correct !== "boolean") { errors.push(prefix + "_correct_must_be_boolean"); return; }
    const expectedCorrect = String(check.expected).trim() === String(check.actual).trim();
    if (check.correct !== expectedCorrect) errors.push(prefix + "_verdict_mismatch");
    if (!expectedCorrect) counted++;
  });
  if (!Number.isInteger(value.error_count) || value.error_count < 0) errors.push("error_count_must_be_integer");
  else if (value.error_count !== counted) errors.push(`error_count_mismatch:reported=${value.error_count},computed=${counted}`);
  if (typeof value.answer !== "string" || !value.answer.trim()) errors.push("answer_must_be_nonempty_string");
  if (!CONFIDENCE.has(value.confidence)) errors.push("confidence_must_be_low_medium_or_high");
  if (typeof value.search_used !== "boolean") errors.push("search_used_must_be_boolean");
  return errors;
}
let failed = 0;
for (const item of fixtures.cases) {
  let errors;
  if (item.raw_input !== undefined) {
    try { errors = validate(extractJson(item.raw_input)); }
    catch { errors = ["invalid_json"]; }
  } else errors = validate(item.input);
  const pass = sameArray(errors, item.expected_errors);
  console.log(`${pass ? "PASS" : "FAIL"} ${item.id}${pass ? "" : " expected=" + JSON.stringify(item.expected_errors) + " actual=" + JSON.stringify(errors)}`);
  if (!pass) failed++;
}
console.log(`RESULT ${fixtures.cases.length - failed}/${fixtures.cases.length}`);
process.exitCode = failed ? 1 : 0;

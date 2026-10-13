#!/usr/bin/env python3
"""Validate structured AI review output without calling any AI API.

Expected JSON:
{
  "checks": [
    {"label": "48*27", "expected": "1296", "actual": "1296", "correct": true}
  ],
  "error_count": 1,
  "answer": "검증 결과 오류 1개",
  "confidence": "high",
  "search_used": false
}

Exit codes: 0 valid, 1 invalid JSON/schema/inconsistent verdicts.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any

REQUIRED_TOP_LEVEL = {"checks", "error_count", "answer", "confidence", "search_used"}
REQUIRED_CHECK_FIELDS = {"label", "expected", "actual", "correct"}
CONFIDENCE_VALUES = {"low", "medium", "high"}


def extract_json(text: str) -> Any:
    """Accept a raw JSON value or one JSON object wrapped in a Markdown fence."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^\`\`\`(?:json)?\s*", "", candidate, count=1, flags=re.I)
        candidate = re.sub(r"\s*\`\`\`$", "", candidate, count=1)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json: {exc.msg} at line {exc.lineno}, column {exc.colno}") from exc


def _js_string(value: Any) -> str:
    """Mirror JavaScript String() for JSON values used in parity checks."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, list):
        return ",".join("" if item is None else _js_string(item) for item in value)
    if isinstance(value, dict):
        return "[object Object]"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def validate(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["root_must_be_object"]

    missing = sorted(REQUIRED_TOP_LEVEL - value.keys())
    extra = sorted(value.keys() - REQUIRED_TOP_LEVEL)
    if missing:
        errors.append("missing_fields:" + ",".join(missing))
    if extra:
        errors.append("unexpected_fields:" + ",".join(extra))
    if missing:
        return errors

    checks = value["checks"]
    if not isinstance(checks, list) or not checks:
        errors.append("checks_must_be_nonempty_array")
        checks = []

    counted_errors = 0
    for index, check in enumerate(checks):
        prefix = f"checks[{index}]"
        if not isinstance(check, dict):
            errors.append(prefix + "_must_be_object")
            continue
        absent = sorted(REQUIRED_CHECK_FIELDS - check.keys())
        unexpected = sorted(check.keys() - REQUIRED_CHECK_FIELDS)
        if absent:
            errors.append(prefix + "_missing_fields:" + ",".join(absent))
            continue
        if unexpected:
            errors.append(prefix + "_unexpected_fields:" + ",".join(unexpected))
        if not isinstance(check["correct"], bool):
            errors.append(prefix + "_correct_must_be_boolean")
            continue
        # For this deterministic claim-checking schema, values are compared as normalized strings.
        expected_correct = _js_string(check["expected"]).strip() == _js_string(check["actual"]).strip()
        if check["correct"] != expected_correct:
            errors.append(prefix + "_verdict_mismatch")
        if not expected_correct:
            counted_errors += 1

    if (
        not isinstance(value["error_count"], int)
        or isinstance(value["error_count"], bool)
        or value["error_count"] < 0
    ):
        errors.append("error_count_must_be_integer")
    elif value["error_count"] != counted_errors:
        errors.append(f"error_count_mismatch:reported={value['error_count']},computed={counted_errors}")

    if not isinstance(value["answer"], str) or not value["answer"].strip():
        errors.append("answer_must_be_nonempty_string")
    if (
        not isinstance(value["confidence"], str)
        or value["confidence"] not in CONFIDENCE_VALUES
    ):
        errors.append("confidence_must_be_low_medium_or_high")
    if not isinstance(value["search_used"], bool):
        errors.append("search_used_must_be_boolean")
    return errors


def self_test() -> bool:
    good = {
        "checks": [
            {"label": "48*27", "expected": "1296", "actual": "1296", "correct": True},
            {"label": "1296/48", "expected": "27", "actual": "28", "correct": False},
            {"label": "1296/27", "expected": "48", "actual": "48", "correct": True},
        ],
        "error_count": 1,
        "answer": "검증 결과 오류 1개",
        "confidence": "high",
        "search_used": False,
    }
    bad_verdict = json.loads(json.dumps(good))
    bad_verdict["checks"][2]["correct"] = False
    bad_count = json.loads(json.dumps(good))
    bad_count["error_count"] = 0
    tests = [
        ("valid_payload", validate(good) == []),
        ("wrong_verdict_rejected", any("verdict_mismatch" in e for e in validate(bad_verdict))),
        ("wrong_error_count_rejected", any("error_count_mismatch" in e for e in validate(bad_count))),
        ("markdown_fence_parsed", validate(extract_json("```json\n" + json.dumps(good) + "\n```")) == []),
        ("malformed_json_rejected", _invalid_json_rejected()),
    ]
    for name, passed in tests:
        print(f'{"PASS" if passed else "FAIL"} {name}')
    print(f"RESULT {sum(p for _, p in tests)}/{len(tests)}")
    return all(p for _, p in tests)


def _invalid_json_rejected() -> bool:
    try:
        extract_json('{"checks": ')
    except ValueError:
        return True
    return False


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        return 0 if self_test() else 1
    raw = sys.stdin.read()
    try:
        parsed = extract_json(raw)
        errors = validate(parsed)
    except ValueError as exc:
        errors = [str(exc)]
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

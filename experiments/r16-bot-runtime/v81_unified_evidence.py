#!/usr/bin/env python3
"""Offline AI BOT v8.1 evidence coordinator, not an independent LLM/native task.

Combines a freshness/SHA-checked Python+Java+JS receipt, actual C11 binary
execution and locally parallelized 20/100 role checks. Any inconsistency
blocks; successful local checks NEVER certify a ChatGPT scheduled run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import runner
import v81_swarm

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = (
    "v81_unified_evidence.py", "v81_swarm.py", "catalog.json",
    "utc_strict_oracle.c", "utc_strict_oracle_cases.tsv",
    "UtcStrictOracle.java", "utc_strict_oracle.js", "test_runtime.py",
)


class EvidenceError(Exception):
    pass


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hashes(root):
    return {name: _sha(root / name) for name in SOURCE_FILES}


def _run(argv, root, *, timeout=30):
    """No shell, no user-supplied commands or network calls; output redacted."""
    try:
        p = subprocess.run(argv, cwd=root, capture_output=True, text=True,
                           check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise EvidenceError("TRUSTED_LOCAL_COMMAND_UNAVAILABLE") from None
    if p.returncode != 0:
        raise EvidenceError("TRUSTED_LOCAL_COMMAND_FAILED")
    return p.stdout


def run_c11(root=ROOT):
    fixture = root / "utc_strict_oracle_cases.tsv"
    if not fixture.is_file():
        raise EvidenceError("SHARED_UTC_FIXTURE_MISSING")
    with tempfile.TemporaryDirectory(prefix="v81-unified-c-") as d:
        binary = str(Path(d) / "c11_oracle")
        _run(["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
              "-pedantic", "-o", binary, str(root / "utc_strict_oracle.c")], root)
        return _run([binary, str(fixture)], root, timeout=15)


def _assert_int(value, n, name):
    if type(value) is not int or value != n:
        raise EvidenceError(name)


def _receipt_proof(proof):
    if not isinstance(proof, dict) or proof.get("format") != "LOCAL_TEST_RECEIPT_V6":
        raise EvidenceError("POLYGLOT_RECEIPT_UNVERIFIED")
    counts = proof.get("counts")
    if not isinstance(counts, dict) or set(counts) != {"python", "java", "js"}:
        raise EvidenceError("POLYGLOT_COUNTS_MISSING")
    out = {}
    for lang in ("python", "java", "js"):
        row = counts[lang]
        if not isinstance(row, dict):
            raise EvidenceError("POLYGLOT_COUNT_MALFORMED")
        passed, total = row.get("passed"), row.get("total")
        if type(passed) is not int or type(total) is not int or passed <= 0 or passed != total:
            raise EvidenceError("POLYGLOT_COUNT_NOT_ALL_PASS")
        out[lang] = passed
    _assert_int(proof.get("total_passed"), sum(out.values()), "POLYGLOT_SUM_MISMATCH")
    return out


def _swarm_proof(result, *, mode, count, groups, worker_cap):
    if not isinstance(result, dict) or result.get("kind") != "ISOLATED_OFFLINE_SWARM_NOT_NATIVE":
        raise EvidenceError("SWARM_PROVENANCE_INVALID")
    if result.get("status") != "PASS" or result.get("mode") != mode:
        raise EvidenceError("SWARM_NOT_PASS")
    for key, expected in (("selected_roles", count), ("group_count", groups),
                          ("effective_worker_cap", worker_cap),
                          ("external_model_calls", 0),
                          ("external_provider_calls", 0), ("production_changes", 0)):
        _assert_int(result.get(key), expected, "SWARM_FIELDS_MISMATCH")
    if result.get("independent_serial_oracle_match") is not True:
        raise EvidenceError("SWARM_ORACLE_MISMATCH")
    if result.get("status_counts") != {"PASS": count}:
        raise EvidenceError("SWARM_RESULT_COUNTS_INVALID")
    if result.get("native_chatgpt_run_verified") is not False:
        raise EvidenceError("FORGED_NATIVE_ATTESTATION")
    if result.get("same_run_github_slack_proven") is not False:
        raise EvidenceError("FORGED_SAME_RUN_PROOF")
    if result.get("original_v81_source_deployed") is not False:
        raise EvidenceError("FORGED_ORIGINAL_SOURCE_CLAIM")
    sha = result.get("input_sha256")
    if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{64}", sha) is None:
        raise EvidenceError("SWARM_INPUT_HASH_INVALID")
    return sha


def combine(proof, c_output, audit, full, source_hashes, *, fixture_rows,
            runner_env=None):
    """Pure fail-closed aggregator; NEVER asserts platform authentication."""
    counts = _receipt_proof(proof)
    if type(fixture_rows) is not int or fixture_rows <= 0:
        raise EvidenceError("C_FIXTURE_EMPTY")
    if not isinstance(c_output, str):
        raise EvidenceError("C_ORACLE_OUTPUT_MISSING")
    expected = f"C strict timestamp oracle: PASS {fixture_rows}/{fixture_rows}\n"
    if c_output != expected:
        raise EvidenceError("C_ORACLE_MISMATCH")
    if not isinstance(source_hashes, dict) or set(source_hashes) != set(SOURCE_FILES):
        raise EvidenceError("SOURCE_HASH_SET_INCOMPLETE")
    if any(not isinstance(sha, str) or re.fullmatch(r"[a-f0-9]{64}", sha) is None
           for sha in source_hashes.values()):
        raise EvidenceError("SOURCE_HASH_MALFORMED")
    fast_sha = _swarm_proof(audit, mode="audit", count=20, groups=2, worker_cap=2)
    full_sha = _swarm_proof(full, mode="all", count=100, groups=10, worker_cap=4)
    if fast_sha != full_sha:
        raise EvidenceError("FAST_FULL_INPUT_MISMATCH")
    all_counts = {**counts, "c": fixture_rows}
    if runner_env is None:
        runner_env = {}
    if not isinstance(runner_env, dict):
        raise EvidenceError("RUNNER_CONTEXT_MALFORMED")
    # The CI env belongs to the local runner; independent GitHub API is still needed.
    context = {key: runner_env.get(key) for key in
               ("github_run_id", "github_sha", "github_event")}
    if any(v is not None and
           (not isinstance(v, str) or len(v) > 128 or
            re.fullmatch(r"[A-Za-z0-9._/-]+", v) is None)
           for v in context.values()):
        raise EvidenceError("RUNNER_CONTEXT_UNSAFE")
    transcript = {
        "format": "V81_OFFLINE_UNIFIED_EVIDENCE_V1",
        "status": "PASS", "scope": "ISOLATED_LOCAL_OFFLINE_NOT_NATIVE_PLATFORM",
        "languages": all_counts, "language_total": sum(all_counts.values()),
        "local_swarm": {"fast_pass": 20, "full_pass": 100,
                        "groups": 10, "worker_cap": 4,
                        "independent_serial_oracle_match": True,
                        "input_sha256": fast_sha},
        "source_sha256": dict(sorted(source_hashes.items())),
        "runner_context_self_reported": context,
        "runner_context_officially_authenticated": False,
        "github_api_run_verified": False, "native_chatgpt_run_verified": False,
        "same_run_github_slack_proven": False,
        "real_external_llm_agents": 0, "external_model_calls": 0,
        "production_changes": 0,
    }
    canonical = json.dumps(transcript, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    transcript["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    return transcript


def build(root=ROOT):
    # Existing v6 receipt already independently checks input hashes and freshness.
    proof, reason = runner.read_runtime_receipt()
    if proof is None:
        raise EvidenceError("POLYGLOT_RECEIPT_INVALID_OR_STALE")
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf8"))
    evidence = json.loads((root / "evidence.json").read_text(encoding="utf8"))
    audit = v81_swarm.collaborate(catalog, evidence, "audit", 4)
    full = v81_swarm.collaborate(catalog, evidence, "all", 4)
    fixture = (root / "utc_strict_oracle_cases.tsv").read_text(encoding="utf8")
    lines = fixture.splitlines()
    if not lines or lines[0] != "value\texpected":
        raise EvidenceError("C_FIXTURE_INVALID_HEADER")
    result = combine(
        proof, run_c11(root), audit, full, _source_hashes(root),
        fixture_rows=len(lines) - 1,
        runner_env={
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_event": os.environ.get("GITHUB_EVENT_NAME"),
        },
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="offline SHA-bound evidence coordinator")
    parser.add_argument("--output", default=None,
                        help="local JSON receipt destination, ideally RUNNER_TEMP")
    args = parser.parse_args()
    try:
        result = build()
    except (EvidenceError, OSError, ValueError, TypeError, KeyError, OverflowError):
        result = {
            "format": "V81_OFFLINE_UNIFIED_EVIDENCE_V1",
            "status": "BLOCKED", "reason": "LOCAL_EVIDENCE_MISSING_OR_MISMATCH",
            "native_chatgpt_run_verified": False, "github_api_run_verified": False,
            "external_model_calls": 0, "production_changes": 0,
        }
    encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False)
    if args.output:
        try:
            Path(args.output).write_text(encoded + "\n", encoding="utf8")
        except (OSError, ValueError):
            result["status"] = "BLOCKED"
            result["reason"] = "LOCAL_RECEIPT_WRITE_FAILED"
            encoded = json.dumps(result, ensure_ascii=False, sort_keys=True)
    print("R16_V81_UNIFIED_EVIDENCE=" + encoded)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

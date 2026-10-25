#!/usr/bin/env python3
"""Public, fail-closed v8.1 source fingerprint comparison; NO original source upload.

Original fingerprints were measured locally from the user's v8.1 ZIP. The ZIP
itself and its private fixtures are NOT present or executable in this CI.
'EXACT' means byte-identical mapped file, NOT end-to-end semantic parity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCAL_V81_ZIP_SHA256 = "8c06d103af54d119c31ed927e0266a6d15dab4d9e24036cd2974e9b76739035a"
# Local source ZIP: AI_R16_100_BOT_v8/<filename>.
# Mapping is intentionally limited to files in the existing isolated branch.
ORIGINAL_SHA256 = {
    "runner.py": "268e887aeeb82576f45735a18ba0abe7cb74720ec835f5bdf2df28a5ea8ed109",
    "replacement_bots.py": "0974d8833c486eb8e91348b8622d6817dd87d0d40f0cca1a3f36e151711fc620",
    "catalog.json": "5ec2ff7e7dd511c9ab77c12540f5916e327df7652e4bd4543331b577fb16f188",
    "evidence.json": "1e4417c65b6c2d9e3ba9ae480071a08c6935c376ce5a877bb12d921c011341b2",
    "fixture_SYNTHETIC.json": "b93079c6b20a349b59e60c00e3cc7e87829673c67e00cfa1fe8fa1473a7b3a3f",
    "measure_runtime.py": "7c577d82146108a4c8b7bef8260dcc9ee824441ec99f4c2ea07b07279ad78e4e",
    "UtcStrictOracle.java": "ac649fffca107b287221d474d7234bff9047f221e794fbd7842fc600bcbce09a",
    "utc_strict_oracle.js": "dfba42e7fd8fe43bd3d09b4072b548c799a19706f29196b508fa9c9a4cd66b4f",
    "utc_strict_oracle_cases.tsv": "70875aed3a2c6bac72d63df07af9716876e9f91a912bb57a69d4c3dbc6f9e781",
    "test_runtime.py": "e17702c624115305f9aad360dcc237b7e6d3364867f449f2de6bf234a770260e",
}
# Exact source bytes are not automatically provided to this public runner.
assert len(ORIGINAL_SHA256) == 10
assert all(len(x) == 64 and set(x) <= set("0123456789abcdef") for x in ORIGINAL_SHA256.values())

# Record reviewed isolated-branch differences; the original ZIP is unavailable
# on public CI. A hardening disposition never implies source byte equality.
# Missing files always remain unresolved, even if a previous version was reviewed.
REVIEWED_DIFFERENCES = {
    "runner.py": {
        "disposition": "KEEP_BRANCH_HARDENING",
        "reason": "isolated branch retains strict RRULE validation and avoids absent private replacement dependencies",
    },
    "test_runtime.py": {
        "disposition": "KEEP_BRANCH_HARDENING",
        "reason": "isolated branch removes an absent legacy-native file dependency and adds strict RRULE negative coverage while retaining fail-closed native gates",
    },
    "utc_strict_oracle.js": {
        "disposition": "KEEP_BRANCH_HARDENING",
        "reason": "isolated branch resolves the fixture beside the script and rejects empty, malformed, or invalid-result rows fail-closed",
    },
    "measure_runtime.py": {
        "disposition": "KEEP_BRANCH_HARDENING",
        "reason": "pin trusted Java fixture by absolute path and run from isolated cwd; original hash remains DIFFERENT",
    },
    "UtcStrictOracle.java": {
        "disposition": "KEEP_BRANCH_HARDENING",
        "reason": "isolated branch accepts an explicit fixture path and rejects invalid headers and result labels fail-closed",
    },
}
assert set(REVIEWED_DIFFERENCES) <= set(ORIGINAL_SHA256)


def compare(root: Path = ROOT) -> dict:
    rows = {}
    for filename, original_hash in ORIGINAL_SHA256.items():
        file = root / filename
        if file.is_symlink():
            raise ValueError("source path must not be symlink: " + filename)
        if not file.is_file():
            rows[filename] = {"status": "ABSENT", "source_sha256": original_hash, "branch_sha256": None}
            continue
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        rows[filename] = {
            "status": "EXACT" if digest == original_hash else "DIFFERENT",
            "source_sha256": original_hash,
            "branch_sha256": digest,
        }
    counts = {key: sum(row["status"] == key for row in rows.values())
              for key in ("EXACT", "DIFFERENT", "ABSENT")}
    exact = counts["EXACT"] == len(ORIGINAL_SHA256)
    reviewed = {
        filename: REVIEWED_DIFFERENCES[filename]
        for filename, row in rows.items()
        if row["status"] == "DIFFERENT" and filename in REVIEWED_DIFFERENCES
    }
    unresolved = sorted(
        filename for filename, row in rows.items()
        if row["status"] != "EXACT" and filename not in reviewed
    )
    return {
        "kind": "OFFLINE_SOURCE_SHA_COMPARISON_NOT_NATIVE_PLATFORM_EVIDENCE",
        "local_original_zip_sha256": LOCAL_V81_ZIP_SHA256,
        "local_original_archive_available_on_runner": False,
        "file_count": len(rows),
        "counts": counts,
        "reviewed_differences": reviewed,
        "reviewed_difference_count": len(reviewed),
        "unresolved_difference_count": len(unresolved),
        "unresolved_difference_files": unresolved,
        "verbatim_source_match": exact,
        "full_v81_deployed": False,
        "external_llm_calls": 0,
        "native_chatgpt_scheduled_calls_verified": False,
        "report_status": "EXACT_FILES_ONLY_NOT_FULL_RUNTIME_PARITY" if exact else "PARTIAL_NOT_VERBATIM",
        "files": rows,
    }


def require_verbatim(report: dict) -> None:
    if not report.get("verbatim_source_match"):
        raise ValueError("fail-closed: local original v8.1 files differ or are absent")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--require-verbatim", action="store_true", help="fail if any original file differs or is absent")
    a = p.parse_args()
    result = compare()
    print("R16_V81_SOURCE_PARITY=" + json.dumps(result, sort_keys=True, ensure_ascii=False))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf8") as f:
            f.write("\n## v8.1 original ZIP vs isolated branch SHA fingerprints\n")
            f.write("Original archive itself is not available on this public runner.\n\n")
            f.write("| Byte comparison | Count |\n|---|---:|\n")
            for key, count in result["counts"].items():
                f.write(f"| {key} | {count} |\n")
            f.write("\nNo original source or private fixture was uploaded to this public repo.\n")
    if a.require_verbatim:
        try:
            require_verbatim(result)
        except ValueError as exc:
            print(str(exc))
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

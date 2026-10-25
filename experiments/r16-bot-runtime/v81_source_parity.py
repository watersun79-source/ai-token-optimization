#!/usr/bin/env python3
"""Public, fail-closed v8.1 source fingerprint comparison; NO original source upload.

Original fingerprints were measured locally from the user's v8.1 ZIP. The ZIP
itself and its private fixtures are NOT present or executable in this CI.
'EXACT' means byte-identical mapped file, NOT end-to-end semantic parity.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import stat
import zipfile
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
    "catalog.json": {
        "disposition": "KEEP_BRANCH_HARDENING",
        "reason": "private v8.1 ZIP SHA-256 verified locally 2026-10-25; of 100 rule fingerprints 79 unchanged and 21 hardened: S04-S06 strict RRULE, L06-L10/A07-A09/E01-E10 native-evidence fail-closed; original bytes remain private; not verbatim",
    },
    "fixture_SYNTHETIC.json": {
        "disposition": "KEEP_BRANCH_HARDENING",
        "reason": "public fabricated fixture generated from adapter sample only, distinct from private ZIP bytes; 18 synthetic checks and no native provider attestation",
    },
    "replacement_bots.py": {
        "disposition": "KEEP_BRANCH_HARDENING",
        "reason": "private v8.1 ZIP fingerprint and original offline 18/18 sample verified; public synthetic-only facade delegates 18 checks to v81_split_bench with untrusted provenance always UNVERIFIED; not verbatim and original source never uploaded",
    },
    "UtcStrictOracle.java": {
        "disposition": "KEEP_BRANCH_HARDENING",
        "reason": "isolated branch accepts an explicit fixture path and rejects invalid headers and result labels fail-closed",
    },
}
assert set(REVIEWED_DIFFERENCES) <= set(ORIGINAL_SHA256)


def verify_private_zip_local(path: Path, *, expected_zip_sha256: str = LOCAL_V81_ZIP_SHA256,
                             expected_hashes: dict | None = None) -> dict:
    """Validate a *local-only* archive without extraction, execution or publication.

    Overrideable fingerprints are for synthetic offline tests only; CLI fixes
    both expected values to the independently measured private fingerprints.
    """
    hashes = ORIGINAL_SHA256 if expected_hashes is None else expected_hashes
    if (not isinstance(expected_zip_sha256, str) or
        len(expected_zip_sha256) != 64 or
        any(c not in "0123456789abcdef" for c in expected_zip_sha256) or
        not isinstance(hashes, dict) or not hashes or
        any(not isinstance(k, str) or "/" in k or "\\" in k or
            k in ("", ".", "..") or not isinstance(v, str) or
            len(v) != 64 or any(c not in "0123456789abcdef" for c in v)
            for k, v in hashes.items())):
        raise ValueError("INVALID_EXPECTED_FINGERPRINTS")
    if not isinstance(path, Path):
        raise ValueError("INVALID_LOCAL_PATH")
    # Open once: the bytes authenticated by SHA must be the exact bytes parsed
    # by ZipFile. Reopening a mutable path here creates a TOCTOU integrity gap.
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    elif path.is_symlink():  # Best-effort fallback on platforms without O_NOFOLLOW.
        raise ValueError("PRIVATE_ZIP_NOT_REGULAR_FILE")
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise ValueError("PRIVATE_ZIP_NOT_REGULAR_FILE") from None
    with os.fdopen(descriptor, "rb") as stream:
        meta = os.fstat(stream.fileno())
        if not stat.S_ISREG(meta.st_mode):
            raise ValueError("PRIVATE_ZIP_NOT_REGULAR_FILE")
        if not 0 < meta.st_size <= 32 * 1024 * 1024:
            raise ValueError("PRIVATE_ZIP_SIZE_LIMIT")
        # Bounded immutable snapshot prevents path swaps and in-place writes
        # from changing the ZIP data after its SHA has been authenticated.
        archive_bytes = stream.read(32 * 1024 * 1024 + 1)
        if len(archive_bytes) != meta.st_size:
            raise ValueError("PRIVATE_ZIP_CHANGED_DURING_READ")
    if hashlib.sha256(archive_bytes).hexdigest() != expected_zip_sha256:
        raise ValueError("PRIVATE_ZIP_SHA256_MISMATCH")

    prefix = "AI_R16_100_BOT_v8/"
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        infos = archive.infolist()
        if not 0 < len(infos) <= 256:
            raise ValueError("PRIVATE_ZIP_ENTRY_LIMIT")
        seen = set()
        total_size = 0
        for entry in infos:
            name = entry.filename
            parts = name.split("/")
            if (not name or "\\" in name or name.startswith("/") or
                any(part in ("", ".", "..") for part in parts[:-1]) or
                (parts[-1] in ("", ".", "..") and not entry.is_dir()) or
                name in seen or entry.flag_bits & 1 or
                (entry.create_system == 3 and
                 stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFLNK)):
                raise ValueError("PRIVATE_ZIP_UNSAFE_ENTRY")
            seen.add(name)
            if entry.file_size > 4 * 1024 * 1024 or entry.file_size < 0:
                raise ValueError("PRIVATE_ZIP_MEMBER_SIZE_LIMIT")
            total_size += entry.file_size
            if total_size > 64 * 1024 * 1024:
                raise ValueError("PRIVATE_ZIP_TOTAL_SIZE_LIMIT")
        for filename, expected_hash in hashes.items():
            path_in_zip = prefix + filename
            if path_in_zip not in seen:
                raise ValueError("PRIVATE_ZIP_EXPECTED_FILE_MISSING")
            entry = archive.getinfo(path_in_zip)
            if entry.is_dir():
                raise ValueError("PRIVATE_ZIP_EXPECTED_FILE_INVALID")
            digest = hashlib.sha256()
            total = 0
            with archive.open(entry, "r") as member:
                for chunk in iter(lambda: member.read(65536), b""):
                    total += len(chunk)
                    if total > 4 * 1024 * 1024:
                        raise ValueError("PRIVATE_ZIP_MEMBER_SIZE_LIMIT")
                    digest.update(chunk)
            if digest.hexdigest() != expected_hash:
                raise ValueError("PRIVATE_ZIP_MEMBER_SHA256_MISMATCH")
    return {
        "kind": "PRIVATE_ORIGINAL_ZIP_LOCAL_FINGERPRINT_CHECK_NOT_DEPLOYMENT",
        "status": "PASS",
        "archive_sha256_verified": True,
        "member_sha256_verified": len(hashes),
        "private_bytes_published": False,
        "extracted_or_executed": False,
        "native_chatgpt_run_verified": False,
        "full_v81_deployed": False,
    }


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
    p.add_argument("--verify-private-zip-local", type=Path, default=None,
                   help="LOCAL DEVICE ONLY: validate trusted original ZIP; never use in public CI")
    a = p.parse_args()
    if a.verify_private_zip_local is not None:
        try:
            local_report = verify_private_zip_local(a.verify_private_zip_local)
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile):
            print("R16_V81_PRIVATE_ZIP_LOCAL_CHECK=" +
                  json.dumps({"status": "UNVERIFIED", "reason": "PRIVATE_ZIP_VALIDATION_FAILED",
                              "private_bytes_published": False,
                              "native_chatgpt_run_verified": False}))
            return 2
        print("R16_V81_PRIVATE_ZIP_LOCAL_CHECK=" + json.dumps(local_report, sort_keys=True))
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

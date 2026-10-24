#!/usr/bin/env python3
"""Independent, privacy-preserving original v8.1 / isolated 100-role OUTPUT contract.

Expected digests were calculated by running the user's original v8.1 ZIP in a
private local workspace. Only hashes of ten groups of sanitized JSON result
records are committed; original ZIP, fixture and private inputs are NOT
uploaded. A matching digest proves output-byte equivalence on one OFFLINE
fixture, NOT program equivalence, CI deployment or native ChatGPT app calls.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys

import v81_split_bench as adapter

ROOT = Path(__file__).resolve().parent
PRIVATE_ORIGINAL_ARCHIVE_SHA256 = "8c06d103af54d119c31ed927e0266a6d15dab4d9e24036cd2974e9b76739035a"
ORIGINAL_GROUP_SHA256 = {
    "S": "38e010ff6fabf63f68346c7866f726beb802444672878244abe873883ba4cc92",
    "G": "40484851e3a1081a8002a70f63edfb18826fdc67f8dcb03101d15c1b27aa8b91",
    "P": "5824f51b96251bef271be004f88b914e5314bb313b8e32936bb154653f9a0aa9",
    "L": "279d83069e7283fc88db88041f5a59d7c45e26cadb5a315ca2d9fcc0ab1f5c73",
    "A": "b5622b8dd937fe19c82f55950ff1c1310fc3422aa55bd4b7245e4899b2eccc10",
    "O": "8ab66712f811d930417cea3f8cfa1a663b80ba73363007c60e3d27f4e33c4bad",
    "C": "7f29288484fc843f6892a1fb9a840866881a46fcc82a7966e486a6106d0866b6",
    "M": "f61c8670ada6e78a7190100280cd5cff26e37ad4158f43a1d40f290b8135e002",
    "T": "c7d36024834bd1a8d0751e626936c6d878cf49a659e727a5a864536d9b32c5a8",
    "E": "af01edaf75a357e380e028b7d7c9112143144e36b96234f0e4bb60e0bbf67802",
}
ORIGINAL_ALL_SHA256 = "613955ada746d4f8e5a0fa06b1361d51f35206953ae3c3949c4555016450fa09"
SCOPE_ROLES = adapter.REPLACEMENTS | {f"M{i:02}" for i in range(1, 5)}
BASE_KEYS = {"id", "category", "name", "source", "status", "detail"}
assert len(ORIGINAL_GROUP_SHA256) == 10

def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf8")
    return hashlib.sha256(encoded).hexdigest()

def compare_results(output):
    """Fail closed for missing/misleading records, but report honest digest gaps."""
    if output.get("mode") != "all" or output.get("kind") != "ISOLATED_V81_COMPATIBILITY_ADAPTER_NOT_NATIVE":
        raise ValueError("unexpected adapter identity")
    if output.get("native_chatgpt_run_proven") is not False or output.get("same_run_github_slack_proven") is not False or output.get("production_deployed") is not False:
        raise ValueError("native provider attestation cannot come from synthetic input")
    if output.get("executed_independent_llms") != 0:
        raise ValueError("independent LLM count falsely attested")
    rows = output.get("details")
    if not isinstance(rows, list) or len(rows) != 100:
        raise ValueError("expected 100 distinct local results")
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if len(ids) != 100 or set(ids) != adapter.IDS or len(set(ids)) != 100:
        raise ValueError("missing or duplicate role identifiers")
    if output.get("selected_count") != 100 or output.get("statuses") != {"PASS": 100}:
        raise ValueError("adapter did not pass the full offline synthetic baseline")
    for row in rows:
        req = BASE_KEYS | ({"scope"} if row["id"] in SCOPE_ROLES else set())
        if set(row) != req:
            raise ValueError("role "+row["id"]+" field schema mismatch: "+str(sorted(set(row)^req)))
        if row["status"] != "PASS" or not all(isinstance(row.get(k), str) and row[k] for k in ("category","name","source","detail")):
            raise ValueError("invalid role output: "+row["id"])
        if row["id"] in adapter.REPLACEMENTS:
            if row["scope"] != "LOCAL_FIXTURE_ONLY" or row["source"] != "SYNTHETIC_LOCAL_FIXTURE_NOT_PROVIDER_EVIDENCE":
                raise ValueError("synthetic record falsely attributed")
    grouped = {}
    for prefix, expected_hash in ORIGINAL_GROUP_SHA256.items():
        group = sorted((row for row in rows if row["id"][0] == prefix), key=lambda row: row["id"])
        if len(group) != 10:
            raise ValueError("missing ten roles in "+prefix)
        measured = digest(group)
        grouped[prefix] = {"count": 10, "exact_on_offline_fixture": measured == expected_hash,
                           "github_adapter_sha256": measured}
    actual_all = digest(sorted(rows, key=lambda row: row["id"]))
    num_exact = sum(x["exact_on_offline_fixture"] for x in grouped.values())
    return {
        "kind": "ISOLATED_100_ROLE_OUTPUT_CONTRACT_NOT_NATIVE_PROVIDER",
        "original_zip_sha256_measured_private": PRIVATE_ORIGINAL_ARCHIVE_SHA256,
        "private_original_archive_present_in_ci": False,
        "matched_groups": num_exact,
        "groups_total": 10,
        "matched_role_groups": num_exact * 10,
        "adapter_output_total": 100,
        "record_field_schemas_exact": 100,
        "original_output_digest_exact": actual_all == ORIGINAL_ALL_SHA256,
        "offline_fixture_only": True,
        "full_source_byte_identity": False,
        "native_chatgpt_scheduler_verified": False,
        "paid_external_model_calls": 0,
        "groups": grouped,
    }

def run():
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf8"))
    evidence = json.loads((ROOT / "evidence.json").read_text(encoding="utf8"))
    report = compare_results(adapter.execute(catalog, evidence, "all"))
    print("R16_V81_100_ROLE_OUTPUT_PARITY="+json.dumps(report,sort_keys=True))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf8") as f:
            f.write("\n## 100-role output schema and digests (offline fixture only)\n\n")
            f.write(f"- Record schemas: {report['record_field_schemas_exact']}/100\n")
            f.write(f"- Full content match: {report['matched_role_groups']}/100 grouped roles\n")
            f.write(f"- Native ChatGPT app-call proof: UNVERIFIED\n")
    return report

if __name__ == "__main__":
    out=run()
    # A mismatch is recorded as partial, not a false success. Shape/provenance
    # violations raise and make the isolated CI fail.
    sys.exit(0)

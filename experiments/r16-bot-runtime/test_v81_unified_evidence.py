"""Fail-closed tests for the unified four-language, 100-rule offline receipt."""
import copy
import hashlib
import json
import re
import unittest
from unittest.mock import patch

import v81_unified_evidence as ev


class UnifiedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = {
            "format": "LOCAL_TEST_RECEIPT_V6",
            "counts": {k: {"passed": n, "total": n}
                       for k, n in (("python", 23), ("java", 20), ("js", 20))},
            "total_passed": 63,
        }
        cls.hashes = {name: hashlib.sha256(name.encode()).hexdigest()
                      for name in ev.SOURCE_FILES}
        cls.fast = dict(
            kind="ISOLATED_OFFLINE_SWARM_NOT_NATIVE", status="PASS",
            mode="audit", selected_roles=20, group_count=2,
            effective_worker_cap=2, external_model_calls=0,
            external_provider_calls=0, production_changes=0,
            independent_serial_oracle_match=True, status_counts={"PASS": 20},
            native_chatgpt_run_verified=False, same_run_github_slack_proven=False,
            original_v81_source_deployed=False, input_sha256="a" * 64,
        )
        cls.full = {**cls.fast, "mode": "all", "selected_roles": 100,
                    "group_count": 10, "effective_worker_cap": 4,
                    "status_counts": {"PASS": 100}}

    def aggregate(self, **update):
        values = dict(proof=copy.deepcopy(self.proof),
                      c_output="C strict timestamp oracle: PASS 20/20\n",
                      audit=copy.deepcopy(self.fast), full=copy.deepcopy(self.full),
                      source_hashes=dict(self.hashes), fixture_rows=20,
                      runner_env={"github_run_id": "40150000001",
                                  "github_sha": "e" * 40,
                                  "github_event": "push"})
        values.update(update)
        return ev.combine(**values)

    def test_normal_83_language_checks_and_100_rule_swarm(self):
        result = self.aggregate()
        self.assertEqual("PASS", result["status"])
        self.assertEqual(83, result["language_total"])
        self.assertEqual({"python": 23, "java": 20, "js": 20, "c": 20},
                         result["languages"])
        self.assertEqual(100, result["local_swarm"]["full_pass"])
        self.assertEqual(4, result["local_swarm"]["worker_cap"])
        self.assertRegex(result["evidence_sha256"], r"^[0-9a-f]{64}$")

    def test_stable_sha_is_content_hash_not_runner_authentication(self):
        a = self.aggregate()
        b = self.aggregate()
        self.assertEqual(a["evidence_sha256"], b["evidence_sha256"])
        self.assertFalse(a["runner_context_officially_authenticated"])
        self.assertFalse(a["github_api_run_verified"])
        self.assertFalse(a["native_chatgpt_run_verified"])
        self.assertFalse(a["same_run_github_slack_proven"])
        self.assertEqual(0, a["real_external_llm_agents"])

    def test_negative_in_one_language_rejects_all(self):
        for lang in ("python", "java", "js"):
            proof = copy.deepcopy(self.proof)
            proof["counts"][lang]["passed"] -= 1
            with self.subTest(lang=lang), self.assertRaises(ev.EvidenceError):
                self.aggregate(proof=proof)
        with self.assertRaises(ev.EvidenceError):
            self.aggregate(c_output="C strict timestamp oracle: PASS 19/20\n")

    def test_fake_totals_rejected(self):
        for n in (False, 83, 63.0, None):
            proof = copy.deepcopy(self.proof)
            proof["total_passed"] = n
            if n == 63.0:
                # Equality alone would incorrectly accept float as an int.
                pass
            with self.subTest(n=n), self.assertRaises(ev.EvidenceError):
                self.aggregate(proof=proof)

    def test_undocumented_synthetic_native_success_is_rejected(self):
        for field in ("native_chatgpt_run_verified",
                      "same_run_github_slack_proven",
                      "original_v81_source_deployed"):
            fast = copy.deepcopy(self.fast)
            fast[field] = True
            with self.subTest(field=field), self.assertRaises(ev.EvidenceError):
                self.aggregate(audit=fast)

    def test_one_failed_or_missing_rule_blocks(self):
        for value in ("FAIL", "UNVERIFIED", "BLOCKED"):
            full = copy.deepcopy(self.full)
            full["status"] = value
            with self.subTest(value=value), self.assertRaises(ev.EvidenceError):
                self.aggregate(full=full)
        full = copy.deepcopy(self.full)
        full["status_counts"] = {"PASS": 99, "UNVERIFIED": 1}
        with self.assertRaises(ev.EvidenceError):
            self.aggregate(full=full)

    def test_serial_oracle_mismatch_blocks(self):
        bad = copy.deepcopy(self.full)
        bad["independent_serial_oracle_match"] = False
        with self.assertRaises(ev.EvidenceError):
            self.aggregate(full=bad)

    def test_fast_full_input_mismatch_blocks(self):
        full = copy.deepcopy(self.full)
        full["input_sha256"] = "b" * 64
        with self.assertRaises(ev.EvidenceError):
            self.aggregate(full=full)

    def test_nonzero_external_model_or_write_is_rejected(self):
        for field in ("external_model_calls", "external_provider_calls",
                      "production_changes"):
            full = copy.deepcopy(self.full)
            full[field] = 1
            with self.subTest(field=field), self.assertRaises(ev.EvidenceError):
                self.aggregate(full=full)

    def test_hash_tampering_and_spoofed_bool_blocked(self):
        tampered = dict(self.hashes)
        tampered["utc_strict_oracle.c"] = "not-sha"
        with self.assertRaises(ev.EvidenceError):
            self.aggregate(source_hashes=tampered)
        full = copy.deepcopy(self.full)
        full["selected_roles"] = True
        with self.assertRaises(ev.EvidenceError):
            self.aggregate(full=full)

    def test_extra_runner_env_rejected_but_no_native_proof(self):
        with self.assertRaises(ev.EvidenceError):
            self.aggregate(runner_env={"github_run_id": "token=secret value"})
        record = self.aggregate(runner_env={"github_event": "schedule"})
        self.assertFalse(record["github_api_run_verified"])

    def test_missing_or_failed_c_binary_blocks(self):
        with patch.object(ev, "_run", side_effect=ev.EvidenceError("failed")):
            with self.assertRaises(ev.EvidenceError):
                ev.run_c11()

    def test_source_file_catalog_is_fixed_and_local(self):
        self.assertEqual(len(ev.SOURCE_FILES), len(set(ev.SOURCE_FILES)))
        self.assertTrue(all("/" not in name and ".." not in name
                            for name in ev.SOURCE_FILES))


if __name__ == "__main__":
    unittest.main()

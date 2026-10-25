"""Synthetic-only bridge regressions. No original archive or credentials."""
import copy
import unittest

import replacement_bots as bridge
import v81_split_bench as adapter


class ReplacementBridgeTests(unittest.TestCase):
    def test_expected_18_roles_match_existing_adapter(self):
        self.assertEqual(18, len(bridge.BOT_CHECKS))
        self.assertEqual(set(adapter.REPLACEMENTS), set(bridge.BOT_CHECKS))
        self.assertEqual(adapter.ORIGINAL_REPLACEMENT_NAMES, bridge.REPLACEMENTS)

    def test_baseline_local_18_checks_run(self):
        sample = adapter.sample_fixture()
        self.assertEqual(
            {name: "LOCAL_PASS" for name in bridge.BOT_CHECKS},
            bridge.check_all(sample),
        )
        self.assertEqual("UNVERIFIED", bridge.classify_provenance(sample["runs"][0]))

    def test_live_looking_or_untrusted_input_never_claims_success(self):
        cases = [None, {}, {"source": "provider_verified"},
                 {"source": "synthetic_fixture", "runs": []},
                 {"source": "synthetic_fixture", "runs": "not-a-list"}]
        mismatched_run = adapter.sample_fixture()
        mismatched_run["runs"][0]["source"] = "provider_verified"
        cases.append(mismatched_run)
        wrong_root = adapter.sample_fixture()
        wrong_root["source"] = "provider_verified"
        cases.append(wrong_root)
        for sample in cases:
            with self.subTest(input_type=type(sample).__name__):
                self.assertEqual(
                    {"UNVERIFIED"}, set(bridge.check_all(sample).values())
                )

    def test_synthetic_secret_and_forged_attestation_fail(self):
        sample = adapter.sample_fixture()
        sample["slack"]["messages"][0]["text"] = "token=FAKE_TEST_ONLY"
        sample["runs"][0]["_externally_attested"] = True
        outcome = bridge.check_all(sample)
        self.assertEqual("FAIL", outcome["L10"])
        self.assertEqual("FAIL", outcome["E10"])
        self.assertEqual("UNVERIFIED", bridge.classify_provenance(
            {"_externally_attested": True}
        ))

    def test_public_fixture_file_matches_safe_generator(self):
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parent / "fixture_SYNTHETIC.json"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(adapter.sample_fixture(), loaded)
        self.assertEqual("C0000000000", loaded["slack"]["messages"][0]["channel"])
        self.assertEqual("synthetic_fixture", loaded["source"])
        self.assertEqual("synthetic_fixture", loaded["runs"][0]["source"])
        self.assertEqual({"LOCAL_PASS"}, set(bridge.check_all(loaded).values()))
        self.assertEqual("UNVERIFIED", bridge.classify_provenance(loaded["runs"][0]))

    def test_malformed_synthetic_field_stays_unverified(self):
        sample = adapter.sample_fixture()
        sample["runs"][0].pop("raw_log")
        self.assertEqual("UNVERIFIED", bridge.check_all(sample)["E08"])


if __name__ == "__main__":
    unittest.main()

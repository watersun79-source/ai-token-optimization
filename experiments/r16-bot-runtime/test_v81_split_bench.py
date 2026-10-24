"""Isolated negative tests for the v8.1 fast/full adapter; no network/API calls."""
import copy
import json
from pathlib import Path
import unittest

import runner
import v81_split_bench as b

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / "catalog.json").read_text(encoding="utf8"))
EVIDENCE = json.loads((ROOT / "evidence.json").read_text(encoding="utf8"))
CAT = {x["id"]: x for x in CATALOG}


class SplitBenchTests(unittest.TestCase):
    def test_role_catalog_unique_100(self):
        self.assertEqual(100, len(CATALOG))
        self.assertEqual(b.IDS, set(CAT))
        self.assertEqual(18, len(b.REPLACEMENTS))

    def test_fast_audit_exactly_20(self):
        out = b.execute(CATALOG, EVIDENCE, "audit")
        self.assertEqual(20, out["selected_count"])
        self.assertEqual(10, out["replacements_total"])
        self.assertEqual(set("SE"), {r["id"][0] for r in out["details"]})
        self.assertEqual({"PASS": 20}, out["statuses"])

    def test_full_100_roles_all_selected(self):
        out = b.execute(CATALOG, EVIDENCE, "all")
        self.assertEqual(100, out["selected_count"])
        self.assertEqual(18, out["replacements_total"])
        self.assertEqual(set(b.IDS), {r["id"] for r in out["details"]})

    def test_all_replacement_18_positive(self):
        fixture = b.sample_fixture()
        self.assertEqual(18, len(b.CHECKS))
        self.assertTrue(all(fn(fixture) for fn in b.CHECKS.values()))

    def test_all_replacement_18_negative(self):
        breakers = {
            "L06": lambda x: x["slack"]["messages"][0].pop("text"),
            "L07": lambda x: x["slack"]["messages"][0].update(ts="bad"),
            "L08": lambda x: x["slack"]["messages"][0].update(thread_ts="9999999999.123456"),
            "L09": lambda x: x["slack"]["messages"][0].update(text="A" * 40001),
            "L10": lambda x: x["slack"]["messages"][0].update(text="API_KEY=FAKE_EXAMPLE_ONLY"),
            "A07": lambda x: x["activepieces"]["nodes"].append({"id": "process", "next": []}),
            "A08": lambda x: x["activepieces"]["nodes"][0].update(next=["bad-node"]),
            "A09": lambda x: x["activepieces"]["nodes"][1].update(next=["trigger"]),
            "E01": lambda x: x.update(schema_version="wrong"),
            "E02": lambda x: x["runs"].append(copy.deepcopy(x["runs"][0])),
            "E03": lambda x: x["runs"][0].update(started_at="2026-10-24T08:00:03"),
            "E04": lambda x: x["runs"][0].update(ended_at="2026-10-24T08:00:01+09:00"),
            "E05": lambda x: x["runs"][0].update(started_at="2026-10-24T09:00:03+09:00"),
            "E06": lambda x: x["runs"][0]["events"].append(
                {"at": "2026-10-24T08:00:04+09:00", "level": "INFO", "type": "out-of-order"}),
            "E07": lambda x: x["runs"][0]["events"][0].update(level="ALL_OK"),
            "E08": lambda x: x["runs"][0].update(raw_log="modified"),
            "E09": lambda x: x["runs"][0].update(artifact_path="../escape.json"),
            "E10": lambda x: x["runs"][0].update(_externally_attested=True),
        }
        self.assertEqual(set(b.REPLACEMENTS), set(breakers))
        for name, break_it in breakers.items():
            with self.subTest(name=name):
                fixture = b.sample_fixture()
                break_it(fixture)
                try:
                    accepted = b.CHECKS[name](fixture)
                except (ValueError, TypeError, KeyError, AssertionError, AttributeError):
                    accepted = False
                self.assertFalse(accepted)

    def test_legacy_native_is_still_unverified(self):
        self.assertEqual("UNVERIFIED", runner.validate(CAT["E10"], EVIDENCE)["status"])
        out = b.execute(CATALOG, EVIDENCE, "audit")
        self.assertEqual("PASS", next(x for x in out["details"] if x["id"] == "E10")["status"])
        self.assertEqual("LOCAL_FIXTURE_ONLY",
                         next(x for x in out["details"] if x["id"] == "E10")["scope"])

    def test_no_native_authentication_claim(self):
        for mode in ("audit", "all"):
            x = b.execute(CATALOG, EVIDENCE, mode)
            self.assertFalse(x["native_chatgpt_run_proven"])
            self.assertFalse(x["same_run_github_slack_proven"])
            self.assertFalse(x["production_deployed"])
            self.assertEqual(0, x["executed_independent_llms"])

    def test_tampered_100_catalog_rejected(self):
        catalog = copy.deepcopy(CATALOG)
        catalog[0]["id"] = catalog[1]["id"]
        with self.assertRaises(ValueError):
            b.execute(catalog, EVIDENCE, "all")

    def test_fake_synthetic_secret_rejected(self):
        fixture = b.sample_fixture()
        fixture["slack"]["messages"][0]["text"] = "token=FAKE_TEST"
        self.assertFalse(b.l10(fixture))

    def test_invalid_audit_schema_rejected(self):
        fixture = b.sample_fixture()
        fixture["runs"][0]["scheduled_at"] = "yesterday"
        self.assertEqual("UNVERIFIED",
                         next(x for x in b.execute(CATALOG, EVIDENCE, "audit", fixture)["details"]
                              if x["id"] == "E03")["status"])


if __name__ == "__main__":
    unittest.main()

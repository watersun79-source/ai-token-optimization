"""Fast audit contract: only 20 scheduled/evidence roles. No 100-role receipt prerequisite."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

import v81_split_bench as adapter
import v81_output_contract as baseline

ROOT = Path(__file__).resolve().parent
C = json.loads((ROOT / "catalog.json").read_text(encoding="utf8"))
E = json.loads((ROOT / "evidence.json").read_text(encoding="utf8"))

class FastAuditContract(unittest.TestCase):
    def _run(self):
        return adapter.execute(C, E, "audit")

    def test_exact_20_roles_and_original_output_hashes(self):
        d = self._run()
        self.assertEqual(20, d["selected_count"])
        self.assertEqual({"PASS": 20}, d["statuses"])
        self.assertEqual(0, d["executed_independent_llms"])
        self.assertFalse(d["native_chatgpt_run_proven"])
        self.assertFalse(d["production_deployed"])
        for prefix in ("S", "E"):
            rows = sorted([r for r in d["details"] if r["id"][0] == prefix],
                          key=lambda r: r["id"])
            self.assertEqual(10, len(rows))
            self.assertEqual(baseline.ORIGINAL_GROUP_SHA256[prefix], baseline.digest(rows))

    def test_each_role_has_private_original_field_schema(self):
        d = self._run()
        for row in d["details"]:
            req = baseline.BASE_KEYS | ({"scope"} if row["id"] in baseline.SCOPE_ROLES else set())
            self.assertEqual(req, set(row), row["id"])

    def test_role_name_tampering_changes_digest(self):
        d = self._run()
        original = baseline.digest(d["details"])
        d["details"][0]["name"] = "changed"
        self.assertNotEqual(original, baseline.digest(d["details"]))

    def test_legacy_unverified_provider_claim_is_not_revived(self):
        d = self._run()
        self.assertFalse(d["same_run_github_slack_proven"])
        self.assertTrue(all(r["status"] == "PASS" for r in d["details"]))
        self.assertTrue(all("original" not in r.get("scope","").lower() for r in d["details"]))

if __name__ == "__main__":
    unittest.main()

"""Full 100-role output schema & original-digest fixture regression."""
import copy
import json
from pathlib import Path
import unittest

import v81_split_bench as adapter
import v81_output_contract as contract

ROOT = Path(__file__).resolve().parent
C = json.loads((ROOT / "catalog.json").read_text(encoding="utf8"))
E = json.loads((ROOT / "evidence.json").read_text(encoding="utf8"))

class OutputContractTests(unittest.TestCase):
    def _output(self):
        return adapter.execute(C,E,"all")
    def test_original_schemas_for_all_100(self):
        out=contract.compare_results(self._output())
        self.assertEqual(100,out["record_field_schemas_exact"])
        self.assertEqual(10,out["groups_total"])
        self.assertEqual(10,out["matched_groups"])
        self.assertTrue(out["original_output_digest_exact"])
        self.assertEqual(100,out["adapter_output_total"])
        self.assertFalse(out["native_chatgpt_scheduler_verified"])
    def test_100_ids_have_no_duplicates(self):
        rows=self._output()["details"]
        self.assertEqual(100,len(rows))
        self.assertEqual(adapter.IDS,{r["id"] for r in rows})
    def test_18_replacements_use_original_scope_and_metadata(self):
        out=self._output()
        for row in out["details"]:
            if row["id"] in adapter.REPLACEMENTS:
                self.assertEqual("LOCAL_FIXTURE_ONLY",row["scope"])
                self.assertEqual("SYNTHETIC_LOCAL_FIXTURE_NOT_PROVIDER_EVIDENCE",row["source"])
                self.assertEqual(adapter.ORIGINAL_REPLACEMENT_NAMES[row["id"]],row["name"])
                self.assertIn("synthetic fixture",row["detail"])
    def test_provenance_claim_forgery_rejected(self):
        d=self._output();d["native_chatgpt_run_proven"]=True
        with self.assertRaises(ValueError): contract.compare_results(d)
    def test_missing_field_fail_closed(self):
        d=self._output();d["details"][0].pop("detail")
        with self.assertRaises(ValueError): contract.compare_results(d)
    def test_duplicate_id_fail_closed(self):
        d=self._output();d["details"][0]["id"]=d["details"][1]["id"]
        with self.assertRaises(ValueError): contract.compare_results(d)
    def test_non_pass_rejected(self):
        d=self._output();d["details"][0]["status"]="FAIL"
        with self.assertRaises(ValueError): contract.compare_results(d)
    def test_output_hash_sensitive_to_display_mutation(self):
        d=self._output();base=contract.compare_results(d)
        d["details"][0]["name"]+=" CHANGED"
        changed=contract.compare_results(d)
        self.assertNotEqual(base["groups"]["A"]["github_adapter_sha256"],
                            changed["groups"]["A"]["github_adapter_sha256"])
    def test_no_secrets_or_native_run_in_receipt(self):
        d=contract.compare_results(self._output())
        self.assertEqual(0,d["paid_external_model_calls"])
        self.assertFalse(d["full_source_byte_identity"])
        self.assertTrue(d["offline_fixture_only"])

if __name__=="__main__":
    unittest.main()

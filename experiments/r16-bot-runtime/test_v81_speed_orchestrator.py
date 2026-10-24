"""Offline-only regression for SHA caching, parallel read batching and compact reporting."""
import copy
import json
from pathlib import Path
import unittest

import v81_speed_orchestrator as fast

ROOT=Path(__file__).resolve().parent
CAT=json.loads((ROOT/"catalog.json").read_text(encoding="utf-8"))
EV=json.loads((ROOT/"evidence.json").read_text(encoding="utf-8"))
SHA="d8ed3420f5354042161ca90a675b11353de8b2f5"


class SpeedOrchestratorTests(unittest.TestCase):
    def test_sha_idempotent_and_changed_input(self):
        a=fast.fingerprint(CAT,EV,SHA)
        self.assertEqual(a,fast.fingerprint(copy.deepcopy(CAT),copy.deepcopy(EV),SHA))
        e=copy.deepcopy(EV);e["new_safe_marker"]=123
        self.assertNotEqual(a,fast.fingerprint(CAT,e,SHA))
        self.assertNotEqual(a,fast.fingerprint(CAT,EV,"b"*40))

    def test_invalid_source_sha_fails_closed(self):
        for bad in ("", "not-a-sha", "A"*40, None):
            with self.assertRaises(ValueError):fast.fingerprint(CAT,EV,bad)

    def test_fast_first_then_reuse_same_inputs(self):
        r=fast.AdaptiveOfflineRunner()
        first=r.run(CAT,EV,SHA)
        self.assertEqual((20,0),(first["fast_checks"],first["full_checks"]))
        self.assertFalse(first["native_chatgpt_verified"])
        self.assertFalse(first["full_regression_verified"])
        again=r.run(CAT,EV,SHA)
        self.assertEqual("REUSED_FAST_LOCAL",again["mode"])
        self.assertEqual((0,0),(again["fast_checks"],again["full_checks"]))

    def test_changed_inputs_invalidate_local_cache(self):
        r=fast.AdaptiveOfflineRunner()
        r.run(CAT,EV,SHA)
        e=copy.deepcopy(EV);e["marker"]="changed"
        fresh=r.run(CAT,e,SHA)
        self.assertEqual("FAST_ONLY_LOCAL",fresh["mode"])
        self.assertEqual(0,fresh["full_checks"])

    def test_changed_head_invalidates_local_cache(self):
        r=fast.AdaptiveOfflineRunner()
        r.run(CAT,EV,SHA)
        fresh=r.run(CAT,EV,"b"*40)
        self.assertEqual(20,fresh["fast_checks"])

    def test_ci_reuse_needs_independent_head_and_success(self):
        rec={"source":"GITHUB_API_INDEPENDENTLY_CHECKED","head_sha":SHA,
             "status":"completed","conclusion":"success","changed_inputs":False}
        self.assertEqual("REUSE_ONLY_AFTER_INDEPENDENT_READBACK",fast.plan_ci(SHA,rec))
        for change in ({"head_sha":"b"*40},{"conclusion":"failure"},
                       {"source":"SELF_REPORTED"},{"changed_inputs":True}):
            self.assertTrue(fast.plan_ci(SHA,{**rec,**change}).startswith("RUN_FAST"))
        self.assertTrue(fast.plan_ci(SHA,None).startswith("RUN_FAST"))

    def test_dedup_keeps_original_order_and_values(self):
        req=[("G","head"),("S","thread"),("G","head"),("G","ci"),("S","thread")]
        seen=[]
        def read(tool,locator):
            seen.append((tool,locator))
            return tool+locator
        out=fast.batch_read(req,read)
        self.assertEqual((5,3,2),(out["requested"],out["unique"],out["skipped_duplicates"]))
        self.assertEqual(set(req),set(seen))
        self.assertEqual([out["results"][k] for k in req],["Ghead","Sthread","Ghead","Gci","Sthread"])
        self.assertEqual("UNVERIFIED",out["native_provider_authenticity"])

    def test_batch_rejects_invalid_keys(self):
        for inp in ([("G",)],[(1,"head")],[("G","")]):
            with self.assertRaises(ValueError):fast.batch_read(inp,lambda *_:None)

    def test_reader_error_propagates(self):
        with self.assertRaises(RuntimeError):
            fast.batch_read([("G","head")],lambda *_: (_ for _ in ()).throw(RuntimeError("offline failure")))

    def test_compact_hides_only_unchanged_pass(self):
        result=fast.compact_report({"a":"PASS","b":"UNVERIFIED","c":"PASS"},
                                   {"a":"PASS","b":"UNVERIFIED","c":"FAIL"})
        self.assertEqual({"b":"UNVERIFIED","c":"FAIL"},result["changed"])
        self.assertEqual("UNVERIFIED",result["unattended_native_run"])

    def test_sealed_snapshot_reuse_is_fast_and_origin_limited(self):
        snap=fast.SealedInputs(CAT,EV,SHA)
        runner=fast.AdaptiveOfflineRunner()
        first=runner.run_prepared(snap)
        self.assertEqual(20,first["fast_checks"])
        again=runner.run_prepared(snap)
        self.assertEqual("REUSED_FAST_SEALED_LOCAL",again["mode"])
        self.assertEqual(0,again["full_checks"])
        self.assertFalse(again["native_chatgpt_verified"])

    def test_sealed_snapshot_preserves_original_inputs(self):
        ev=copy.deepcopy(EV)
        snap=fast.SealedInputs(CAT,ev,SHA)
        first=snap.fingerprint
        ev["new_field"]=1
        self.assertEqual(first,snap.fingerprint)
        self.assertNotEqual(first,fast.SealedInputs(CAT,ev,SHA).fingerprint)
        with self.assertRaises(TypeError):
            fast.AdaptiveOfflineRunner().run_prepared({"fingerprint":first})

    def test_ci_fast_real_20_rule_dispatch_and_reuse(self):
        out=fast.ci_fast(SHA)
        self.assertEqual(20,out["fast_checks"])
        self.assertEqual(20,out["duplicates_skipped"])
        self.assertFalse(out["full_check_run"])
        self.assertFalse(out["native_run_verified"])
        self.assertEqual(0,out["external_model_calls"])

    def test_ci_fast_rejects_unverified_sha(self):
        with self.assertRaises(ValueError):
            fast.ci_fast("invalid")

    def test_benchmark_never_reports_official_proof(self):
        r=fast.bench(5)
        self.assertTrue(r["mock_io_only"])
        self.assertEqual("SEALED_SNAPSHOT_SAME_PROCESS_ONLY",r["cache_scope"])
        self.assertGreaterEqual(r["one_time_snapshot_prepare_ms"],0)
        self.assertFalse(r["native_chatgpt_same_run_proven"])
        self.assertEqual(0,r["paid_model_calls"])


if __name__=="__main__":
    unittest.main()

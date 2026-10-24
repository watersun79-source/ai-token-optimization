"""Offline 4->8->16 tiering and fail-closed reduction with deterministic faults."""
import threading
import unittest
import v81_adaptive_parallel as p

def keys(n):
    return [("GitHub","safe-"+str(i)) for i in range(n)]

class AdaptiveTierTests(unittest.TestCase):
    def test_4_8_16_promotion_requires_two_clean_full_batches(self):
        p0=p.AdaptiveParallel(lambda tool,key:key,ceiling=16)
        used=[]
        for _ in range(5):
            r=p0.read(keys(32))
            used.append((r["used_tier"],r["next_tier"]))
            self.assertEqual(32,len(r["results"]))
            self.assertFalse(r["provider_quota_verified"])
        self.assertEqual([(4,4),(4,8),(8,8),(8,16),(16,16)],used)

    def test_safe_default_stays_four(self):
        c=p.AdaptiveParallel(lambda *x:x)
        for _ in range(3):
            self.assertEqual(4,c.read(keys(20))["next_tier"])

    def test_dedup_order_and_no_claim_of_app_authenticity(self):
        seq=[("G","a"),("G","a"),("S","b"),("G","c")]
        r=p.safe_batch_read(seq,lambda *x:x,16)
        self.assertEqual((4,3,1),(r["requested"],r["unique"],r["skipped_duplicates"]))
        self.assertEqual([r["results"][key] for key in seq],seq)
        self.assertEqual("UNVERIFIED",r["native_provider_authenticity"])
        self.assertEqual(3,r["effective_workers"])

    def test_failing_reader_halts_and_reduces_to_eight(self):
        counter={"count":0}
        def maybe_fail(tool,key):
            counter["count"]+=1
            if key=="safe-2" and counter["count"]>100:
                raise OSError("temporary network problem")
            return key
        c=p.AdaptiveParallel(maybe_fail,ceiling=16)
        for _ in range(4):
            c.read(keys(32))
        self.assertEqual(16,c.workers)
        old_count=counter["count"]
        # Specific failure at 16; do not replay same batch implicitly.
        with self.assertRaises(p.AdaptiveReadError) as caught:
            c.read([("G","invalid")] if False else keys(32))
        # reader above has deterministic failure only after 100 calls
        self.assertEqual("READ_ERROR",caught.exception.reason)
        self.assertEqual(8,c.workers)
        self.assertEqual(0,c.clean_batches)
        self.assertEqual(32,counter["count"]-old_count)

    def test_rate_limit_and_permission_go_to_four_no_retry(self):
        for msg,want in (("HTTP 429 Retry-After: 30","RATE_LIMIT"),("HTTP 403 permission denied","ACCESS_DENIED")):
            counters={"called":0}
            def provider(*key):
                counters["called"]+=1
                raise RuntimeError(msg)
            c=p.AdaptiveParallel(provider,ceiling=16)
            c.workers=16
            with self.assertRaises(p.AdaptiveReadError) as got:
                c.read(keys(4))
            self.assertEqual(want,got.exception.reason)
            self.assertEqual(4,c.workers)
            self.assertEqual(4,counters["called"])

    def test_invalid_limits_readers_and_keys(self):
        for cap in (0,3,17,True):
            with self.assertRaises(ValueError): p.safe_batch_read(keys(1),lambda *_:1,cap)
        for bad in ([(1,"x")],[(None,"a")],[("G",)],["no"],[("G","")]):
            with self.assertRaises(ValueError): p.safe_batch_read(bad,lambda *_:1)
        with self.assertRaises(ValueError): p.safe_batch_read(keys(129),lambda *_:1)
        with self.assertRaises(ValueError): p.AdaptiveParallel(None,ceiling=16)
        with self.assertRaises(ValueError): p.AdaptiveParallel(lambda *_:1,ceiling=32)

    def test_benchmark_never_reports_live_provider_results(self):
        r=p.benchmark(2)
        self.assertEqual([4,8,16],[x["tier"] for x in r["samples"]])
        self.assertEqual([4,8,16],[x["measured_peak_inflight"] for x in r["samples"]])
        self.assertEqual(0,r["paid_calls"])
        self.assertFalse(r["native_chatgpt_run_verified"])
        self.assertFalse(r["provider_quota_verified"])

if __name__=="__main__":
    unittest.main()

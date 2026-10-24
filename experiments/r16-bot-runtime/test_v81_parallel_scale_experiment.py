"""Isolated local-only 4->128 scaling and negative tests; no network calls."""
import unittest
import v81_parallel_scale_experiment as e
import v81_adaptive_parallel as b

def keys(n):
    return [("LOCAL",str(i)) for i in range(n)]

class TestScaling(unittest.TestCase):
    def test_promotes_stages_only_after_two_complete_batches(self):
        s=e.OfflineAdaptiveScaling(lambda _tool,k:k)
        history=[]
        for _ in range(11):
            o=s.read(keys(128))
            self.assertEqual(128,o["unique"])
            self.assertFalse(o["provider_quota_verified"])
            self.assertEqual("OFFLINE_ONLY",o["source"])
            history.append(o["tier_used"])
        self.assertEqual([4,4,8,8,16,16,32,32,64,64,128],history)
        self.assertEqual(128,s.workers)

    def test_ceiling_is_enforced(self):
        s=e.OfflineAdaptiveScaling(lambda t,k:k,ceiling=32)
        for _ in range(12):
            s.read(keys(128))
        self.assertEqual(32,s.workers)

    def test_downshift_does_not_retry_failed_batch(self):
        times={"calls":0}
        def read(tool,key):
            times["calls"]+=1
            if key=="0":
                raise ConnectionError("simulated failure")
            return key
        s=e.OfflineAdaptiveScaling(read)
        s.workers=128
        with self.assertRaises(b.AdaptiveReadError) as failure:
            s.read(keys(128))
        self.assertEqual("READ_ERROR",failure.exception.reason)
        self.assertEqual(64,s.workers)
        self.assertEqual(0,s.clean)
        self.assertGreaterEqual(times["calls"],1)
        self.assertLessEqual(times["calls"],128)

    def test_rate_limit_permission_reset_four_no_retry(self):
        for text,code in (("HTTP 429 Retry-After","RATE_LIMIT"),("HTTP 403 permission","ACCESS_DENIED")):
            s=e.OfflineAdaptiveScaling(lambda a,b:(_ for _ in ()).throw(RuntimeError(text)))
            s.workers=128
            with self.assertRaises(b.AdaptiveReadError) as caught:
                s.read(keys(16))
            self.assertEqual(code,caught.exception.reason)
            self.assertEqual(4,s.workers)

    def test_order_dedup_and_valid_caps(self):
        original=[("L","a"),("L","a"),("L","b"),("L","c")]
        r=e.offline_batch(original,lambda *x:x[-1],128)
        self.assertEqual((4,3,1,3),(r["requested"],r["unique"],r["duplicate_skipped"],r["effective_workers"]))
        self.assertEqual([r["results"][key] for key in original],["a","a","b","c"])
        for invalid in (0,3,17,256,False,"16"):
            with self.assertRaises(ValueError):
                e.offline_batch(original,lambda *x:1,invalid)
        with self.assertRaises(ValueError):
            e.offline_batch(keys(257),lambda *x:1,128)
        with self.assertRaises(ValueError):
            e.OfflineAdaptiveScaling(lambda *x:1,ceiling=256)

    def test_bench_marks_local_only_and_all_workloads(self):
        result=e.benchmark(2)
        self.assertEqual(0,result["provider_requests"])
        self.assertFalse(result["provider_quota_verified"])
        self.assertEqual(18,len(result["rows"]))
        self.assertEqual({"sleep_1ms","sleep_8ms","cpu_sha256"},set(x["workload"] for x in result["rows"]))
        self.assertTrue(all(x["errors"]==0 and x["tasks"]==128 for x in result["rows"]))
        self.assertGreaterEqual(result["peak_process_rss_kib"],0)

if __name__=="__main__":
    unittest.main()

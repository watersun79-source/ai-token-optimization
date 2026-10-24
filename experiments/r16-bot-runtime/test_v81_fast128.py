"""Offline isolated FAST128 promotion, backoff and benchmark evidence."""
import time
import unittest
from v81_fast128 import Fast128,compare64_128
from v81_adaptive_parallel import AdaptiveReadError
from v81_fast64 import Fast64

def keys(n=128):
    return [("LOCAL",str(i)) for i in range(n)]

class TestFast128(unittest.TestCase):
    def test_local_long_io_promotes_4_to_128(self):
        def read(tool,key):
            time.sleep(.008)
            return key
        p=Fast128(read,memory_limit_kib=131072)
        observed=[]
        for _ in range(11):
            r=p.read(keys(),workload_tag="sleep_8ms")
            observed.append(r["tier_used"])
            self.assertEqual(128,len(r["results"]))
            self.assertEqual(0,r["provider_requests"])
            self.assertFalse(r["native_chatgpt_verified"])
        self.assertEqual([4,4,8,8,16,16,32,32,64,64,128],observed)
        self.assertEqual(128,p.workers)

    def test_existing_fast64_default_never_exceeds_64(self):
        p=Fast64(lambda a,b:b)
        self.assertEqual(64,p.runner.ceiling)
        with self.assertRaises(ValueError):
            p.observe(128,1,"same",128,100)

    def test_128_latency_regression_downshifts_to64(self):
        p=Fast128(lambda a,b:b)
        p.runner.workers=128
        p.observe(64,10,"same",128,100)
        p.observe(64,10,"same",128,100)
        p.observe(128,12,"same",128,100)
        p.observe(128,13,"same",128,100)
        self.assertEqual(64,p.workers)
        self.assertEqual(64,p.runner.ceiling)
        self.assertEqual("SLOWER_THAN_PREVIOUS_TIER",p.downshifts[-1]["reason"])

    def test_128_rss_downshifts_to64(self):
        p=Fast128(lambda a,b:b,memory_limit_kib=200)
        p.runner.workers=128
        p.observe(128,20,"same",128,201)
        self.assertEqual(64,p.workers)
        self.assertEqual("RSS_LIMIT",p.downshifts[-1]["reason"])

    def test_error_aborts_and_downshifts_without_replay(self):
        attempts=[0]
        def read(a,b):
            attempts[0]+=1
            if b=="0":
                raise RuntimeError("network simulation")
            return b
        p=Fast128(read)
        p.runner.workers=128
        with self.assertRaises(AdaptiveReadError):
            p.read(keys())
        self.assertEqual(64,p.workers)
        self.assertGreaterEqual(attempts[0],1)
        self.assertLessEqual(attempts[0],128)

    def test_429_resets_four_and_no_auto_retry(self):
        p=Fast128(lambda *args:(_ for _ in ()).throw(RuntimeError("HTTP 429 rate limit")))
        p.runner.workers=128
        with self.assertRaises(AdaptiveReadError) as cm:
            p.read(keys(8))
        self.assertEqual("RATE_LIMIT",cm.exception.reason)
        self.assertEqual(4,p.workers)

    def test_same_host_comparison_not_api_proof(self):
        r=compare64_128(2)
        self.assertEqual(6,len(r["samples"]))
        self.assertEqual({64,128},set(x["tier"] for x in r["samples"]))
        self.assertEqual(0,r["provider_requests"])
        self.assertFalse(r["provider_quota_verified"])
        self.assertFalse(r["native_scheduled_run_verified"])
        self.assertTrue(all(x["errors"]==0 for x in r["samples"]))

if __name__=="__main__":
    unittest.main()

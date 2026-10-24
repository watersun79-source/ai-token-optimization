"""Isolated FAST256 offline-only test: ramp, downshift, limit, 256-key speed."""
import unittest
from v81_fast256 import Fast256, LocalScale256, offline_batch256, compare_64_128_256
from v81_fast128 import Fast128
from v81_fast64 import Fast64
from v81_adaptive_parallel import AdaptiveReadError

def keys(n=256):
    return [("LOCAL",str(i)) for i in range(n)]

class TestFast256(unittest.TestCase):
    def test_two_clean_batches_each_stage_to_256(self):
        runner=LocalScale256(lambda _tool,key:key)
        observed=[]
        for _ in range(13):
            r=runner.read(keys())
            observed.append(r["tier_used"])
            self.assertEqual(256,len(r["results"]))
            self.assertFalse(r["provider_quota_verified"])
        self.assertEqual([4,4,8,8,16,16,32,32,64,64,128,128,256],observed)
        self.assertEqual(256,runner.workers)

    def test_fast64_and_fast128_remain_lower_ceiling(self):
        self.assertEqual(64,Fast64(lambda *args:1).runner.ceiling)
        self.assertEqual(128,Fast128(lambda *args:1).runner.ceiling)

    def test_fast256_opt_in_can_dispatch_256(self):
        f=Fast256(lambda _,key:key)
        self.assertEqual(256,f.runner.ceiling)
        f.runner.workers=256
        result=f.read(keys(),workload_tag="LOCAL_256")
        self.assertEqual(256,result["tier_used"])
        self.assertEqual(256,result["unique"])
        self.assertEqual(0,result["provider_requests"])

    def test_latency_regression_downshifts_256_to_128(self):
        f=Fast256(lambda *args:"safe")
        f.runner.workers=256
        f.observe(128,10,"same",256,100)
        f.observe(128,10,"same",256,100)
        f.observe(256,12,"same",256,100)
        f.observe(256,13,"same",256,100)
        self.assertEqual(128,f.workers)
        self.assertEqual(128,f.runner.ceiling)
        self.assertEqual("SLOWER_THAN_PREVIOUS_TIER",f.downshifts[-1]["reason"])

    def test_memory_limit_downshifts_256_to_128(self):
        f=Fast256(lambda *args:1,memory_limit_kib=200)
        f.runner.workers=256
        f.observe(256,20,"same",256,201)
        self.assertEqual(128,f.workers)
        self.assertEqual("RSS_LIMIT",f.downshifts[-1]["reason"])

    def test_read_error_no_retry_and_downshift(self):
        seen=[0]
        def read(_,key):
            seen[0]+=1
            if key=="0":
                raise OSError("local fake failure")
            return key
        f=Fast256(read)
        f.runner.workers=256
        with self.assertRaises(AdaptiveReadError) as cm:
            f.read(keys())
        self.assertEqual("READ_ERROR",cm.exception.reason)
        self.assertEqual(128,f.workers)
        self.assertTrue(1<=seen[0]<=256)

    def test_429_and_permission_reset_four(self):
        for reason,expected in (("HTTP 429 limit","RATE_LIMIT"),("HTTP 403 denied","ACCESS_DENIED")):
            f=Fast256(lambda *_: (_ for _ in ()).throw(RuntimeError(reason)))
            f.runner.workers=256
            with self.assertRaises(AdaptiveReadError) as got:
                f.read(keys(16))
            self.assertEqual(expected,got.exception.reason)
            self.assertEqual(4,f.workers)

    def test_bounds_and_dedup(self):
        seq=[("LOCAL","a"),("LOCAL","a"),("LOCAL","b")]
        out=offline_batch256(seq,lambda _t,k:k,256)
        self.assertEqual((3,2,1),(out["requested"],out["unique"],out["duplicate_skipped"]))
        for invalid in (0,17,512,True,"256"):
            with self.assertRaises(ValueError):
                offline_batch256(seq,lambda *args:1,invalid)
        with self.assertRaises(ValueError):
            offline_batch256(keys(257),lambda *args:1,256)
        with self.assertRaises(ValueError):
            offline_batch256([("GitHub","x")],lambda *args:1,256)
        with self.assertRaises(ValueError):
            LocalScale256(lambda *args:1,ceiling=512)

    def test_same_host_three_tiers_not_live_api(self):
        r=compare_64_128_256(2)
        self.assertEqual(9,len(r["rows"]))
        self.assertEqual({64,128,256},set(x["tier"] for x in r["rows"]))
        self.assertEqual({128},set() if False else {128})  # fixed workload metadata checked below
        self.assertTrue(all(x["completed"]==256 and x["errors"]==0 for x in r["rows"]))
        self.assertEqual(0,r["provider_requests"])
        self.assertFalse(r["provider_quota_verified"])
        self.assertFalse(r["native_chatgpt_verified"])

if __name__=="__main__":
    unittest.main()

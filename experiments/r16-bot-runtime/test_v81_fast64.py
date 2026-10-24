"""Tests for local-only 64-cap adaptive FAST, controlled regression and RSS failure."""
import unittest
import time
import v81_fast64 as f
import v81_adaptive_parallel as inherited

def keys(count=128):
    return [("LOCAL",str(i)) for i in range(count)]

class TestFast64(unittest.TestCase):
    def test_ramp_stops_at_64(self):
        def io_bound(_, key):
            time.sleep(0.008)
            return key
        obj=f.Fast64(io_bound)
        used=[]
        for _ in range(14):
            result=obj.read(keys(),workload_tag="constant")
            used.append(result["tier_used"])
            self.assertLessEqual(result["adaptive_ceiling"],64)
            self.assertEqual(0,result["provider_requests"])
            self.assertFalse(result["native_chatgpt_verified"])
        self.assertEqual([4,4,8,8,16,16,32,32,64,64,64,64,64,64],used)

    def test_latency_regression_downshift_sticks_for_same_session(self):
        obj=f.Fast64(lambda *args:"ok")
        obj.runner.workers=64
        obj.observe(32,10,"SAME",128,100)
        obj.observe(32,10,"SAME",128,100)
        obj.observe(64,12,"SAME",128,100)
        self.assertEqual(64,obj.workers)
        obj.observe(64,13,"SAME",128,100)
        self.assertEqual(32,obj.workers)
        self.assertEqual(32,obj.runner.ceiling)
        self.assertEqual("SLOWER_THAN_PREVIOUS_TIER",obj.downshifts[-1]["reason"])

    def test_different_workloads_do_not_cross_compare(self):
        obj=f.Fast64(lambda *args:1)
        obj.runner.workers=64
        obj.observe(32,1,"short",128,100)
        obj.observe(64,100,"long",128,100)
        obj.observe(64,100,"long",128,100)
        self.assertEqual(64,obj.workers)

    def test_memory_limit_cuts_tier_and_caps(self):
        obj=f.Fast64(lambda *args:"safe",memory_limit_kib=200)
        obj.runner.workers=64
        obj.observe(64,10,"same",128,201)
        self.assertEqual(32,obj.workers)
        self.assertEqual("RSS_LIMIT",obj.downshifts[-1]["reason"])

    def test_read_actual_memory_capture_cuts_tier(self):
        obj=f.Fast64(lambda _,k:k,memory_limit_kib=1)
        obj.runner.workers=16
        r=obj.read(keys())
        self.assertEqual((16,8),(r["tier_used"],r["next_tier"]))
        self.assertEqual("RSS_LIMIT",r["downshift_reason"])
        self.assertEqual(128,len(r["results"]))

    def test_error_no_auto_retry_and_downshift(self):
        calls=[0]
        def bad(_,key):
            calls[0]+=1
            if key=="0":
                raise RuntimeError("simulated failure")
            return key
        obj=f.Fast64(bad)
        obj.runner.workers=64
        with self.assertRaises(inherited.AdaptiveReadError):
            obj.read(keys())
        self.assertEqual(32,obj.workers)
        self.assertLessEqual(calls[0],128)

    def test_429_fail_closed(self):
        obj=f.Fast64(lambda *_: (_ for _ in ()).throw(RuntimeError("HTTP 429 rate limit")))
        obj.runner.workers=64
        with self.assertRaises(inherited.AdaptiveReadError) as failure:
            obj.read(keys())
        self.assertEqual("RATE_LIMIT",failure.exception.reason)
        self.assertEqual(4,obj.workers)

    def test_invalid_feedback_and_bad_configuration(self):
        with self.assertRaises(ValueError):
            f.Fast64(lambda *_:None,memory_limit_kib=-1)
        with self.assertRaises(ValueError):
            f.Fast64(None)
        obj=f.Fast64(lambda *_:None)
        for invalid in (0,128):
            with self.assertRaises(ValueError):
                obj.observe(invalid,1,"valid",128,100)
        with self.assertRaises(ValueError):
            obj.observe(64,-1,"valid",128,100)

    def test_offline_profile_uses_only_tiers_upto_64(self):
        p=f.profile64(2)
        self.assertEqual(64,p["configured_max"])
        self.assertEqual(0,p["provider_calls"])
        self.assertEqual(15,len(p["rows"]))
        self.assertFalse(p["provider_quota_verified"])

if __name__=="__main__":
    unittest.main()

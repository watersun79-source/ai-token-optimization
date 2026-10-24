"""Fail-closed adaptive FAST ceiling tests: offline data only."""
import unittest
from v81_fast_auto import AdaptiveFast,choose_ceiling,_validate_profile

KINDS=("sleep_1ms","sleep_8ms","cpu_sha256")
TIERS=(64,128,256)

def mockprofile(short=(10,20,21),long=(40,28,30),cpu=(160,167,170)):
    values={"sleep_1ms":short,"sleep_8ms":long,"cpu_sha256":cpu}
    return {"kind":"ISOLATED_FAST256_256_LOCAL_TASKS_NOT_PROVIDER","provider_requests":0,
            "rows":[{"workload":name,"tier":tier,"median_ms":value,
                     "completed":256,"errors":0}
                    for name in KINDS for tier,value in zip(TIERS,values[name])]}

class TestAdaptiveFast(unittest.TestCase):
    def test_measured_policy_prefers_64_short_and_128_long(self):
        a=mockprofile()
        b=mockprofile(short=(12,21,22),long=(39,29,31))
        self.assertEqual(64,choose_ceiling("sleep_1ms",a,b))
        self.assertEqual(128,choose_ceiling("sleep_8ms",a,b))

    def test_no_256_without_two_independent_gains(self):
        a=mockprofile(long=(40,27,22))
        b=mockprofile(long=(39,28,29))
        self.assertEqual(128,choose_ceiling("sleep_8ms",a,b))
        c=mockprofile(long=(40,27,22))
        self.assertEqual(256,choose_ceiling("sleep_8ms",a,c))

    def test_cpu_and_unknown_fail_closed_to_four(self):
        a=mockprofile()
        self.assertEqual(4,choose_ceiling("cpu_sha256",a,a))
        self.assertEqual(4,choose_ceiling("unknown",a,a))
        self.assertEqual(4,choose_ceiling("sleep_8ms",a,None))
        self.assertEqual(4,choose_ceiling("sleep_8ms",a,a,host_cpu=0))

    def test_reject_invalid_stats_or_permissions(self):
        a=mockprofile()
        b=mockprofile()
        b["provider_requests"]=1
        self.assertEqual(4,choose_ceiling("sleep_8ms",a,b))
        b=mockprofile()
        b["rows"][0]["median_ms"]=float("nan")
        self.assertEqual(4,choose_ceiling("sleep_8ms",a,b))
        b=mockprofile()
        b["rows"][0]["errors"]=1
        self.assertEqual(4,choose_ceiling("sleep_8ms",a,b))
        b=mockprofile()
        b["rows"][0]["completed"]=128
        self.assertEqual(4,choose_ceiling("sleep_8ms",a,b))
        b=mockprofile()
        b["rows"].append(dict(b["rows"][0]))
        self.assertEqual(4,choose_ceiling("sleep_8ms",a,b))

    def test_profiles_do_not_bypass_live_quota(self):
        a=mockprofile()
        f=AdaptiveFast(lambda _,k:k,"sleep_8ms",a,a)
        self.assertEqual(128,f.runner.ceiling)
        self.assertFalse(f.provider_quota_verified)
        seq=[("LOCAL",str(i)) for i in range(128)]
        out=f.read(seq)
        self.assertEqual(128,len(out["results"]))
        self.assertEqual(0,out["provider_requests"])
        self.assertFalse(out["profile_is_real_provider_evidence"])
        self.assertEqual(128,out["profile_based_ceiling"])

    def test_unknown_workload_keeps_four(self):
        f=AdaptiveFast(lambda _,k:k,"unknown")
        self.assertEqual(4,f.runner.ceiling)
        for _ in range(4):
            r=f.read([("LOCAL",str(i)) for i in range(16)])
            self.assertEqual(4,r["next_tier"])

    def test_mismatched_tag_rejected(self):
        f=AdaptiveFast(lambda _,k:k,"sleep_8ms")
        with self.assertRaises(ValueError):
            f.read([("LOCAL","x")],workload_tag="sleep_1ms")

    def test_error_reduces_workers_without_replay(self):
        def fail(*args):
            raise RuntimeError("HTTP 429 simulated")
        f=AdaptiveFast(fail,"sleep_8ms",mockprofile(),mockprofile())
        f.runner.workers=128
        from v81_adaptive_parallel import AdaptiveReadError
        with self.assertRaises(AdaptiveReadError):
            f.read([("LOCAL","x")])
        self.assertEqual(4,f.workers)

    def test_latency_and_rss_downshift_honored(self):
        f=AdaptiveFast(lambda _,k:k,"sleep_8ms",mockprofile(),mockprofile())
        f.runner.workers=128
        f.observe(64,10,"sleep_8ms",128,100)
        f.observe(128,12,"sleep_8ms",128,100)
        f.observe(128,13,"sleep_8ms",128,100)
        self.assertEqual(64,f.runner.ceiling)
        self.assertEqual(64,f.workers)

if __name__=="__main__":
    unittest.main()

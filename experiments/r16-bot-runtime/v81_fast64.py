#!/usr/bin/env python3
"""AI BOT v8.1: isolated adaptive FAST64 *local-only* worker.
No network/client imports. This is NOT GitHub/Slack API permission to use 64.
"""
from __future__ import annotations
from collections import deque
import json
import os
import resource
import statistics
import time

import v81_parallel_scale_experiment as experiment

TIERS = (4, 8, 16, 32, 64)

class Fast64:
    """Opt-in LOCAL worker controller. Promotions: two clean full batches.
    For comparable workload and key counts, two >10% regressions or memory
    threshold force a tier downshift and cap it for this controller instance.
    Original failures propagate without replay. Never uses real API on its own.
    """
    def __init__(self, reader, memory_limit_kib=131072):
        if not callable(reader) or isinstance(memory_limit_kib, bool) or not isinstance(memory_limit_kib,int) or memory_limit_kib <= 0:
            raise ValueError("local reader and positive RSS threshold required")
        self.runner = experiment.OfflineAdaptiveScaling(reader,ceiling=64)
        self.memory_limit_kib = memory_limit_kib
        self.samples={}
        self.slow_streak=0
        self.downshifts=[]
        self.provider_quota_verified=False

    @property
    def workers(self):
        return self.runner.workers

    def observe(self, tier, elapsed_ms, workload_tag, unique, rss_kib):
        """Measurement feedback; caller must use identical workload signatures."""
        if (tier not in TIERS or not isinstance(workload_tag,str) or not workload_tag
            or isinstance(elapsed_ms,bool) or not isinstance(elapsed_ms,(int,float))
            or not 0 <= elapsed_ms < 1e9 or not isinstance(unique,int) or unique < 0
            or not isinstance(rss_kib,int) or rss_kib < 0):
            raise ValueError("invalid measurable observation")
        key=(workload_tag,unique)
        lower = self.samples.get((key,tier//2))
        if rss_kib > self.memory_limit_kib and tier>4:
            self._downshift(tier,"RSS_LIMIT")
        elif lower and tier>4 and elapsed_ms > statistics.median(lower)*1.10:
            self.slow_streak += 1
            if self.slow_streak>=2:
                self._downshift(tier,"SLOWER_THAN_PREVIOUS_TIER")
        else:
            self.slow_streak=0
        hist=self.samples.setdefault((key,tier),deque(maxlen=3))
        hist.append(elapsed_ms)

    def _downshift(self,tier,reason):
        next_tier=max(4,tier//2)
        self.runner.workers=next_tier
        self.runner.ceiling=min(self.runner.ceiling,next_tier)
        self.runner.clean=0
        self.slow_streak=0
        self.downshifts.append({"from":tier,"to":next_tier,"reason":reason})

    def read(self,keys,workload_tag="LOCAL_ONLY"):
        start=time.perf_counter_ns()
        result=self.runner.read(keys)  # fail closed; exceptions downshift here, no retry
        elapsed=(time.perf_counter_ns()-start)/1e6
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # Linux: KiB
        self.observe(result["tier_used"],elapsed,workload_tag,result["unique"],rss)
        return {**result,"measured_ms":round(elapsed,3),
                "next_tier":self.runner.workers,"rss_kib":rss,
                "adaptive_ceiling":self.runner.ceiling,
                "provider_requests":0,"native_chatgpt_verified":False,
                "downshift_reason":self.downshifts[-1]["reason"] if self.downshifts and self.downshifts[-1]["from"]==result["tier_used"] else None}

def profile64(repeats=3):
    if not 2 <= repeats <= 6:
        raise ValueError("unsafe repetition count")
    rows=[]
    for name in ("sleep_1ms","sleep_8ms","cpu_sha256"):
        for tier in TIERS:
            vals=[]
            for _ in range(repeats):
                elapsed,_peak=experiment._scenario(name,128,tier)
                vals.append(elapsed)
            rows.append({"workload":name,"tier":tier,"median_ms":round(statistics.median(vals),3),"errors":0})
    choices={}
    for name in ("sleep_1ms","sleep_8ms","cpu_sha256"):
        subset=[x for x in rows if x["workload"]==name]
        choices[name]=min(subset,key=lambda x:x["median_ms"])["tier"]
    r={"kind":"ISOLATED_FAST64_LOCAL_ONLY","host_cpu":os.cpu_count(),
       "host_peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
       "configured_max":64,"provider_quota_verified":False,"provider_calls":0,
       "native_chatgpt_verified":False,"rows":rows,"fastest_measured_tier":choices}
    print("R16_V81_FAST64="+json.dumps(r,sort_keys=True))
    return r

if __name__=="__main__":
    profile64()

#!/usr/bin/env python3
"""AI BOT v8.1 FAST256 — explicit isolated local-only read experiment.

Never calls external providers or changes schedulers. 256 threads != 256 API
permissions, cores or AI agents. Keep existing FAST64/FAST128 and live API caps.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import resource
import statistics
import threading
import time

from v81_fast128 import Fast128
from v81_adaptive_parallel import AdaptiveReadError, classify_failure
import v81_parallel_scale_experiment as experiment

TIERS=(4,8,16,32,64,128,256)
MAX_KEYS=256

def offline_batch256(keys, reader, workers):
    """Bounded, exact-key deduplicated OFFLINE local batch; no provider client."""
    if (not isinstance(keys,list) or len(keys)>MAX_KEYS or
        not callable(reader) or type(workers) is not int or workers not in TIERS):
        raise ValueError("invalid bounded local batch")
    if not all(isinstance(k,tuple) and len(k)==2 and
               all(isinstance(x,str) and x for x in k) and k[0]=="LOCAL"
               for k in keys):
        raise ValueError("local (LOCAL,nonempty-key) tuples only")
    distinct=list(dict.fromkeys(keys))
    if not distinct:
        return {"results":{},"requested":0,"unique":0,
                "duplicate_skipped":0,"effective_workers":0,"native_app_verified":False}
    with ThreadPoolExecutor(max_workers=min(workers,len(distinct))) as pool:
        results=list(pool.map(lambda k:reader(*k),distinct))
    return {"results":dict(zip(distinct,results)),"requested":len(keys),
            "unique":len(distinct),"duplicate_skipped":len(keys)-len(distinct),
            "effective_workers":min(workers,len(distinct)),"native_app_verified":False}

class LocalScale256(experiment.OfflineAdaptiveScaling):
    """Promotion only after two clean saturated batches; no automatic retry."""
    def __init__(self,reader,ceiling=256):
        if ceiling not in TIERS or not callable(reader):
            raise ValueError("invalid local ceiling or reader")
        super().__init__(reader,ceiling=128)
        self.ceiling=ceiling

    def read(self,keys):
        tier=self.workers
        try:
            result=offline_batch256(keys,self.reader,tier)
        except Exception as exc:
            kind=classify_failure(exc)
            self.workers=4 if kind in ("RATE_LIMIT","ACCESS_DENIED") else max(4,tier//2)
            self.clean=0
            raise AdaptiveReadError(kind,tier,self.workers) from exc
        self.clean = self.clean+1 if result["unique"]>=tier else 0
        if self.clean>=2 and tier<self.ceiling:
            self.workers=min(tier*2,self.ceiling)
            self.clean=0
        return {**result,"tier_used":tier,"next_tier":self.workers,
                "provider_quota_verified":False,"source":"OFFLINE_ONLY"}

class Fast256(Fast128):
    """FAST64 unchanged, FAST128 unchanged; opt in explicitly to max 256."""
    allowed_tiers=TIERS
    def __init__(self,reader,memory_limit_kib=131072):
        super().__init__(reader,memory_limit_kib=memory_limit_kib)
        self.runner=LocalScale256(reader,ceiling=256)

def _scenario256(kind,workers):
    lock=threading.Lock()
    active=[0,0]
    keys=[("LOCAL",str(i)) for i in range(MAX_KEYS)]
    def local_reader(tool,locator):
        with lock:
            active[0]+=1
            active[1]=max(active[1],active[0])
        try:
            if kind=="sleep_1ms":
                time.sleep(.001)
            elif kind=="sleep_8ms":
                time.sleep(.008)
            elif kind=="cpu_sha256":
                payload=(tool+"/"+locator).encode()
                for _ in range(2000):
                    payload=hashlib.sha256(payload).digest()
            else:
                raise ValueError("unsupported workload")
            return locator
        finally:
            with lock:
                active[0]-=1
    start=time.perf_counter_ns()
    batch=offline_batch256(keys,local_reader,workers)
    elapsed_ms=(time.perf_counter_ns()-start)/1e6
    if len(batch["results"])!=MAX_KEYS or any(batch["results"][k]!=k[1] for k in keys):
        raise AssertionError("missing local results")
    return elapsed_ms,active[1]

def compare_64_128_256(repeats=3):
    if type(repeats) is not int or not 2<=repeats<=6:
        raise ValueError("repeats out of bounds")
    rows=[]
    for workload in ("sleep_1ms","sleep_8ms","cpu_sha256"):
        for tier in (64,128,256):
            samples=[]
            peaks=[]
            for _ in range(repeats):
                elapsed,peak=_scenario256(workload,tier)
                samples.append(elapsed)
                peaks.append(peak)
            rows.append({"workload":workload,"tier":tier,
                         "median_ms":round(statistics.median(samples),3),
                         "best_ms":round(min(samples),3),
                         "peak_inflight":max(peaks),"completed":MAX_KEYS,"errors":0})
    data={"kind":"ISOLATED_FAST256_256_LOCAL_TASKS_NOT_PROVIDER",
          "opt_in_ceiling":256,"other_fast64_ceiling_unchanged":64,
          "other_fast128_ceiling_unchanged":128,"provider_limit_unchanged":4,
          "host_cpu":os.cpu_count(),
          "peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          "provider_requests":0,"provider_quota_verified":False,
          "native_chatgpt_verified":False,"rows":rows,"repeats":repeats}
    print("R16_V81_FAST256="+json.dumps(data,sort_keys=True))
    return data

if __name__=="__main__":
    compare_64_128_256()

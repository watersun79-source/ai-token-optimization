#!/usr/bin/env python3
"""Bounded, isolated 4..128 thread scaling experiment: OFFLINE local readers ONLY.
No network imports, app credentials, paid service, API requests or production writes.
Thread ceilings are NOT provider quotas or number of CPU cores.
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
import v81_adaptive_parallel as baseline

TIERS=(4,8,16,32,64,128)
MAX_KEYS=256

def offline_batch(keys, reader, workers):
    """Strictly local experiment, exact-key dedup, no cache across runs."""
    if workers not in TIERS or not callable(reader) or not isinstance(keys,list) or len(keys)>MAX_KEYS:
        raise ValueError("invalid offline parallel workload or cap")
    if not all(isinstance(key,tuple) and len(key)==2 and
               all(isinstance(s,str) and s for s in key) for key in keys):
        raise ValueError("expected nonempty two-string read keys")
    distinct=list(dict.fromkeys(keys))
    if not distinct:
        return {"results":{},"requested":0,"unique":0,"duplicate_skipped":0,"effective_workers":0,
                "native_app_verified":False}
    with ThreadPoolExecutor(max_workers=min(workers,len(distinct))) as pool:
        values=list(pool.map(lambda key:reader(*key),distinct))
    return {"results":dict(zip(distinct,values)),"requested":len(keys),"unique":len(distinct),
            "duplicate_skipped":len(keys)-len(distinct),
            "effective_workers":min(workers,len(distinct)),"native_app_verified":False}

class OfflineAdaptiveScaling:
    """Staged promotion needs two full successful batches; failures downshift without retry."""
    def __init__(self,reader,ceiling=128):
        if ceiling not in TIERS or not callable(reader):
            raise ValueError("offline reader and 4..128 ceiling required")
        self.reader=reader
        self.ceiling=ceiling
        self.workers=4
        self.clean=0

    def read(self,keys):
        before=self.workers
        try:
            out=offline_batch(keys,self.reader,before)
        except Exception as ex:
            kind=baseline.classify_failure(ex)
            self.workers=4 if kind in ("RATE_LIMIT","ACCESS_DENIED") else max(4,before//2)
            self.clean=0
            # No automatic replay; original exception may contain secrets.
            raise baseline.AdaptiveReadError(kind,before,self.workers) from ex
        self.clean = self.clean+1 if out["unique"]>=before else 0
        if self.clean>=2 and before<self.ceiling:
            self.workers=min(before*2,self.ceiling)
            self.clean=0
        return {**out,"tier_used":before,"next_tier":self.workers,
                "provider_quota_verified":False,"source":"OFFLINE_ONLY"}

def _scenario(kind,count,workers):
    active=[0,0]
    lock=threading.Lock()
    keys=[("LOCAL",str(i)) for i in range(count)]
    def reader(tool,number):
        with lock:
            active[0]+=1
            active[1]=max(active[1],active[0])
        try:
            if kind=="sleep_1ms":
                time.sleep(.001)
            elif kind=="sleep_8ms":
                time.sleep(.008)
            elif kind=="cpu_sha256":
                payload=(tool+"/"+number).encode()
                for _ in range(2000):
                    payload=hashlib.sha256(payload).digest()
            else:
                raise ValueError("unknown scenario")
            return number
        finally:
            with lock:
                active[0]-=1
    started=time.perf_counter_ns()
    output=offline_batch(keys,reader,workers)
    wall_ms=(time.perf_counter_ns()-started)/1e6
    if len(output["results"])!=count or any(output["results"][key]!=key[1] for key in keys):
        raise AssertionError("incomplete local work")
    return wall_ms,active[1]

def benchmark(repeats=3,count=128):
    """Hosted-runner wall time for synthetic I/O and actual local CPU hashing.
    No provider app read is part of this measurement; no source code deployment.
    """
    if not isinstance(repeats,int) or repeats<2 or repeats>8 or count!=128:
        raise ValueError("benchmark requires fixed 128 tasks, 2..8 repetitions")
    rows=[]
    for kind in ("sleep_1ms","sleep_8ms","cpu_sha256"):
        for workers in TIERS:
            samples=[]
            peaks=[]
            for _ in range(repeats):
                ms,peak=_scenario(kind,count,workers)
                samples.append(ms)
                peaks.append(peak)
            rows.append({"workload":kind,"tier":workers,
                         "median_ms":round(statistics.median(samples),3),
                         "best_ms":round(min(samples),3),"peak_inflight":max(peaks),
                         "errors":0,"tasks":count})
    mem_total_kib=None
    try:
        with open("/proc/meminfo",encoding="utf-8") as inp:
            line=next(x for x in inp if x.startswith("MemTotal:"))
        mem_total_kib=int(line.split()[1])
    except (OSError,ValueError,StopIteration,IndexError):
        pass
    result={"kind":"ISOLATED_LOCAL_128_TASK_SCALING_NOT_PROVIDER",
            "runner_cpu":os.cpu_count(),"runner_mem_total_kib":mem_total_kib,
            "peak_process_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "provider_quota_verified":False,"native_chatgpt_verified":False,
            "provider_requests":0,"paid_model_calls":0,"repeats":repeats,"rows":rows}
    print("R16_V81_SCALE_128="+json.dumps(result,sort_keys=True))
    return result

if __name__=="__main__":
    benchmark()

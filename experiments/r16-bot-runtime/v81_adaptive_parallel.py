#!/usr/bin/env python3
"""Isolated v8.1 adaptive read-only *local* executor. Never calls APIs itself.
4/8/16 are local thread ceilings, not approved GitHub/Slack provider quotas.
Fail closed: do not re-submit failed requests without a provider-authenticated
Retry-After/permission check; users must opt in to tiers above 4.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json
import os
import resource
import statistics
import threading
import time

TIERS = (4, 8, 16)
MAX_KEYS = 128

class AdaptiveReadError(RuntimeError):
    def __init__(self, reason: str, tier: int, next_tier: int):
        self.reason, self.tier, self.next_tier = reason, tier, next_tier
        super().__init__(f"read batch blocked: {reason}; tier {tier}->{next_tier}, NO auto retry")

def safe_batch_read(requests, reader, max_workers=4):
    """Exact-key dedup, ordered mapping, caller-supplied read function only."""
    if not isinstance(requests, list) or len(requests) > MAX_KEYS or not isinstance(max_workers, int) or isinstance(max_workers, bool) or not 1 <= max_workers <= 16:
        raise ValueError("invalid batch size or worker cap")
    if not all(isinstance(k, tuple) and len(k) == 2 and
               all(isinstance(x, str) and x for x in k) for k in requests):
        raise ValueError("read keys must be (tool,locator) nonempty text tuples")
    uniq = list(dict.fromkeys(requests))
    if not uniq:
        return {"results": {}, "requested": 0, "unique": 0,
                "skipped_duplicates": 0, "effective_workers": 0,
                "native_provider_authenticity": "UNVERIFIED"}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(uniq))) as pool:
        replies = list(pool.map(lambda key: reader(*key), uniq))
    return {"results": dict(zip(uniq, replies)), "requested": len(requests),
            "unique": len(uniq), "skipped_duplicates": len(requests)-len(uniq),
            "effective_workers": min(max_workers, len(uniq)),
            "native_provider_authenticity": "UNVERIFIED"}

def classify_failure(error: Exception) -> str:
    # No exception body is logged: it may contain secrets.
    s = str(error).lower()
    if "429" in s or "rate limit" in s or "retry-after" in s:
        return "RATE_LIMIT"
    if "403" in s or "permission" in s or "unauthorized" in s or "401" in s:
        return "ACCESS_DENIED"
    return "READ_ERROR"

class AdaptiveParallel:
    """Sequential batches adapt; independent keys within each batch parallel.
    Default maximum=4; max 8/16 MUST be explicit and provider-approved.
    Two clean saturated batches needed to promote. Any failure downshifts
    and fails this batch; unknown/RATE_LIMIT/403 errors are never auto retried.
    """
    def __init__(self, reader, ceiling=4):
        if ceiling not in TIERS or not callable(reader):
            raise ValueError("expected callable reader and tier 4,8,16")
        self.reader = reader
        self.ceiling = ceiling
        self.workers = 4
        self.clean_batches = 0

    def read(self, requests):
        tier = self.workers
        try:
            out = safe_batch_read(requests, self.reader, max_workers=tier)
        except Exception as error:
            reason = classify_failure(error)
            # Rate/permission: back to 4; never claim a provider retry is safe.
            self.workers = 4 if reason in ("RATE_LIMIT", "ACCESS_DENIED") else max(4,tier//2)
            self.clean_batches = 0
            raise AdaptiveReadError(reason,tier,self.workers) from error
        if out["unique"] >= tier:
            self.clean_batches += 1
        else:
            self.clean_batches = 0
        if self.clean_batches >= 2 and tier < self.ceiling:
            self.workers = min(self.ceiling, tier*2)
            self.clean_batches = 0
        return {**out,"used_tier":tier,"next_tier":self.workers,
                "provider_quota_verified":False,"paid_calls":0}

def benchmark(repeats=3):
    """Real hosted CPU/RSS and wall clock; requests are synthetic sleep only."""
    if not isinstance(repeats,int) or not 2 <= repeats <= 10:
        raise ValueError("repeat count outside permitted interval")
    catalog=[("LOCAL","read-"+str(i)) for i in range(32)]
    measurements=[]
    for tier in TIERS:
        samples=[]
        concurrency_peaks=[]
        for _ in range(repeats):
            active=[0,0]
            lock=threading.Lock()
            def sleep_read(tool,locator):
                with lock:
                    active[0]+=1
                    active[1]=max(active[0],active[1])
                try:
                    time.sleep(0.008)
                    return tool+"/"+locator
                finally:
                    with lock:
                        active[0]-=1
            started=time.perf_counter_ns()
            r=safe_batch_read(catalog,sleep_read,tier)
            elapsed=(time.perf_counter_ns()-started)/1e6
            if r["unique"]!=32 or any(r["results"][k] != "/".join(k) for k in catalog):
                raise ValueError("synthetic completeness check failed")
            samples.append(elapsed)
            concurrency_peaks.append(active[1])
        measurements.append({"tier":tier, "median_ms":round(statistics.median(samples),3),
             "measured_peak_inflight":max(concurrency_peaks),"completed":32,"errors":0})
    rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    mem_kib=None
    try:
        line=next(l for l in open("/proc/meminfo",encoding="utf-8") if l.startswith("MemTotal:"))
        mem_kib=int(line.split()[1])
    except (OSError,StopIteration,ValueError,IndexError):
        pass
    result={"kind":"ISOLATED_HOSTED_SIMULATED_IO_NOT_PROVIDER_LATENCY",
            "runner_cpu_count":os.cpu_count(),"runner_mem_total_kib":mem_kib,
            "process_peak_rss_kib":rss_kib,"provider_quota_verified":False,
            "native_chatgpt_run_verified":False,"paid_calls":0,
            "repeats":repeats,"samples":measurements}
    print("R16_V81_ADAPTIVE_PARALLEL="+json.dumps(result,sort_keys=True))
    return result

if __name__=="__main__":
    benchmark()

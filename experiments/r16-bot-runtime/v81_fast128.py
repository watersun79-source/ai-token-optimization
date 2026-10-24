#!/usr/bin/env python3
"""Explicit FAST128 opt-in for ISOLATED LOCAL tasks, never a connector quota."""
from __future__ import annotations
import json
import os
import resource
import statistics

from v81_fast64 import Fast64
import v81_parallel_scale_experiment as experiment

class Fast128(Fast64):
    """Local-only opt-in 4→8→16→32→64→128; 64 default elsewhere unchanged.
    Two complete clean batches promote, repeated slower tier or high RSS
    downshifts; an error aborts with no automatic retry.
    """
    allowed_tiers=(4,8,16,32,64,128)
    def __init__(self, reader, memory_limit_kib=131072):
        super().__init__(reader,memory_limit_kib=memory_limit_kib)
        self.runner.ceiling=128

def compare64_128(repeats=3):
    """Same-run comparable 128-key workloads; NO live GitHub/Slack requests."""
    if not isinstance(repeats,int) or isinstance(repeats,bool) or not 2<=repeats<=6:
        raise ValueError("repeats must be 2..6")
    rows=[]
    for kind in ("sleep_1ms","sleep_8ms","cpu_sha256"):
        for tier in (64,128):
            measurements=[]
            peaks=[]
            for _ in range(repeats):
                ms,peak=experiment._scenario(kind,128,tier)
                measurements.append(ms)
                peaks.append(peak)
            rows.append({"workload":kind,"tier":tier,
                         "median_ms":round(statistics.median(measurements),3),
                         "peak_inflight":max(peaks),"completed":128,"errors":0})
    output={"kind":"ISOLATED_FAST128_OPT_IN_LOCAL_ONLY","worker_tiers":[4,8,16,32,64,128],
            "default_local_limit_elsewhere":64,"real_app_connector_limit_unmodified":4,
            "host_cpu_count":os.cpu_count(),
            "peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "provider_requests":0,"provider_quota_verified":False,
            "native_scheduled_run_verified":False,"samples":rows,"repeats":repeats}
    print("R16_V81_FAST128="+json.dumps(output,sort_keys=True))
    return output

if __name__=="__main__":
    compare64_128()

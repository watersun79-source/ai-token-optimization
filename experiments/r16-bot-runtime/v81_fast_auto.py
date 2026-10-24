#!/usr/bin/env python3
"""Adaptive FAST local-only ceiling policy derived from *two* offline profiles.

Defaults fail-closed; never grants GitHub/Slack/ChatGPT concurrency rights.
"""
from __future__ import annotations

import math
from v81_fast256 import Fast256

WORKLOADS=("sleep_1ms","sleep_8ms","cpu_sha256")
TIERS=(64,128,256)
MIN_GAIN=0.05

def _validate_profile(profile):
    """Only like-for-like, error-free 256-task local benchmark results."""
    if not isinstance(profile,dict) or profile.get("provider_requests")!=0 or profile.get("kind")!="ISOLATED_FAST256_256_LOCAL_TASKS_NOT_PROVIDER":
        raise ValueError("must provide verified-format offline FAST256 profile")
    rows=profile.get("rows")
    if not isinstance(rows,list) or len(rows)!=9:
        raise ValueError("incomplete benchmark rows")
    result={}
    for r in rows:
        if not isinstance(r,dict):
            raise ValueError("malformed benchmark row")
        key=(r.get("workload"),r.get("tier"))
        ms=r.get("median_ms")
        if (key[0] not in WORKLOADS or key[1] not in TIERS or key in result
            or r.get("completed")!=256 or r.get("errors")!=0
            or isinstance(ms,bool) or not isinstance(ms,(int,float))
            or not math.isfinite(ms) or ms<=0):
            raise ValueError("unsafe or non-comparable benchmark row")
        result[key]=ms
    if len(result)!=9:
        raise ValueError("missing matrix entries")
    return result

def choose_ceiling(workload_tag,profile_a=None,profile_b=None,host_cpu=4):
    """Choose only reproducible gains; never implicitly use FAST256.

    CPU work: bounded to measured host CPU count tier 4 (user can choose a
    separate CPU executor, but this local I/O controller is not that executor).
    Unknown/missing/invalid evidence: return 4.
    For verified I/O, baseline 64; promote only when BOTH profiles show >=5%
    gain against previous tier.
    """
    if workload_tag not in WORKLOADS or type(host_cpu) is not int or host_cpu<1:
        return 4
    if workload_tag=="cpu_sha256":
        return 4
    if profile_a is None or profile_b is None:
        return 4
    try:
        a,b=_validate_profile(profile_a),_validate_profile(profile_b)
    except ValueError:
        return 4
    best=64
    for candidate,lower in ((128,64),(256,128)):
        if all(p[(workload_tag,candidate)]<=p[(workload_tag,lower)]*(1-MIN_GAIN) for p in (a,b)):
            best=candidate
        else:
            break
    return best

class AdaptiveFast(Fast256):
    """Explicitly opt-in to offline local profile based ceiling; no real API."""
    def __init__(self,reader,workload_tag,profile_a=None,profile_b=None,host_cpu=4,memory_limit_kib=131072):
        super().__init__(reader,memory_limit_kib=memory_limit_kib)
        self.workload_tag=workload_tag
        self.chosen_ceiling=choose_ceiling(workload_tag,profile_a,profile_b,host_cpu)
        self.runner.ceiling=self.chosen_ceiling

    def read(self,keys,workload_tag=None):
        if workload_tag is not None and workload_tag!=self.workload_tag:
            raise ValueError("mixed workload would invalidate benchmark comparison")
        result=super().read(keys,workload_tag=self.workload_tag)
        return {**result,"profile_based_ceiling":self.chosen_ceiling,
                "effective_ceiling":self.runner.ceiling,
                "profile_is_real_provider_evidence":False}

#!/usr/bin/env python3
"""Isolated v8.1 fast/full benchmark adapter. NO provider, cloud, or native task writes.

Reuses the 82 previously implemented v7 rules from the pinned source tree.
Implements the 18 v8.1 replacements over explicitly synthetic sample inputs.
This is a representative v8.1-compatible adapter, NOT a verbatim v8.1 ZIP
deployment, nor authentication of external scheduler/Slack/Activepieces calls.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import statistics
import time

import runner

ROOT = Path(__file__).resolve().parent
PREFIXES = frozenset("SGPLAOCMTE")
IDS = frozenset(f"{p}{n:02}" for p in PREFIXES for n in range(1, 11))
REPLACEMENTS = frozenset(
    [f"L{n:02}" for n in range(6, 11)]
    + [f"A{n:02}" for n in range(7, 10)]
    + [f"E{n:02}" for n in range(1, 11)]
)
GOALS = {"audit": frozenset("SE"), "all": PREFIXES}
TS = re.compile(r"^[0-9]{10}\.[0-9]{6}$")
SECRET = re.compile(r"(?i)(?:sk-[a-z0-9_-]{12,}|(?:api[_-]?key|token|password|secret)\s*[:=]\s*\S+)")


def iso(value: str) -> datetime:
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("timezone required")
    return instant


def sample_fixture() -> dict:
    """All IDs and content are intentionally invented, never service evidence."""
    raw = '{"event":"completed","result":"synthetic"}'
    return {
        "schema_version": "bot100-v2",
        "source": "synthetic_fixture",
        "slack": {"messages": [
            {"channel": "C0000000000", "ts": "1700000000.000001",
             "thread_ts": "1700000000.000001", "text": "synthetic example"}
        ]},
        "activepieces": {"nodes": [
            {"id": "trigger", "next": ["process"]},
            {"id": "process", "next": []}
        ]},
        "max_start_delay_seconds": 600,
        "runs": [{
            "id": "fixture-run-001", "source": "synthetic_fixture",
            "scheduled_at": "2026-10-24T08:00:00+09:00",
            "started_at": "2026-10-24T08:00:03+09:00",
            "ended_at": "2026-10-24T08:00:09+09:00",
            "events": [{"at": "2026-10-24T08:00:05+09:00", "level": "INFO", "type": "fixture"}],
            "raw_log": raw,
            "raw_log_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "artifact_path": "logs/synthetic.json"
        }]
    }


def messages(s: dict) -> list:
    items = s["slack"]["messages"]
    assert isinstance(items, list) and items
    return items


def nodes(s: dict) -> list:
    items = s["activepieces"]["nodes"]
    assert isinstance(items, list) and items
    return items


def runs(s: dict) -> list:
    items = s["runs"]
    assert isinstance(items, list) and items
    return items


def l06(s):
    return all(isinstance(v.get("channel"), str) and isinstance(v.get("ts"), str)
               and isinstance(v.get("text"), str) for v in messages(s))


def l07(s):
    return all(bool(TS.fullmatch(v["ts"])) for v in messages(s))


def l08(s):
    return all(v.get("thread_ts") is None or
               (bool(TS.fullmatch(v["thread_ts"]))
                and float(v["thread_ts"]) <= float(v["ts"])) for v in messages(s))


def l09(s):
    return all(len(v["text"].encode("utf-8")) <= 40000 for v in messages(s))


def l10(s):
    return all(not SECRET.search(v["text"]) for v in messages(s))


def a07(s):
    ids = [v["id"] for v in nodes(s)]
    return len(ids) == len(set(ids)) and all(isinstance(v, str) and v for v in ids)


def a08(s):
    records = nodes(s)
    ids = {v["id"] for v in records}
    return all(isinstance(v.get("next"), list) and
               all(n in ids for n in v["next"]) for v in records)


def a09(s):
    graph = {v["id"]: v.get("next", []) for v in nodes(s)}
    state = {}

    def visit(v):
        if state.get(v) == 1:
            return False
        if state.get(v) == 2:
            return True
        state[v] = 1
        for target in graph.get(v, []):
            if target not in graph or not visit(target):
                return False
        state[v] = 2
        return True

    return all(visit(v) for v in graph)


def e01(s):
    return s.get("schema_version") == "bot100-v2" and isinstance(s.get("runs"), list)


def e02(s):
    ids = [v["id"] for v in runs(s)]
    return len(ids) == len(set(ids)) and all(isinstance(v, str) and bool(v) for v in ids)


def e03(s):
    return all(iso(v[k]).tzinfo is not None for v in runs(s)
               for k in ("scheduled_at", "started_at", "ended_at"))


def e04(s):
    return all(iso(v["scheduled_at"]) <= iso(v["started_at"]) <= iso(v["ended_at"])
               for v in runs(s))


def e05(s):
    delay = s.get("max_start_delay_seconds", 3600)
    return isinstance(delay, int) and delay >= 0 and all(
        0 <= (iso(v["started_at"]) - iso(v["scheduled_at"])).total_seconds() <= delay
        for v in runs(s))


def e06(s):
    for v in runs(s):
        events = [iso(e["at"]) for e in v["events"]]
        if not events or events != sorted(events) or any(
            not iso(v["started_at"]) <= t <= iso(v["ended_at"]) for t in events
        ):
            return False
    return True


def e07(s):
    return all(e.get("level") in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
               and isinstance(e.get("type"), str) and bool(e.get("type"))
               for v in runs(s) for e in v["events"])


def e08(s):
    return all(hashlib.sha256(v["raw_log"].encode()).hexdigest() == v["raw_log_sha256"]
               for v in runs(s))


def e09(s):
    for v in runs(s):
        p = v["artifact_path"]
        q = PurePosixPath(p)
        if not p or q.is_absolute() or ".." in q.parts or "\\" in p or "\x00" in p:
            return False
    return True


def e10(s):
    return all(not v.get("_externally_attested", False)
               for v in runs(s) if v.get("source") == "synthetic_fixture")


CHECKS = {
    "L06": l06, "L07": l07, "L08": l08, "L09": l09, "L10": l10,
    "A07": a07, "A08": a08, "A09": a09,
    "E01": e01, "E02": e02, "E03": e03, "E04": e04, "E05": e05,
    "E06": e06, "E07": e07, "E08": e08, "E09": e09, "E10": e10
}
assert set(CHECKS) == REPLACEMENTS


def execute(catalog: list, evidence: dict, mode: str, fixture: dict | None = None) -> dict:
    """Use pinned pre-existing rules for 82 and v8.1-style local replacements for 18."""
    if mode not in GOALS:
        raise ValueError("unsupported mode")
    if len(catalog) != 100 or {v["id"] for v in catalog} != IDS:
        raise ValueError("catalog must contain 100 distinct known BOT IDs")
    if not isinstance(evidence, dict):
        raise ValueError("offline evidence must be an object")
    fixture = sample_fixture() if fixture is None else fixture
    selected = sorted((v for v in catalog if v["id"][0] in GOALS[mode]),
                      key=lambda v: v["id"])
    details = []
    for role in selected:
        name = role["id"]
        if name not in REPLACEMENTS:
            record = runner.validate(role, evidence)
        else:
            try:
                passed = CHECKS[name](fixture)
                status = "PASS" if passed else "FAIL"
            except (KeyError, ValueError, TypeError, AssertionError,
                    AttributeError, OverflowError, RecursionError):
                status = "UNVERIFIED"
            record = {
                "id": name,
                "status": status,
                "scope": "SYNTHETIC_LOCAL_FIXTURE_ONLY",
                "source": "SYNTHETIC_LOCAL_FIXTURE_NOT_PROVIDER_EVIDENCE",
            }
        details.append(record)
    counts = dict(Counter(x["status"] for x in details))
    return {
        "kind": "ISOLATED_V81_COMPATIBILITY_ADAPTER_NOT_NATIVE",
        "mode": mode,
        "catalog_total": 100,
        "selected_count": len(details),
        "replacements_total": sum(x["id"] in REPLACEMENTS for x in details),
        "statuses": counts,
        "executed_independent_llms": 0,
        "native_chatgpt_run_proven": False,
        "same_run_github_slack_proven": False,
        "production_deployed": False,
        "details": details,
    }


def benchmark(mode: str, repeats: int) -> dict:
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf8"))
    evidence = json.loads((ROOT / "evidence.json").read_text(encoding="utf8"))
    expected = 20 if mode == "audit" else 100
    result = execute(catalog, evidence, mode)
    if result["selected_count"] != expected or result["statuses"] != {"PASS": expected}:
        raise RuntimeError(f"fail-closed: selected check incomplete: {result['statuses']}")
    for _ in range(5):
        execute(catalog, evidence, mode)
    durations = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        execute(catalog, evidence, mode)
        durations.append((time.perf_counter_ns() - start) / 1e6)
    ordered = sorted(durations)
    output = {
        "kind": "V81_ADAPTER_BENCH_NOT_NATIVE_PLATFORM",
        "mode": mode,
        "n": repeats,
        "rules": expected,
        "synthetic_replacement_checks": result["replacements_total"],
        "pass": expected,
        "median_ms": round(statistics.median(ordered), 4),
        "p95_ms": round(ordered[max(0, (95 * repeats + 99) // 100 - 1)], 4),
        "cpu_count": os.cpu_count(),
        "head_sha": os.environ.get("GITHUB_SHA", "LOCAL_ONLY"),
        "actual_v81_archive_on_runner": False,
        "native_run_proven": False,
        "external_model_calls": 0,
    }
    print("R16_V81_BENCH=" + json.dumps(output, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf8") as out:
            out.write("## V8.1-compatible isolated benchmark — " + mode + "\n\n")
            for name, value in output.items():
                out.write(f"- {name}: {value}\n")
            out.write("\nOffline fixture and v7 82-rule source only; not native task attestation.\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "all"), required=True)
    parser.add_argument("--repeats", type=int, default=150)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 500:
        parser.error("repeats must be 1..500")
    benchmark(args.mode, args.repeats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

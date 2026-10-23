"""Fail-closed OTLP JSON adapter for the offline R16 evidence checker.

The adapter validates trace structure and GenAI execute_tool span semantics, then
produces audit_v2's private ``tool_calls`` shape.  It never authenticates a
ChatGPT scheduled run: OTLP JSON and custom attributes remain caller-supplied.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re


TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
SPAN_ID = re.compile(r"^[0-9a-f]{16}$")
MAX_SPANS = 2048


def _attrs(items):
    out = {}
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            continue
        if item["key"] in out:
            return {}  # Fail closed on duplicate OTLP attribute keys.
        value = item.get("value")
        if not isinstance(value, dict):
            continue
        for key in ("stringValue", "boolValue", "intValue"):
            if key in value:
                out[item["key"]] = value[key]
                break
    return out


def _time_ns(value):
    if not isinstance(value, str) or not value.isdigit():
        return None
    number = int(value)
    if number <= 0:
        return None
    return number


def _iso_utc(number):
    seconds, nanos = divmod(number, 1_000_000_000)
    dt = datetime.fromtimestamp(seconds, timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{nanos:09d}Z"


def _valid_id(value, pattern):
    return isinstance(value, str) and bool(pattern.fullmatch(value)) and set(value) != {"0"}


def _ok_status(span):
    status = span.get("status")
    if not isinstance(status, dict):
        return False
    code = status.get("code")
    return code in (2, "2", "STATUS_CODE_OK") and not status.get("message")


def _descends_from(span, root_span_id, by_id):
    """Require an unbroken, acyclic parent chain to the scheduled-run root."""
    parent_id = span.get("parentSpanId")
    visited = set()
    while parent_id:
        if parent_id == root_span_id:
            return True
        if parent_id in visited or parent_id not in by_id:
            return False
        visited.add(parent_id)
        parent_id = by_id[parent_id][0].get("parentSpanId")
    return False


def adapt_otlp(payload, *, expected_run_id, expected_targets):
    """Convert one authenticated-run-shaped OTLP export into private tool calls.

    ``expected_targets`` maps target -> (tool aliases, locator, version regex).
    All ``ai.*`` attributes are private correlation hints, not OTel standard
    authentication fields.  Arguments/results are deliberately ignored.
    """
    result = {"tool_calls": [], "reason": "OTLP 호출 증거 미충족", "trace_id": None}
    if not isinstance(payload, dict) or not isinstance(expected_run_id, str) or not expected_run_id:
        return result
    spans = []
    resource_spans = payload.get("resourceSpans")
    if not isinstance(resource_spans, list):
        return result
    for resource in resource_spans:
        if not isinstance(resource, dict):
            continue
        scopes = resource.get("scopeSpans")
        if not isinstance(scopes, list):
            continue
        for scope in scopes:
            if isinstance(scope, dict) and isinstance(scope.get("spans"), list):
                spans.extend(scope["spans"])
                if len(spans) > MAX_SPANS:
                    result["reason"] = "OTLP span 2048건 초과"
                    return result

    by_id = {}
    for span in spans:
        if not isinstance(span, dict):
            continue
        trace_id, span_id = span.get("traceId"), span.get("spanId")
        if not _valid_id(trace_id, TRACE_ID) or not _valid_id(span_id, SPAN_ID) or span_id in by_id:
            continue
        start, end = _time_ns(span.get("startTimeUnixNano")), _time_ns(span.get("endTimeUnixNano"))
        if start is None or end is None or start > end:
            continue
        by_id[span_id] = (span, _attrs(span.get("attributes")), start, end)

    roots = []
    for span, attrs, start, end in by_id.values():
        if (attrs.get("ai.scheduler.run.id") == expected_run_id
                and attrs.get("gen_ai.operation.name") == "invoke_agent"
                and not span.get("parentSpanId") and _ok_status(span)):
            roots.append((span, attrs, start, end))
    if len(roots) != 1:
        result["reason"] = "공식 회차에 대응하는 단일 root span 없음"
        return result
    root, _, root_start, root_end = roots[0]
    root_trace = root["traceId"]
    result["trace_id"] = root_trace

    seen_targets, seen_span_ids = set(), set()
    calls = []
    for span, attrs, start, end in by_id.values():
        target = attrs.get("ai.evidence.target")
        if target not in expected_targets or target in seen_targets:
            continue
        aliases, locator, version_pattern = expected_targets[target]
        tool_name = attrs.get("gen_ai.tool.name")
        span_name = span.get("name")
        version = attrs.get("ai.evidence.version")
        if (attrs.get("gen_ai.operation.name") != "execute_tool"
                or not isinstance(tool_name, str) or tool_name not in aliases
                or span_name != f"execute_tool {tool_name}" or span.get("kind") not in (1, "1", "SPAN_KIND_INTERNAL")
                or span["traceId"] != root_trace or not _descends_from(span, root["spanId"], by_id)
                or not (root_start <= start <= end <= root_end) or not _ok_status(span)
                or attrs.get("ai.scheduler.run.id") != expected_run_id
                or attrs.get("ai.evidence.locator") != locator
                or not isinstance(version, str) or not version_pattern.fullmatch(version)
                or span["spanId"] in seen_span_ids):
            continue
        calls.append({
            "target": target,
            "origin": "official_task_tool_call",
            "run_id": expected_run_id,
            "success": True,
            "tool": tool_name,
            "locator": locator,
            "invocation_id": f"otel-span:{span['spanId']}",
            "observed_at": _iso_utc(end),
            "version": version,
            "trace_id": root_trace,
            "span_id": span["spanId"],
            "provider_tool_call_id": attrs.get("gen_ai.tool.call.id"),
        })
        seen_targets.add(target)
        seen_span_ids.add(span["spanId"])
    result["tool_calls"] = calls
    result["reason"] = "OTLP span 형식·인과 연결 통과 · 원본 진위 미검증" if calls else result["reason"]
    return result

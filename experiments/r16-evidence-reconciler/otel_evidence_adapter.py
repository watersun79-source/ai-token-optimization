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
ANY_VALUE_FIELDS = {
    "stringValue", "boolValue", "intValue", "doubleValue", "arrayValue",
    "kvlistValue", "bytesValue", "stringValueStrindex",
}


def _attrs(items):
    out = {}
    if not isinstance(items, list):
        return out
    seen_keys = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            continue
        attr_key = item["key"]
        if attr_key in seen_keys:
            return {}  # Fail closed even if the first value was unsupported.
        seen_keys.add(attr_key)
        value = item.get("value")
        if not isinstance(value, dict):
            continue
        if len(ANY_VALUE_FIELDS.intersection(value)) > 1:
            return {}  # Protobuf AnyValue is a oneof, never several variants.
        for value_key in ("stringValue", "boolValue", "intValue"):
            if value_key in value:
                decoded = value[value_key]
                if value_key == "stringValue" and not isinstance(decoded, str):
                    return {}
                if value_key == "boolValue" and type(decoded) is not bool:
                    return {}
                if value_key == "intValue":
                    if isinstance(decoded, str):
                        if not (1 <= len(decoded) <= 20 and re.fullmatch(r"-?[0-9]+", decoded)):
                            return {}
                        decoded = int(decoded)
                    if type(decoded) is not int or not -(1 << 63) <= decoded < (1 << 63):
                        return {}
                out[attr_key] = decoded
                break
    return out


def _time_ns(value):
    # OTLP fixed64 accepts JSON integers or decimal strings, never booleans.
    # Bound strings before conversion to avoid Unicode/int-limit exceptions.
    if type(value) is int:
        number = value
    elif isinstance(value, str) and 1 <= len(value) <= 20 and value.isascii() and value.isdigit():
        number = int(value)
    else:
        return None
    if not 0 < number <= 0xFFFFFFFFFFFFFFFF:
        return None
    return number


def _iso_utc(number):
    seconds, nanos = divmod(number, 1_000_000_000)
    dt = datetime.fromtimestamp(seconds, timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{nanos:09d}Z"


def _valid_id(value, pattern):
    return isinstance(value, str) and bool(pattern.fullmatch(value)) and set(value) != {"0"}


def _enum_is(value, number, name):
    # Keep legacy string aliases, but bool/float equality is not enum typing.
    return ((type(value) is int and value == number)
            or (isinstance(value, str) and value in (str(number), name)))


def _ok_status(span):
    status = span.get("status")
    if not isinstance(status, dict):
        return False
    code = status.get("code")
    # OTLP trace.proto StatusCode: UNSET=0, OK=1, ERROR=2.
    return _enum_is(code, 1, "STATUS_CODE_OK") and not status.get("message")


def _descends_from(span, root_span_id, root_trace_id, by_id):
    """Require an unbroken, acyclic same-trace chain to the run root."""
    parent_id = span.get("parentSpanId")
    visited = set()
    while parent_id:
        # OTLP parentSpanId is a hex string. Lists/dicts can otherwise raise
        # TypeError on dictionary/set membership, aborting the entire audit.
        if not isinstance(parent_id, str):
            return False
        parent_key = (root_trace_id, parent_id)
        if (parent_id in visited or parent_key not in by_id
                or by_id[parent_key][0].get("traceId") != root_trace_id):
            return False
        if parent_id == root_span_id:
            return True
        visited.add(parent_id)
        parent_id = by_id[parent_key][0].get("parentSpanId")
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
    # OpenTelemetry's real span identity is (traceId, spanId). A repeated
    # identity is ambiguous even if the later span has invalid timestamps.
    # Reject rather than silently using the first (potentially forged) copy.
    seen_trace_span_ids = set()
    for span in spans:
        if not isinstance(span, dict):
            continue
        # OTLP wire IDs are case-insensitive hex. Canonicalize a shallow copy
        # before validation, duplicate detection and parent lookup; never alter
        # the caller's original export or case-sensitive evidence attributes.
        span = dict(span)
        for id_field in ("traceId", "spanId", "parentSpanId"):
            if isinstance(span.get(id_field), str):
                span[id_field] = span[id_field].lower()
        trace_id, span_id = span.get("traceId"), span.get("spanId")
        if not _valid_id(trace_id, TRACE_ID) or not _valid_id(span_id, SPAN_ID):
            continue
        identity = (trace_id, span_id)
        if identity in seen_trace_span_ids:
            result["reason"] = "동일 trace 내 중복 span ID · 원본 진위 미검증"
            return result
        seen_trace_span_ids.add(identity)
        # Check the type before root detection: falsey containers/scalars must
        # not be mistaken for the empty parent ID of a root span.
        parent_id = span.get("parentSpanId", "")
        if not isinstance(parent_id, str) or (parent_id and not _valid_id(parent_id, SPAN_ID)):
            continue
        start, end = _time_ns(span.get("startTimeUnixNano")), _time_ns(span.get("endTimeUnixNano"))
        if start is None or end is None or start > end:
            continue
        by_id[identity] = (span, _attrs(span.get("attributes")), start, end)

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
                or span_name != f"execute_tool {tool_name}" or not _enum_is(span.get("kind"), 1, "SPAN_KIND_INTERNAL")
                or span["traceId"] != root_trace or not _descends_from(span, root["spanId"], root_trace, by_id)
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
            "started_at": _iso_utc(start),
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




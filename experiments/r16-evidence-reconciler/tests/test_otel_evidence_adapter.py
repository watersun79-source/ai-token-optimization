import copy
import re
import unittest

from audit_v2 import AUTOMATION_ID, check
from otel_evidence_adapter import adapt_otlp

RUN = "native-run-1"
TRACE = "1" * 32
ROOT = "2" * 16
GITHUB = "3" * 16
SLACK = "4" * 16
SHA = re.compile(r"^[a-f0-9]{40}$")
TS = re.compile(r"^\d{10}\.\d{6}$")
TARGETS = {
    "current_handoff": ({"mcp__codex_apps__github_fetch_file"}, "docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md", SHA),
    "slack_thread": ({"mcp__codex_apps__slack_slack_read_thread"}, "C0C9649RQAZ/1792416391.631669", TS),
}


def attr(key, value):
    return {"key": key, "value": {"stringValue": value}}


def span(span_id, name, operation, tool=None, target=None, locator=None, version=None):
    attrs = [attr("ai.scheduler.run.id", RUN), attr("gen_ai.operation.name", operation)]
    if tool:
        attrs += [attr("gen_ai.tool.name", tool), attr("ai.evidence.target", target),
                  attr("ai.evidence.locator", locator), attr("ai.evidence.version", version)]
    return {"traceId": TRACE, "spanId": span_id, "parentSpanId": "" if operation == "invoke_agent" else ROOT,
            "name": name, "kind": "SPAN_KIND_INTERNAL", "startTimeUnixNano": "1792735200000000000",
            "endTimeUnixNano": "1792735201000000000", "status": {"code": "STATUS_CODE_OK"}, "attributes": attrs}


def fixture():
    root = span(ROOT, "invoke_agent R16", "invoke_agent")
    root["startTimeUnixNano"] = "1792735199000000000"
    root["endTimeUnixNano"] = "1792735205000000000"
    github = span(GITHUB, "execute_tool mcp__codex_apps__github_fetch_file", "execute_tool",
                  "mcp__codex_apps__github_fetch_file", "current_handoff",
                  "docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md", "a" * 40)
    slack = span(SLACK, "execute_tool mcp__codex_apps__slack_slack_read_thread", "execute_tool",
                 "mcp__codex_apps__slack_slack_read_thread", "slack_thread",
                 "C0C9649RQAZ/1792416391.631669", "1792735600.070409")
    return {"resourceSpans": [{"scopeSpans": [{"spans": [root, github, slack]}]}]}


class TestOtelAdapter(unittest.TestCase):
    def test_malformed_timestamps_are_rejected_without_crashing(self):
        for value in ("²", "9" * 5000, "18446744073709551616", "0", True, 1.5):
            with self.subTest(value=repr(value)[:50]):
                data = fixture()
                data["resourceSpans"][0]["scopeSpans"][0]["spans"][1]["endTimeUnixNano"] = value
                out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
                self.assertEqual(["slack_thread"], [c["target"] for c in out["tool_calls"]])

    def test_json_integer_timestamps_are_accepted(self):
        data = fixture()
        for item in data["resourceSpans"][0]["scopeSpans"][0]["spans"]:
            for key in ("startTimeUnixNano", "endTimeUnixNano"):
                item[key] = int(item[key])
        out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertCountEqual(TARGETS, [c["target"] for c in out["tool_calls"]])

    def test_out_of_range_root_timestamp_is_rejected(self):
        data = fixture()
        data["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["endTimeUnixNano"] = "18446744073709551616"
        self.assertEqual([], adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)["tool_calls"])

    def test_uint64_max_timestamp_is_accepted(self):
        data = fixture()
        spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
        spans[0]["endTimeUnixNano"] = "18446744073709551615"
        spans[1]["endTimeUnixNano"] = "18446744073709551615"
        out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertEqual(2, len(out["tool_calls"]))
        self.assertEqual("2554-07-21T23:34:33.709551615Z", out["tool_calls"][0]["observed_at"])

    def test_valid_trace_maps_two_calls_without_promoting_trace_to_run_id(self):
        out = adapt_otlp(fixture(), expected_run_id=RUN, expected_targets=TARGETS)
        self.assertEqual(2, len(out["tool_calls"]))
        self.assertEqual(TRACE, out["trace_id"])
        self.assertTrue(all(c["run_id"] == RUN and c["invocation_id"].startswith("otel-span:") for c in out["tool_calls"]))

    def test_audit_checker_consumes_otlp_but_keeps_authenticity_unverified(self):
        payload = {
            "target_slot": "2026-10-23T06:00:00Z",
            "schedule": {"id": AUTOMATION_ID, "is_enabled": True,
                         "last_run_time": "2026-10-23T06:00:10Z"},
            "native_run": {"origin": "official_task_run_details", "run_id": RUN,
                           "automation_id": AUTOMATION_ID, "scheduled_for": "2026-10-23T06:00:00Z",
                           "started_at": "2026-10-23T06:00:00Z", "completed_at": "2026-10-23T06:00:05Z",
                           "status": "completed"},
            "otel": fixture(),
            "tool_calls": [{"target": "current_handoff", "success": True}],
        }
        out = check(payload)
        self.assertEqual("형식 통과 · 진위 미검증", out["status"])
        self.assertFalse(out["official_success_verified"])
        self.assertEqual(TRACE, out["otel_trace_id"])
        self.assertCountEqual(TARGETS, out["verified_targets"])

    def test_rejects_cross_trace_child(self):
        data = fixture(); data["resourceSpans"][0]["scopeSpans"][0]["spans"][1]["traceId"] = "5" * 32
        self.assertEqual(1, len(adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)["tool_calls"]))

    def test_rejects_cross_trace_intermediate_parent(self):
        data = fixture()
        spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
        middle = span("7" * 16, "intermediate", "chat")
        middle["traceId"] = "9" * 32
        spans.append(middle)
        spans[1]["parentSpanId"] = middle["spanId"]
        out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertEqual(["slack_thread"], [call["target"] for call in out["tool_calls"]])

    def test_accepts_same_trace_intermediate_parent(self):
        data = fixture()
        spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
        middle = span("7" * 16, "intermediate", "chat")
        spans.append(middle)
        spans[1]["parentSpanId"] = middle["spanId"]
        out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertCountEqual(["current_handoff", "slack_thread"],
                              [call["target"] for call in out["tool_calls"]])

    def test_rejects_orphan_parent(self):
        data = fixture(); data["resourceSpans"][0]["scopeSpans"][0]["spans"][1]["parentSpanId"] = "9" * 16
        self.assertEqual(1, len(adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)["tool_calls"]))

    def test_rejects_parent_chain_not_connected_to_root(self):
        data = fixture(); spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
        fake_parent = span("7" * 16, "chat", "chat")
        fake_parent["parentSpanId"] = "8" * 16
        spans.append(fake_parent)
        spans[1]["parentSpanId"] = fake_parent["spanId"]
        self.assertEqual(1, len(adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)["tool_calls"]))

    def test_rejects_error_status_and_forged_success_attribute(self):
        data = fixture(); call = data["resourceSpans"][0]["scopeSpans"][0]["spans"][1]
        call["status"] = {"code": "STATUS_CODE_ERROR"}; call["attributes"].append(attr("success", "true"))
        self.assertEqual(1, len(adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)["tool_calls"]))

    def test_rejects_child_outside_root_time(self):
        data = fixture(); data["resourceSpans"][0]["scopeSpans"][0]["spans"][1]["endTimeUnixNano"] = "1792735210000000000"
        self.assertEqual(1, len(adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)["tool_calls"]))

    def test_rejects_missing_version_and_bad_span_name(self):
        data = fixture(); call = data["resourceSpans"][0]["scopeSpans"][0]["spans"][1]
        call["attributes"] = [a for a in call["attributes"] if a["key"] != "ai.evidence.version"]
        data["resourceSpans"][0]["scopeSpans"][0]["spans"][2]["name"] = "execute_tool forged"
        self.assertEqual([], adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)["tool_calls"])

    def test_rejects_zero_ids_duplicate_root_and_excess_spans(self):
        data = fixture(); data["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["traceId"] = "0" * 32
        self.assertEqual([], adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)["tool_calls"])
        data = fixture(); data["resourceSpans"][0]["scopeSpans"][0]["spans"].append(copy.deepcopy(data["resourceSpans"][0]["scopeSpans"][0]["spans"][0]))
        data["resourceSpans"][0]["scopeSpans"][0]["spans"][-1]["spanId"] = "6" * 16
        self.assertEqual([], adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)["tool_calls"])


    def test_rejects_duplicate_keys_when_first_value_type_is_unsupported(self):
        data = fixture()
        root = data["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        root["attributes"].insert(
            0, {"key": "ai.scheduler.run.id", "value": {"doubleValue": 1.0}}
        )
        self.assertEqual([], adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)["tool_calls"])

        data = fixture()
        call = data["resourceSpans"][0]["scopeSpans"][0]["spans"][1]
        call["attributes"].insert(
            0, {"key": "ai.evidence.target", "value": {"doubleValue": 1.0}}
        )
        out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertEqual(["slack_thread"], [item["target"] for item in out["tool_calls"]])


if __name__ == "__main__":
    unittest.main()


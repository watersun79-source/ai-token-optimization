"""Adversarial OTLP trace identity and parent-type regressions.

Original OTel SDKs identify a span by (trace_id, span_id). This offline
R16 reader must fail closed on conflicting same-trace span duplicates.
Tests use synthetic traces; never authenticate scheduled ChatGPT work.
"""
import copy
import unittest

from otel_evidence_adapter import adapt_otlp
from test_otel_evidence_adapter import fixture, TARGETS, RUN, TRACE, ROOT


class TestTraceIdentity(unittest.TestCase):
    def test_duplicate_tool_span_id_rejects_entire_export(self):
        data = fixture()
        spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
        forged = copy.deepcopy(spans[1])
        forged["status"] = {"code": "STATUS_CODE_ERROR"}
        spans.append(forged)
        result = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertEqual([], result["tool_calls"])
        self.assertIn("중복", result["reason"])

    def test_duplicate_root_span_id_rejects_entire_export(self):
        data = fixture()
        spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
        duplicate = copy.deepcopy(spans[0])
        duplicate["status"] = {"code": "STATUS_CODE_ERROR"}
        spans.append(duplicate)
        result = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertEqual([], result["tool_calls"])
        self.assertIn("중복", result["reason"])

    def test_duplicate_invalid_time_still_rejected(self):
        data = fixture()
        spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
        duplicate = copy.deepcopy(spans[1])
        duplicate["endTimeUnixNano"] = "0"
        spans.append(duplicate)
        result = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertEqual([], result["tool_calls"])
        self.assertIn("중복", result["reason"])

    def test_non_string_parent_ids_fail_closed_not_type_error(self):
        for value in ([ROOT], {"id": ROOT}, 123, True):
            with self.subTest(parent=repr(value)):
                data = fixture()
                spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
                spans[1]["parentSpanId"] = value
                result = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
                self.assertEqual(["slack_thread"], [c["target"] for c in result["tool_calls"]])

    def test_same_span_id_in_different_trace_not_conflicting(self):
        data = fixture()
        spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
        other = copy.deepcopy(spans[1])
        other["traceId"] = "5" * 32
        spans.append(other)
        result = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertCountEqual(TARGETS, [c["target"] for c in result["tool_calls"]])


if __name__ == "__main__":
    unittest.main()

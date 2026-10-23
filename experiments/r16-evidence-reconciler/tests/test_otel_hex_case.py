"""Case-insensitive wire IDs per the official OTLP JSON specification."""
import copy
import unittest

from otel_evidence_adapter import adapt_otlp
from test_otel_evidence_adapter import fixture, RUN, TARGETS


def alpha_fixture():
    data = fixture()
    spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
    for item, span_id in zip(spans, ("b2" * 8, "c3" * 8, "d4" * 8)):
        item["traceId"] = "a1" * 16
        item["spanId"] = span_id
        item["parentSpanId"] = "" if item is spans[0] else "b2" * 8
        item["status"] = {"code": 1}
        item["kind"] = 1
    return data


class TestHexCase(unittest.TestCase):
    def test_uppercase_wire_ids_are_accepted_without_mutating_input(self):
        data = alpha_fixture()
        for item in data["resourceSpans"][0]["scopeSpans"][0]["spans"]:
            for key in ("traceId", "spanId", "parentSpanId"):
                item[key] = item[key].upper()
        before = copy.deepcopy(data)
        out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertEqual(before, data)
        self.assertEqual("a1" * 16, out["trace_id"])
        self.assertCountEqual(["current_handoff", "slack_thread"],
                              [c["target"] for c in out["tool_calls"]])
        self.assertCountEqual(["c3" * 8, "d4" * 8],
                              [c["span_id"] for c in out["tool_calls"]])

    def test_mixed_case_trace_and_parent_ids_keep_ancestry(self):
        for index in range(3):
            for field in ("traceId", "spanId", "parentSpanId"):
                with self.subTest(index=index, field=field):
                    data = alpha_fixture()
                    item = data["resourceSpans"][0]["scopeSpans"][0]["spans"][index]
                    item[field] = item[field].upper()
                    out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
                    self.assertCountEqual(["current_handoff", "slack_thread"],
                                          [c["target"] for c in out["tool_calls"]])

    def test_case_variants_of_same_identity_cannot_evade_duplicate_guard(self):
        for index in (0, 1):
            for first in (True, False):
                with self.subTest(index=index, first=first):
                    data = alpha_fixture()
                    spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
                    duplicate = copy.deepcopy(spans[index])
                    duplicate["traceId"] = duplicate["traceId"].upper()
                    duplicate["spanId"] = duplicate["spanId"].upper()
                    duplicate["status"] = {"code": 2}
                    spans.insert(0 if first else len(spans), duplicate)
                    self.assertEqual([], adapt_otlp(data, expected_run_id=RUN,
                                                    expected_targets=TARGETS)["tool_calls"])

    def test_normalization_preserves_separate_trace_identity(self):
        data = alpha_fixture()
        spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
        other_trace = copy.deepcopy(spans[1])
        other_trace["traceId"] = "e5" * 16
        spans[1]["traceId"] = spans[1]["traceId"].upper()
        spans[1]["spanId"] = spans[1]["spanId"].upper()
        spans.insert(0, other_trace)
        out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
        self.assertCountEqual(["current_handoff", "slack_thread"],
                              [c["target"] for c in out["tool_calls"]])


if __name__ == "__main__":
    unittest.main()

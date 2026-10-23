"""OTLP wire enum regressions; values independently from upstream trace.proto."""
import unittest

from otel_evidence_adapter import adapt_otlp
from test_otel_evidence_adapter import fixture, RUN, TARGETS


class TestOtelEnums(unittest.TestCase):
    def test_numeric_ok_accepts_root_and_tools(self):
        # trace.proto StatusCode: UNSET=0, OK=1, ERROR=2.
        for code in (1, "1", "STATUS_CODE_OK"):
            with self.subTest(code=code):
                data = fixture()
                for span in data["resourceSpans"][0]["scopeSpans"][0]["spans"]:
                    span["status"] = {"code": code}
                out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
                self.assertCountEqual(["current_handoff", "slack_thread"],
                                      [c["target"] for c in out["tool_calls"]])

    def test_error_root_cannot_supply_successful_tool_evidence(self):
        for code in (2, "2", "STATUS_CODE_ERROR"):
            with self.subTest(code=code):
                data = fixture()
                data["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["status"] = {"code": code}
                self.assertEqual([], adapt_otlp(data, expected_run_id=RUN,
                                                expected_targets=TARGETS)["tool_calls"])

    def test_error_tool_is_not_accepted_as_success(self):
        for code in (2, "2", "STATUS_CODE_ERROR"):
            with self.subTest(code=code):
                data = fixture()
                data["resourceSpans"][0]["scopeSpans"][0]["spans"][1]["status"] = {"code": code}
                out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
                self.assertEqual(["slack_thread"], [c["target"] for c in out["tool_calls"]])

    def test_boolean_and_float_status_codes_are_not_enums(self):
        for code in (True, False, 1.0, 2.0):
            with self.subTest(code=code, type=type(code).__name__):
                data = fixture()
                data["resourceSpans"][0]["scopeSpans"][0]["spans"][1]["status"] = {"code": code}
                out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
                self.assertEqual(["slack_thread"], [c["target"] for c in out["tool_calls"]])

    def test_boolean_and_float_kind_cannot_impersonate_internal(self):
        for kind in (True, 1.0):
            with self.subTest(kind=kind, type=type(kind).__name__):
                data = fixture()
                data["resourceSpans"][0]["scopeSpans"][0]["spans"][1]["kind"] = kind
                out = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
                self.assertEqual(["slack_thread"], [c["target"] for c in out["tool_calls"]])


if __name__ == "__main__":
    unittest.main()

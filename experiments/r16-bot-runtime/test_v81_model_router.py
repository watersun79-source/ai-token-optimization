"""Offline tests for routing only: do not call OpenAI or any provider."""
import contextlib
from io import StringIO
import json
import unittest

from v81_model_router import MODEL_IDS, make_plan, main


class ModelRouterTests(unittest.TestCase):
    def test_class_mapping_and_ids(self):
        self.assertEqual(MODEL_IDS, {
            "terra": "gpt-6.1-terra", "sol": "gpt-6.1-sol",
            "astra": "gpt-6-astra"})
        for task, model in {
            "routine": "terra", "screen": "terra", "scoped_fix": "terra",
            "engineering": "sol", "project": "sol", "deep_review": "astra",
        }.items():
            with self.subTest(task=task):
                plan = make_plan(task)
                self.assertEqual(plan["recommended_model"], model)
                self.assertEqual(plan["model_id"], MODEL_IDS[model])
                self.assertEqual(plan["status"], "ROUTING_ONLY_NOT_EXECUTED")
                self.assertEqual(plan["provider_calls"], 0)
                self.assertFalse(plan["external_paid_api_autocall"])
                self.assertEqual(plan["native_automation_execution"], "UNVERIFIED")
                self.assertEqual(plan["production_changes"], 0)

    def test_deep_review_and_material_risk_use_astra(self):
        self.assertEqual(make_plan("deep_review")["recommended_model"], "astra")
        self.assertEqual(make_plan("routine", material_risk=True)["recommended_model"], "astra")

    def test_escalate_only_after_repeat_failure(self):
        self.assertEqual(make_plan("routine", failed_checks=1)["recommended_model"], "terra")
        self.assertEqual(make_plan("routine", failed_checks=2)["recommended_model"], "sol")
        self.assertEqual(make_plan("engineering", failed_checks=2)["recommended_model"], "astra")

    def test_no_silent_fallback_on_unavailable(self):
        p = make_plan("deep_review", available_models=["terra", "sol"])
        self.assertEqual(p["model_availability"], "NOT_AVAILABLE_AS_DECLARED")
        self.assertEqual(p["recommended_model"], "astra")
        self.assertEqual(p["provider_calls"], 0)
        p = make_plan("routine", available_models=["terra"])
        self.assertEqual(p["model_availability"], "AVAILABLE_AS_DECLARED_NOT_AUTHENTICATED")

    def test_unknown_availability_remains_unverified(self):
        self.assertEqual(make_plan("project")["model_availability"], "UNVERIFIED")

    def test_bad_input_fails_closed(self):
        bad = [dict(task_kind="other"), dict(task_kind="routine", failed_checks=-1),
               dict(task_kind="routine", failed_checks=True),
               dict(task_kind="routine", material_risk="yes"),
               dict(task_kind="routine", available_models=["gpt-unknown"]),
               dict(task_kind="routine", available_models="terra")]
        for kwargs in bad:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    make_plan(**kwargs)

    def test_unhashable_task_kind_fails_closed(self):
        # JSON-originated task kinds can be arrays or objects, not only strings.
        for bad in ([], {}, ["routine"], {"routine": True}):
            with self.subTest(kind=type(bad).__name__):
                with self.assertRaisesRegex(ValueError, "unknown task kind"):
                    make_plan(bad)

    def test_cli_dry_run(self):
        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            ret = main(["--task-kind", "engineering", "--available-model", "sol"])
        self.assertEqual(ret, 0)
        plan = json.loads(stream.getvalue())
        self.assertEqual(plan["recommended_model"], "sol")
        self.assertEqual(plan["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()

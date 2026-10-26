"""Regression for the SHA-bound user-requested real GitHub runner task."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from queued_task_worker import execute, _append_job_summary


class QueuedTaskTests(unittest.TestCase):
    def setUp(self):
        message = "프롬프트 압축 실행\n반복 작업 생략\n반복 작업 생략\n증분 처리 우선"
        self.request = {
            "task_id": "r16-20261025-1713",
            "mode": "bounded_offline_optimize",
            "message": message,
            "expected_input_sha256": hashlib.sha256(message.encode("utf-8")).hexdigest()
        }

    def test_real_offline_worker_receipt_is_bound_to_input(self):
        output = execute(self.request)
        self.assertEqual(output["status"], "PASS")
        self.assertEqual(output["kind"],
                         "REAL_ISOLATED_GITHUB_HOSTED_PYTHON_TASK_NOT_NATIVE_CHATGPT")
        self.assertEqual(output["input_sha256"], self.request["expected_input_sha256"])
        self.assertGreater(output["bytes_saved"], 0)
        self.assertEqual(output["duplicate_lines_removed"], 1)
        self.assertEqual(output["external_model_calls"], 0)
        self.assertEqual(output["production_writes"], 0)
        self.assertFalse(output["native_chatgpt_run_verified"])

    def test_approved_receipt_is_recorded_without_input_text(self):
        receipt = execute(self.request)
        with TemporaryDirectory() as d:
            summary = Path(d) / "ci-summary.md"
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}):
                self.assertTrue(_append_job_summary(receipt))
            content = summary.read_text(encoding="utf-8")
        self.assertIn(receipt["task_id"], content)
        self.assertIn(receipt["input_sha256"], content)
        self.assertIn(receipt["output_sha256"], content)
        self.assertIn("ChatGPT native unattended run: UNVERIFIED", content)
        self.assertNotIn(self.request["message"], content)

    def test_invalid_or_unauthenticated_receipt_does_not_write_summary(self):
        receipt = execute(self.request)
        with TemporaryDirectory() as d:
            summary = Path(d) / "ci-summary.md"
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}):
                for altered in (
                    {**receipt, "status": "FAIL"},
                    {**receipt, "task_id": "r16-bad-`text"},
                    {**receipt, "native_chatgpt_run_verified": True},
                    {**receipt, "bytes_saved": -1},
                ):
                    with self.subTest(changed_keys=altered), self.assertRaises(ValueError):
                        _append_job_summary(altered)
            self.assertFalse(summary.exists())

    def test_digest_tampering_is_blocked(self):
        self.request["expected_input_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            execute(self.request)

    def test_unknown_mode_and_extra_fields_are_blocked(self):
        self.request["mode"] = "allow_network"
        with self.assertRaises(ValueError):
            execute(self.request)
        self.request["mode"] = "bounded_offline_optimize"
        self.request["new_key"] = "openapi"
        with self.assertRaises(ValueError):
            execute(self.request)

    def test_unapproved_role_is_blocked(self):
        text = "예약 GitHub 확인"
        self.request["message"] = text
        self.request["expected_input_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        with self.assertRaises(ValueError):
            execute(self.request)

    def test_credentials_are_rejected_without_echoing(self):
        credential = "github_pat_" + "x" * 25
        text = "프롬프트 압축 실행\n" + credential
        self.request["message"] = text
        self.request["expected_input_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        with self.assertRaises(ValueError) as err:
            execute(self.request)
        self.assertNotIn(credential, str(err.exception))


if __name__ == "__main__":
    unittest.main()

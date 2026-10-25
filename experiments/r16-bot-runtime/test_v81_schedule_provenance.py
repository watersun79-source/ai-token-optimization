"""Offline synthetic negative tests; never evidence of external model calls."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stdout
from io import StringIO
from v81_schedule_provenance import main, verify_schedule

WORKFLOW = "9097914284baf4896919e850c49690737d5715f3"
SOURCE = "353940b40b73b4001350ce07b323963bda14aa00"
RUN = {"id": 40159999999, "event": "schedule", "head_branch": "main",
       "head_sha": WORKFLOW, "path": ".github/workflows/ai-r16-hourly.yml",
       "status": "completed", "conclusion": "success"}
JOBS = [{"id": 121069999999, "run_id": RUN["id"], "name": "hourly-offline-audit",
         "status": "completed", "conclusion": "success"}]


def log_fixture():
    def record(mode, count, groups):
        return "R16_V81_SWARM=" + json.dumps({
            "mode": mode, "selected_roles": count, "group_count": groups,
            "independent_serial_oracle_match": True, "status": "PASS",
            "external_model_calls": 0, "native_chatgpt_run_verified": False,
            "production_changes": 0})
    return "\n".join((
        "HEAD is now at " + SOURCE[:7] + " checked source",
        "OFFLINE_SINGLE_PROCESS_100_RULE_CHECKS_NOT_100_LLM_MODELS",
        "R16_HOURLY_OFFLINE_RECEIPT_VALIDATED", "Ran 10 tests in 0.067s",
        record("audit", 20, 2), record("all", 100, 10),
        "Ran 8 tests in 0.188s", "C strict timestamp oracle: PASS 20/20",
    ))


def verify(run=RUN, jobs=JOBS, log=None):
    return verify_schedule(run, jobs, log_fixture() if log is None else log,
                           workflow_sha=WORKFLOW, source_sha=SOURCE)


class ProvenanceTests(unittest.TestCase):
    def test_positive_structure_never_authenticates_native(self):
        result = verify()
        self.assertEqual("PASS", result["status"])
        self.assertFalse(result["native_chatgpt_proven"])
        self.assertFalse(result["source_authenticated_here"])

    def test_absent_run_unverified(self):
        self.assertEqual("UNVERIFIED", verify(run=None)["status"])

    def test_push_not_schedule(self):
        self.assertEqual("NOT_APPLICABLE", verify(run=dict(RUN, event="push"))["status"])

    def test_missing_event_unverified(self):
        self.assertEqual("UNVERIFIED", verify(run={"id": RUN["id"]})["status"])

    def test_wrong_workflow_head_fails(self):
        self.assertEqual("FAIL", verify(run=dict(RUN, head_sha="a" * 40))["status"])

    def test_job_incomplete_unverified(self):
        jobs = [dict(JOBS[0], status="in_progress", conclusion=None)]
        self.assertEqual("UNVERIFIED", verify(jobs=jobs)["status"])

    def test_job_failure_fails(self):
        self.assertEqual("FAIL", verify(jobs=[dict(JOBS[0], conclusion="failure")])["status"])

    def test_mismatched_job_run_id_unverified(self):
        self.assertEqual("UNVERIFIED", verify(jobs=[dict(JOBS[0], run_id=1)])["status"])

    def test_wrong_checkout_unverified(self):
        self.assertEqual("UNVERIFIED", verify(log=log_fixture().replace(SOURCE[:7], "abcdef0"))["status"])

    def test_missing_c_oracle_unverified(self):
        self.assertEqual("UNVERIFIED", verify(log=log_fixture().replace(
            "C strict timestamp oracle: PASS 20/20", ""))["status"])

    def test_swarm_fail(self):
        self.assertEqual("FAIL", verify(log=log_fixture().replace(
            '"status": "PASS"', '"status": "FAIL"', 1))["status"])

    def test_duplicate_swarm_unverified(self):
        receipt = next(x for x in log_fixture().splitlines() if '"mode": "audit"' in x)
        self.assertEqual("UNVERIFIED", verify(log=log_fixture()+"\n"+receipt)["status"])

    def test_bad_ids_unverified(self):
        self.assertEqual("UNVERIFIED", verify(run=dict(RUN, id=True))["status"])
        self.assertEqual("UNVERIFIED", verify(run=dict(RUN, id=None))["status"])

    def test_missing_log_unverified(self):
        self.assertEqual("UNVERIFIED", verify_schedule(
            RUN, JOBS, None, workflow_sha=WORKFLOW, source_sha=SOURCE)["status"])

    def test_cli_json(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "evidence.json"
            path.write_text(json.dumps({"run": RUN, "jobs": JOBS,
                "log": log_fixture(), "workflow_sha": WORKFLOW,
                "source_sha": SOURCE}), encoding="utf8")
            import sys
            old = sys.argv
            try:
                sys.argv = ["v81_schedule_provenance.py", "--input", str(path)]
                with redirect_stdout(StringIO()) as output:
                    result = main()
            finally:
                sys.argv = old
            self.assertEqual(0, result)
            self.assertFalse(json.loads(output.getvalue())["native_chatgpt_proven"])


if __name__ == "__main__":
    unittest.main()

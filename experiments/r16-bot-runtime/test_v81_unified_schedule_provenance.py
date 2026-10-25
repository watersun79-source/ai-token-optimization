"""Offline synthetic API fixtures; NOT a real GitHub API attestation."""
import copy
import hashlib
import json
import unittest

from v81_unified_schedule_provenance import verify, COUNTS

WORKFLOW = "923c281f82023cc6b49f3844bad17f508f1ab203"
SOURCE = "a88c7993c27404da43cba84a8f69e01a917315a6"
ID = 40169999999


def receipt():
    raw = {
        "format": "V81_OFFLINE_UNIFIED_EVIDENCE_V1",
        "scope": "ISOLATED_LOCAL_OFFLINE_NOT_NATIVE_PLATFORM",
        "status": "PASS", "languages": COUNTS, "language_total": 83,
        "local_swarm": {
            "fast_pass": 20, "full_pass": 100, "groups": 10, "worker_cap": 4,
            "independent_serial_oracle_match": True, "input_sha256": "a" * 64,
        },
        "source_sha256": {"v81_swarm.py": "b" * 64},
        "runner_context_self_reported": {
            "github_run_id": str(ID), "github_sha": WORKFLOW,
            "github_event": "schedule",
        },
        "native_chatgpt_run_verified": False,
        "same_run_github_slack_proven": False,
        "github_api_run_verified": False,
        "runner_context_officially_authenticated": False,
        "external_model_calls": 0, "production_changes": 0,
        "real_external_llm_agents": 0,
    }
    raw["evidence_sha256"] = hashlib.sha256(json.dumps(
        raw, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()
    return raw


def build(replace=None, rec=None):
    run = {"id": ID, "event": "schedule", "head_branch": "main",
           "head_sha": WORKFLOW, "path": ".github/workflows/ai-r16-hourly.yml",
           "status": "completed", "conclusion": "success"}
    job = [{"id": 12108888888, "run_id": ID, "name": "hourly-offline-audit",
            "status": "completed", "conclusion": "success"}]
    obj = rec if rec is not None else receipt()
    log = ("\n".join([
        "2026-10-25T05:36:00Z [command]/usr/bin/git checkout --progress --force " + SOURCE,
        "2026-10-25T05:36:01Z R16_HOURLY_OFFLINE_RECEIPT_VALIDATED",
        "2026-10-25T05:36:01Z Ran 31 tests in 0.245s",
        "2026-10-25T05:36:02Z R16_V81_UNIFIED_EVIDENCE=" +
        json.dumps(obj, sort_keys=True, ensure_ascii=False),
    ]) + "\n")
    if replace:
        log = replace(log)
    return run, job, log


class UnifiedScheduledProofTests(unittest.TestCase):
    def verify(self, run=None, jobs=None, log=None):
        fixture = build()
        return verify(fixture[0] if run is None else run,
                      fixture[1] if jobs is None else jobs,
                      fixture[2] if log is None else log,
                      workflow_sha=WORKFLOW, source_sha=SOURCE)

    def test_positive_synthetic_schedule_only(self):
        r = self.verify()
        self.assertEqual("PASS", r["status"])
        self.assertFalse(r["github_api_inputs_authenticated_here"])
        self.assertFalse(r["native_chatgpt_run_verified"])
        self.assertEqual(83, sum(r["counts"].values()))

    def test_push_is_not_schedule(self):
        run, _, _ = build()
        self.assertEqual("NOT_APPLICABLE", self.verify(run=dict(run, event="push"))["status"])

    def test_wrong_sha_fails(self):
        run, _, _ = build()
        self.assertEqual("FAIL", self.verify(run=dict(run, head_sha="c"*40))["status"])

    def test_missing_official_run_unverified(self):
        _, jobs, log = build()
        self.assertEqual("UNVERIFIED", verify(None, jobs, log, workflow_sha=WORKFLOW,
                                              source_sha=SOURCE)["status"])

    def test_absent_or_wrong_job_unverified(self):
        self.assertEqual("UNVERIFIED", self.verify(jobs=[])["status"])
        _, jobs, _ = build()
        self.assertEqual("UNVERIFIED",
                         self.verify(jobs=[dict(jobs[0], run_id=1)])["status"])

    def test_false_or_failed_job_blocks(self):
        _, jobs, _ = build()
        self.assertEqual("FAIL", self.verify(jobs=[dict(jobs[0], conclusion="failure")])["status"])
        self.assertEqual("UNVERIFIED",
                         self.verify(jobs=[dict(jobs[0], status="in_progress")])["status"])

    def test_wrong_checkout_sha_not_authenticated(self):
        _, _, log = build()
        self.assertEqual("UNVERIFIED",
                         self.verify(log=log.replace(SOURCE, "d"*40))["status"])

    def test_duplicate_checkout_blocked(self):
        _, _, log = build()
        head = log.splitlines()[0] + "\n"
        self.assertEqual("UNVERIFIED", self.verify(log=log+head)["status"])

    def test_duplicate_receipt_blocked(self):
        _, _, log = build()
        marker = [x for x in log.splitlines() if "R16_V81_UNIFIED_EVIDENCE=" in x][0]
        self.assertEqual("UNVERIFIED", self.verify(log=log+marker+"\n")["status"])

    def test_forged_receipt_sha_fails(self):
        x = receipt()
        x["evidence_sha256"] = "0"*64
        _, _, log = build(rec=x)
        self.assertEqual("FAIL", self.verify(log=log)["status"])

    def test_changed_languages_recomputed_digest_still_fails(self):
        x = receipt()
        x["languages"]["c"] = 19
        x.pop("evidence_sha256")
        x["evidence_sha256"] = hashlib.sha256(json.dumps(
            x, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        _, _, log = build(rec=x)
        self.assertEqual("FAIL", self.verify(log=log)["status"])

    def test_environment_run_link_required(self):
        x = receipt()
        x["runner_context_self_reported"]["github_run_id"] = "999"
        x.pop("evidence_sha256")
        x["evidence_sha256"] = hashlib.sha256(json.dumps(
            x, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        _, _, log = build(rec=x)
        self.assertEqual("FAIL", self.verify(log=log)["status"])

    def test_native_attestation_spoof_is_rejected(self):
        x = receipt()
        x["native_chatgpt_run_verified"] = True
        x.pop("evidence_sha256")
        x["evidence_sha256"] = hashlib.sha256(json.dumps(
            x, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        _, _, log = build(rec=x)
        self.assertEqual("FAIL", self.verify(log=log)["status"])

    def test_missing_regression_line_unverified(self):
        _, _, log = build()
        self.assertEqual("UNVERIFIED", self.verify(log=log.replace("Ran 31 tests", "Ran 30 tests"))["status"])

    def test_unexpected_boolean_job_id_blocked(self):
        _, jobs, _ = build()
        self.assertEqual("UNVERIFIED",
                         self.verify(jobs=[dict(jobs[0], id=True)])["status"])

    def test_empty_or_bad_json_unverified(self):
        self.assertEqual("UNVERIFIED", self.verify(log="")["status"])
        _, _, log = build()
        self.assertEqual("UNVERIFIED", self.verify(log=log.replace('"format"', '"format"BAD', 1))["status"])


if __name__ == "__main__":
    unittest.main()

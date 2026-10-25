"""Mock GitHub API tests: no network, token, or real native-run attestation."""
import copy
import json
import tempfile
from pathlib import Path
import unittest
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch

from test_v81_unified_schedule_provenance import build, WORKFLOW, SOURCE
from v81_live_schedule_collector import collect, gh_read, GitHubReadError, main

REPO = "watersun79-source/ai-token-optimization"
BASE = "/repos/" + REPO


def fake_api(*, mode="ok", bad_log=False):
    run, jobs, log = build()
    run["run_number"] = 100
    old = dict(run, id=run["id"] - 1, head_sha="f"*40, run_number=99)
    if mode == "old":
        run["head_sha"] = "f"*40
    if mode == "running":
        run["status"] = "in_progress"
        run["conclusion"] = None
    if mode == "job_failed":
        jobs[0]["conclusion"] = "failure"
    if mode == "wrong_job":
        jobs[0]["run_id"] = 2
    runs = [] if mode == "missing_run" else [run, old]
    values = {
        BASE + "/actions/runs?event=schedule&per_page=20":
            json.dumps({"workflow_runs": runs}),
        BASE + "/actions/runs/" + str(run["id"]) + "/jobs?per_page=100":
            json.dumps({"jobs": jobs}),
        BASE + "/actions/jobs/" + str(jobs[0]["id"]) + "/logs":
            "garbage" if bad_log else log,
    }
    seen = []
    def fetch(path):
        seen.append(path)
        if path not in values:
            raise GitHubReadError("MOCK_NOT_FOUND")
        return values[path]
    return fetch, seen


class LiveCollectorTests(unittest.TestCase):
    def test_complete_matching_schedule_cross_checks(self):
        fetch, seen = fake_api()
        out = collect(fetch, REPO, WORKFLOW, SOURCE)
        self.assertEqual("PASS", out["status"])
        self.assertTrue(out["official_github_api_get_attempted"])
        self.assertEqual(3, len(seen))
        self.assertTrue(all("/actions/" in p for p in seen))
        self.assertFalse(out["native_chatgpt_run_verified"])

    def test_previous_schedule_not_promoted(self):
        fetch, seen = fake_api(mode="old")
        out = collect(fetch, REPO, WORKFLOW, SOURCE)
        self.assertEqual("NOT_APPLICABLE", out["status"])
        self.assertEqual("EXPECTED_NEW_SCHEDULE_NOT_OBSERVED", out["reason"])
        self.assertEqual(1, len(seen))

    def test_no_schedule_unverified(self):
        fetch, seen = fake_api(mode="missing_run")
        self.assertEqual("UNVERIFIED", collect(fetch, REPO, WORKFLOW, SOURCE)["status"])
        self.assertEqual(1, len(seen))

    def test_running_unverified(self):
        fetch, seen = fake_api(mode="running")
        self.assertEqual("UNVERIFIED", collect(fetch, REPO, WORKFLOW, SOURCE)["status"])
        self.assertEqual(1, len(seen))

    def test_failed_job_blocks(self):
        fetch, seen = fake_api(mode="job_failed")
        self.assertEqual("FAIL", collect(fetch, REPO, WORKFLOW, SOURCE)["status"])
        self.assertEqual(2, len(seen))

    def test_wrong_job_unverified(self):
        fetch, seen = fake_api(mode="wrong_job")
        self.assertEqual("UNVERIFIED", collect(fetch, REPO, WORKFLOW, SOURCE)["status"])
        self.assertEqual(2, len(seen))

    def test_bad_log_not_promoted(self):
        fetch, seen = fake_api(bad_log=True)
        self.assertEqual("UNVERIFIED", collect(fetch, REPO, WORKFLOW, SOURCE)["status"])
        self.assertEqual(3, len(seen))

    def test_invalid_repo_no_queries(self):
        fetch, seen = fake_api()
        self.assertEqual("UNVERIFIED", collect(fetch, "../evil", WORKFLOW, SOURCE)["status"])
        self.assertEqual([], seen)

    def test_direct_get_path_traversal_blocked(self):
        with patch.dict("os.environ", {"GH_TOKEN": "dummy-test-token"}), patch(
                "v81_live_schedule_collector.subprocess.run") as proc:
            with self.assertRaises(GitHubReadError):
                gh_read("/repos/../evil/actions/runs?event=schedule&per_page=20")
            proc.assert_not_called()

    def test_missing_token_no_process(self):
        with patch.dict("os.environ", {"GH_TOKEN": ""}), patch(
                "v81_live_schedule_collector.subprocess.run") as proc:
            with self.assertRaises(GitHubReadError):
                gh_read(BASE + "/actions/runs?event=schedule&per_page=20")
            proc.assert_not_called()

    def test_only_allowlisted_get(self):
        with patch.dict("os.environ", {"GH_TOKEN": "dummy-test-token"}), patch(
                "v81_live_schedule_collector.subprocess.run") as proc:
            with self.assertRaises(GitHubReadError):
                gh_read(BASE + "/issues")
            proc.assert_not_called()

    def test_no_token_in_process_arguments(self):
        class Proc:
            returncode = 0
            stdout = '{"workflow_runs":[]}'
        with patch.dict("os.environ", {"GH_TOKEN": "dummy-test-token"}), patch(
                "v81_live_schedule_collector.subprocess.run", return_value=Proc()) as proc:
            self.assertEqual('{"workflow_runs":[]}',
                             gh_read(BASE + "/actions/runs?event=schedule&per_page=20"))
            args = proc.call_args.args[0]
            self.assertEqual(["gh", "api", "--method", "GET"], args[:4])
            self.assertNotIn("dummy-test-token", repr(args))
            self.assertFalse(proc.call_args.kwargs.get("shell", False))

    def test_api_failure_unverified(self):
        def fetch(_):
            raise GitHubReadError("GITHUB_API_GET_FAILED")
        out = collect(fetch, REPO, WORKFLOW, SOURCE)
        self.assertEqual("UNVERIFIED", out["status"])
        self.assertEqual("GITHUB_API_GET_FAILED", out["reason"])

    def test_ambiguous_latest_not_pass(self):
        fetch, seen = fake_api()
        raw = fetch(BASE + "/actions/runs?event=schedule&per_page=20")
        data = json.loads(raw)
        data["workflow_runs"].append(copy.deepcopy(data["workflow_runs"][0]))
        def dup(path):
            if path.endswith("/runs?event=schedule&per_page=20"):
                return json.dumps(data)
            return fetch(path)
        self.assertEqual("UNVERIFIED", collect(dup, REPO, WORKFLOW, SOURCE)["status"])

    def test_missing_job_metadata(self):
        fetch, seen = fake_api()
        def invalid(path):
            if path.endswith("/jobs?per_page=100"):
                return json.dumps({"jobs": []})
            return fetch(path)
        self.assertEqual("UNVERIFIED", collect(invalid, REPO, WORKFLOW, SOURCE)["status"])

    def test_cli_marks_successful_official_get_even_before_new_schedule(self):
        fetch, seen = fake_api(mode="old")
        argv = ["v81_live_schedule_collector.py", "--repository", REPO,
                "--expected-workflow-sha", WORKFLOW,
                "--expected-source-sha", SOURCE]
        with patch("sys.argv", argv), patch(
                "v81_live_schedule_collector.gh_read", side_effect=fetch), redirect_stdout(StringIO()) as output:
            self.assertEqual(0, main())
        raw = output.getvalue().split("R16_V81_LIVE_SCHEDULE_CHECK=", 1)[1]
        result = json.loads(raw)
        self.assertEqual("NOT_APPLICABLE", result["status"])
        self.assertTrue(result["official_github_api_get_attempted"])
        self.assertEqual(1, len(seen))


    def test_cli_exports_sanitized_cloud_receipt_without_promoting_native(self):
        fetch, seen = fake_api(mode="old")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cloud-receipt.json"
            argv = ["v81_live_schedule_collector.py", "--repository", REPO,
                    "--expected-workflow-sha", WORKFLOW,
                    "--expected-source-sha", SOURCE,
                    "--output-json", str(path)]
            with patch("sys.argv", argv), patch(
                    "v81_live_schedule_collector.gh_read", side_effect=fetch), redirect_stdout(StringIO()) as printed:
                self.assertEqual(0, main())
            receipt = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("NOT_APPLICABLE", receipt["status"])
            self.assertTrue(receipt["official_github_api_get_attempted"])
            self.assertFalse(receipt["native_chatgpt_run_verified"])
            self.assertFalse(receipt["same_run_github_slack_proven"])
            self.assertEqual(1, len(seen))
            self.assertIn(json.dumps(receipt, sort_keys=True, ensure_ascii=False),
                          printed.getvalue())
            self.assertNotIn("GH_TOKEN", path.read_text(encoding="utf-8"))

    def test_json_corruption_unverified(self):
        def corrupt(_):
            return "<html>"
        self.assertEqual("UNVERIFIED", collect(corrupt, REPO, WORKFLOW, SOURCE)["status"])


if __name__ == "__main__":
    unittest.main()

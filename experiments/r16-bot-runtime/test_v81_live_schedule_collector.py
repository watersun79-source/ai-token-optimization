"""Mock GitHub API tests: no network, token, or real native-run attestation."""
import copy
import base64
import json
import unittest
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch

from test_v81_unified_schedule_provenance import build, WORKFLOW, SOURCE
from v81_live_schedule_collector import collect, gh_read, GitHubReadError, main, resolve_main_target

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
    workflow = (
        "name: hourly\n"
        "on:\n  schedule:\n    - cron: '15 * * * *'\n"
        "jobs:\n  audit:\n    steps:\n      - uses: actions/checkout@sha\n"
        "        with:\n          ref: " + SOURCE + "\n"
    )
    values = {
        BASE + "/git/ref/heads/main":
            json.dumps({"ref": "refs/heads/main", "object": {"sha": WORKFLOW}}),
        BASE + "/contents/.github/workflows/ai-r16-hourly.yml?ref=" + WORKFLOW:
            json.dumps({"type": "file", "encoding": "base64",
                        "path": ".github/workflows/ai-r16-hourly.yml",
                        "content": base64.b64encode(workflow.encode()).decode()}),
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
        self.assertEqual("UNVERIFIED", out["status"])
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

    def test_failed_run_blocks_before_jobs(self):
        fetch, seen = fake_api()
        def failed(path):
            raw = fetch(path)
            if path.endswith("/runs?event=schedule&per_page=20"):
                obj = json.loads(raw)
                obj["workflow_runs"][0]["conclusion"] = "failure"
                return json.dumps(obj)
            return raw
        out = collect(failed, REPO, WORKFLOW, SOURCE)
        self.assertEqual("FAIL", out["status"])
        self.assertEqual("OFFICIAL_RUN_FAILED", out["reason"])
        self.assertEqual(1, len(seen))

    def test_missing_run_conclusion_unverified(self):
        fetch, seen = fake_api()
        def missing(path):
            raw = fetch(path)
            if path.endswith("/runs?event=schedule&per_page=20"):
                obj = json.loads(raw)
                obj["workflow_runs"][0].pop("conclusion", None)
                return json.dumps(obj)
            return raw
        out = collect(missing, REPO, WORKFLOW, SOURCE)
        self.assertEqual("UNVERIFIED", out["status"])
        self.assertEqual("OFFICIAL_RUN_CONCLUSION_MISSING", out["reason"])
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

    def test_gh_http_error_classification_is_redacted(self):
        endpoint = BASE + "/actions/runs?event=schedule&per_page=20"
        class Proc:
            returncode = 1
            stdout = ""
            stderr = ("gh: HTTP 403: Resource not accessible by integration "
                      "token=DO_NOT_LEAK_TEST_SECRET")
        with patch.dict("os.environ", {"GH_TOKEN": "another-secret"}), patch(
                "v81_live_schedule_collector.subprocess.run",
                return_value=Proc()) as proc:
            with self.assertRaises(GitHubReadError) as error:
                gh_read(endpoint)
            self.assertEqual("GITHUB_API_HTTP_403", str(error.exception))
            self.assertNotIn("DO_NOT_LEAK", str(error.exception))
            self.assertNotIn("another-secret", repr(proc.call_args.args[0]))

    def test_gh_network_error_and_unknown_error_are_redacted(self):
        endpoint = BASE + "/actions/runs?event=schedule&per_page=20"
        class Proc:
            returncode = 1
            stdout = ""
            stderr = "lookup api.github.com: no such host"
        with patch.dict("os.environ", {"GH_TOKEN": "dummy-test-token"}), patch(
                "v81_live_schedule_collector.subprocess.run",
                return_value=Proc()):
            with self.assertRaisesRegex(
                    GitHubReadError, "^GITHUB_API_NETWORK_UNAVAILABLE$"):
                gh_read(endpoint)
            Proc.stderr = "unclassified failure token=DO_NOT_LEAK_TEST_SECRET"
            with self.assertRaisesRegex(GitHubReadError, "^GITHUB_API_GET_FAILED$"):
                gh_read(endpoint)

    def test_safe_http_failure_keeps_official_run_unverified(self):
        def fetch(_):
            raise GitHubReadError("GITHUB_API_HTTP_403")
        result = collect(fetch, REPO, WORKFLOW, SOURCE)
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertEqual("GITHUB_API_HTTP_403", result["reason"])
        self.assertFalse(result["native_chatgpt_run_verified"])

    def test_api_failures_identify_bounded_read_stage(self):
        for stage, suffix in (
            ("RUN_LIST", "/actions/runs?event=schedule&per_page=20"),
            ("JOBS", "/jobs?per_page=100"),
            ("JOB_LOG", "/logs"),
        ):
            with self.subTest(stage=stage):
                fetch, seen = fake_api()
                def fail_at_stage(path):
                    if path.endswith(suffix):
                        raise GitHubReadError("GITHUB_API_GET_FAILED")
                    return fetch(path)
                result = collect(fail_at_stage, REPO, WORKFLOW, SOURCE)
                self.assertEqual("UNVERIFIED", result["status"])
                self.assertEqual("GITHUB_API_GET_FAILED", result["reason"])
                self.assertEqual(stage, result["failed_stage"])
                self.assertFalse(result["native_chatgpt_run_verified"])

    def test_api_error_stage_is_never_a_native_success_claim(self):
        fetch, seen = fake_api()
        def fail_log(path):
            if path.endswith("/logs"):
                raise GitHubReadError("GITHUB_API_HTTP_403")
            return fetch(path)
        result = collect(fail_log, REPO, WORKFLOW, SOURCE)
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertEqual("JOB_LOG", result["failed_stage"])
        self.assertEqual("GITHUB_API_HTTP_403", result["reason"])

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
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertTrue(result["official_github_api_get_attempted"])
        self.assertEqual(1, len(seen))

    def test_auto_resolves_live_main_and_pinned_source(self):
        fetch, seen = fake_api()
        self.assertEqual((WORKFLOW, SOURCE), resolve_main_target(fetch, REPO))
        argv = ["v81_live_schedule_collector.py", "--repository", REPO]
        with patch("sys.argv", argv), patch(
                "v81_live_schedule_collector.gh_read", side_effect=fetch), redirect_stdout(StringIO()) as out:
            self.assertEqual(0, main())
        obj = json.loads(out.getvalue().split("R16_V81_LIVE_SCHEDULE_CHECK=", 1)[1])
        self.assertEqual("PASS", obj["status"])
        self.assertEqual("OFFICIAL_MAIN_REF_AND_PINNED_WORKFLOW", obj["target_resolution"])
        self.assertEqual(WORKFLOW, obj["expected_workflow_sha"])
        self.assertEqual(SOURCE, obj["expected_source_sha"])
        self.assertFalse(obj["native_chatgpt_run_verified"])
        self.assertGreaterEqual(len(seen), 5)

    def test_auto_old_schedule_cannot_be_promoted(self):
        fetch, seen = fake_api(mode="old")
        argv = ["v81_live_schedule_collector.py", "--repository", REPO]
        with patch("sys.argv", argv), patch(
                "v81_live_schedule_collector.gh_read", side_effect=fetch), redirect_stdout(StringIO()) as out:
            self.assertEqual(0, main())
        obj = json.loads(out.getvalue().split("R16_V81_LIVE_SCHEDULE_CHECK=", 1)[1])
        self.assertEqual("UNVERIFIED", obj["status"])
        self.assertEqual("EXPECTED_NEW_SCHEDULE_NOT_OBSERVED", obj["reason"])
        self.assertEqual(3, len(seen))

    def test_auto_rejects_changed_protected_cron(self):
        fetch, _ = fake_api()
        def altered(endpoint):
            raw = fetch(endpoint)
            if "/contents/" in endpoint:
                obj = json.loads(raw)
                data = base64.b64decode(obj["content"]).decode().replace(
                    "15 * * * *", "* * * * *")
                obj["content"] = base64.b64encode(data.encode()).decode()
                return json.dumps(obj)
            return raw
        with self.assertRaises(GitHubReadError) as ex:
            resolve_main_target(altered, REPO)
        self.assertEqual("PROTECTED_HOURLY_CRON_MISMATCH", str(ex.exception))

    def test_auto_rejects_second_cron_even_when_protected_slot_exists(self):
        fetch, _ = fake_api()
        def altered(endpoint):
            raw = fetch(endpoint)
            if "/contents/" in endpoint:
                obj = json.loads(raw)
                data = base64.b64decode(obj["content"]).decode()
                data = data.replace(
                    "    - cron: '15 * * * *'",
                    "    - cron: '15 * * * *'\n    - cron: '30 * * * *'")
                obj["content"] = base64.b64encode(data.encode()).decode()
                return json.dumps(obj)
            return raw
        with self.assertRaises(GitHubReadError) as ex:
            resolve_main_target(altered, REPO)
        self.assertEqual("PROTECTED_HOURLY_CRON_MISMATCH", str(ex.exception))

    def test_auto_rejects_duplicate_checkout_ref(self):
        fetch, _ = fake_api()
        def altered(endpoint):
            raw = fetch(endpoint)
            if "/contents/" in endpoint:
                obj = json.loads(raw)
                data = base64.b64decode(obj["content"]).decode()
                data += "\n          ref: " + "f" * 40 + "\n"
                obj["content"] = base64.b64encode(data.encode()).decode()
                return json.dumps(obj)
            return raw
        with self.assertRaises(GitHubReadError) as ex:
            resolve_main_target(altered, REPO)
        self.assertEqual("PINNED_SOURCE_NOT_UNIQUE", str(ex.exception))

    def test_auto_rejects_bad_workflow_encoding(self):
        fetch, _ = fake_api()
        def altered(endpoint):
            raw = fetch(endpoint)
            if "/contents/" in endpoint:
                obj = json.loads(raw)
                obj["content"] = "$$"
                return json.dumps(obj)
            return raw
        with self.assertRaises(GitHubReadError) as ex:
            resolve_main_target(altered, REPO)
        self.assertEqual("WORKFLOW_ENCODING_INVALID", str(ex.exception))

    def test_incomplete_manual_sha_pair_never_uses_api(self):
        argv = ["v81_live_schedule_collector.py", "--repository", REPO,
                "--expected-workflow-sha", WORKFLOW]
        with patch("sys.argv", argv), patch(
                "v81_live_schedule_collector.gh_read") as reader, redirect_stdout(StringIO()) as out:
            self.assertEqual(0, main())
        obj = json.loads(out.getvalue().split("R16_V81_LIVE_SCHEDULE_CHECK=", 1)[1])
        self.assertEqual("UNVERIFIED", obj["status"])
        self.assertEqual("EXPECTED_SHA_PAIR_REQUIRED", obj["reason"])
        reader.assert_not_called()

    def test_main_ref_and_contents_path_allowlist(self):
        with patch.dict("os.environ", {"GH_TOKEN": "dummy"}), patch(
                "v81_live_schedule_collector.subprocess.run") as process:
            for endpoint in (
                    BASE + "/git/ref/heads/other",
                    BASE + "/contents/.github/workflows/ai-r16-hourly.yml?ref=main",
                    BASE + "/contents/.github/workflows/ai-r16-hourly.yml?ref=" + "a" * 39 + "Z"):
                with self.subTest(endpoint=endpoint), self.assertRaises(GitHubReadError):
                    gh_read(endpoint)
            process.assert_not_called()

    def test_json_corruption_unverified(self):
        def corrupt(_):
            return "<html>"
        self.assertEqual("UNVERIFIED", collect(corrupt, REPO, WORKFLOW, SOURCE)["status"])


if __name__ == "__main__":
    unittest.main()

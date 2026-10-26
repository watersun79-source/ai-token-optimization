"""Real local executor regression; no network or model calls."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from task_executor import compact

class TaskExecutorTests(unittest.TestCase):
    def test_real_dedup(self):
        r=compact("alpha\nbeta\nalpha\n  beta  \ngamma\n")
        self.assertEqual(r["output"],"alpha\nbeta\ngamma")
        self.assertEqual(r["duplicate_lines_removed"],2)
        self.assertGreater(r["bytes_saved"],0)
        self.assertEqual(r["external_model_calls"],0)

    def test_no_fake_savings(self):
        self.assertEqual(compact("alpha\nbeta")["bytes_saved"],0)

    def test_secret_refused(self):
        with self.assertRaises(ValueError):
            compact("api_key=supersecretkey12345")

    def test_github_pat_and_auth_tokens_blocked(self):
        for secret in (
            "ghp_" + "a" * 36,
            "github_pat_" + "A" * 36,
            "access_token=" + "x" * 30,
            "auth-token:" + "y" * 30,
        ):
            with self.subTest(prefix=secret[:6]):
                with self.assertRaisesRegex(ValueError, "credential"):
                    compact("safe\n" + secret + "\n")

    def test_prefixed_environment_secrets_blocked(self):
        for name in ("OPENAI_API_KEY", "GITHUB_TOKEN",
                     "SLACK_BOT_TOKEN", "DATABASE_PASSWORD"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "credential"):
                    compact(name + "=notARealSecret1234567")

    def test_authorization_headers_blocked_without_leak(self):
        for scheme in ("Bearer", "Basic"):
            credential = "Authorization: " + scheme + " notARealSecret1234567"
            with self.subTest(scheme=scheme):
                with self.assertRaisesRegex(ValueError, "credential"):
                    compact(credential)
                p = subprocess.run(
                    [sys.executable, str(Path(__file__).with_name("task_executor.py")), "--stdin"],
                    input=credential, text=True, capture_output=True, timeout=3)
                self.assertEqual(p.returncode, 2)
                self.assertNotIn("notARealSecret1234567", p.stdout)

    def test_quoted_config_credential_refused(self):
        cases = (
            '{"OPENAI_API_KEY": "fakeValue12345678"}',
            '{"GITHUB_TOKEN": "fakeValue12345678"}',
            "{'SLACK_BOT_TOKEN': 'fakeValue12345678'}",
            '{"DATABASE_PASSWORD":"fakeValue12345678"}',
        )
        for message in cases:
            with self.subTest(name=message.split(":")[0]):
                with self.assertRaisesRegex(ValueError, "credential"):
                    compact(message)

    def test_quoted_config_cli_does_not_echo_secret(self):
        message = '{"OPENAI_API_KEY": "fakeValue12345678"}'
        p = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("task_executor.py")), "--stdin"],
            input=message, text=True, capture_output=True, timeout=3)
        self.assertEqual(p.returncode, 2)
        self.assertIn("BLOCKED", p.stdout)
        self.assertNotIn("fakeValue12345678", p.stdout)

    def test_quoted_authorization_json_and_mapping_headers_blocked(self):
        messages = (
            '{"Authorization":"Bearer fakeValue12345678"}',
            '{"authorization": "Basic fakeValue12345678"}',
            "{'HTTP_AUTHORIZATION': 'Bearer fakeValue12345678'}",
        )
        for message in messages:
            with self.subTest(header=message.split(":")[0]):
                with self.assertRaisesRegex(ValueError, "credential"):
                    compact(message)

    def test_quoted_authorization_cli_never_echoes_value(self):
        message = '{"Authorization": "Bearer fakeValue12345678"}'
        process = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("task_executor.py")), "--stdin"],
            input=message, text=True, capture_output=True, timeout=3)
        self.assertEqual(process.returncode, 2)
        self.assertIn("BLOCKED", process.stdout)
        self.assertNotIn("fakeValue12345678", process.stdout)

    def test_json_array_repeated_elements_preserved(self):
        message = '[\n  "task",\n  "task",\n  "done"\n]'
        report = compact(message)
        self.assertEqual(report["output"], message)
        self.assertEqual(json.loads(report["output"]), ["task", "task", "done"])
        self.assertEqual(report["duplicate_lines_removed"], 0)
        self.assertEqual(report["bytes_saved"], 0)

    def test_json_object_nested_array_and_whitespace_preserved(self):
        message = '{\n "steps": [\n  "repeat",\n  "repeat"\n ]\n}\n'
        report = compact(message)
        self.assertEqual(report["output"], message)
        self.assertEqual(json.loads(report["output"])["steps"], ["repeat", "repeat"])
        self.assertEqual(report["bytes_saved"], 0)

    def test_json_secret_guard_still_precedes_preservation(self):
        with self.assertRaisesRegex(ValueError, "credential"):
            compact('{"GITHUB_TOKEN": "fakeValue12345678"}')

    def test_noncredential_json_still_allowed(self):
        message = '{"title": "example_value123"}'
        self.assertEqual(compact(message)["output"], message)

    def test_bad_input_refused(self):
        for value in (""," "*12,"a"*4001,None):
            with self.assertRaises(ValueError):
                compact(value)

    def test_fenced_code_keeps_repeated_statements_and_indentation(self):
        fence = chr(96) * 3
        text = "summary\nsummary\n" + fence + "python\n    print(1)\n    print(1)\n\n" + fence + "\n"
        result = compact(text)
        self.assertEqual(result["duplicate_lines_removed"], 1)
        self.assertIn("    print(1)\n    print(1)\n\n", result["output"])

    def test_unclosed_code_fence_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "unclosed code fence"):
            compact((chr(96) * 3) + "python\n  x = 1")

    def test_code_fence_duplicate_text_is_not_deduplicated(self):
        fence = chr(96) * 3
        result = compact(fence + "\nx = 1\nx = 1\n" + fence)
        self.assertEqual(result["duplicate_lines_removed"], 0)

    def test_prompt_duplicate_text_still_removed(self):
        result = compact("repeat\nrepeat\nunique")
        self.assertEqual(result["output"], "repeat\nunique")

    def test_indented_code_keeps_repeated_statements_and_scope(self):
        message = "설명\n\n    if ready:\n        send()\n        send()\n\n요약\n요약"
        report = compact(message)
        self.assertIn("    if ready:\n        send()\n        send()", report["output"])
        self.assertIn("설명\n\n    if ready:", report["output"])
        self.assertIn("        send()\n\n요약", report["output"])
        self.assertEqual(1, report["duplicate_lines_removed"])
        self.assertEqual(report["external_model_calls"], 0)

    def test_tab_indented_code_is_not_deduplicated(self):
        message = "code\n\tstep()\n\tstep()\nnormal\nnormal"
        report = compact(message)
        self.assertEqual("code\n\tstep()\n\tstep()\nnormal", report["output"])
        self.assertEqual(1, report["duplicate_lines_removed"])

    def test_unfenced_repeated_calls_preserve_side_effects(self):
        message = "send()\nsend()\nqueue.push(1);\nqueue.push(1);\nsummary\nsummary"
        report = compact(message)
        self.assertEqual(
            report["output"],
            "send()\nsend()\nqueue.push(1);\nqueue.push(1);\nsummary",
        )
        self.assertEqual(report["duplicate_lines_removed"], 1)

    def test_cli_unfenced_repeated_calls_preserved(self):
        p = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("task_executor.py")), "--stdin"],
            input="send()\nsend()\nnote\nnote",
            text=True, capture_output=True, timeout=3)
        self.assertEqual(p.returncode, 0, p.stderr)
        report = json.loads(p.stdout.split("R16_TASK_EXECUTOR=", 1)[1])
        self.assertEqual(report["output"], "send()\nsend()\nnote")
        self.assertEqual(report["duplicate_lines_removed"], 1)

    def test_unfenced_repeated_assignments_preserve_effects(self):
        message = ("result = send()\nresult = send()\n"
                   "count += 1\ncount += 1\n"
                   "note\nnote")
        report = compact(message)
        self.assertEqual(
            report["output"],
            "result = send()\nresult = send()\ncount += 1\ncount += 1\nnote",
        )
        self.assertEqual(report["duplicate_lines_removed"], 1)

    def test_unfenced_javascript_and_indexed_assignments_preserved(self):
        for expression in ("const job = enqueue();", "let value = get();",
                           "items[0] = pop()", "total -= 1"):
            with self.subTest(expression=expression):
                message = expression + "\n" + expression + "\nplain\nplain"
                report = compact(message)
                self.assertEqual(report["output"],
                                 expression + "\n" + expression + "\nplain")
                self.assertEqual(report["duplicate_lines_removed"], 1)

    def test_cli_assignment_dedup_is_fail_safe(self):
        message = "count += 1\ncount += 1\nordinary\nordinary"
        p = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("task_executor.py")), "--stdin"],
            input=message, text=True, capture_output=True, timeout=3)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout.split("R16_TASK_EXECUTOR=", 1)[1])
        self.assertEqual(result["output"], "count += 1\ncount += 1\nordinary")
        self.assertEqual(result["duplicate_lines_removed"], 1)

    def test_plain_prose_dedup_unchanged(self):
        message = "한 줄\n한 줄\n마지막"
        result = compact(message)
        self.assertEqual("한 줄\n마지막", result["output"])
        self.assertEqual(1, result["duplicate_lines_removed"])

    def test_quad_backtick_fence_keeps_inner_triple_and_repeat(self):
        text = "````python\n```\nwrite()\nwrite()\n````"
        result = compact(text)
        self.assertEqual(result["output"], text)
        self.assertEqual(result["duplicate_lines_removed"], 0)

    def test_tilde_fence_keeps_repeated_side_effects(self):
        text = "~~~python\nwrite()\nwrite()\n~~~"
        self.assertEqual(compact(text)["output"], text)

    def test_fence_wrong_marker_or_short_closer_blocked(self):
        for text in ("~~~python\nrun()\n```", "````python\nrun()\n```"):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, "unclosed code fence"):
                    compact(text)

    def test_repeated_setext_headings_preserved_without_losing_prose_dedup(self):
        message = "note\\nnote\\nTopic\\n=====\\nfirst\\nTopic\\n=====\\nsecond"
        report = compact(message)
        self.assertEqual(report["output"], "note\\nTopic\\n=====\\nfirst\\nTopic\\n=====\\nsecond")
        self.assertEqual(report["duplicate_lines_removed"], 1)

    def test_repeated_dash_setext_titles_preserved(self):
        message = "Section\\n---\\nSection\\n---"
        self.assertEqual(compact(message)["output"], message)

    def test_repeated_markdown_headings_preserved(self):
        message = "# Part A\n## Result\n# Part B\n## Result"
        report = compact(message)
        self.assertEqual(report["output"], message)
        self.assertEqual(report["duplicate_lines_removed"], 0)

    def test_repeated_markdown_tasks_and_quotes_preserved(self):
        message = "- [ ] verify\n- [ ] verify\n1. run\n1. run\n> note\n> note"
        report = compact(message)
        self.assertEqual(report["output"], message)
        self.assertEqual(report["duplicate_lines_removed"], 0)

    def test_repeated_markdown_table_rows_preserved(self):
        message = "| Key | Value |\n| item | PASS |\n| item | PASS |"
        report = compact(message)
        self.assertEqual(report["output"], message)
        self.assertEqual(report["duplicate_lines_removed"], 0)

    def test_cli_real_execution(self):
        p=subprocess.run([sys.executable,str(Path(__file__).with_name("task_executor.py")),"--stdin"],
                         input="one\ntwo\none\n",text=True,capture_output=True,timeout=3)
        self.assertEqual(p.returncode,0,p.stderr)
        report=json.loads(p.stdout.split("R16_TASK_EXECUTOR=",1)[1])
        self.assertEqual(report["output"],"one\ntwo")

    def test_cli_secret_not_echoed(self):
        secret="sk-"+"a"*25
        p=subprocess.run([sys.executable,str(Path(__file__).with_name("task_executor.py")),"--stdin"],
                         input=secret,text=True,capture_output=True,timeout=3)
        self.assertEqual(p.returncode,2)
        self.assertNotIn(secret,p.stdout)

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

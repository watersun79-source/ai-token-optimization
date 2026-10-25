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

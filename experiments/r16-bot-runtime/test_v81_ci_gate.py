"""Negative cases and Git-diff safety policy for isolated adaptive FAST gate."""
import subprocess
import tempfile
from pathlib import Path
import unittest
import v81_ci_gate as gate

A="a"*40
B="b"*40
DOC="docs/ai/V81_SPEED_OPTIMIZATION_20261024.md"
CODE="experiments/r16-bot-runtime/v81_speed_orchestrator.py"

class GateTests(unittest.TestCase):
    def d(self,paths,event="push",before=A,parent=A,head=B):
        return gate.decision(event,before,head,parent,paths)

    def test_exact_allowlisted_document_skips(self):
        d=self.d([DOC])
        self.assertFalse(d["run_full"])
        self.assertEqual("docs_only_single_commit",d["reason"])
        self.assertFalse(d["native_chatgpt_attested"])

    def test_more_than_one_safe_doc_still_skips(self):
        self.assertFalse(self.d([DOC,"docs/ai/V81_SOURCE_PARITY_20261024.md"])["run_full"])

    def test_modified_code_workflow_tests_fail_closed(self):
        for p in [CODE,".github/workflows/v81-fast-full-isolated.yml",
                  "experiments/r16-bot-runtime/test_v81_ci_gate.py",
                  "docs/ai/OTHER.md",".github/workflows/ai-r16-hourly.yml"]:
            self.assertTrue(self.d([DOC,p])["run_full"], p)

    def test_unknown_multi_commit_and_missing_baseline_full(self):
        for kw in ({"parent":B},{"before":""},{"before":"0"*40},
                   {"event":"workflow_dispatch"},{"head":"x"}):
            self.assertTrue(self.d([DOC],**kw)["run_full"])

    def test_empty_diff_and_bad_paths_full(self):
        for p in ([],[None],[123],[""],None):
            self.assertTrue(self.d(p)["run_full"])

    def test_no_repo_history_full(self):
        with tempfile.TemporaryDirectory() as temp:
            d=gate.checkout_decision("push",A,B,Path(temp))
        self.assertTrue(d["run_full"])

    def test_git_checkout_uses_trusted_diff_not_caller_guess(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def git(*args):
                return subprocess.run(["git",*args],cwd=root,check=True,
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout.strip()
            git("init","-q");git("config","user.email","test@example.invalid")
            git("config","user.name","Offline Test")
            p=root/DOC;p.parent.mkdir(parents=True)
            p.write_text("base",encoding="utf-8")
            git("add",".");git("commit","-qm","first")
            before=git("rev-parse","HEAD")
            p.write_text("changed",encoding="utf-8")
            git("add",".");git("commit","-qm","doc")
            head=git("rev-parse","HEAD")
            d=gate.checkout_decision("push",before,head,root)
            self.assertFalse(d["run_full"])
            c=root/CODE;c.parent.mkdir(parents=True)
            c.write_text("changed",encoding="utf-8")
            git("add",".");git("commit","-qm","code")
            second=git("rev-parse","HEAD")
            self.assertTrue(gate.checkout_decision("push",head,second,root)["run_full"])
            self.assertTrue(gate.checkout_decision("push",before,second,root)["run_full"])

if __name__=="__main__":
    unittest.main()

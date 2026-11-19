"""Offline checks for real SDK integration CI: no provider import required."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
WF=ROOT/".github/workflows/oss-top10-real-sdk.yml"
PY=ROOT/"experiments/oss-top10-safe-adoption/sdk_functional_python.py"

class TestOssFunctionalGuards(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.wf=WF.read_text(encoding="utf-8")
  cls.py=PY.read_text(encoding="utf-8")
 def test_five_allowed_sdk_versions_pinned(self):
  self.assertEqual(set(re.findall(r'\{ id: ([^,]+), package: [^}\n]+, version: "[^"]+" \}', self.wf)),
                   {"langgraph", "mem0", "langfuse", "agent-framework", "openai-agents"})
 def test_licensed_isolation_and_free_sdk(self):
  self.assertIn('contents: read',self.wf)
  self.assertIn('persist-credentials: false',self.wf)
  self.assertIn('--only-binary=:all:',self.wf)
 def test_no_schedule_or_secrets(self):
  for term in ("workflow_dispatch:","pull_request_target:","repository_dispatch:","schedule:","secrets."):
   self.assertNotIn(term,self.wf)
 def test_offline_guards(self):
  self.assertIn("socket.create_connection=deny_network",self.py)
  self.assertNotIn("from openhands",self.py)
  self.assertNotIn("from crewai",self.py)
 def test_functional_real_sdk_paths(self):
  self.assertIn("sdk_functional_python.py",self.wf)
  self.assertIn("SDK_FUNCTIONAL_RESULT=",self.py)
 def test_freeze_receipts(self):
  self.assertIn("SDK_DEPENDENCY_LOCK_BEGIN:",self.wf)
 def test_install_and_sdk_execution_require_the_quarantine_check(self):
  sdk_jobs = self.wf.split("  flowise-eol:", 1)[0]
  inventory = sdk_jobs.index('test "$allowed" = true')
  advisory = sdk_jobs.index("--advisory-only")
  self.assertLess(inventory, advisory)
  for command in ('-r "$SDK_LOCK"', "sdk_functional_python.py", "importlib.import_module"):
   self.assertLess(advisory, sdk_jobs.index(command))
  self.assertNotIn("npm ci", sdk_jobs)
 def test_all_five_sdk_dependency_locks_exist(self):
  pins={"langgraph":"1.2.20","mem0ai":"2.2.1",
   "langfuse":"5.2.0","agent-framework-core":"1.25.0",
   "openai-agents":"0.24.0"}
  ids={"agent-framework-core":"agent-framework",
   "mem0ai":"mem0","openai-agents":"openai-agents"}
  for package,version in pins.items():
   ident=ids.get(package,package)
   p=ROOT/"experiments/oss-top10-safe-adoption/locks"/(ident+"-pip.txt")
   self.assertTrue(p.is_file(),ident)
   lines=p.read_text(encoding="utf-8").splitlines()
   self.assertIn(package+"=="+version,lines)
   self.assertTrue(all(re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+",line) for line in lines))
 def test_flowise_eol(self):
  self.assertIn("FLOWISE_EOL_INSTALL_BLOCKED",self.wf)
  self.assertNotIn("package: Flowise",self.wf)

if __name__=="__main__": unittest.main()

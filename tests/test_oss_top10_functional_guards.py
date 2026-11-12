"""Offline checks for real SDK integration CI: no provider import required."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
WF=ROOT/".github/workflows/oss-top10-real-sdk.yml"
PY=ROOT/"experiments/oss-top10-safe-adoption/sdk_functional_python.py"
JS=ROOT/"experiments/oss-top10-safe-adoption/sdk_functional_node.mjs"

class TestOssFunctionalGuards(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.wf=WF.read_text(encoding="utf-8")
  cls.py=PY.read_text(encoding="utf-8")
  cls.js=JS.read_text(encoding="utf-8")
 def test_nine_direct_sdk_versions_pinned(self):
  self.assertEqual(len(re.findall(r'\{ id: [^}\n]+, version: "[^"]+" \}', self.wf)),9)
  self.assertIn('version: "1.62.0"',self.wf)
  self.assertIn('version: "0.8.86"',self.wf)
 def test_licensed_isolation_and_free_sdk(self):
  self.assertIn('contents: read',self.wf)
  self.assertIn('persist-credentials: false',self.wf)
  self.assertIn('--only-binary=:all:',self.wf)
  self.assertIn('--ignore-scripts',self.wf)
 def test_no_schedule_or_secrets(self):
  for term in ("workflow_dispatch:","pull_request_target:","repository_dispatch:","schedule:","secrets."):
   self.assertNotIn(term,self.wf)
 def test_offline_guards(self):
  self.assertIn("socket.create_connection=deny_network",self.py)
  self.assertIn("SDK_NETWORK_DENIED",self.js)
  self.assertNotIn("conversation.run(",self.py)
  self.assertNotIn("client.connect(",self.js)
 def test_functional_real_sdk_paths(self):
  self.assertIn("sdk_functional_python.py",self.wf)
  self.assertIn("sdk_functional_node.mjs",self.wf)
  self.assertIn("SDK_FUNCTIONAL_RESULT=",self.py)
  self.assertIn("SDK_FUNCTIONAL_RESULT=",self.js)
 def test_freeze_receipts(self):
  self.assertIn("SDK_DEPENDENCY_LOCK_BEGIN:",self.wf)
  self.assertIn("NODE_LOCK_GZIP_B64_BEGIN:",self.wf)
 def test_flowise_eol(self):
  self.assertIn("FLOWISE_EOL_INSTALL_BLOCKED",self.wf)
  self.assertNotIn("package: Flowise",self.wf)

if __name__=="__main__": unittest.main()

"""Only the new collector's serialization and fail-closed behavior."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'experiments/oss-top10-safe-adoption/pr31_authenticated_schedule_snapshot.py'
spec = importlib.util.spec_from_file_location('schedule_collector', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NewCollectorCases(unittest.TestCase):
    def test_allowlisted_run_fields_and_digest(self):
        p = {'workflow_runs': [{'id': 12345, 'event': 'schedule', 'head_sha': 'a'*40,
              'status': 'completed', 'conclusion': 'success', 'created_at': '2026-11-19T00:00:00Z',
              'actor': {'login': 'secret'}, 'token': 'secret-token'}]}
        result = module.transform(p)
        self.assertEqual(result['observed_count'], 1)
        self.assertEqual(result['runs'][0]['id'], 12345)
        self.assertNotIn('secret', str(result))
        self.assertEqual(result['site_runtime_integration'], 'UNVERIFIED')
        self.assertFalse(result['operational_write_allowed'])

    def test_untrusted_event_rejected(self):
        with self.assertRaises(ValueError):
            module.transform({'workflow_runs': [{'id': 1, 'event': 'pull_request', 'head_sha': 'a'*40}]})

    def test_no_token_means_no_network_and_exit2(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(module.os.environ, {'GITHUB_REPOSITORY': module.REPOSITORY,
                 'GITHUB_EVENT_NAME': 'pull_request', 'GH_TOKEN': ''}):
                with patch.object(module, 'urlopen', side_effect=AssertionError('MUST_NOT_CALL')):
                    self.assertEqual(module.main(), 2)


if __name__ == '__main__':
    unittest.main()

import unittest

from audit_v2 import AUTOMATION_ID, REQUIRED, check


class ConnectedToolNameTests(unittest.TestCase):
    def test_current_connected_app_tool_names_are_accepted(self):
        target_slot = '2026-10-23T00:00:00+09:00'
        run_id = 'EXAMPLE-ONLY-NOT-A-REAL-RUN-ID'
        calls = []
        actual_names = {
            'current_handoff': 'mcp__codex_apps__github_fetch_file',
            'slack_thread': 'mcp__codex_apps__slack_slack_read_thread',
        }
        for i, (target, (_, locator, version_type)) in enumerate(REQUIRED.items()):
            calls.append({
                'origin': 'official_task_tool_call',
                'run_id': run_id,
                'target': target,
                'tool': actual_names[target],
                'locator': locator,
                'success': True,
                'observed_at': '2026-10-23T00:02:00+09:00',
                'version': 'a' * 40 if version_type == 'sha' else '1792680263.547459',
                'invocation_id': f'EXAMPLE-{i}',
            })
        payload = {
            'target_slot': target_slot,
            'schedule': {
                'id': AUTOMATION_ID,
                'is_enabled': True,
                'last_run_time': '2026-10-22T15:03:14Z',
            },
            'native_run': {
                'origin': 'official_task_run_details',
                'automation_id': AUTOMATION_ID,
                'run_id': run_id,
                'scheduled_for': target_slot,
                'started_at': '2026-10-23T00:01:00+09:00',
                'completed_at': '2026-10-23T00:03:00+09:00',
                'status': 'completed',
            },
            'tool_calls': calls,
        }

        result = check(payload)

        self.assertTrue(result['status'].startswith('형식 통과'))
        self.assertEqual(result['missing'], [])


if __name__ == '__main__':
    unittest.main()

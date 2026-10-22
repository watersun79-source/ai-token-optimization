"""Non-network policy tests for ten specialists."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from specialist_team import ROLES, DEMO, run_role, run_all


class TenRoleTests(unittest.TestCase):
    def test_registry_exact(self):
        self.assertEqual(len(ROLES), 10)
        self.assertEqual(len(set(ROLES)), 10)

    def test_every_role_executes_without_external_writes(self):
        for name in ROLES:
            with self.subTest(name=name):
                out = run_role(name, DEMO[name])
                self.assertEqual(out['role'], name)
                self.assertEqual(out['mode'], 'OFFLINE_REFERENCE_ONLY')
                self.assertEqual(out['external_model_calls'], 0)
                self.assertEqual(out['external_writes'], 0)

    def test_memory_hash_only(self):
        r = run_role('memory_recovery', DEMO['memory_recovery'])['result']
        self.assertEqual(r['snapshots_read'], 1)
        self.assertFalse(r['restored_chatgpt_memory'])
        self.assertEqual(len(r['content_sha256'][0]), 64)

    def test_audit_never_claims_platform_proof(self):
        p = {'record': {'official_run_id': 'fabricated', 'platform_supplied_id': True,
                        'same_run_raw_logs_verified': True}}
        self.assertFalse(run_role('scheduled_audit', p)['result']['independently_proven_by_offline_check'])

    def test_debug_only_suggests(self):
        r = run_role('auto_debug', {'error': 'permission denied'})['result']
        self.assertEqual(r['diagnostic_action'], 'check_permissions_without_bypass')
        self.assertFalse(r['code_changed'])

    def test_code_good_and_bad(self):
        self.assertTrue(run_role('code_verification', {'python_source': 'x = 1'})['result']['python_syntax_ok'])
        self.assertFalse(run_role('code_verification', {'python_source': 'def x('})['result']['python_syntax_ok'])

    def test_license_filter_only_metadata(self):
        r = run_role('open_source_research', {'projects': [{'name': 'one', 'license': 'MIT'},
             {'name': 'two', 'license': 'UNKNOWN'}]})['result']
        self.assertEqual(r['candidate_names'], ['one'])
        self.assertFalse(r['licenses_checked_against_live_upstream'])

    def test_automation_cycle_rejected(self):
        r = run_role('automation_design', {'steps': [{'id': 'x', 'after': 'y'},
              {'id': 'y', 'after': 'x'}]})['result']
        self.assertFalse(r['plan_valid'])

    def test_automation_missing_ref_rejected(self):
        r = run_role('automation_design', {'steps': [{'id':'x','after':'nope'}]})['result']
        self.assertFalse(r['plan_valid'])

    def test_suspected_secret_not_echoed(self):
        secret = 'sk-' + 'A'*25
        out = run_role('cost_security', {'sample': secret})
        self.assertTrue(out['result']['possible_secret_detected'])
        self.assertNotIn(secret, json.dumps(out))

    def test_cost_provider_call_not_approved(self):
        r = run_role('cost_security', {'provider_call': True})['result']
        self.assertFalse(r['provider_execution_allowed'])

    def test_github_plan_is_not_git_mutation(self):
        r = run_role('github_management', DEMO['github_management'])['result']
        self.assertTrue(r['valid_repo_format'])
        self.assertEqual(r['commits_written'], 0)

    def test_untrusted_ref_rejected(self):
        self.assertFalse(run_role('github_management', {'repository':'one/two', 'ref':'../main'})['result']['valid_ref_format'])

    def test_model_review_not_real_models(self):
        r = run_role('cross_model_review', DEMO['cross_model_review'])['result']
        self.assertTrue(r['conflict_in_supplied_reviews'])
        self.assertFalse(r['provider_responses_proven'])

    def test_optimization_no_fabricated_tokens(self):
        r = run_role('ai_optimization', DEMO['ai_optimization'])['result']
        self.assertEqual(r['duplicate_tasks_omitted'], 1)
        self.assertFalse(r['measured_token_saving'])

    def test_run_all_is_exact_ten(self):
        r = run_all()
        self.assertEqual(r['role_count'], 10)
        self.assertEqual({x['role'] for x in r['roles']}, set(ROLES))
        self.assertFalse(r['chatgpt_unattended_execution_verified'])

    def test_invalid_role_blocked(self):
        with self.assertRaises(ValueError):
            run_role('not-a-bot', {})

    def test_bounded_input(self):
        with self.assertRaises(ValueError):
            run_role('memory_recovery', {'snapshots': [{}] * 999})

    def test_cli_runs_ten(self):
        p = subprocess.run([sys.executable, str(HERE/'specialist_team.py'), '--role', 'all'],
                           capture_output=True, text=True, timeout=12)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['role_count'], 10)

    def test_parallel_order_stable(self):
        self.assertEqual([x['role'] for x in run_all()['roles']], list(ROLES))


if __name__ == '__main__':
    unittest.main()

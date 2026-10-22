"""No network and no external provider APIs are invoked by these tests."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from auto_dispatch import dispatch, ROLE_TRIGGERS


class AutoDispatchTests(unittest.TestCase):
    def test_all_ten_roles_defined(self):
        self.assertEqual(len(ROLE_TRIGGERS), 10)

    def test_simple_greeting_direct(self):
        self.assertEqual(dispatch("안녕")['route'], "DIRECT_CHAT")

    def test_weather_stays_direct(self):
        self.assertEqual(dispatch("오늘 날씨 알려줘")['roles'], [])

    def test_unrelated_question_direct(self):
        self.assertEqual(dispatch("한국 수도가 어디야?")['route'], "DIRECT_CHAT")

    def test_generic_project_uses_coordinator(self):
        self.assertEqual(dispatch("AI 프로젝트 진행")['route'], "THREE_ROLE_WORKFLOW")

    def test_debug_without_bot_name(self):
        self.assertIn('ai-auto-debug', dispatch('에러 고쳐')['roles'])

    def test_memory_without_bot_name(self):
        self.assertIn('ai-memory-recovery', dispatch('지난 AI 작업 기억 복원해')['roles'])

    def test_audit_without_bot_name(self):
        self.assertIn('ai-scheduled-audit', dispatch('예약 AI 정규 회차 검증')['roles'])

    def test_automation_without_bot_name(self):
        self.assertIn('ai-automation-design', dispatch('봇 자동 선택 되게 해줘')['roles'])

    def test_test_without_bot_name(self):
        self.assertIn('ai-code-verification', dispatch('CI 확인')['roles'])

    def test_oss_without_bot_name(self):
        self.assertIn('ai-open-source-research', dispatch('무료 오픈소스 찾아')['roles'])

    def test_billing_requires_review(self):
        x=dispatch('유료 api 과금 확인')
        self.assertTrue(x['requires_action_permission_review'])
        self.assertIn('ai-cost-security',x['roles'])

    def test_git_management(self):
        self.assertIn('ai-github-management',dispatch('브랜치 관리')['roles'])

    def test_cross_model_no_provider_call(self):
        x=dispatch('gemini와 claude 교차 검토')
        self.assertIn('ai-cross-model-review',x['roles'])
        self.assertEqual(x['external_provider_api_calls'],0)

    def test_optimization(self):
        self.assertIn('ai-optimization',dispatch('토큰 최적화')['roles'])

    def test_multi_role_cap(self):
        self.assertLessEqual(len(dispatch('기억 복원 예약 AI 오류 수정 CI 검증 무료 오픈소스 과금',2)['roles']),2)

    def test_deterministic(self):
        self.assertEqual(dispatch('오류 수정과 CI 검증'),dispatch('오류 수정과 CI 검증'))

    def test_no_global_hook_or_production_changes(self):
        x=dispatch('AI 프로젝트 개발')
        self.assertFalse(x['chatgpt_global_auto_hook_installed'])
        self.assertFalse(x['chatgpt_skill_auto_invocation_verified'])
        self.assertEqual(x['production_changes'],0)

    def test_invalid_input(self):
        for bad in ('', '  ', 'x'*4001):
            with self.assertRaises(ValueError): dispatch(bad)

    def test_invalid_max_roles(self):
        for bad in (0,11,True):
            with self.assertRaises(ValueError): dispatch('AI 프로젝트',bad)

    def test_cli_invocation(self):
        p=subprocess.run([sys.executable,str(ROOT/'auto_dispatch.py'),'--message','에러 고쳐'],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0)
        self.assertIn('ai-auto-debug',json.loads(p.stdout)['roles'])


if __name__ == '__main__': unittest.main()

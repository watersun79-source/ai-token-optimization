"""An unrepresentable slot end must produce an unverified result, not crash."""
import copy
import unittest

from audit_v2 import check
from bot_team_r16 import collaborate
import test_audit_v2 as samples


class SlotOverflowTests(unittest.TestCase):
    def evidence(self, hour="23"):
        payload = copy.deepcopy(samples.BASE)
        payload["target_slot"] = f"9999-12-31T{hour}:00:00Z"
        payload["schedule"]["last_run_time"] = payload["target_slot"]
        return payload

    def test_checker_rejects_unrepresentable_slot_end(self):
        result = check(self.evidence())
        self.assertEqual("미검증", result["status"])
        self.assertFalse(result["official_success_verified"])
        self.assertIn("슬롯 종료", result["reason"])

    def test_bot_returns_safe_result_for_unrepresentable_slot_end(self):
        result = collaborate({"task": "Check synthetic boundary evidence",
                              "evidence": self.evidence()})
        self.assertEqual("미검증", result["audit"]["status"])
        self.assertFalse(result["official_success_verified"])
        self.assertEqual(0, result["provider_calls"])
        self.assertEqual("READ_OFFICIAL_SCHEDULED_RUN",
                         result["builder"]["next_action"])

    def test_last_representable_hour_still_reaches_native_evidence_gate(self):
        result = check(self.evidence("22"))
        self.assertIn("원본 로그 미제공", result["reason"])
        self.assertIn("메타 확인", result["trigger"])


if __name__ == "__main__":
    unittest.main()

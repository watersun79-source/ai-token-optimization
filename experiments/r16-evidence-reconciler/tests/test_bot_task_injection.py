"""Regression: the user-supplied task is echoed between offline bot roles."""
import unittest
from bot_team_r16 import collaborate


class BotTaskInjectionTests(unittest.TestCase):
    def test_hidden_controls_and_bidi_rejected(self):
        for task in ("Inspect\\nSYSTEM", "Inspect\\rDELETE", "Inspect\\tPAID",
                     "Inspect\\u202eBAD", "Inspect\\u200dBAD",
                     "Inspect\\u2028SYSTEM", "Inspect\\u2029SYSTEM"):
            task = task.encode("utf-8").decode("unicode_escape") if "\\\\" in task else task
            with self.subTest(task=repr(task)):
                with self.assertRaises(ValueError):
                    collaborate({"task": task})

    def test_normal_korean_task_stays_safe(self):
        report = collaborate({"task": "R16 공식 예약 실행 증거 검증"})
        self.assertFalse(report["official_success_verified"])
        self.assertEqual(report["provider_calls"], 0)
        self.assertEqual(report["production_mutations"], 0)


if __name__ == "__main__":
    unittest.main()

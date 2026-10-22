"""Tests for the deterministic chat router; not a ChatGPT integration test."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chat_router import route_task, demo
from bot_team import load_sources


class ChatRouterTests(unittest.TestCase):
    def test_explicit_project_auto_route(self):
        self.assertEqual(route_task("AI 프로젝트 오류 수정해")["route"], "THREE_ROLE_WORKFLOW")

    def test_ordinary_chat_stays_direct(self):
        self.assertEqual(route_task("오늘 점심 뭐 먹지?")["route"], "DIRECT_CHAT")

    def test_explicit_three_bots(self):
        self.assertEqual(route_task("3봇 협력 테스트")["route"], "THREE_ROLE_WORKFLOW")

    def test_no_false_automatic_chat_integration(self):
        self.assertFalse(route_task("AI 프로젝트 검증")["automatic_in_any_chat"])

    def test_team_demo_structure(self):
        sources = load_sources(ROOT / "examples/sources.json")
        result = demo("AI 봇 협업", sources)
        self.assertEqual(result["team_demo"]["verifier"]["status"], "PASS")
        self.assertEqual(result["team_demo"]["provider_api_calls"], 0)

    def test_direct_does_not_call_team(self):
        self.assertIsNone(demo("안녕", [])["team_demo"])

    def test_empty_fails(self):
        with self.assertRaises(ValueError):
            route_task("")

    def test_cli_blocked_evidence(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "sources.json"
            src.write_text("[]", encoding="utf-8")
            p = subprocess.run([sys.executable, str(ROOT / "chat_router.py"), "--task", "AI 봇 협업", "--sources", str(src)], capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(json.loads(p.stdout)["team_demo"]["verifier"]["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()

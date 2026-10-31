"""Credential-free, offline regression for opt-in ChatGPT->Neon connector plans."""
import hashlib
import unittest

from tools.isolated_neon_chat_turn_bridge_v853 import (
    _utf8_literal, prepare_selected_neon_commands, validate_neon_connector_results,
)
from tools.isolated_selective_memory_v85 import TEST_PROJECT_ID, TEST_BRANCH_ID, TEST_DB_NAME


def event(**kwargs):
    obj = {
        "selected": True,
        "record_id": "synthetic-v853-chat-turn-001",
        "project_key": "project.ai-bot-v81",
        "kind": "task_result",
        "title": "Isolated connector result",
        "body": "Approved project result only.",
    }
    obj.update(kwargs)
    return obj


def responses(plan):
    expected = plan["expected"]
    return (
        [{k: expected[k] for k in ("record_id", "kind", "content_sha256")}],
        [dict(expected)],
    )


class TestChatTurnConnectorBridge(unittest.TestCase):
    def test_selected_event_fixed_neon_target(self):
        p = prepare_selected_neon_commands(event())
        self.assertEqual(p["project_id"], TEST_PROJECT_ID)
        self.assertEqual(p["branch_id"], TEST_BRANCH_ID)
        self.assertEqual(p["database_name"], TEST_DB_NAME)
        self.assertFalse(p["automatic_global_chat_capture"])
        self.assertFalse(p["production_connected"])

    def test_sql_hex_encoding_prevents_raw_injection(self):
        body = "Approved O'Brien and 日本語 project result."
        p = prepare_selected_neon_commands(event(body=body))
        self.assertNotIn("O'Brien", p["insert_sql"])
        self.assertNotIn(body, p["insert_sql"])
        self.assertIn("decode('", p["insert_sql"])
        self.assertIn("ON CONFLICT (record_id) DO NOTHING", p["insert_sql"])
        self.assertIn("LIMIT 2", p["read_sql"])
        self.assertEqual(p["expected"]["content_sha256"], hashlib.sha256(body.encode()).hexdigest())
        self.assertEqual(_utf8_literal(body), "convert_from(decode('" + body.encode().hex() + "','hex'),'UTF8')")

    def test_positive_insert_and_readback(self):
        p = prepare_selected_neon_commands(event())
        ack, rows = responses(p)
        out = validate_neon_connector_results(p, ack, rows)
        self.assertEqual(out["status"], "INSERTED")
        self.assertTrue(out["readback_verified"])
        self.assertFalse(out["native_chat_automation_verified"])

    def test_idempotent_duplicate_and_readback(self):
        p = prepare_selected_neon_commands(event())
        _, rows = responses(p)
        self.assertEqual(validate_neon_connector_results(p, [], rows)["status"], "ALREADY_EXISTS")

    def test_wrong_content_is_rejected(self):
        p = prepare_selected_neon_commands(event())
        ack, rows = responses(p)
        rows[0]["body"] = "tampered"
        with self.assertRaisesRegex(RuntimeError, "READBACK_MISMATCH"):
            validate_neon_connector_results(p, ack, rows)

    def test_false_success_ack_rejected(self):
        p = prepare_selected_neon_commands(event())
        ack, rows = responses(p)
        ack[0]["record_id"] = "another"
        with self.assertRaisesRegex(RuntimeError, "INSERT_ACK_MISMATCH"):
            validate_neon_connector_results(p, ack, rows)

    def test_multiple_readback_rows_rejected(self):
        p = prepare_selected_neon_commands(event())
        ack, rows = responses(p)
        with self.assertRaisesRegex(RuntimeError, "READBACK_MISMATCH"):
            validate_neon_connector_results(p, ack, rows + rows)

    def test_wrong_target_rejected(self):
        p = prepare_selected_neon_commands(event())
        ack, rows = responses(p)
        p["branch_id"] = "br-solitary-firefly-azge9w3x"
        with self.assertRaisesRegex(ValueError, "WRONG_NEON_TARGET"):
            validate_neon_connector_results(p, ack, rows)

    def test_unselected_and_chat_transcript_skipped(self):
        for obj in (event(selected=False), event(kind="transcript")):
            self.assertEqual(prepare_selected_neon_commands(obj)["status"], "SKIPPED")

    def test_unselected_cannot_claim_success(self):
        plan = prepare_selected_neon_commands(event(selected=False))
        with self.assertRaisesRegex(ValueError, "PLAN_NOT_SELECTED"):
            validate_neon_connector_results(plan, [], [])

    def test_credentials_and_raw_message_keys_denied(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_FIELDS"):
            prepare_selected_neon_commands(event(raw_conversation="not allowed"))
        with self.assertRaisesRegex(ValueError, "POSSIBLE_SECRET"):
            prepare_selected_neon_commands(event(body="postgresql://example.com/private"))

    def test_invalid_connector_response_rejected(self):
        p = prepare_selected_neon_commands(event())
        for bad in (None, {"rows": []}, "[]"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "INVALID_CONNECTOR_RESPONSE"):
                    validate_neon_connector_results(p, bad, [])

if __name__ == "__main__":
    unittest.main()

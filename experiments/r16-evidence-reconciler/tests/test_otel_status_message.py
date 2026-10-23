"""Status.message must obey ProtoJSON typing, not Python truthiness."""
import unittest

from otel_evidence_adapter import adapt_otlp
from test_otel_evidence_adapter import RUN, TARGETS, fixture
from bot_team_r16 import collaborate
import test_bot_team_r16 as bot_tests


class TestStatusMessage(unittest.TestCase):
    def test_malformed_falsey_root_message_cannot_supply_evidence(self):
        for message in (False, 0, 0.0, [], {}):
            with self.subTest(message=message):
                data = fixture()
                data['resourceSpans'][0]['scopeSpans'][0]['spans'][0]['status']['message'] = message
                result = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
                self.assertEqual([], result['tool_calls'])

    def test_malformed_falsey_tool_message_does_not_advance_bot(self):
        for message in (False, 0, 0.0, [], {}):
            with self.subTest(message=message):
                payload = bot_tests.BotTeamR16Tests().otel_sample()
                spans = payload['evidence']['otel']['resourceSpans'][0]['scopeSpans'][0]['spans']
                spans[1]['status']['message'] = message
                result = collaborate(payload)
                self.assertEqual(['slack_thread'], result['audit']['verified_targets'])
                self.assertEqual('READ_SAME_RUN_APP_CALLS', result['builder']['next_action'])
                self.assertFalse(result['official_success_verified'])
                self.assertEqual(0, result['provider_calls'])

    def test_empty_and_null_messages_preserve_protojson_unset_semantics(self):
        for message in ('', None):
            with self.subTest(message=message):
                data = fixture()
                for span in data['resourceSpans'][0]['scopeSpans'][0]['spans']:
                    span['status']['message'] = message
                result = adapt_otlp(data, expected_run_id=RUN, expected_targets=TARGETS)
                self.assertCountEqual(TARGETS, [c['target'] for c in result['tool_calls']])


if __name__ == '__main__':
    unittest.main()

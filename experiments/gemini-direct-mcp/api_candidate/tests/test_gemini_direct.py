"""Offline contract tests. Every credential and response below is synthetic."""

from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import io
import json
from pathlib import Path
import socket
import ssl
import traceback
import unittest
from unittest import mock
import uuid


NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
SYNTHETIC_KEY = "offline-fixture-key-not-a-provider-credential"
SYNTHETIC_AQ_KEY = "AQ.OFFLINE_SYNTHETIC_NOT_A_PROVIDER_CREDENTIAL_0001"
PROMPT = "Return the word ready."
FIXTURES = Path(__file__).parent / "fixtures"


def verified_fixture(**overrides):
    """A fictional operator assertion, never evidence about a real account."""
    data = {
        "schema_version": 1,
        "status": "VERIFIED_BY_OPERATOR",
        "evidence_id": str(uuid.uuid4()),
        "api_key_sha256": hashlib.sha256(SYNTHETIC_KEY.encode()).hexdigest(),
        "model": "gemini-3.5-flash-lite",
        "observed_at": "2026-11-04T11:59:00+00:00",
        "quota_day_pacific": "2026-11-04",
        "auth_verified": True,
        "key_project_binding_verified": True,
        "free_tier_verified": True,
        "billing_account_linked": False,
        "paid_billing_enabled": False,
        "quota_verified": True,
        "remaining_requests": 1,
        "evidence_refs": {
            "auth": "fixture:auth-only-not-real",
            "project_binding": "fixture:project-only-not-real",
            "free_tier": "fixture:free-only-not-real",
            "billing": "fixture:unlinked-only-not-real",
            "daily_quota": "fixture:quota-only-not-real",
        },
    }
    data.update(overrides)
    return data


class ResponseFixture:
    def __init__(self, body, status=200, headers=None):
        self.body = io.BytesIO(body)
        self.status = status
        self.headers = headers or {}
        self.read_sizes = []

    def getheader(self, name, default=None):
        return self.headers.get(name.lower(), default)

    def read(self, amount):
        self.read_sizes.append(amount)
        return self.body.read(amount)


class ConnectionFixture:
    """A fake socket boundary; request serialization and all gates stay real."""

    def __init__(self, response=None, request_error=None):
        self.response = response
        self.request_error = request_error
        self.requests = []
        self.closed = False

    def request(self, method, path, body=None, headers=None):
        self.requests.append((method, path, body, headers))
        if self.request_error is not None:
            raise self.request_error

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True

    def set_debuglevel(self, level):
        self.debuglevel = level


class CandidateTests(unittest.TestCase):
    def setUp(self):
        # A missing implementation is an assertion failure during the red phase.
        try:
            self.direct = importlib.import_module("gemini_direct")
        except ModuleNotFoundError:
            self.fail("Candidate implementation is absent; no request can be prepared yet")
        self.network_guard = mock.patch.object(
            socket, "create_connection", side_effect=AssertionError("OFFLINE_SOCKET_FORBIDDEN")
        )
        self.network_guard.start()
        self.addCleanup(self.network_guard.stop)
        # Avoid consulting system certificate environment paths in offline tests.
        self.cert_loader = mock.patch.object(ssl.SSLContext, "load_default_certs", return_value=None)
        self.cert_loader.start()
        self.addCleanup(self.cert_loader.stop)

    def client(self, enabled=True, key=SYNTHETIC_KEY):
        return self.direct.GeminiDirectClient(self.direct.Config(api_key=key, enabled=enabled))

    def evidence(self, **overrides):
        return self.direct.OperatorEvidence.from_mapping(verified_fixture(**overrides))

    def run_fixture(self, client, evidence, response=None, request_error=None, prompt=PROMPT):
        connection = ConnectionFixture(response=response, request_error=request_error)
        with mock.patch.object(self.direct.http.client, "HTTPSConnection", return_value=connection) as ctor:
            with mock.patch.object(self.direct, "_utc_now", return_value=NOW):
                result = client.generate_once(prompt, evidence=evidence)
        return result, connection, ctor

    def assert_blocked_without_connection(self, client, evidence, prompt=PROMPT):
        with mock.patch.object(self.direct.http.client, "HTTPSConnection") as ctor:
            with mock.patch.object(self.direct, "_utc_now", return_value=NOW):
                with self.assertRaises(self.direct.CandidateError):
                    client.generate_once(prompt, evidence=evidence)
            self.assertEqual(ctor.call_count, 0, "A rejected preflight must not open HTTP")

    def test_default_configuration_and_absent_evidence_block_before_http(self):
        self.assert_blocked_without_connection(self.client(enabled=False), self.evidence())
        self.assert_blocked_without_connection(self.client(), None)
        sample = json.loads((Path(__file__).parents[1] / "evidence.example.json").read_text())
        self.assert_blocked_without_connection(
            self.client(), self.direct.OperatorEvidence.from_mapping(sample)
        )

    def test_aq_key_format_is_bounded_and_disabled_by_default(self):
        for key in (SYNTHETIC_AQ_KEY, "AQ." + "O" * 16, "AQ." + "O" * 253,
                    "O" * 16, "O" * 256):
            with self.subTest(length=len(key), aq=key.startswith("AQ.")):
                try:
                    config = self.direct.Config(api_key=key)
                except self.direct.CandidateError:
                    self.fail("A supported synthetic key format was rejected")
                self.assertFalse(config.enabled)
                self.assertNotIn(key, repr(config))
        invalid = ("AQ.", "AQ." + "O" * 15, "AQ." + "O" * 254,
                   "O" * 15, "O" * 257, "AX." + "O" * 20,
                   SYNTHETIC_AQ_KEY + ".extra", " " + SYNTHETIC_AQ_KEY,
                   SYNTHETIC_AQ_KEY + "\r\n", SYNTHETIC_AQ_KEY + "\t",
                   "AQ.OFFLINE.OTHER_TOKEN_0001", "AQ." + "한" * 20)
        for key in invalid:
            with self.subTest(length=len(key)), self.assertRaisesRegex(self.direct.CandidateError, "^KEY_INVALID$"):
                self.direct.Config(api_key=key)

    def test_aq_key_in_prompt_or_response_is_redacted_without_provider_io(self):
        try:
            client = self.client(key=SYNTHETIC_AQ_KEY)
        except self.direct.CandidateError:
            self.fail("The synthetic AQ. key format must reach the secret checks")
        evidence = self.evidence(api_key_sha256=hashlib.sha256(SYNTHETIC_AQ_KEY.encode()).hexdigest())
        self.assert_blocked_without_connection(client, evidence, prompt="Do not send " + SYNTHETIC_AQ_KEY)
        echoed = json.loads((FIXTURES / "success.json").read_text())
        echoed["candidates"][0]["content"]["parts"][0]["text"] = SYNTHETIC_AQ_KEY
        with self.assertRaisesRegex(self.direct.CandidateError, "^RESPONSE_SECRET_REDACTED$") as error:
            self.run_fixture(client, evidence, ResponseFixture(json.dumps(echoed).encode()))
        self.assertNotIn(SYNTHETIC_AQ_KEY, str(error.exception))

    def test_other_aq_key_in_prompt_or_response_is_also_rejected(self):
        self.assert_blocked_without_connection(self.client(), self.evidence(), prompt=SYNTHETIC_AQ_KEY)
        echoed = json.loads((FIXTURES / "success.json").read_text())
        echoed["candidates"][0]["content"]["parts"][0]["text"] = SYNTHETIC_AQ_KEY
        with self.assertRaisesRegex(self.direct.CandidateError, "^RESPONSE_SECRET_REDACTED$") as error:
            self.run_fixture(self.client(), self.evidence(), ResponseFixture(json.dumps(echoed).encode()))
        self.assertNotIn(SYNTHETIC_AQ_KEY, str(error.exception))

    def test_aq_key_in_operator_evidence_refs_is_rejected_before_http(self):
        refs = verified_fixture()["evidence_refs"]
        refs["auth"] = "private:fixture/" + SYNTHETIC_AQ_KEY
        evidence = self.evidence(evidence_refs=refs)
        self.assert_blocked_without_connection(self.client(), evidence)

    def test_changed_key_model_paid_status_or_unverified_operator_fact_blocks_http(self):
        for changed in (
            {"api_key_sha256": "0" * 64},
            {"model": "gemini-3.8-flash"},
            {"status": "UNVERIFIED"},
            {"auth_verified": False},
            {"key_project_binding_verified": False},
            {"free_tier_verified": False},
            {"billing_account_linked": True},
            {"paid_billing_enabled": True},
            {"quota_verified": False},
            {"remaining_requests": 0},
            {"remaining_requests": True},
            {"remaining_requests": "1"},
            {"evidence_refs": {}},
        ):
            with self.subTest(changed=list(changed)):
                self.assert_blocked_without_connection(self.client(), self.evidence(**changed))

    def test_stale_future_naive_and_previous_quota_day_are_rejected(self):
        for changed in (
            {"observed_at": (NOW - timedelta(minutes=15, seconds=1)).isoformat()},
            {"observed_at": (NOW + timedelta(seconds=1)).isoformat()},
            {"observed_at": "2026-11-04T11:59:00"},
            {"observed_at": "not-a-date"},
            {"quota_day_pacific": "2026-11-03"},
        ):
            with self.subTest(changed=list(changed)):
                self.assert_blocked_without_connection(self.client(), self.evidence(**changed))

    def test_pacific_day_boundary_is_not_computed_as_utc_date(self):
        boundary = datetime(2026, 11, 4, 7, 59, tzinfo=timezone.utc)
        evidence = self.evidence(observed_at=boundary.isoformat(), quota_day_pacific="2026-11-03")
        response = ResponseFixture((FIXTURES / "success.json").read_bytes())
        connection = ConnectionFixture(response=response)
        with mock.patch.object(self.direct.http.client, "HTTPSConnection", return_value=connection):
            with mock.patch.object(self.direct, "_utc_now", return_value=boundary):
                result = self.client().generate_once(PROMPT, evidence=evidence)
        self.assertEqual(result.text, "ready")

    def test_only_fixed_text_request_is_sent_with_tls_and_timeout(self):
        response = ResponseFixture((FIXTURES / "success.json").read_bytes())
        result, connection, ctor = self.run_fixture(self.client(), self.evidence(), response)
        self.assertEqual(result.text, "ready")
        self.assertEqual(result.model, "gemini-3.5-flash-lite")
        self.assertEqual(result.usage, {"promptTokenCount": 9, "candidatesTokenCount": 2, "totalTokenCount": 11})
        args, kwargs = ctor.call_args
        self.assertEqual(args, ("generativelanguage.googleapis.com",))
        self.assertEqual(kwargs["port"], 443)
        self.assertEqual(kwargs["timeout"], 30)
        self.assertTrue(kwargs["context"].check_hostname)
        self.assertEqual(kwargs["context"].verify_mode, ssl.CERT_REQUIRED)
        self.assertIsNone(kwargs["context"].keylog_filename)
        self.assertEqual(len(connection.requests), 1)
        method, path, body, headers = connection.requests[0]
        self.assertEqual(method, "POST")
        self.assertEqual(path, "/v1beta/models/gemini-3.5-flash-lite:generateContent")
        self.assertNotIn(SYNTHETIC_KEY, path)
        self.assertEqual(headers["x-goog-api-key"], SYNTHETIC_KEY)
        self.assertEqual(json.loads(body), {
            "contents": [{"role": "user", "parts": [{"text": PROMPT}]}],
            "generationConfig": {"candidateCount": 1, "maxOutputTokens": 256, "responseModalities": ["TEXT"]},
            "tools": [],
        })
        self.assertTrue(connection.closed)

    def test_proxy_environment_is_not_consulted_with_explicit_config(self):
        class ForbiddenEnvironment:
            def get(self, *args, **kwargs):
                raise AssertionError("Environment access is forbidden in explicit-config requests")
            def __getitem__(self, key):
                raise AssertionError("Environment access is forbidden in explicit-config requests")
        with mock.patch.object(self.direct.os, "environ", ForbiddenEnvironment()):
            result, _, _ = self.run_fixture(
                self.client(), self.evidence(), ResponseFixture((FIXTURES / "success.json").read_bytes())
            )
        self.assertEqual(result.text, "ready")

    def test_environment_loader_reads_only_dedicated_caller_key(self):
        requested = []
        class CallerEnvironment:
            def get(self, key, default=None):
                requested.append(key)
                return SYNTHETIC_KEY if key == "GEMINI_DIRECT_API_KEY" else default
        config = self.direct.Config.from_environment(environ=CallerEnvironment())
        self.assertEqual(requested, ["GEMINI_DIRECT_API_KEY"])
        self.assertNotIn(SYNTHETIC_KEY, repr(config))
        self.assertFalse(config.enabled)

    def test_dry_request_contains_no_prompt_key_or_auth_headers(self):
        dry = self.direct.dry_request()
        self.assertEqual(set(dry), {"endpoint", "body_shape"})
        self.assertEqual(dry["endpoint"], "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent")
        serialized = json.dumps(dry)
        for forbidden in (SYNTHETIC_KEY, PROMPT, "x-goog-api-key", "Authorization"):
            self.assertNotIn(forbidden, serialized)

    def test_mutating_a_preview_cannot_enable_image_output_in_real_request(self):
        preview = self.direct.dry_request()
        preview["body_shape"]["generationConfig"]["responseModalities"].append("IMAGE")
        try:
            _, connection, _ = self.run_fixture(
                self.client(), self.evidence(), ResponseFixture((FIXTURES / "success.json").read_bytes())
            )
            body = json.loads(connection.requests[0][2])
            self.assertEqual(body["generationConfig"]["responseModalities"], ["TEXT"])
        finally:
            # Until the regression is fixed, don't contaminate later tests.
            preview["body_shape"]["generationConfig"]["responseModalities"].remove("IMAGE")

    def test_global_http_debug_setting_cannot_print_authorization_headers(self):
        response_bytes = (FIXTURES / "success.json").read_bytes()
        class OfflineSocket:
            def sendall(self, data):
                pass
            def makefile(self, mode):
                return io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: " +
                    str(len(response_bytes)).encode() + b"\r\n\r\n" + response_bytes)
            def close(self):
                pass
        def connect_offline(connection):
            connection.sock = OfflineSocket()
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(self.direct.http.client.HTTPConnection, "debuglevel", 1):
            with mock.patch.object(self.direct.http.client.HTTPSConnection, "connect", connect_offline):
                with mock.patch.object(self.direct, "_utc_now", return_value=NOW):
                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        result = self.client().generate_once(PROMPT, evidence=self.evidence())
        self.assertEqual(result.text, "ready")
        self.assertNotIn(SYNTHETIC_KEY, stdout.getvalue() + stderr.getvalue())

    def test_invalid_unicode_prompt_becomes_a_static_error_before_http(self):
        self.assert_blocked_without_connection(self.client(), self.evidence(), prompt="invalid\ud800text")

    def test_oversized_multibyte_prompt_or_key_in_prompt_is_blocked_before_http(self):
        self.assert_blocked_without_connection(self.client(), self.evidence(), prompt="한" * 24000)
        self.assert_blocked_without_connection(self.client(), self.evidence(), prompt=SYNTHETIC_KEY)
        self.assert_blocked_without_connection(self.client(), self.evidence(), prompt={"text": PROMPT})

    def test_redirect_rate_limit_and_server_error_are_not_retried_or_followed(self):
        for status in (301, 302, 307, 308, 401, 403, 429, 500, 503):
            with self.subTest(status=status):
                connection = ConnectionFixture(ResponseFixture(b"sensitive upstream error", status=status,
                    headers={"location": "https://untrusted.invalid/"}))
                with mock.patch.object(self.direct.http.client, "HTTPSConnection", return_value=connection) as ctor:
                    with mock.patch.object(self.direct, "_utc_now", return_value=NOW):
                        with self.assertRaises(self.direct.CandidateError):
                            self.client().generate_once(PROMPT, evidence=self.evidence())
                self.assertEqual(ctor.call_count, 1)
                self.assertEqual(len(connection.requests), 1)
                self.assertEqual(connection.response.read_sizes, [])
                self.assertTrue(connection.closed)

    def test_transport_exception_is_sanitized_without_exception_context(self):
        client, evidence = self.client(), self.evidence()
        connection = ConnectionFixture(request_error=OSError(SYNTHETIC_KEY + " " + PROMPT))
        with mock.patch.object(self.direct.http.client, "HTTPSConnection", return_value=connection):
            with mock.patch.object(self.direct, "_utc_now", return_value=NOW):
                try:
                    client.generate_once(PROMPT, evidence=evidence)
                except self.direct.CandidateError as exc:
                    self.assertNotIn(SYNTHETIC_KEY, str(exc))
                    self.assertNotIn(SYNTHETIC_KEY, repr(exc))
                    self.assertNotIn(SYNTHETIC_KEY, "".join(traceback.format_exception(exc)))
                    self.assertIsNone(exc.__context__)
                else:
                    self.fail("Leaky upstream errors must become a sanitized failure")
        self.assertTrue(connection.closed)

    def test_a_client_and_an_evidence_id_cannot_send_a_second_request(self):
        client, evidence = self.client(), self.evidence()
        self.run_fixture(client, evidence, ResponseFixture((FIXTURES / "success.json").read_bytes()))
        self.assert_blocked_without_connection(client, self.evidence())
        self.assert_blocked_without_connection(self.client(), evidence)

    def test_failed_ambiguous_network_attempt_consumes_evidence(self):
        evidence = self.evidence()
        with self.assertRaises(self.direct.CandidateError):
            self.run_fixture(self.client(), evidence, request_error=TimeoutError("timeout"))
        self.assert_blocked_without_connection(self.client(), evidence)

    def test_oversized_or_non_json_response_is_sanitized_and_bounded(self):
        responses = (
            ResponseFixture(b"x" * (64 * 1024 + 1)),
            ResponseFixture(b"", headers={"content-length": str(64 * 1024 + 1)}),
            ResponseFixture(("not-json " + SYNTHETIC_KEY).encode()),
        )
        for response in responses:
            with self.subTest(headers=response.headers):
                with self.assertRaises(self.direct.CandidateError) as caught:
                    self.run_fixture(self.client(), self.evidence(), response)
                self.assertNotIn(SYNTHETIC_KEY, str(caught.exception))
                self.assertTrue(all(size <= 64 * 1024 + 1 for size in response.read_sizes))

    def test_key_echo_tool_calls_and_filtered_content_are_not_returned(self):
        success = json.loads((FIXTURES / "success.json").read_text())
        echoed = copy.deepcopy(success)
        echoed["candidates"][0]["content"]["parts"][0]["text"] = SYNTHETIC_KEY
        for body in (
            echoed,
            json.loads((FIXTURES / "tool_call.json").read_text()),
            json.loads((FIXTURES / "blocked.json").read_text()),
        ):
            with self.subTest(kind=list(body)):
                with self.assertRaises(self.direct.CandidateError) as caught:
                    self.run_fixture(self.client(), self.evidence(), ResponseFixture(json.dumps(body).encode()))
                self.assertNotIn(SYNTHETIC_KEY, str(caught.exception))


if __name__ == "__main__":
    unittest.main()

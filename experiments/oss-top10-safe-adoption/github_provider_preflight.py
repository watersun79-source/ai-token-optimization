"""Bounded GitHub REST API read check: Actions context is NOT Site context.

Makes exactly one GET for a pinned commit with a read-only Actions token.
Does not echo tokens, error bodies or arbitrary HTTP headers; never retries
or changes GitHub, Site, D1, scheduling or production.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import unittest
from urllib import error, request

API = "https://api.github.com/repos/watersun79-source/ai-token-optimization/git/commits/"
SHA = re.compile(r"[0-9a-f]{40}\Z")
RID = re.compile(r"[A-Za-z0-9:.-]{1,80}\Z")
MAX_BYTES = 65536


def result(sha, verdict, status=None, hdr=None, matched=False):
    headers = hdr if callable(getattr(hdr, "get", None)) else {}
    def get(name):
        val = headers.get(name, "")
        return val if isinstance(val, str) else ""
    remaining = get("x-ratelimit-remaining")
    request_id = get("x-github-request-id")
    return {
        "schema": "GH_PROVIDER_ACTIONS_PROBE_V1",
        "status": verdict,
        "http_status": status,
        "sha_match": bool(matched),
        "rate_limit_remaining": int(remaining) if remaining.isdigit() and len(remaining) < 10 else None,
        "retry_after_present": bool(get("retry-after")),
        "sso_indicator_present": bool(get("x-github-sso")),
        "github_request_id": request_id if RID.fullmatch(request_id) else None,
        "scope": "ACTIONS_READ_TOKEN_NOT_SITE_CREDENTIAL",
        "site_authentication": "UNVERIFIED",
        "site_403_root_cause": "UNVERIFIED",
        "operational_clearance": "BLOCKED",
        "external_api_get_attempts": 0 if verdict == "INPUT_INVALID" else 1,
        "external_mutations": 0,
        "allow_retry": False,
        "allow_write": False,
    }


def probe(sha, token, opener=request.urlopen):
    if (not isinstance(sha, str) or not SHA.fullmatch(sha)
            or not isinstance(token, str) or not 8 <= len(token) <= 4096
            or "\r" in token or "\n" in token):
        return result("", "INPUT_INVALID")
    req = request.Request(
        API + sha, method="GET",
        headers={"Accept": "application/vnd.github+json",
                 "Authorization": "Bearer " + token,
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "PR31-readonly-provider-probe"})
    try:
        with opener(req, timeout=8) as response:
            status, headers = response.status, response.headers
            if status != 200:
                return result(sha, "BLOCKED_UNEXPECTED_STATUS", status, headers)
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                return result(sha, "UNVERIFIED_RESPONSE", status, headers)
            try:
                doc = json.loads(raw)
            except (TypeError, ValueError, UnicodeError):
                return result(sha, "UNVERIFIED_RESPONSE", status, headers)
            match = isinstance(doc, dict) and doc.get("sha") == sha
            return result(sha, "PASS_ACTIONS_ONLY" if match else "BLOCKED_SHA_MISMATCH", status, headers, match)
    except error.HTTPError as exc:
        status, h = exc.code, exc.headers
        h = h if callable(getattr(h, "get", None)) else {}
        if status in (403, 429):
            if h.get("x-github-sso"):
                reason = "BLOCKED_SSO_INDICATOR"
            elif h.get("x-ratelimit-remaining") == "0":
                reason = "BLOCKED_RATE_LIMIT_INDICATOR"
            elif h.get("retry-after"):
                reason = "BLOCKED_RETRY_AFTER_INDICATOR"
            else:
                reason = ("BLOCKED_429_UNDETERMINED" if status == 429
                          else "BLOCKED_403_UNDETERMINED")
        elif status == 401:
            reason = "BLOCKED_AUTH"
        elif status == 404:
            reason = "BLOCKED_NOT_VISIBLE"
        else:
            reason = "BLOCKED_HTTP_ERROR"
        return result(sha, reason, status, h)
    except (error.URLError, TimeoutError, OSError, ValueError):
        return result(sha, "UNVERIFIED_TRANSPORT")


class StubResponse:
    def __init__(self, sha, raw=None, status=200):
        self.status, self.headers = status, {}
        self.raw = json.dumps({"sha": sha}).encode() if raw is None else raw

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, amount):
        return self.raw[:amount]


class ContractTests(unittest.TestCase):
    sha = "a" * 40
    token = "test-token-only"

    def test_good_actions_sha_never_clears_site(self):
        x = probe(self.sha, self.token, lambda *_a, **_k: StubResponse(self.sha))
        self.assertEqual(x["status"], "PASS_ACTIONS_ONLY")
        self.assertEqual(x["site_authentication"], "UNVERIFIED")
        self.assertEqual(x["operational_clearance"], "BLOCKED")
        self.assertFalse(x["allow_write"])

    def test_wrong_sha_blocks(self):
        x = probe(self.sha, self.token, lambda *_a, **_k: StubResponse("b"*40))
        self.assertEqual(x["status"], "BLOCKED_SHA_MISMATCH")

    def test_403_rate_indicator(self):
        def reject(*_a, **_k):
            raise error.HTTPError(API, 403, "private", {"x-ratelimit-remaining": "0"}, None)
        self.assertEqual(probe(self.sha, self.token, reject)["status"], "BLOCKED_RATE_LIMIT_INDICATOR")

    def test_403_other_unknown(self):
        def reject(*_a, **_k):
            raise error.HTTPError(API, 403, "private", {}, None)
        self.assertEqual(probe(self.sha, self.token, reject)["status"], "BLOCKED_403_UNDETERMINED")

    def test_sso_url_redacted(self):
        def reject(*_a, **_k):
            raise error.HTTPError(API, 403, "no", {"x-github-sso": "authorize: secret-url"}, None)
        x = probe(self.sha, self.token, reject)
        self.assertEqual(x["status"], "BLOCKED_SSO_INDICATOR")
        self.assertNotIn("secret-url", json.dumps(x))

    def test_retry_after(self):
        def reject(*_a, **_k):
            raise error.HTTPError(API, 429, "no", {"retry-after": "60"}, None)
        self.assertEqual(probe(self.sha, self.token, reject)["status"], "BLOCKED_RETRY_AFTER_INDICATOR")

    def test_403_missing_headers_fails_closed(self):
        def reject(*_a, **_k):
            raise error.HTTPError(API, 403, "blocked", None, None)
        x = probe(self.sha, self.token, reject)
        self.assertEqual(x["status"], "BLOCKED_403_UNDETERMINED")
        self.assertFalse(x["allow_retry"])
        self.assertFalse(x["allow_write"])

    def test_429_missing_headers_reports_correct_status(self):
        def reject(*_a, **_k):
            raise error.HTTPError(API, 429, "rate-limited", None, None)
        x = probe(self.sha, self.token, reject)
        self.assertEqual(x["status"], "BLOCKED_429_UNDETERMINED")
        self.assertEqual(x["http_status"], 429)
        self.assertFalse(x["allow_retry"])

    def test_403_invalid_headers_fails_closed(self):
        def reject(*_a, **_k):
            raise error.HTTPError(API, 403, "blocked", "malformed-headers", None)
        x = probe(self.sha, self.token, reject)
        self.assertEqual(x["status"], "BLOCKED_403_UNDETERMINED")

    def test_429_zero_remaining_keeps_rate_limit_classification(self):
        def reject(*_a, **_k):
            raise error.HTTPError(API, 429, "blocked", {"x-ratelimit-remaining": "0"}, None)
        x = probe(self.sha, self.token, reject)
        self.assertEqual(x["status"], "BLOCKED_RATE_LIMIT_INDICATOR")
        self.assertFalse(x["allow_retry"])


    def test_bad_token_never_calls(self):
        called = []
        x = probe(self.sha, "", lambda *_a, **_k: called.append(1))
        self.assertEqual(x["status"], "INPUT_INVALID")
        self.assertEqual(called, [])

    def test_bad_sha_never_calls(self):
        called = []
        x = probe("invalid", self.token, lambda *_a, **_k: called.append(1))
        self.assertEqual(x["status"], "INPUT_INVALID")
        self.assertEqual(called, [])

    def test_only_one_get_pinned_sha(self):
        calls = []
        def openit(req, timeout):
            calls.append((req.get_method(), req.full_url, timeout))
            return StubResponse(self.sha)
        probe(self.sha, self.token, openit)
        self.assertEqual(calls, [("GET", API + self.sha, 8)])

    def test_secret_body_never_echoed(self):
        body = json.dumps({"sha": self.sha, "secret": "never-output"}).encode()
        x = probe(self.sha, "secret-token-test", lambda *_a, **_k: StubResponse(self.sha, raw=body))
        self.assertNotIn("never-output", json.dumps(x))
        self.assertNotIn("secret-token-test", json.dumps(x))

    def test_network_error_has_no_retry(self):
        calls = []
        def timeout(*_a, **_k):
            calls.append(1)
            raise error.URLError("private error")
        x = probe(self.sha, self.token, timeout)
        self.assertEqual(x["status"], "UNVERIFIED_TRANSPORT")
        self.assertEqual(len(calls), 1)

    def test_invalid_json_fails_closed(self):
        x = probe(self.sha, self.token, lambda *_a, **_k: StubResponse(self.sha, raw=b'bad'))
        self.assertEqual(x["status"], "UNVERIFIED_RESPONSE")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sha")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 2
    x = probe(args.sha, os.environ.get("GH_PREFLIGHT_TOKEN"))
    print(json.dumps(x, sort_keys=True, separators=(",", ":")))
    return 0 if x["status"] == "PASS_ACTIONS_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())

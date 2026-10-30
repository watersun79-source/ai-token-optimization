"""One-shot, public-only HTTPS assertion for isolated v8.3.5 Render gateway.

No credentials, no real synthetic job accepted, no scheduled polling.
Allows intake_enabled True OR False so CI does not become an obstacle to
later manual secure configuration. It MUST always reject unauthenticated work.
"""
from __future__ import annotations
import json
import re
import sys
import urllib.error
import urllib.request

BASE = "https://ai-bot-v835-neon-isolated-20261030.onrender.com"


class StrictNoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("UNEXPECTED_REDIRECT")


def verify() -> int:
    opener = urllib.request.build_opener(StrictNoRedirect)
    try:
        req = urllib.request.Request(BASE + "/healthz", headers={
            "Accept": "application/json",
            "User-Agent": "ai-v835-one-shot-safe-ci/1",
        })
        with opener.open(req, timeout=95) as response:
            if response.status != 200:
                raise ValueError("HEALTH_HTTP_NOT_200")
            if "application/json" not in response.headers.get("Content-Type", ""):
                raise ValueError("WRONG_HEALTH_CONTENT_TYPE")
            raw = response.read(4097)
            if len(raw) > 4096:
                raise ValueError("HEALTH_TOO_LARGE")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("HEALTH_NOT_OBJECT")
        required = {
            "status": "UP",
            "version": "8.3.5",
            "synthetic_only": True,
            "backend": "neon_postgres",
            "production_connected": False,
            "always_on_verified": False,
            "automatic_recovery_verified": False,
        }
        if any(data.get(key) != expected for key, expected in required.items()):
            raise ValueError("HEALTH_CONTRACT_MISMATCH")
        for field in ("intake_enabled", "database_connection_verified"):
            if type(data.get(field)) is not bool:
                raise ValueError("INVALID_STATUS_FLAG")
        if not re.fullmatch("[a-f0-9]{20}", str(data.get("boot_id", ""))):
            raise ValueError("INVALID_BOOT_ID")
        # Intentionally NO X-Queue-Key; this must always be rejected.
        submit = urllib.request.Request(
            BASE + "/private/submit",
            data=b'{"task_id":"synthetic-v83-noauth-v835","kind":"offline_check"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with opener.open(submit, timeout=25) as response:
                status = response.status
                body = response.read(1024)
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read(1024)
        if status != 401:
            raise ValueError("UNAUTHENTICATED_SUBMIT_WAS_NOT_DENIED")
        payload = json.loads(body)
        if payload != {"error": "UNAUTHORIZED"}:
            raise ValueError("UNEXPECTED_REJECTION_RESPONSE")
        print("V835_EXTERNAL_HTTPS_PASS status=200 version=8.3.5")
        print("V835_UNAUTHENTICATED_SUBMIT_PASS status=401")
        print("V835_INTAKE_ENABLED=" + str(data["intake_enabled"]).lower())
        print("V835_DATABASE_CONNECTION_VERIFIED=" + str(data["database_connection_verified"]).lower())
        print("V835_HOSTED_RECOVERY_VERIFIED=false ALWAYS_ON_VERIFIED=false")
        return 0
    except (ValueError, OSError, urllib.error.URLError, TimeoutError,
            json.JSONDecodeError) as e:
        print("V835_EXTERNAL_HTTPS_FAIL=" + type(e).__name__)
        return 1


if __name__ == "__main__":
    sys.exit(verify())

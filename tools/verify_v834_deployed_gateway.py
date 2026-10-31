"""One-shot Render v8.3.4 HTTPS proof for isolated PR CI.

Exactly one GET and one unauthorized POST against the public synthetic-only
gateway. Never provides a credential, never queues a job or exposes secrets.
The test PROVES only one-time HTTPS reachability & fail-closed auth.
"""
import json
import re
import sys
import urllib.error
import urllib.request

BASE = "https://ai-bot-v834-isolated-gateway-20261030.onrender.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("REDIRECT_NOT_ALLOWED")


def check() -> int:
    http = urllib.request.build_opener(NoRedirect)
    try:
        get = urllib.request.Request(BASE + "/healthz", headers={
            "Accept": "application/json",
            "User-Agent": "isolated-v834-official-ci-once/1",
        })
        with http.open(get, timeout=95) as r:
            if r.status != 200 or "application/json" not in r.headers.get("Content-Type", ""):
                raise ValueError("HEALTH_STATUS_OR_TYPE")
            data = r.read(4097)
            if len(data) > 4096:
                raise ValueError("OVERSIZED_HEALTH_RESPONSE")
        parsed = json.loads(data)
        required = {
            "status": "UP",
            "version": "8.3.4",
            "synthetic_only": True,
            "ingress_configured": False,
            "persistent_disk_verified": False,
            "production_connected": False,
            "always_on_verified": False,
        }
        if not isinstance(parsed, dict) or any(parsed.get(k) != v for k, v in required.items()):
            raise ValueError("HEALTH_CONTRACT_MISMATCH")
        if not isinstance(parsed.get("boot_id"), str) or not re.fullmatch(
            "[a-f0-9]{20}", parsed["boot_id"]
        ):
            raise ValueError("INVALID_BOOT_ID")
        req = urllib.request.Request(
            BASE + "/private/submit",
            method="POST",
            data=b'{"task_id":"synthetic-v83-unauthorized","kind":"offline_check"}',
            headers={"Content-Type": "application/json"},
        )
        try:
            with http.open(req, timeout=20) as r:
                status = r.status
        except urllib.error.HTTPError as e:
            status = e.code
        if status != 401:
            raise ValueError("UNAUTHENTICATED_JOB_NOT_BLOCKED")
        print("V834_PUBLIC_HEALTH_PASS http=200 version=8.3.4 ingress_configured=false")
        print("V834_UNAUTHORIZED_SUBMIT_PASS http=401")
        print("BOOT_ID=" + parsed["boot_id"])
        print("UPTIME_SECONDS=" + str(parsed.get("uptime_seconds", "UNKNOWN")))
        print("PERSISTENCE_PROVEN=false ALWAYS_ON_PROVEN=false")
        return 0
    except (ValueError, TimeoutError, OSError, urllib.error.URLError,
            json.JSONDecodeError) as ex:
        print("V834_HTTPS_VERIFICATION_FAIL " + type(ex).__name__)
        return 1


if __name__ == "__main__":
    sys.exit(check())

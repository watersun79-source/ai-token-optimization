"""One-shot, credential-free, bounded external HTTPS probe (isolated PR only).

This script sends exactly one HTTPS GET to the public read-only /healthz
endpoint; it does not ping repeatedly, mutate state, or fetch user data.
A successful response attests HTTPS at one instant, NOT 24/7 availability.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request

URL = "https://ai-bot-v832-isolated-probe-20261030.onrender.com/healthz"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("UNEXPECTED_REDIRECT")


def main() -> int:
    req = urllib.request.Request(
        URL, headers={"Accept": "application/json", "User-Agent": "ai-bot-isolated-ci-readonly-probe/1"}
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=95) as response:
            status = response.status
            body = response.read(4097)
            media = response.headers.get("Content-Type", "")
        if status != 200 or len(body) > 4096 or "application/json" not in media:
            print("HTTPS_PROBE_FAIL INVALID_STATUS_OR_CONTENT_TYPE")
            return 1
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("INVALID_BODY")
        if not (data.get("status") == "UP"
                and data.get("probe_version") == "8.3.2"
                and data.get("lease_code_version") == "8.3.1"
                and data.get("read_only") is True
                and data.get("jobs_enabled") is False
                and data.get("persistent_database_connected") is False
                and data.get("native_execution_verified") is False
                and data.get("automatic_restart_verified") is False
                and isinstance(data.get("uptime_seconds"), int)
                and data["uptime_seconds"] >= 0
                and isinstance(data.get("boot_id"), str)
                and re.fullmatch(r"[0-9a-f]{20}", data["boot_id"])):
            print("HTTPS_PROBE_FAIL UNEXPECTED_PUBLIC_HEALTH_CONTRACT")
            return 1
        print("HTTPS_PROBE_PASS status=200 probe=v8.3.2 read_only=true jobs=false")
        print("BOOT_ID=" + data["boot_id"])
        print("UPTIME_SECONDS=" + str(data["uptime_seconds"]))
        print("AUTOMATIC_RESTART_PROVEN=false")
        return 0
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, RuntimeError,
            ValueError, UnicodeError, json.JSONDecodeError) as exc:
        # Never expose redirects, HTTP response bodies, or secrets.
        print("HTTPS_PROBE_FAIL " + type(exc).__name__)
        return 1


if __name__ == "__main__":
    sys.exit(main())

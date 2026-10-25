"""One-shot SHA-bound queued task: actual offline Python worker, no secrets or network."""
import hashlib
import json
from pathlib import Path
import re

from real_gateway import run_message

QUEUE_PATH = Path(__file__).with_name("task_request.json")
REQUIRED = {"task_id", "mode", "message", "expected_input_sha256"}


def execute(request: dict) -> dict:
    if not isinstance(request, dict) or set(request) != REQUIRED:
        raise ValueError("invalid task request structure")
    task_id, mode = request["task_id"], request["mode"]
    message, expected = request["message"], request["expected_input_sha256"]
    if not isinstance(task_id, str) or not re.fullmatch(r"r16-[0-9a-z-]{8,56}", task_id):
        raise ValueError("invalid task id")
    if mode != "bounded_offline_optimize":
        raise ValueError("unapproved task mode")
    if not isinstance(message, str) or not message.strip() or len(message) > 1200:
        raise ValueError("invalid bounded task text")
    if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("invalid expected digest")
    if hashlib.sha256(message.encode("utf-8")).hexdigest() != expected:
        raise ValueError("task digest mismatch")
    result = run_message(message, network=False)
    if result.get("status") != "DONE" or result.get("selected_roles") != ["ai-optimization"]:
        raise ValueError("task did not execute its approved offline worker")
    workers = result.get("workers") or []
    if len(workers) != 1 or workers[0].get("status") != "DONE":
        raise ValueError("worker execution was not successful")
    evidence = workers[0].get("evidence") or {}
    if evidence.get("input_sha256") != expected:
        raise ValueError("worker receipt digest mismatch")
    output_sha = evidence.get("output_sha256")
    if not isinstance(output_sha, str) or not re.fullmatch(r"[a-f0-9]{64}", output_sha):
        raise ValueError("worker receipt output digest missing")
    if evidence.get("external_model_calls") != 0 or result.get("production_writes") != 0:
        raise ValueError("worker attempted disallowed external or production action")
    return {
        "status": "PASS",
        "kind": "REAL_ISOLATED_GITHUB_HOSTED_PYTHON_TASK_NOT_NATIVE_CHATGPT",
        "task_id": task_id,
        "input_sha256": expected,
        "output_sha256": output_sha,
        "bytes_saved": evidence.get("bytes_saved"),
        "duplicate_lines_removed": evidence.get("duplicate_lines_removed"),
        "external_model_calls": 0,
        "production_writes": 0,
        "native_chatgpt_run_verified": False,
    }


def main() -> int:
    try:
        blob = QUEUE_PATH.read_bytes()
        if len(blob) > 4096:
            raise ValueError("oversize task file")
        task = json.loads(blob)
        result = execute(task)
    except Exception:
        print('R16_REAL_QUEUED_TASK=' + json.dumps({
            "status": "BLOCKED", "native_chatgpt_run_verified": False
        }, sort_keys=True))
        return 2
    print('R16_REAL_QUEUED_TASK=' + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

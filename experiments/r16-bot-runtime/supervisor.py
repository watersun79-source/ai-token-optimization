"""Isolated, free, offline R16 BOT supervisor. No provider APIs or writes outside state dir."""
import argparse
import fcntl  # Unix/Linux worker: non-blocking advisory process lock
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def run_once(state_dir: Path, *, script=ROOT / "batch_validate_100.py", timeout=120):
    """Run at most one check per state directory (Linux/Unix workers only)."""
    state_dir.mkdir(parents=True, exist_ok=True)
    # flock releases automatically when the owning process closes or crashes.
    # O_NOFOLLOW prevents a pre-existing lock-file symlink redirection.
    fd = os.open(state_dir / ".supervisor.lock",
                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # Do not overwrite latest.json with the status of a skipped run.
            return {"status": "BUSY", "reason": "another_check_is_running",
                    "kind": "OFFLINE_LOCAL_CHECK_NOT_SCHEDULED_APP_PROOF"}
        return _run_once_locked(state_dir, script=script, timeout=timeout)
    finally:
        os.close(fd)


def _run_once_locked(state_dir: Path, *, script, timeout):
    started = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run([sys.executable, str(script)], cwd=ROOT,
                              capture_output=True, text=True, timeout=timeout)
        result = {"status": "PASS" if proc.returncode == 0 else "ERROR",
                  "exit_code": proc.returncode,
                  "stdout_tail": proc.stdout[-2000:],
                  "stderr_tail": proc.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        result = {"status": "ERROR", "reason": "timeout"}
    result["started_at"] = started
    result["completed_at"] = datetime.now(timezone.utc).isoformat()
    result["kind"] = "OFFLINE_LOCAL_CHECK_NOT_SCHEDULED_APP_PROOF"
    target = state_dir / "latest.json"
    temp = state_dir / ("latest." + str(os.getpid()) + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, target)
    return result


def main():
    parser = argparse.ArgumentParser(description="Offline R16 supervisor (no external APIs)")
    parser.add_argument("--once", action="store_true", help="Run one check then exit")
    parser.add_argument("--interval", type=int, default=3600, help="Seconds between checks (>=3600)")
    parser.add_argument("--state-dir", type=Path, default=ROOT / ".supervisor_state")
    args = parser.parse_args()
    if args.interval < 3600:
        parser.error("interval must be >= 3600 seconds")
    while True:
        result = run_once(args.state_dir)
        print(json.dumps({"status": result["status"], "kind": result["kind"]}), flush=True)
        if args.once:
            return 0 if result["status"] == "PASS" else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())

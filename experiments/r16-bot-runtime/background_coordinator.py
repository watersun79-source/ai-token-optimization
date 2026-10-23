"""Opt-in offline BOT coordinator loop.

Not a ChatGPT scheduled run, a cloud deployment, or independent LLM agents.
Nothing starts merely by importing or pushing this module.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import time

from bot_coordinator import dispatch

ROOT = Path(__file__).resolve().parent
KIND = "OFFLINE_BACKGROUND_LOOP_NOT_NATIVE_RESERVATION"


def run_loop(goal, state_dir, *, interval_seconds=3600, max_runs=None,
             dispatch_fn=None, sleep_fn=None, emit_fn=None):
    """Hold one daemon lock, periodically invoke the offline rule dispatcher.

    max_runs is a test/manual limit; None means run until externally stopped.
    A process manager and an always-on host are needed for unattended uptime.
    """
    if interval_seconds < 3600:
        raise ValueError("interval must be at least 3600 seconds")
    if max_runs is not None and max_runs < 1:
        raise ValueError("max_runs must be positive")
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    dispatch_fn = dispatch if dispatch_fn is None else dispatch_fn
    sleep_fn = time.sleep if sleep_fn is None else sleep_fn
    emit_fn = print if emit_fn is None else emit_fn

    # Own this lock across all sleep intervals to exclude a duplicate daemon.
    fd = os.open(state_dir / ".background.lock",
                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "BUSY", "kind": KIND,
                    "reason": "another_background_loop_is_running"}

        cycles = 0
        errors = 0
        while max_runs is None or cycles < max_runs:
            started = datetime.now(timezone.utc).isoformat()
            try:
                receipt = dispatch_fn(goal, state_dir)
                if not isinstance(receipt, dict) or receipt.get("status") not in ("PASS", "BUSY", "ERROR"):
                    raise ValueError("invalid dispatcher status")
                status = receipt["status"]
            except Exception as exc:
                # Do not serialize exceptions or traceback text (possibly sensitive).
                status = "ERROR"
                receipt = {"status": status, "reason": type(exc).__name__}
            cycles += 1
            if status != "PASS":
                errors += 1
            event = {
                "kind": KIND, "goal": goal, "cycle": cycles,
                "status": status, "errors": errors,
                "started_at": started,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "official_unattended_app_call_success": "UNVERIFIED",
                "executed_selected_rule_checks": receipt.get("executed_selected_rule_checks", 0),
                "selected_statuses": receipt.get("selected_statuses", {}),
                "selected_outcome": receipt.get("selected_outcome", "UNVERIFIED"),
                "selected_evidence_scope": "OFFLINE_SNAPSHOT_NOT_PROVIDER_AUTHENTICATED",
            }
            # Replace atomically; never claim this is official platform telemetry.
            target = state_dir / "background_latest.json"
            temp = state_dir / ("background." + str(os.getpid()) + ".tmp")
            temp.write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
            os.replace(temp, target)
            emit_fn(json.dumps(event, ensure_ascii=False))
            if max_runs is not None and cycles >= max_runs:
                break
            sleep_fn(interval_seconds)
        return {"status": "PASS" if errors == 0 else "ERROR",
                "kind": KIND, "cycles": cycles, "errors": errors}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description="Offline BOT loop (opt-in, no cloud deployment)")
    parser.add_argument("--goal", choices=["audit", "build", "research", "verify"], default="audit")
    parser.add_argument("--state-dir", type=Path, default=ROOT / ".supervisor_state")
    parser.add_argument("--repeat", action="store_true",
                        help="Opt in to repeated checks (requires an always-on host)")
    parser.add_argument("--interval", type=int, default=3600)
    parser.add_argument("--max-runs", type=int, default=None,
                        help="Limit repeat cycles for manual/CI verification")
    args = parser.parse_args()
    if args.max_runs is not None and not args.repeat:
        parser.error("--max-runs requires --repeat")
    result = run_loop(args.goal, args.state_dir,
                      interval_seconds=args.interval,
                      max_runs=(args.max_runs if args.repeat else 1))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

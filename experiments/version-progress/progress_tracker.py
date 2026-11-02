"""AI BOT version progress reconciler (OFFLINE, NO network or production writes).

Input is independently authenticated provider evidence. This pure function validates
structural gates only. Caller MUST enforce remote D1 expected_version CAS.
"""
import copy
import datetime as dt
import json
from pathlib import Path


class ProgressError(ValueError):
    pass


class Conflict(ProgressError):
    pass


def utc(raw):
    try:
        d = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise ValueError("timezone")
        return d.astimezone(dt.timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ProgressError("offset-aware timestamp required") from exc


def reconcile(board, observation, expected_version, record_version):
    if expected_version != record_version:
        raise Conflict("CAS mismatch: reread authoritative D1 record")
    if board.get("schema") != "AI_BOT_VERSION_PROGRESS_BOARD_V1":
        raise ProgressError("wrong schema")
    ids = [i for i, x in enumerate(board.get("components", []))
           if x.get("id") == observation.get("id")]
    if len(ids) != 1:
        raise ProgressError("missing or duplicate component id")
    c = board["components"][ids[0]]
    if not observation.get("authenticated_source") or not observation.get("evidence_id"):
        raise ProgressError("independently authenticated evidence required")
    observed = utc(observation.get("observed_at"))
    if c.get("last_observed_at") and observed < utc(c["last_observed_at"]):
        raise ProgressError("stale evidence")
    proposed = observation.get("gates", {})
    if (not isinstance(proposed, dict)
        or any(k not in c.get("gates", {}) for k in proposed)
        or any(x not in ("PASS", "IN_PROGRESS", "BLOCKED", "UNVERIFIED", "NO_UPDATE")
               for x in proposed.values())):
        raise ProgressError("invalid milestone")
    sensitive = {"deploy", "deployed", "current_deploy", "runtime_release",
                 "live", "live_binding", "external_ledger", "result_same_run",
                 "native_integration"}
    if any(k in sensitive and x == "PASS" for k, x in proposed.items()):
        p = observation.get("runtime_proof", {})
        if not isinstance(p, dict) or not p.get("authenticated_provider_readback") or not p.get("receipt_id"):
            raise ProgressError("provider runtime proof required")
    v = observation.get("version", c.get("version"))
    if v != c.get("version"):
        proof = observation.get("version_proof", {})
        if not isinstance(proof, dict) or not proof.get("authenticated_provider_readback"):
            raise ProgressError("cannot upgrade version from an assertion")
        needed = ("approval_id", "deployment_id", "live_health_receipt", "source_sha") if c["id"] == "bot_operating" else ("source_sha", "ci_run_id", "ci_success_receipt")
        if any(not proof.get(k) for k in needed):
            raise ProgressError("missing release evidence")
    out = copy.deepcopy(board)
    target = out["components"][ids[0]]
    changed = False
    if v != target.get("version"):
        target["version"] = v
        changed = True
    for k, x in proposed.items():
        if target["gates"][k] != x:
            target["gates"][k] = x
            changed = True
    if observation.get("state") and observation["state"] != target.get("state"):
        if observation["state"] not in ("PASS", "IN_PROGRESS", "BLOCKED", "UNVERIFIED", "NO_UPDATE", "CI_VERIFIED"):
            raise ProgressError("bad state")
        target["state"] = observation["state"]
        changed = True
    if observation.get("source_sha") and observation["source_sha"] != target.get("last_source_sha"):
        target["last_source_sha"] = observation["source_sha"]
        changed = True
    if not changed:
        return board, "NO_UPDATE"
    target["last_observed_at"] = observation["observed_at"]
    target["last_evidence_id"] = observation["evidence_id"]
    event = {"component_id": target["id"], "at": observation["observed_at"],
             "evidence_id": observation["evidence_id"], "result": "COMPONENT_PROGRESS_CHANGED"}
    history = out.get("history", [])
    if not any(x.get("component_id") == event["component_id"] and
               x.get("evidence_id") == event["evidence_id"] for x in history):
        out["history"] = (history + [event])[-12:]
    out["source_snapshot_at_utc"] = observation["observed_at"]
    return out, "UPDATE"


def main():
    import argparse
    p = argparse.ArgumentParser(description="Offline isolated version progress reconciler")
    p.add_argument("--board", type=Path, required=True)
    p.add_argument("--observation", type=Path, required=True)
    p.add_argument("--expected-version", type=int, required=True)
    p.add_argument("--record-version", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    board = json.loads(a.board.read_text(encoding="utf-8"))
    obs = json.loads(a.observation.read_text(encoding="utf-8"))
    result, status = reconcile(board, obs, a.expected_version, a.record_version)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()

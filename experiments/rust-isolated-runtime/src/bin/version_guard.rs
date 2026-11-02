//! Offline Rust version/progress reconciler for the existing shared D1 board.
//! It never performs network requests, writes D1, changes schedules or promotes production.
//! The caller must *independently* authenticate evidence and perform server-side CAS.
use chrono::DateTime;
use serde_json::{json, Value};
use std::{env, fs, process};

const SCHEMA: &str = "AI_BOT_VERSION_PROGRESS_BOARD_V1";
const STATES: &[&str] = &["PASS", "IN_PROGRESS", "BLOCKED", "UNVERIFIED", "NO_UPDATE"];

fn nonempty(v: &Value, key: &str) -> bool {
    v.get(key)
        .and_then(Value::as_str)
        .is_some_and(|s| !s.trim().is_empty())
}

fn timestamp(v: &Value, key: &str) -> Result<i64, String> {
    let raw = v
        .get(key)
        .and_then(Value::as_str)
        .ok_or("missing timestamp")?;
    DateTime::parse_from_rfc3339(raw)
        .map(|t| t.timestamp_millis())
        .map_err(|_| "offset-aware RFC3339 timestamp required".into())
}

fn reconcile(
    board: &Value,
    observation: &Value,
    expected_version: u64,
    record_version: u64,
) -> Result<(Value, &'static str), String> {
    if expected_version != record_version {
        return Err("CAS_CONFLICT: reread the D1 record".into());
    }
    if board.get("schema").and_then(Value::as_str) != Some(SCHEMA) {
        return Err("INVALID_SCHEMA".into());
    }
    let components = board
        .get("components")
        .and_then(Value::as_array)
        .ok_or("INVALID_COMPONENTS")?;
    let id = observation
        .get("id")
        .and_then(Value::as_str)
        .ok_or("MISSING_ID")?;
    let matches: Vec<usize> = components
        .iter()
        .enumerate()
        .filter(|(_, item)| item.get("id").and_then(Value::as_str) == Some(id))
        .map(|(idx, _)| idx)
        .collect();
    if matches.len() != 1 {
        return Err("UNKNOWN_OR_DUPLICATE_COMPONENT".into());
    }
    let component = &components[matches[0]];
    if observation
        .get("authenticated_source")
        .and_then(Value::as_bool)
        != Some(true)
        || !nonempty(observation, "evidence_id")
    {
        return Err("MISSING_AUTHENTICATED_EVIDENCE_ASSERTION".into());
    }
    let observed = timestamp(observation, "observed_at")?;
    if component
        .get("last_observed_at")
        .is_some_and(Value::is_string)
        && observed < timestamp(component, "last_observed_at")?
    {
        return Err("STALE_EVIDENCE".into());
    }
    let gates = component
        .get("gates")
        .and_then(Value::as_object)
        .ok_or("INVALID_GATES")?;
    let proposed = observation
        .get("gates")
        .map(|v| v.as_object().ok_or("INVALID_PROPOSED_GATES"))
        .transpose()?;
    if let Some(proposed) = proposed {
        for (gate, value) in proposed {
            let state = value.as_str().ok_or("INVALID_STATE")?;
            if !gates.contains_key(gate) || !STATES.contains(&state) {
                return Err("UNKNOWN_GATE_OR_STATE".into());
            }
            if state == "PASS"
                && matches!(
                    gate.as_str(),
                    "deploy"
                        | "deployed"
                        | "current_deploy"
                        | "runtime_release"
                        | "live"
                        | "live_binding"
                        | "external_ledger"
                        | "result_same_run"
                        | "native_integration"
                )
            {
                let proof = observation.get("runtime_proof").unwrap_or(&Value::Null);
                if proof
                    .get("authenticated_provider_readback")
                    .and_then(Value::as_bool)
                    != Some(true)
                    || !nonempty(proof, "receipt_id")
                {
                    return Err("MISSING_PROVIDER_RUNTIME_RECEIPT".into());
                }
            }
        }
    }
    let version = observation.get("version").unwrap_or(&component["version"]);
    if version != &component["version"] {
        let proof = observation.get("version_proof").unwrap_or(&Value::Null);
        if proof
            .get("authenticated_provider_readback")
            .and_then(Value::as_bool)
            != Some(true)
        {
            return Err("VERSION_NOT_AUTHENTICATED".into());
        }
        let required: &[&str] = if id == "bot_operating" {
            &[
                "approval_id",
                "deployment_id",
                "live_health_receipt",
                "source_sha",
            ]
        } else {
            &["source_sha", "ci_run_id", "ci_success_receipt"]
        };
        if required.iter().any(|key| !nonempty(proof, key)) {
            return Err("MISSING_VERSION_RELEASE_RECEIPT".into());
        }
    }
    let mut next = board.clone();
    let target = &mut next["components"][matches[0]];
    let mut changed = false;
    if version != &target["version"] {
        target["version"] = version.clone();
        changed = true;
    }
    if let Some(proposed) = proposed {
        for (gate, value) in proposed {
            if target["gates"][gate] != *value {
                target["gates"][gate] = value.clone();
                changed = true;
            }
        }
    }
    if let Some(state) = observation.get("state") {
        let state_str = state.as_str().ok_or("INVALID_COMPONENT_STATE")?;
        if !STATES.contains(&state_str) && state_str != "CI_VERIFIED" {
            return Err("INVALID_COMPONENT_STATE".into());
        }
        if target["state"] != *state {
            target["state"] = state.clone();
            changed = true;
        }
    }
    if nonempty(observation, "source_sha") && target["last_source_sha"] != observation["source_sha"]
    {
        target["last_source_sha"] = observation["source_sha"].clone();
        changed = true;
    }
    if !changed {
        return Ok((board.clone(), "NO_UPDATE"));
    }
    target["last_observed_at"] = observation["observed_at"].clone();
    target["last_evidence_id"] = observation["evidence_id"].clone();
    let mut history = next
        .get("history")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    if !history
        .iter()
        .any(|x| x["component_id"] == id && x["evidence_id"] == observation["evidence_id"])
    {
        history.push(json!({
            "component_id": id,
            "at": observation["observed_at"],
            "evidence_id": observation["evidence_id"],
            "result": "COMPONENT_PROGRESS_CHANGED"
        }));
    }
    if history.len() > 12 {
        history.drain(..history.len() - 12);
    }
    next["history"] = Value::Array(history);
    next["source_snapshot_at_utc"] = observation["observed_at"].clone();
    Ok((next, "UPDATE"))
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 6 || args[1] != "--reconcile" {
        return Err("USAGE: version_guard --reconcile <board.json> <observation.json> <expected_revision> <actual_revision>".into());
    }
    let board = fs::read_to_string(&args[2]).map_err(|_| "BOARD_READ_ERROR")?;
    let observation = fs::read_to_string(&args[3]).map_err(|_| "OBSERVATION_READ_ERROR")?;
    let board: Value = serde_json::from_str(&board).map_err(|_| "INVALID_BOARD_JSON")?;
    let observation: Value =
        serde_json::from_str(&observation).map_err(|_| "INVALID_OBSERVATION_JSON")?;
    let expected: u64 = args[4].parse().map_err(|_| "INVALID_REVISION")?;
    let actual: u64 = args[5].parse().map_err(|_| "INVALID_REVISION")?;
    let (candidate, status) = reconcile(&board, &observation, expected, actual)?;
    println!(
        "{}",
        json!({"status": status, "candidate_board": candidate, "remote_write_performed": false})
    );
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn board() -> Value {
        json!({
            "schema": SCHEMA,
            "components": [
                {"id":"github_isolated_dev","version":"v8.5.14","state":"CI_VERIFIED",
                 "gates":{"ci":"PASS","review":"UNVERIFIED","live":"UNVERIFIED"}},
                {"id":"bot_operating","version":"v8.1","state":"NO_UPDATE",
                 "gates":{"deployed":"UNVERIFIED","live":"UNVERIFIED"}}
            ],
            "history": []
        })
    }
    fn obs() -> Value {
        json!({"id":"github_isolated_dev", "authenticated_source":true,
               "evidence_id":"synthetic-1", "observed_at":"2026-11-03T00:10:00Z",
               "gates":{"review":"IN_PROGRESS"}})
    }
    #[test]
    fn updates_only_target() {
        let old = board();
        let (new, code) = reconcile(&old, &obs(), 3, 3).unwrap();
        assert_eq!(code, "UPDATE");
        assert_eq!(new["components"][0]["gates"]["review"], "IN_PROGRESS");
        assert_eq!(new["components"][1], old["components"][1]);
        assert_eq!(old["components"][0]["gates"]["review"], "UNVERIFIED");
    }
    #[test]
    fn no_update_does_not_bump() {
        let mut o = obs();
        o["gates"] = json!({"ci":"PASS"});
        let (new, code) = reconcile(&board(), &o, 3, 3).unwrap();
        assert_eq!(code, "NO_UPDATE");
        assert_eq!(new, board());
    }
    #[test]
    fn cas_conflict() {
        assert!(reconcile(&board(), &obs(), 3, 4)
            .unwrap_err()
            .contains("CAS_CONFLICT"));
    }
    #[test]
    fn version_requires_provider_proof() {
        let mut o = obs();
        o["version"] = json!("v9.9.9");
        assert_eq!(
            reconcile(&board(), &o, 1, 1).unwrap_err(),
            "VERSION_NOT_AUTHENTICATED"
        );
    }
    #[test]
    fn operating_requires_deploy_and_approval() {
        let mut o = obs();
        o["id"] = json!("bot_operating");
        o["version"] = json!("v9.9");
        o["version_proof"] = json!({
            "authenticated_provider_readback":true,"source_sha":"a",
            "ci_run_id":"12","ci_success_receipt":"ok"
        });
        assert_eq!(
            reconcile(&board(), &o, 1, 1).unwrap_err(),
            "MISSING_VERSION_RELEASE_RECEIPT"
        );
    }
    #[test]
    fn live_requires_runtime_receipt() {
        let mut o = obs();
        o["gates"] = json!({"live":"PASS"});
        assert_eq!(
            reconcile(&board(), &o, 1, 1).unwrap_err(),
            "MISSING_PROVIDER_RUNTIME_RECEIPT"
        );
    }
    #[test]
    fn rejects_unknown_component() {
        let mut o = obs();
        o["id"] = json!("not_exist");
        assert!(reconcile(&board(), &o, 1, 1).is_err());
    }
    #[test]
    fn rejects_untrusted_source() {
        let mut o = obs();
        o["authenticated_source"] = json!(false);
        assert!(reconcile(&board(), &o, 1, 1).is_err());
    }
    #[test]
    fn rejects_stale_source() {
        let mut b = board();
        b["components"][0]["last_observed_at"] = json!("2026-11-03T00:11:00Z");
        assert_eq!(reconcile(&b, &obs(), 1, 1).unwrap_err(), "STALE_EVIDENCE");
    }
    #[test]
    fn rejects_unknown_gate() {
        let mut o = obs();
        o["gates"] = json!({"other":"PASS"});
        assert!(reconcile(&board(), &o, 1, 1).is_err());
    }
    #[test]
    fn rejects_timezone_naive() {
        let mut o = obs();
        o["observed_at"] = json!("2026-11-03T00:10:00");
        assert!(reconcile(&board(), &o, 1, 1).is_err());
    }
    #[test]
    fn handles_timezone_offset() {
        let mut b = board();
        b["components"][0]["last_observed_at"] = json!("2026-11-03T09:09:00+09:00");
        assert_eq!(reconcile(&b, &obs(), 1, 1).unwrap().1, "UPDATE");
    }
    #[test]
    fn bounded_history() {
        let mut b = board();
        b["history"] = Value::Array(
            (0..25)
                .map(|i| json!({"evidence_id":i.to_string()}))
                .collect(),
        );
        assert_eq!(
            reconcile(&b, &obs(), 1, 1).unwrap().0["history"]
                .as_array()
                .unwrap()
                .len(),
            12
        );
    }
    #[test]
    fn duplicate_component_rejected() {
        let mut b = board();
        let duplicate = b["components"][0].clone();
        b["components"].as_array_mut().unwrap().push(duplicate);
        assert_eq!(
            reconcile(&b, &obs(), 1, 1).unwrap_err(),
            "UNKNOWN_OR_DUPLICATE_COMPONENT"
        );
    }
    #[test]
    fn validates_component_state() {
        let mut o = obs();
        o["state"] = json!("DEPLOYED");
        assert_eq!(
            reconcile(&board(), &o, 1, 1).unwrap_err(),
            "INVALID_COMPONENT_STATE"
        );
    }
    #[test]
    fn unchanged_evidence_dedup() {
        let (b, _) = reconcile(&board(), &obs(), 1, 1).unwrap();
        let (again, state) = reconcile(&b, &obs(), 2, 2).unwrap();
        assert_eq!(state, "NO_UPDATE");
        assert_eq!(again["history"].as_array().unwrap().len(), 1);
    }
}

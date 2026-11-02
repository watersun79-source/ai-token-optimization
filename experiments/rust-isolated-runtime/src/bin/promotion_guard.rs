//! Offline, fail-closed pre-production evidence checklist for the Rust pilot.
//! NO provider authentication, deployments, D1 writes or secret access occur.
//! Even structurally complete evidence needs independent provider verification.
use serde_json::{json, Value};
use std::{env, fs, process};

fn nonblank(v: &Value, path: &[&str]) -> bool {
    let mut x = v;
    for key in path {
        x = match x.get(*key) {
            Some(value) => value,
            None => return false,
        };
    }
    x.as_str().is_some_and(|s| !s.trim().is_empty())
}
fn is_true(v: &Value, path: &[&str]) -> bool {
    let mut x = v;
    for key in path {
        x = match x.get(*key) {
            Some(value) => value,
            None => return false,
        };
    }
    x.as_bool() == Some(true)
}
fn sha40(v: &Value, key: &str) -> bool {
    v.get(key).and_then(Value::as_str).is_some_and(|s| {
        s.len() == 40 && s.bytes().all(|b| b.is_ascii_hexdigit())
    })
}
fn evaluate(v: &Value) -> Value {
    let mut missing = Vec::new();
    if v.get("target").and_then(Value::as_str) != Some("production") {
        missing.push("PRODUCTION_TARGET");
    }
    let head_ok = sha40(v, "candidate_sha");
    if !head_ok {
        missing.push("PINNED_CANDIDATE_SHA");
    }
    if !sha40(v, "ci_head_sha") || !head_ok || v["candidate_sha"] != v["ci_head_sha"] {
        missing.push("MATCHING_OFFICIAL_CI_SHA");
    }
    if !nonblank(v, &["approval", "authorized_change_receipt"]) {
        missing.push("CHANGE_APPROVAL_RECEIPT");
    }
    if !nonblank(v, &["deployment", "immutable_release_receipt"]) {
        missing.push("DEPLOYMENT_RECEIPT");
    }
    if !nonblank(v, &["auth", "provider_identity_receipt"]) {
        missing.push("PROVIDER_AUTHENTICATION_RECEIPT");
    }
    if !nonblank(v, &["auth", "role_policy_receipt"]) {
        missing.push("ROLE_AUTHORIZATION_RECEIPT");
    }
    if !nonblank(v, &["transport", "tls_gateway_receipt"]) {
        missing.push("PRODUCTION_TRANSPORT_PROTECTION");
    }
    if !nonblank(v, &["secrets", "boundary_review_receipt"]) {
        missing.push("SECRET_BOUNDARY_REVIEW");
    }
    if !nonblank(v, &["rollback", "verified_artifact_receipt"])
        || !nonblank(v, &["rollback", "rehearsal_receipt"])
    {
        missing.push("ROLLBACK_ARTIFACT_AND_REHEARSAL");
    }
    if !nonblank(v, &["health", "live_provider_readback_receipt"]) {
        missing.push("LIVE_HEALTH_AND_READBACK");
    }
    if !is_true(v, &["protected", "main_unchanged"])
        || !is_true(v, &["protected", "existing_automations_unchanged"])
        || !is_true(v, &["protected", "no_unapproved_paid_calls"])
    {
        missing.push("PROTECTED_ASSETS_AND_COST_CONTROLS");
    }
    let decision = if missing.is_empty() {
        "INDEPENDENT_PROVIDER_REVIEW_REQUIRED"
    } else {
        "BLOCKED_MISSING_EVIDENCE"
    };
    json!({
        "decision": decision,
        "missing": missing,
        "automatic_promotion_allowed": false,
        "provider_evidence_authenticated": false,
        "actual_deployment_performed": false,
        "remote_writes": 0,
        "scope": "ISOLATED_OFFLINE_STRUCTURAL_CHECK_ONLY"
    })
}
fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 || args[1] != "--check" {
        return Err("USAGE: promotion_guard --check evidence.json".into());
    }
    let body = fs::read_to_string(&args[2]).map_err(|_| "INPUT_READ_FAILED")?;
    let v: Value = serde_json::from_str(&body).map_err(|_| "INVALID_JSON")?;
    let result = evaluate(&v);
    println!("{result}");
    // Fail closed regardless of JSON assertions: human/provider review is required.
    Err("PROMOTION_NOT_AUTHORIZED_BY_OFFLINE_TOOL".into())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        process::exit(2);
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn complete() -> Value {
        let sha = "a".repeat(40);
        json!({
            "target":"production","candidate_sha":sha,"ci_head_sha":sha,
            "approval":{"authorized_change_receipt":"synthetic"},
            "deployment":{"immutable_release_receipt":"synthetic"},
            "auth":{"provider_identity_receipt":"synthetic","role_policy_receipt":"synthetic"},
            "transport":{"tls_gateway_receipt":"synthetic"},
            "secrets":{"boundary_review_receipt":"synthetic"},
            "rollback":{"verified_artifact_receipt":"synthetic","rehearsal_receipt":"synthetic"},
            "health":{"live_provider_readback_receipt":"synthetic"},
            "protected":{"main_unchanged":true,"existing_automations_unchanged":true,"no_unapproved_paid_calls":true}
        })
    }
    fn missing(x: &Value, expected: &str) {
        let v = evaluate(x);
        assert_eq!(v["decision"], "BLOCKED_MISSING_EVIDENCE");
        assert!(v["missing"].as_array().unwrap().iter().any(|g| g == expected));
        assert_eq!(v["automatic_promotion_allowed"], false);
    }
    #[test]
    fn missing_evidence_blocks() { missing(&json!({}), "PROVIDER_AUTHENTICATION_RECEIPT"); }
    #[test]
    fn no_identity_blocks() {
        let mut v=complete();v["auth"]["provider_identity_receipt"]=json!(null);
        missing(&v,"PROVIDER_AUTHENTICATION_RECEIPT");
    }
    #[test]
    fn no_authorization_blocks() {
        let mut v=complete();v["auth"]["role_policy_receipt"]=json!(null);
        missing(&v,"ROLE_AUTHORIZATION_RECEIPT");
    }
    #[test]
    fn no_transport_receipt_blocks() {
        let mut v=complete();v["transport"]["tls_gateway_receipt"]=json!(null);
        missing(&v,"PRODUCTION_TRANSPORT_PROTECTION");
    }
    #[test]
    fn no_rollback_rehearsal_blocks() {
        let mut v=complete();v["rollback"]["rehearsal_receipt"]=json!(null);
        missing(&v,"ROLLBACK_ARTIFACT_AND_REHEARSAL");
    }
    #[test]
    fn no_actual_health_readback_blocks() {
        let mut v=complete();v["health"]["live_provider_readback_receipt"]=json!(null);
        missing(&v,"LIVE_HEALTH_AND_READBACK");
    }
    #[test]
    fn mismatched_sha_blocks() {
        let mut v=complete();v["ci_head_sha"]=json!("b".repeat(40));
        missing(&v,"MATCHING_OFFICIAL_CI_SHA");
    }
    #[test]
    fn existing_tasks_change_blocks() {
        let mut v=complete();v["protected"]["existing_automations_unchanged"]=json!(false);
        missing(&v,"PROTECTED_ASSETS_AND_COST_CONTROLS");
    }
    #[test]
    fn all_synthetic_fields_still_never_authorize_promotion() {
        let x=evaluate(&complete());
        assert_eq!(x["decision"],"INDEPENDENT_PROVIDER_REVIEW_REQUIRED");
        assert_eq!(x["automatic_promotion_allowed"],false);
        assert_eq!(x["provider_evidence_authenticated"],false);
        assert_eq!(x["actual_deployment_performed"],false);
        assert_eq!(x["remote_writes"],0);
    }
}
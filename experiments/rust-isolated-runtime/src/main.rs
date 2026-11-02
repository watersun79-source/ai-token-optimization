//! Isolated, std-only Rust control plane scaffold.
//! This program NEVER invokes models, reads account secrets, or changes live workflows.
use std::io::{self, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::time::Duration;

const LOCAL_STATUS: &str = r#"{"engine":"rust","scope":"ISOLATED_LOCAL_ONLY","operating_bot":"v8.1_UNCHANGED","native_chatgpt":"UNVERIFIED","provider_sync":"UNVERIFIED","paid_model_calls":0}"#;
const HEALTH: &str = r#"{"status":"ok","engine":"rust","scope":"LOCAL_PROCESS_ONLY","production_deployed":false}"#;

fn event_verdict(event: &str) -> &'static str {
    match event {
        "schedule" => "GITHUB_SCHEDULE_NOT_NATIVE_CHATGPT",
        "workflow_dispatch" => "GITHUB_DISPATCH_NOT_SCHEDULE",
        _ => "UNVERIFIED_EVENT",
    }
}

/// A matching ID and sensible time order only prove internal consistency.
/// They do NOT establish a real same-run ChatGPT-to-provider invocation.
fn native_verdict(
    run_id: &str,
    result_run_id: Option<&str>,
    scheduled: i64,
    started: i64,
    completed: Option<i64>,
) -> &'static str {
    if run_id.is_empty() || result_run_id != Some(run_id) {
        return "UNVERIFIED_RESULT_ID";
    }
    if started < scheduled {
        return "UNVERIFIED_STARTED_BEFORE_SCHEDULE";
    }
    if completed.is_none_or(|end| end < started) {
        return "UNVERIFIED_COMPLETION";
    }
    "IDS_AND_TIMES_CONSISTENT_EXTERNAL_LEDGER_UNVERIFIED"
}

fn handle_local(mut stream: TcpStream) -> io::Result<()> {
    stream.set_read_timeout(Some(Duration::from_secs(2)))?;
    stream.set_write_timeout(Some(Duration::from_secs(2)))?;
    let mut buf = [0_u8; 2048];
    let size = stream.read(&mut buf)?;
    let request = String::from_utf8_lossy(&buf[..size]);
    let (status, body) = match request.lines().next().unwrap_or("") {
        "GET /healthz HTTP/1.1" | "GET /healthz HTTP/1.0" => ("200 OK", HEALTH),
        "GET /status HTTP/1.1" | "GET /status HTTP/1.0" => ("200 OK", LOCAL_STATUS),
        _ => ("404 Not Found", r#"{"error":"not_found"}"#),
    };
    let response = format!(
        "HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    );
    stream.write_all(response.as_bytes())?;
    stream.flush()
}

fn serve_local() -> io::Result<()> {
    // The bind address is intentionally fixed to loopback: never expose this pilot publicly.
    let listener = TcpListener::bind("127.0.0.1:8765")?;
    println!("RUST_ISOLATED_LOOPBACK_READY 127.0.0.1:8765");
    for connection in listener.incoming() {
        handle_local(connection?)?;
    }
    Ok(())
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    match args.as_slice() {
        [_, mode] if mode == "--once" => println!("{LOCAL_STATUS}"),
        [_, mode] if mode == "--serve" => {
            if let Err(error) = serve_local() {
                eprintln!("LOCAL_SERVER_ERROR: {error}");
                std::process::exit(1);
            }
        }
        [_, mode, event] if mode == "--event" => println!("{}", event_verdict(event)),
        [_, mode, id, result, sched, start, end] if mode == "--native-check" => {
            let parsed = (sched.parse::<i64>(), start.parse::<i64>(), end.parse::<i64>());
            match parsed {
                (Ok(scheduled), Ok(started), Ok(completed)) => {
                    println!("{}", native_verdict(id, Some(result), scheduled, started, Some(completed)));
                }
                _ => {
                    eprintln!("INVALID_INTEGER_TIMESTAMP");
                    std::process::exit(2);
                }
            }
        }
        _ => {
            eprintln!("USAGE: --once | --serve | --event <event> | --native-check <run> <result> <scheduled_epoch> <started_epoch> <completed_epoch>");
            std::process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::{TcpListener, TcpStream};
    use std::thread;

    #[test]
    fn schedule_is_not_native() {
        assert_eq!(event_verdict("schedule"), "GITHUB_SCHEDULE_NOT_NATIVE_CHATGPT");
    }
    #[test]
    fn dispatch_is_not_schedule() {
        assert_eq!(event_verdict("workflow_dispatch"), "GITHUB_DISPATCH_NOT_SCHEDULE");
    }
    #[test]
    fn unknown_event_is_unverified() {
        assert_eq!(event_verdict("push"), "UNVERIFIED_EVENT");
    }
    #[test]
    fn result_id_mismatch_is_not_pass() {
        assert_eq!(native_verdict("run-1", Some("run-2"), 100, 100, Some(101)), "UNVERIFIED_RESULT_ID");
    }
    #[test]
    fn missing_result_id_is_not_pass() {
        assert_eq!(native_verdict("run-1", None, 100, 100, Some(101)), "UNVERIFIED_RESULT_ID");
    }
    #[test]
    fn early_start_is_not_pass() {
        assert_eq!(native_verdict("run-1", Some("run-1"), 100, 99, Some(101)), "UNVERIFIED_STARTED_BEFORE_SCHEDULE");
    }
    #[test]
    fn incomplete_is_not_pass() {
        assert_eq!(native_verdict("run-1", Some("run-1"), 100, 101, None), "UNVERIFIED_COMPLETION");
    }
    #[test]
    fn inverted_completion_is_not_pass() {
        assert_eq!(native_verdict("run-1", Some("run-1"), 100, 102, Some(101)), "UNVERIFIED_COMPLETION");
    }
    #[test]
    fn matching_records_do_not_attest_provider() {
        assert_eq!(native_verdict("run-1", Some("run-1"), 100, 100, Some(101)), "IDS_AND_TIMES_CONSISTENT_EXTERNAL_LEDGER_UNVERIFIED");
    }
    #[test]
    fn local_health_endpoint_only() {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral loopback");
        let addr = listener.local_addr().expect("local addr");
        let worker = thread::spawn(move || {
            let (socket, _) = listener.accept().expect("accept local connection");
            handle_local(socket).expect("handle request");
        });
        let mut client = TcpStream::connect(addr).expect("connect loopback");
        client.write_all(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\n\r\n").expect("write request");
        let mut response = String::new();
        client.read_to_string(&mut response).expect("read response");
        worker.join().expect("join worker");
        assert!(response.starts_with("HTTP/1.1 200 OK"));
        assert!(response.contains("LOCAL_PROCESS_ONLY"));
        assert!(response.contains("production_deployed"));
    }
    #[test]
    fn no_false_production_or_native_attestation() {
        assert!(LOCAL_STATUS.contains("ISOLATED_LOCAL_ONLY"));
        assert!(LOCAL_STATUS.contains(r#""native_chatgpt":"UNVERIFIED""#));
        assert!(HEALTH.contains(r#""production_deployed":false"#));
    }
}

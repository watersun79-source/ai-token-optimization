"""Bounded local text optimization worker: no shell, network, model or repo writes."""
import argparse
import hashlib
import json
import re
import sys

MAX_INPUT = 4000
SECRET = re.compile(r"(?i)(?:\bsk-[A-Za-z0-9_-]{12,}|\b(?:api[_-]?key|token|password|secret)\s*[=:]\s*[^\s]{8,})")

def compact(text):
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_INPUT:
        raise ValueError("input must contain 1..4000 characters")
    if SECRET.search(text):
        raise ValueError("suspected credential; refuse processing")
    seen, kept, removed = set(), [], 0
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            kept.append(line)
            continue
        if in_code:
            # Code indentation, blank lines and repeated statements carry meaning.
            kept.append(line)
            continue
        normalized = re.sub(r"\s+", " ", line).strip()
        if not normalized:
            continue
        if normalized in seen:
            removed += 1
            continue
        seen.add(normalized)
        kept.append(normalized)
    if in_code:
        raise ValueError("unclosed code fence; refuse lossy compaction")
    output = "\n".join(kept)
    original_bytes = len(text.encode("utf-8"))
    output_bytes = len(output.encode("utf-8"))
    return {
        "status": "DONE", "kind": "REAL_LOCAL_TEXT_DEDUP_NOT_LLM",
        "input_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "original_bytes": original_bytes, "output_bytes": output_bytes,
        "bytes_saved": original_bytes - output_bytes,
        "duplicate_lines_removed": removed, "output": output,
        "external_model_calls": 0, "production_writes": 0,
    }

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--stdin", action="store_true", required=True)
    p.parse_args(argv)
    data = sys.stdin.read(MAX_INPUT * 4 + 1)
    try:
        result = compact(data)
    except ValueError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print("R16_TASK_EXECUTOR=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

"""Bounded local text optimization worker: no shell, network, model or repo writes."""
import argparse
import hashlib
import json
import re
import sys

MAX_INPUT = 4000
SECRET = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9_-]{12,}|\bgh[pousr]_[A-Za-z0-9_]{20,}|"
    r"\bgithub_pat_[A-Za-z0-9_]{20,}|"
    r"\b(?:[A-Za-z][A-Za-z0-9]*[_-])*(?:api[_-]?key|access[_-]?token|"
    r"auth[_-]?token|token|password|secret)\s*[=:]\s*[^\s]{8,}|"
    r"\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[^\s]{8,})"
)
# JSON/Python-style quoted configuration keys must not bypass secret guards.
QUOTED_SECRET = re.compile(
    r"""(?i)["'](?:[A-Za-z][A-Za-z0-9]*[_-])*(?:api[_-]?key|"""
    r"""access[_-]?token|auth[_-]?token|token|password|secret)["']\s*:\s*"""
    r"""["'][^"'\\\s]{8,}["']"""
)
# Quoted HTTP Authorization values include a space after their scheme.
QUOTED_AUTH = re.compile(
    r"""(?i)["'](?:[A-Za-z][A-Za-z0-9]*[_-])*authorization["']\s*:\s*"""
    r"""["'](?:Bearer|Basic)\s+[^"'\\\s]{8,}["']"""
)
# Markdown fence opener/closer: 0..3 spaces, >=3 matching backticks or tildes.
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
# Preserve top-level function calls: repeated invocations may have side effects.
CALL_LINE = re.compile(r"^ {0,3}[A-Za-z_$][\w.$]*\(.*\)\s*;?$")
# Bare assignments (including +=) may invoke code or change mutable state.
ASSIGNMENT_LINE = re.compile(
    r"^ {0,3}(?:(?:const|let|var)\s+)?[A-Za-z_$][\w.$]*"
    r"(?:\[[^\]\n]+\])?\s*(?::=|[+\-*/%&|^]?=)\s*\S"
)
# Structural Markdown tokens are semantic blocks, not redundant prose.
STRUCTURAL = re.compile(r"^ {0,3}(?:#{1,6}(?:[ \t]|$)|[-+*][ \t]|\d{1,9}[.)][ \t]|>|[|]|(?:[-*_][ \t]*){3,}$)")

# Setext headings use the following underline: repetitions are structural, not prose.
SETEXT_UNDERLINE = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")

def compact(text):
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_INPUT:
        raise ValueError("input must contain 1..4000 characters")
    if SECRET.search(text) or QUOTED_SECRET.search(text) or QUOTED_AUTH.search(text):
        raise ValueError("suspected credential; refuse processing")
    # Parsed JSON lists/objects are structured data, not duplicate prose.
    # Preserve array multiplicity and exact serialized bytes.
    preserve_json = False
    if text.lstrip().startswith(("{", "[")):
        try:
            preserve_json = isinstance(json.loads(text), (dict, list))
        except json.JSONDecodeError:
            pass
    seen, kept, removed = set(), [], 0
    in_code = False
    fence_char, fence_len = "", 0
    lines = [] if preserve_json else text.splitlines()
    for index, line in enumerate(lines):
        fence = FENCE.match(line)
        if in_code:
            # Only a matching marker of sufficient length can close this fence.
            if (fence and fence.group(1)[0] == fence_char
                    and len(fence.group(1)) >= fence_len
                    and not fence.group(2).strip()):
                in_code = False
            # Code indentation, blank lines and repeated statements carry meaning.
            kept.append(line)
            continue
        if fence and (fence.group(1)[0] == "~" or "`" not in fence.group(2)):
            fence_char, fence_len = fence.group(1)[0], len(fence.group(1))
            in_code = True
            kept.append(line)
            continue
        if line.startswith(("    ", "\t")):
            # Markdown indented code and its repeated side effects are not prose.
            # Never deduplicate or normalize executable lines.
            kept.append(line)
            continue
        if SETEXT_UNDERLINE.match(line) or (
            index + 1 < len(lines) and SETEXT_UNDERLINE.match(lines[index + 1])
        ):
            # Preserve Setext titles and underlines even when repeated.
            kept.append(line)
            continue
        if STRUCTURAL.match(line):
            # Repeated headings, tasks, table rows or quotations must survive.
            kept.append(line)
            continue
        # Markdown hard line breaks are meaningful: trailing double spaces or
        # a backslash must survive even on repeated textual lines.
        if line.strip() and (line.endswith("  ") or line.endswith(chr(92))):
            kept.append(line)
            continue
        if CALL_LINE.match(line):
            # Unfenced executable-looking calls are not redundant prose.
            kept.append(line)
            continue
        if ASSIGNMENT_LINE.match(line):
            # Repeated assignments can have side effects or accumulate state.
            kept.append(line)
            continue
        normalized = re.sub(r"\s+", " ", line).strip()
        if not normalized:
            # Preserve the boundary around an indented code block, otherwise
            # removing it can silently change Markdown rendering semantics.
            next_is_code = (index + 1 < len(lines)
                            and lines[index + 1].startswith(("    ", "\t")))
            previous_is_code = bool(kept and kept[-1].startswith(("    ", "\t")))
            if next_is_code or previous_is_code:
                kept.append(line)
            continue
        if normalized in seen:
            removed += 1
            continue
        seen.add(normalized)
        kept.append(normalized)
    if in_code:
        raise ValueError("unclosed code fence; refuse lossy compaction")
    output = text if preserve_json else "\n".join(kept)
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

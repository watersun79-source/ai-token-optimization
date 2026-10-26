"""Execute a SHA-guarded text patch only inside an explicitly supplied scratch root.

No network, shell, GitHub writes, repo modification or arbitrary paths.
"""
from __future__ import annotations
import ast
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile

_ALLOWED = re.compile(r"[a-zA-Z0-9_-]{1,64}\.(?:txt|py)\Z")
_MAX_BYTES = 8192

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def apply_patch(scratch_root: str | Path, filename: str, *, expected_sha256: str,
                old: str, new: str) -> dict:
    """Replace one literal match in a scratch .txt or .py file, atomically."""
    if not isinstance(filename, str) or not _ALLOWED.fullmatch(filename):
        raise ValueError("only flat .txt or .py fixture names allowed")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise ValueError("valid SHA256 precondition required")
    if not isinstance(old, str) or not old or not isinstance(new, str):
        raise ValueError("literal nonempty old and string new required")
    if old == new:
        raise ValueError("no-op patch refused")
    if len(old.encode()) > _MAX_BYTES or len(new.encode()) > _MAX_BYTES:
        raise ValueError("patch too large")
    requested_root = Path(scratch_root)
    # Check BEFORE resolve(): resolving a symlink hides that it was a link.
    # Refuse symlinks in parent directories as well as the final scratch root.
    # A linked ancestor otherwise redirects a normal leaf outside the sandbox.
    lexical_path = requested_root.absolute()
    if any(component.is_symlink() for component in (lexical_path, *lexical_path.parents)):
        raise ValueError("symlink scratch root or ancestor refused")
    root = requested_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("scratch root must be a real directory")
    target = root / filename
    if target.is_symlink() or not target.is_file():
        raise ValueError("regular fixture file required")
    if target.stat().st_size > _MAX_BYTES:
        raise ValueError("fixture too large")
    original = target.read_bytes()
    if sha256(original) != expected_sha256:
        raise ValueError("SHA precondition mismatch; refusing stale patch")
    text = original.decode("utf-8")
    if text.count(old) != 1:
        raise ValueError("patch must match exactly once")
    patched = text.replace(old, new, 1).encode("utf-8")
    if len(patched) > _MAX_BYTES:
        raise ValueError("patched file too large")
    if filename.endswith(".py"):
        # Never execute user code; refuse a syntax-breaking patch before writing.
        ast.parse(patched.decode("utf-8"), filename=filename)
    # Atomic replacement otherwise resets permissions to mkstemp's 0600.
    original_mode = stat.S_IMODE(target.stat().st_mode)
    fd, temp_name = tempfile.mkstemp(prefix=".patch-", suffix=".tmp", dir=root)
    try:
        os.fchmod(fd, original_mode)
        with os.fdopen(fd, "wb") as f:
            f.write(patched)
            f.flush()
            os.fsync(f.fileno())
        if target.is_symlink() or sha256(target.read_bytes()) != expected_sha256:
            raise ValueError("target changed before commit")
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {"status": "DONE", "file": filename, "before_sha256": expected_sha256,
            "after_sha256": sha256(patched), "bytes_before": len(original),
            "bytes_after": len(patched), "production_writes": 0,
            "external_model_calls": 0, "scope": "LOCAL_SCRATCH_ONLY"}

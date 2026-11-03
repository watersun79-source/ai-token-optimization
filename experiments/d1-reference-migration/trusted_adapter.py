"""Isolated provenance-checked adapter and crash-recovery protocol.

NO network/production credentials/D1 connectors/schedulers or deploy action.
HMAC receipts here describe an offline *contract*; official MCP content_sha is
opaque and is NOT an authenticated MAC or proof of source identity. A future
provider transport would need its own independent authentication review.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Protocol

from guard import Conflict, FailClosed, utf16_units
from migration import Evidence, REPORT_KEY, plan_migration

MAX_UNITS = 10000
SHA = re.compile(r'^[0-9a-f]{64}$')


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


@dataclass(frozen=True)
class SealedReceipt:
    evidence: Evidence
    purpose: str
    nonce: str
    issuer: str
    audience: str
    mac: str
    request_id: str = ''
    expected_version: int | None = None


def receipt_payload(r: SealedReceipt) -> dict:
    e = r.evidence
    return {'type': 'D1_ISOLATED_RECEIPT_V1', 'purpose': r.purpose, 'nonce': r.nonce,
            'issuer': r.issuer, 'audience': r.audience, 'key': e.key,
            'version': e.version, 'content_sha': e.content_sha,
            'value_sha256': sha256(e.value.encode('utf-8')).hexdigest(),
            'request_id': r.request_id, 'expected_version': r.expected_version}


class SignedTransport(Protocol):
    def read_signed(self, key: str, nonce: str) -> SealedReceipt | None: ...
    def history_signed(self, key: str, revision: int, nonce: str) -> SealedReceipt | None: ...
    def write_signed(self, key: str, value: str, *, expected_version: int,
                     request_id: str, nonce: str) -> SealedReceipt: ...


class TrustedAdapter:
    """Accept only receipts bound to independently configured authority key.

    The caller MUST supply the pinned secret out-of-band, never from the receipt.
    No actual connected D1 provider returns this receipt contract yet.
    """
    def __init__(self, transport: SignedTransport, *, authority: str, audience: str,
                 verification_key: bytes, allow_isolated_writes: bool = False):
        if (not authority or not audience or not isinstance(verification_key, bytes)
                or len(verification_key) < 32):
            raise FailClosed('UNTRUSTED_VERIFIER_CONFIG')
        self._transport = transport
        self._authority = authority
        self._audience = audience
        self._key = verification_key
        self._allow_write = allow_isolated_writes

    @staticmethod
    def _nonce() -> str:
        return secrets.token_hex(16)

    def _verify(self, receipt: SealedReceipt | None, *, purpose: str, nonce: str,
                key: str, revision: int | None = None, request_id: str = '',
                expected_version: int | None = None) -> Evidence | None:
        if receipt is None:
            return None
        if not isinstance(receipt, SealedReceipt):
            raise FailClosed('UNSIGNED_OR_MALFORMED_RECEIPT')
        e = receipt.evidence
        if (not isinstance(e, Evidence) or not isinstance(e.key, str)
                or not isinstance(e.value, str) or not isinstance(e.version, int)
                or isinstance(e.version, bool) or e.version < 1
                or not isinstance(e.content_sha, str) or not SHA.fullmatch(e.content_sha)
                or utf16_units(e.value) > MAX_UNITS):
            raise FailClosed('BAD_RECEIPT_EVIDENCE')
        if (receipt.purpose != purpose or receipt.nonce != nonce
                or receipt.issuer != self._authority or receipt.audience != self._audience
                or e.key != key or (revision is not None and e.version != revision)
                or receipt.request_id != request_id
                or receipt.expected_version != expected_version):
            raise FailClosed('RECEIPT_CONTEXT_MISMATCH')
        expected_mac = hmac.new(self._key, canonical(receipt_payload(receipt)), sha256).hexdigest()
        if not isinstance(receipt.mac, str) or not hmac.compare_digest(expected_mac, receipt.mac):
            raise FailClosed('UNAUTHENTICATED_RECEIPT')
        return e

    def read(self, key: str) -> Evidence | None:
        nonce = self._nonce()
        return self._verify(self._transport.read_signed(key, nonce), purpose='read',
                            nonce=nonce, key=key)

    def history_at(self, key: str, revision: int) -> Evidence | None:
        nonce = self._nonce()
        return self._verify(self._transport.history_signed(key, revision, nonce),
                            purpose='history', nonce=nonce, key=key, revision=revision)

    def write(self, key: str, value: str, *, expected_version: int, request_id: str) -> Evidence:
        if not self._allow_write or key != REPORT_KEY:
            raise FailClosed('ISOLATED_WRITE_DENIED')
        if (not isinstance(value, str) or utf16_units(value) > MAX_UNITS
                or not isinstance(expected_version, int) or expected_version < 1
                or not isinstance(request_id, str) or not request_id.startswith('isolated-')):
            raise FailClosed('WRITE_CONTRACT_REJECTED')
        nonce = self._nonce()
        sealed = self._transport.write_signed(key, value, expected_version=expected_version,
                                             request_id=request_id, nonce=nonce)
        e = self._verify(sealed, purpose='write', nonce=nonce, key=key,
                         revision=expected_version + 1, request_id=request_id,
                         expected_version=expected_version)
        if e is None or e.value != value:
            raise FailClosed('SIGNED_WRITE_ACK_VALUE_MISMATCH')
        return e


@dataclass(frozen=True)
class RecoveryTicket:
    key: str
    source_version: int
    source_value: str
    source_content_sha: str
    candidate_value: str
    nonce: str
    ticket_mac: str


def ticket_payload(t: RecoveryTicket) -> dict:
    return {'type': 'ISOLATED_ROLLBACK_TICKET_V1', 'key': t.key,
            'source_version': t.source_version, 'source_value': t.source_value,
            'source_content_sha': t.source_content_sha,
            'candidate_sha256': sha256(t.candidate_value.encode('utf-8')).hexdigest(),
            'nonce': t.nonce}


class FileRecoveryJournal:
    """Fsync'd immutable file for synthetic recovery across process restarts."""
    def __init__(self, root: Path, *, signing_key: bytes):
        if not isinstance(signing_key, bytes) or len(signing_key) < 32:
            raise FailClosed('JOURNAL_SIGNING_KEY_REQUIRED')
        self.root = Path(root)
        if not self.root.is_dir() or self.root.is_symlink():
            raise FailClosed('JOURNAL_DIRECTORY_NOT_TRUSTED')
        mode = self.root.stat().st_mode
        if ((mode & 0o022) != 0 or self.root.stat().st_uid != os.geteuid()):
            raise FailClosed('JOURNAL_DIRECTORY_PERMISSIONS_UNSAFE')
        self._key = signing_key

    def seal(self, source: Evidence, candidate: str) -> RecoveryTicket:
        if (source.key != REPORT_KEY or not SHA.fullmatch(source.content_sha)
                or not isinstance(source.version, int) or source.version < 1
                or utf16_units(source.value) > MAX_UNITS or utf16_units(candidate) > MAX_UNITS):
            raise FailClosed('JOURNAL_SOURCE_INVALID')
        dummy = RecoveryTicket(source.key, source.version, source.value,
                               source.content_sha, candidate, secrets.token_hex(16), '')
        mac = hmac.new(self._key, canonical(ticket_payload(dummy)), sha256).hexdigest()
        return RecoveryTicket(dummy.key, dummy.source_version, dummy.source_value,
                              dummy.source_content_sha, dummy.candidate_value, dummy.nonce, mac)

    def verify(self, ticket: RecoveryTicket) -> None:
        if (not isinstance(ticket, RecoveryTicket) or ticket.key != REPORT_KEY
                or not SHA.fullmatch(ticket.source_content_sha)
                or not isinstance(ticket.source_version, int) or ticket.source_version < 1
                or not isinstance(ticket.source_value, str)
                or not isinstance(ticket.candidate_value, str)
                or utf16_units(ticket.source_value) > MAX_UNITS
                or utf16_units(ticket.candidate_value) > MAX_UNITS):
            raise FailClosed('BAD_ROLLBACK_TICKET')
        mac = hmac.new(self._key, canonical(ticket_payload(ticket)), sha256).hexdigest()
        if not isinstance(ticket.ticket_mac, str) or not hmac.compare_digest(ticket.ticket_mac, mac):
            raise FailClosed('ROLLBACK_TICKET_TAMPERED')

    def save(self, ticket: RecoveryTicket) -> Path:
        self.verify(ticket)
        name = f'r{ticket.source_version}-{ticket.nonce}.json'
        path = self.root / name
        data = canonical(asdict(ticket))
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            directory = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            # Keep the journal for independent inspection instead of deleting on failure.
            raise
        return path

    def load(self, path: Path) -> RecoveryTicket:
        path = Path(path)
        if path.parent.resolve() != self.root.resolve() or not re.fullmatch(r'r[0-9]+-[a-f0-9]{32}\.json', path.name) or path.is_symlink():
            raise FailClosed('JOURNAL_PATH_NOT_TRUSTED')
        try:
            # Open the exact file without following symlinks (avoid check/use swap).
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
            with os.fdopen(fd, 'rb') as stream:
                metadata = os.fstat(stream.fileno())
                if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
                        or (metadata.st_mode & 0o077) != 0):
                    raise FailClosed('JOURNAL_FILE_PERMISSIONS_UNSAFE')
                raw = stream.read(40001)
            if len(raw) > 40000:
                raise FailClosed('JOURNAL_OVERSIZED')
            d = json.loads(raw)
            if set(d) != set(RecoveryTicket.__dataclass_fields__):
                raise FailClosed('JOURNAL_FIELDS_MISMATCH')
            ticket = RecoveryTicket(**d)
            self.verify(ticket)
            if path.name != f'r{ticket.source_version}-{ticket.nonce}.json':
                raise FailClosed('JOURNAL_NAME_MISMATCH')
            return ticket
        except (OSError, ValueError, TypeError, UnicodeError) as exc:
            raise FailClosed('JOURNAL_MISSING_OR_CORRUPT') from exc


def prepare(store: TrustedAdapter, journal: FileRecoveryJournal) -> tuple[RecoveryTicket, Path]:
    pre = plan_migration(store)
    if pre['status'] != 'READY_OFFLINE':
        raise FailClosed('NOTHING_TO_PREPARE')
    original = store.read(REPORT_KEY)
    if (original is None or original.version != pre['source_revision']
            or original.value != pre['source_value']
            or original.content_sha != pre['source_content_sha']):
        raise Conflict('PREPARE_SOURCE_CHANGED')
    ticket = journal.seal(original, pre['candidate'])
    return ticket, journal.save(ticket)


def apply(store: TrustedAdapter, journal: FileRecoveryJournal, path: Path) -> dict:
    """Only a specifically supplied authenticated OFFLINE adapter may write.

    A write timeout is ambiguous. Keep the journal and call recover() separately.
    """
    ticket = journal.load(path)
    current = store.read(REPORT_KEY)
    if (current is None or current.version != ticket.source_version
            or current.value != ticket.source_value
            or current.content_sha != ticket.source_content_sha):
        raise Conflict('APPLY_STALE_SOURCE')
    ack = store.write(REPORT_KEY, ticket.candidate_value,
                      expected_version=ticket.source_version,
                      request_id='isolated-apply-'+ticket.nonce)
    if ack.value != ticket.candidate_value:
        raise FailClosed('APPLY_ACK_BAD_VALUE')
    final = store.read(REPORT_KEY)
    if (final is None or final.version != ticket.source_version + 1
            or final.value != ticket.candidate_value):
        raise FailClosed('APPLY_UNVERIFIED_KEEP_JOURNAL')
    return {'status': 'APPLIED_OFFLINE', 'revision': final.version, 'journal': path.name}


def recover(store: TrustedAdapter, journal: FileRecoveryJournal, path: Path) -> dict:
    """Compensating CAS only; never rewrites intervening unrelated producer revisions.

    Recovery also works if the signed write ACK was lost after commit.
    """
    ticket = journal.load(path)
    current = store.read(REPORT_KEY)
    if current is None:
        raise FailClosed('RECOVERY_SOURCE_MISSING')
    # A locally signed journal is not proof that its original bytes came from D1.
    # Before classifying any completed write/rollback, independently authenticate
    # the official original revision and compare full bytes plus opaque receipt.
    if current.version > ticket.source_version:
        historical = store.history_at(REPORT_KEY, ticket.source_version)
        if historical is None:
            raise FailClosed('RECOVERY_OFFICIAL_HISTORY_MISSING')
        if (historical.version != ticket.source_version or
                historical.value != ticket.source_value or
                historical.content_sha != ticket.source_content_sha):
            raise FailClosed('RECOVERY_SOURCE_HISTORY_MISMATCH')
    if (current.version == ticket.source_version
            and current.value == ticket.source_value
            and current.content_sha == ticket.source_content_sha):
        return {'status': 'NO_WRITE_OCCURRED'}
    if current.version == ticket.source_version + 2 and current.value == ticket.source_value:
        return {'status': 'ALREADY_RESTORED'}
    if (current.version != ticket.source_version + 1
            or current.value != ticket.candidate_value):
        raise Conflict('RECOVERY_FOREIGN_REVISION_OR_DATA')
    ack = store.write(REPORT_KEY, ticket.source_value,
                      expected_version=current.version,
                      request_id='isolated-rollback-'+ticket.nonce)
    final = store.read(REPORT_KEY)
    if (ack.value != ticket.source_value or final is None
            or final.version != ticket.source_version + 2
            or final.value != ticket.source_value):
        raise FailClosed('ROLLBACK_READBACK_UNVERIFIED_KEEP_JOURNAL')
    return {'status': 'RESTORED_EXACT_OFFLINE', 'revision': final.version,
            'source_sha256': sha256(ticket.source_value.encode('utf-8')).hexdigest()}

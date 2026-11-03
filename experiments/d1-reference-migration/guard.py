"""Isolated AI BOT D1 archive-first CAS rotation protocol.

NO external connections, no API calls, no scheduler mutations, no background runtime.
Adapters must provide read(key) and write(key,value,expected_version,request_id).
Never use on production without a separately authorized and authenticated adapter.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Protocol

WARNING_AT = 9300
MAX_VALUE_UNITS = 10000
LIVE_FIELDS_REQUIRED = ('schema', 'owner_task_id', 'source_runs', 'observed_snapshots', 'summary')
ARCHIVABLE_HISTORY = frozenset({
    'previous_report', 'confirmed_classification_fix',
    'developer_result_diagnostic', 'cross_system_receipt_check',
    'post_run_neon_operation', 'render_next_run_audit', 'traceability_audit',
})


class FailClosed(RuntimeError):
    pass


class Conflict(FailClosed):
    pass


@dataclass(frozen=True)
class Record:
    key: str
    value: str
    version: int


class Store(Protocol):
    def read(self, key: str) -> Record | None: ...
    def write(self, key: str, value: str, *, expected_version: int, request_id: str) -> Record: ...


def utf16_units(value: str) -> int:
    """Match JSON-schema JavaScript string length, including astral emoji."""
    return len(value.encode('utf-16-le')) // 2


def digest(text: str) -> str:
    return sha256(text.encode('utf-8')).hexdigest()


def _load(record: Record) -> dict:
    try:
        obj = json.loads(record.value)
    except (ValueError, TypeError) as exc:
        raise FailClosed('INVALID_JSON') from exc
    if not isinstance(obj, dict):
        raise FailClosed('INVALID_SCHEMA')
    return obj


def inspect(record: Record) -> dict:
    obj = _load(record)
    missing = [k for k in LIVE_FIELDS_REQUIRED if k not in obj]
    missing_archive_index = 'history_archive' not in obj and 'report_archives' not in obj
    return {
        'revision': record.version, 'units': utf16_units(record.value),
        'under_warning': utf16_units(record.value) < WARNING_AT,
        'missing_required': missing,
        'archive_refs_missing': missing_archive_index,
        'status': 'SCHEMA_DRIFT' if missing or missing_archive_index else 'VALID',
    }


def _ensure_original_untouched(store: Store, source: Record) -> None:
    current = store.read(source.key)
    if current is None or current.version != source.version or current.value != source.value:
        raise Conflict('SOURCE_CHANGED')


def _verify_archive(store: Store, archive_key: str, source: Record) -> Record:
    archived = store.read(archive_key)
    if archived is None:
        raise FailClosed('ARCHIVE_MISSING')
    if archived.value != source.value or digest(archived.value) != digest(source.value):
        raise FailClosed('ARCHIVE_MISMATCH')
    if archived.version != 1:
        raise FailClosed('ARCHIVE_WAS_MODIFIED')
    return archived


def _validate_run_refs(obj: dict) -> None:
    snapshots = obj.get('observed_snapshots')
    summary = obj.get('summary')
    source_runs = obj.get('source_runs')
    if not isinstance(snapshots, list) or not isinstance(summary, dict) or not isinstance(source_runs, str):
        raise FailClosed('INVALID_CURRENT_RUN_SCHEMA')
    if summary.get('total') != len(snapshots):
        raise FailClosed('SUMMARY_SNAPSHOT_COUNT_MISMATCH')
    references = source_runs.split('|')
    if len(references) != len(snapshots) or len(set(references)) != len(references):
        raise FailClosed('SOURCE_RUN_REFERENCE_COUNT_MISMATCH')
    for snap in snapshots:
        if not isinstance(snap, dict):
            raise FailClosed('INVALID_SNAPSHOT')
        name, run = snap.get('component'), snap.get('last_run_id') or snap.get('run_id')
        if not isinstance(name, str) or not isinstance(run, str) or f'{name}:{run}' not in references:
            raise FailClosed('SOURCE_RUN_ID_MISMATCH')


def _candidate(source: Record, archive: Record, archive_key: str) -> str:
    obj = _load(source)
    missing = [k for k in LIVE_FIELDS_REQUIRED if k not in obj]
    if missing:
        raise FailClosed('SCHEMA_DRIFT_REQUIRED_FIELDS_' + ','.join(missing))
    _validate_run_refs(obj)
    compact = {k: v for k, v in obj.items() if k not in ARCHIVABLE_HISTORY}
    previous_fields = obj.get('archived_fields', [])
    if not isinstance(previous_fields, list) or any(not isinstance(k, str) for k in previous_fields):
        raise FailClosed('INVALID_PRIOR_ARCHIVED_FIELDS')
    compact['archived_fields'] = sorted(set(previous_fields) | {k for k in obj if k in ARCHIVABLE_HISTORY})
    previous = obj.get('report_archives') or {}
    if not isinstance(previous, dict):
        raise FailClosed('BAD_OLD_ARCHIVE_INDEX')
    compact['report_archives'] = dict(previous)
    pointer = {
        'key': archive_key, 'revision': archive.version,
        'source_revision': source.version, 'source_sha256': digest(source.value),
        'source_units': utf16_units(source.value), 'exact_readback': True,
    }
    compact['report_archives']['auto-r' + str(source.version) + '-' + digest(source.value)[:12]] = pointer
    compact['history_archive'] = pointer
    text = json.dumps(compact, ensure_ascii=False, separators=(',', ':'))
    if utf16_units(text) > MAX_VALUE_UNITS:
        raise FailClosed('COMPACT_EXCEEDS_HARD_LIMIT')
    if utf16_units(text) >= WARNING_AT:
        raise FailClosed('COMPACT_NOT_BELOW_WARNING')
    for key, value in obj.items():
        if key in ARCHIVABLE_HISTORY:
            if key not in compact['archived_fields']:
                raise FailClosed('HISTORICAL_FIELD_LOST')
        elif key == 'report_archives':
            if any(compact['report_archives'].get(k) != v for k, v in value.items()):
                raise FailClosed('ARCHIVE_POINTER_LOST')
        elif key == 'archived_fields':
            if not set(value).issubset(set(compact['archived_fields'])):
                raise FailClosed('PRIOR_ARCHIVED_FIELD_LOST')
        elif key == 'history_archive':
            # Current history_archive is superseded by a verified new archive;
            # the original pointer still exists in the immutable original.
            if value not in compact['report_archives'].values():
                compact['prior_history_archive'] = value
                text = json.dumps(compact, ensure_ascii=False, separators=(',', ':'))
                if utf16_units(text) >= WARNING_AT:
                    raise FailClosed('COMPACT_PRIOR_POINTER_TOO_LARGE')
        elif compact.get(key) != value:
            raise FailClosed('LIVE_FIELD_LOST_' + key)
    return text


def rotate(store: Store, key: str, *, warning_at: int = WARNING_AT) -> dict:
    """Single run, no retries on conflict; correct if another writer wins."""
    source = store.read(key)
    if source is None:
        raise FailClosed('SOURCE_MISSING')
    if not isinstance(source.version, int) or source.version < 1:
        raise FailClosed('INVALID_SOURCE_REVISION')
    size = utf16_units(source.value)
    if size > MAX_VALUE_UNITS:
        raise FailClosed('SOURCE_ALREADY_TOO_LARGE')
    if size < warning_at:
        return {'status': 'NO_UPDATE', 'source_revision': source.version,
                'size_units': size, 'inspection': inspect(source)}
    if warning_at != WARNING_AT:
        raise FailClosed('POLICY_THRESHOLD_MISMATCH')
    # Fail on drift BEFORE any storage write, including archive write.
    inspection = inspect(source)
    missing = inspection['missing_required']
    if missing:
        raise FailClosed('SCHEMA_DRIFT_REQUIRED_FIELDS_' + ','.join(missing))
    # Do not invent vanished older archive links. A verified migration must
    # restore their provenance before this generic rotator can overwrite live.
    if inspection['archive_refs_missing']:
        raise FailClosed('SCHEMA_DRIFT_ARCHIVE_POINTERS_MISSING')
    _validate_run_refs(_load(source))
    archive_key = f'{key}.archive-auto-r{source.version}-{digest(source.value)[:12]}'
    if len(archive_key) > 120:
        raise FailClosed('ARCHIVE_KEY_TOO_LONG')
    existing = store.read(archive_key)
    if existing is None:
        _ensure_original_untouched(store, source)
        try:
            store.write(archive_key, source.value, expected_version=0,
                        request_id=f'archive-{source.version}-{digest(source.value)[:16]}')
        except Conflict:
            # A concurrent archive writer may have won; exact readback required.
            pass
    archived = _verify_archive(store, archive_key, source)
    compact = _candidate(source, archived, archive_key)
    _ensure_original_untouched(store, source)
    try:
        store.write(key, compact, expected_version=source.version,
                    request_id=f'live-compact-{source.version}-{digest(source.value)[:16]}')
    except Conflict as exc:
        raise Conflict('LIVE_CAS_CONFLICT_NO_RETRY') from exc
    # A readback failure is a hard stop; never blind-retry a successful write.
    current = store.read(key)
    if current is None or current.value != compact or current.version != source.version + 1:
        raise FailClosed('LIVE_READBACK_MISMATCH_STOP')
    _verify_archive(store, archive_key, source)
    return {'status': 'PASS_ISOLATED', 'source_revision': source.version,
            'live_revision': current.version, 'archive_key': archive_key,
            'original_units': size, 'live_units': utf16_units(compact),
            'archive_sha256': digest(source.value),
            'retained_run_ids': _load(source)['source_runs'] == _load(current)['source_runs'],
            'retained_summary': _load(source)['summary'] == _load(current)['summary'],
            'retained_snapshots': _load(source)['observed_snapshots'] == _load(current)['observed_snapshots']}

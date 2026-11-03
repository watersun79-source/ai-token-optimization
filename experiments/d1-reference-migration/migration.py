"""AI BOT D1 verified historical-reference migration (ISOLATED, offline-only).

No network, credentials, scheduler calls, or production D1 adapter is included.
The host MUST independently authenticate official version-history reads and D1
archive reads before passing them through the OfflineStore contract.
Metadata content_sha is an *opaque server receipt*, not SHA256(value).
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Protocol

from guard import Conflict, FailClosed, _validate_run_refs, utf16_units

REPORT_KEY = 'project.ai-bot.unified-report'
REPORT_SCHEMA = 'AI_BOT_UNIFIED_REPORT_V1'
TRACE_SCHEMA = 'AI_BOT_RENDER_TRACE_SOURCE_AUDIT_V1'
LEGACY_HISTORY = (27, 28, 29, 30, 31)
REF_HISTORY = (32, 33)
ARCHIVE_RECENT = 36
EXPECTED_COMPONENTS = frozenset({'coordinator', 'render', 'dev', 'site', 'neon'})
HARD_LIMIT = 10000
WARNING_AT = 9300
_SHA_RE = re.compile(r'^[0-9a-f]{64}$')


@dataclass(frozen=True)
class Evidence:
    key: str
    value: str
    version: int
    content_sha: str  # Opaque source-server record hash, NOT local SHA256(content).


class OfflineStore(Protocol):
    def read(self, key: str) -> Evidence | None: ...
    def history_at(self, key: str, revision: int) -> Evidence | None: ...
    def write(self, key: str, value: str, *, expected_version: int, request_id: str) -> Evidence: ...


def _validated_record(record: Evidence | None, expected_key: str, expected_rev: int | None = None) -> Evidence:
    if record is None:
        raise FailClosed('EVIDENCE_MISSING_' + expected_key)
    if record.key != expected_key or (expected_rev is not None and record.version != expected_rev):
        raise FailClosed('EVIDENCE_IDENTITY_MISMATCH')
    if not isinstance(record.value, str) or not isinstance(record.content_sha, str) or not _SHA_RE.fullmatch(record.content_sha):
        raise FailClosed('EVIDENCE_METADATA_INVALID')
    return record


def _json(record: Evidence) -> dict:
    try:
        data = json.loads(record.value)
    except (ValueError, TypeError) as exc:
        raise FailClosed('INVALID_EVIDENCE_JSON') from exc
    if not isinstance(data, dict):
        raise FailClosed('INVALID_EVIDENCE_SCHEMA')
    return data


def _checked_history(store: OfflineStore, report_key: str, revision: int, expected_owner: str) -> tuple[Evidence, dict]:
    record = _validated_record(store.history_at(report_key, revision), report_key, revision)
    obj = _json(record)
    if obj.get('schema') != REPORT_SCHEMA or obj.get('owner_task_id') != expected_owner:
        raise FailClosed('HISTORY_SCHEMA_OR_OWNER_MISMATCH')
    return record, obj


def _checked_archive(store: OfflineStore, report_key: str, revision: int, key: str,
                     history: Evidence) -> Evidence:
    if (not isinstance(key, str) or not key.startswith(f'{report_key}.archive-r{revision}-')
            or len(key) > 120):
        raise FailClosed('ARCHIVE_KEY_NOT_IN_TRUSTED_NAMESPACE')
    record = _validated_record(store.read(key), key, 1)
    if record.value != history.value:
        raise FailClosed('ARCHIVE_SOURCE_NOT_EXACT')
    # Compare complete bytes, do not compare opaque backend hashes to local SHA256.
    if sha256(record.value.encode('utf-8')).digest() != sha256(history.value.encode('utf-8')).digest():
        raise FailClosed('ARCHIVE_VALUE_DIGEST_MISMATCH')
    return record


def _validate_current(live: Evidence, obj: dict) -> None:
    if obj.get('schema') != REPORT_SCHEMA or not isinstance(obj.get('owner_task_id'), str):
        raise FailClosed('LIVE_SCHEMA_OR_OWNER_INVALID')
    if not isinstance(live.version, int) or live.version <= 33:
        raise FailClosed('NOT_A_POST_HISTORY_LIVE_REVISION')
    if utf16_units(live.value) > HARD_LIMIT:
        raise FailClosed('LIVE_ABOVE_HARD_LIMIT')
    _validate_run_refs(obj)
    if {row['component'] for row in obj['observed_snapshots']} != EXPECTED_COMPONENTS:
        raise FailClosed('LATEST_COMPONENT_SET_INVALID')
    if obj['summary'].get('enabled') != len(obj['observed_snapshots']):
        raise FailClosed('LATEST_ENABLED_COUNT_INVALID')
    if any(not isinstance(row.get('enabled'), bool) or not row['enabled'] for row in obj['observed_snapshots']):
        raise FailClosed('LATEST_ENABLED_STATUS_INVALID')


def _extract_ref(p: str | dict, revision: int) -> str:
    if isinstance(p, str):
        return p
    if isinstance(p, dict) and isinstance(p.get('key'), str):
        if p.get('source_revision') != revision or p.get('archive_revision') != 1:
            raise FailClosed('ARCHIVE_REFERENCE_REVISION_WRONG')
        return p['key']
    raise FailClosed('ARCHIVE_REFERENCE_INVALID')


def _historical_trace_ref(store: OfflineStore, obj30: dict, obj31: dict, obj32: dict) -> str:
    ref = obj32.get('render_trace_evidence')
    if not isinstance(ref, str) or not ref.endswith('@1'):
        raise FailClosed('TRACE_VERSION_OR_REFERENCE_MISSING')
    if obj30.get('render_trace_evidence') != ref or obj31.get('render_trace_evidence') != ref:
        raise FailClosed('TRACE_HISTORIC_PROVENANCE_MISMATCH')
    target = ref[:-2]
    if not target.startswith('project.ai-bot.render-trace-path-') or len(target) > 120:
        raise FailClosed('TRACE_NAMESPACE_INVALID')
    rec = _validated_record(store.read(target), target, 1)
    trace = _json(rec)
    run31 = next((x.get('last_run_id') or x.get('run_id') for x in obj31.get('observed_snapshots', [])
                  if x.get('component') == 'render'), None)
    run30 = next((x.get('last_run_id') or x.get('run_id') for x in obj30.get('observed_snapshots', [])
                  if x.get('component') == 'render'), None)
    if trace.get('schema') != TRACE_SCHEMA or trace.get('target_native_run_id') != run30 or run30 != run31:
        raise FailClosed('TRACE_PAYLOAD_WRONG_HISTORICAL_RUN')
    return ref


def plan_migration(store: OfflineStore, report_key: str = REPORT_KEY) -> dict:
    """Pure read-only preflight: verified, historical-only references; no writes."""
    live = _validated_record(store.read(report_key), report_key)
    obj = _json(live)
    _validate_current(live, obj)
    owner = obj['owner_task_id']

    history = {}
    parsed = {}
    for rev in (*LEGACY_HISTORY, *REF_HISTORY, ARCHIVE_RECENT):
        history[rev], parsed[rev] = _checked_history(store, report_key, rev, owner)

    reference32 = parsed[32]
    reference33 = parsed[33]
    for name in ('report_archives', 'history_archive', 'render_trace_evidence'):
        if name not in reference32 or reference32[name] != reference33.get(name):
            raise FailClosed('OFFICIAL_REFERENCES_DISAGREE_' + name)
    previous = reference32['report_archives']
    if not isinstance(previous, dict):
        raise FailClosed('LEGACY_REFERENCE_NOT_AN_INDEX')
    if (previous.get('source_rev') != 29 or
            previous.get('source_sha') != history[29].content_sha or
            previous.get('archived_sha') != _checked_archive(
                store, report_key, 29, _extract_ref(previous.get('r29'), 29),
                history[29]).content_sha or previous.get('verbatim_readback') is not True):
        raise FailClosed('LEGACY_R29_INDEX_RECEIPT_MISMATCH')

    canonical = {}
    for revision in LEGACY_HISTORY:
        name = f'r{revision}'
        key = _extract_ref(previous.get(name), revision)
        archive = _checked_archive(store, report_key, revision, key, history[revision])
        if isinstance(previous[name], dict):
            reference = previous[name]
            if (reference.get('source_content_sha') != history[revision].content_sha or
                reference.get('archive_content_sha') != archive.content_sha or
                reference.get('original_chars') != len(history[revision].value)):
                raise FailClosed('LEGACY_ARCHIVE_RECEIPT_MISMATCH')
        canonical[name] = key  # only verified names; remove unverified version/index metadata

    r31_ptr = reference32['history_archive']
    if (not isinstance(r31_ptr, dict) or r31_ptr.get('key') != canonical['r31'] or
            r31_ptr.get('archive_revision') != 1 or
            r31_ptr.get('source_revision') != 31 or
            r31_ptr.get('source_content_sha') != history[31].content_sha):
        raise FailClosed('R31_HISTORY_POINTER_INVALID')

    trace_ref = _historical_trace_ref(store, parsed[30], parsed[31], reference32)

    # r37 contained this independently recorded r36 archive. Do not label r31
    # "current backup" since it predates r37's newer native run IDs.
    recent = obj.get('archive_before_provider_audit')
    if not isinstance(recent, dict) or recent.get('source_revision') != ARCHIVE_RECENT:
        raise FailClosed('RECENT_ARCHIVE_OR_PROVENANCE_MISSING')
    recent_key = recent.get('key')
    recent_archive = _checked_archive(store, report_key, ARCHIVE_RECENT, recent_key, history[ARCHIVE_RECENT])
    if (recent.get('source_sha') != history[ARCHIVE_RECENT].content_sha or
            recent.get('archive_sha') != recent_archive.content_sha or recent.get('verbatim_readback') is not True):
        raise FailClosed('RECENT_ARCHIVE_RECEIPT_MISMATCH')
    canonical[f'r{ARCHIVE_RECENT}'] = recent_key

    # A nonempty conflicting existing pointer is never overwritten automatically.
    existing_archives = obj.get('report_archives')
    if existing_archives is not None and existing_archives != canonical:
        raise FailClosed('EXISTING_ARCHIVE_INDEX_CONFLICT')
    previous_history = obj.get('history_archive')
    recent_pointer = {
        'key': recent_key, 'source_revision': ARCHIVE_RECENT,
        'archive_revision': recent_archive.version,
        'source_content_sha': history[ARCHIVE_RECENT].content_sha,
        'archive_content_sha': recent_archive.content_sha,
        'original_chars': len(recent_archive.value),
        'verbatim': True,
    }
    if previous_history is not None and previous_history != recent_pointer:
        raise FailClosed('EXISTING_HISTORY_POINTER_CONFLICT')
    if obj.get('render_trace_evidence') is not None and obj['render_trace_evidence'] != trace_ref:
        raise FailClosed('EXISTING_TRACE_POINTER_CONFLICT')

    patch = {
        'report_archives': canonical,
        'history_archive': recent_pointer,
        'render_trace_evidence': trace_ref,
        'archive_reference_scope': 'HISTORICAL_VERIFIED_ONLY_NOT_CURRENT_NATIVE_RENDER_CAUSALITY',
    }
    if all(obj.get(k) == v for k, v in patch.items()):
        return {'status': 'NO_UPDATE', 'source_revision': live.version, 'candidate': live.value,
                'verified_archive_revisions': list(LEGACY_HISTORY) + [ARCHIVE_RECENT],
                'current_units': utf16_units(live.value)}

    candidate = dict(obj)  # never recompute or rewrite current run IDs or results
    candidate.update(patch)
    raw = json.dumps(candidate, ensure_ascii=False, separators=(',', ':'))
    if utf16_units(raw) > HARD_LIMIT:
        raise FailClosed('MIGRATION_EXCEEDS_HARD_LIMIT')
    if utf16_units(raw) >= WARNING_AT:
        raise FailClosed('MIGRATION_NOT_BELOW_WARNING')
    for k, v in obj.items():
        if candidate.get(k) != v:
            raise FailClosed('CURRENT_VALUE_ALTERED_' + k)
    if (candidate['source_runs'] != obj['source_runs'] or
        candidate['summary'] != obj['summary'] or
        candidate['observed_snapshots'] != obj['observed_snapshots']):
        raise FailClosed('CURRENT_EVIDENCE_MUTATED')
    return {
        'status': 'READY_OFFLINE', 'source_revision': live.version,
        'source_value': live.value, 'source_content_sha': live.content_sha,
        'candidate': raw,
        'current_units': utf16_units(live.value), 'candidate_units': utf16_units(raw),
        'verified_archive_revisions': list(LEGACY_HISTORY) + [ARCHIVE_RECENT],
        'trace_scope': patch['archive_reference_scope'],
    }


def migrate(store: OfflineStore, report_key: str = REPORT_KEY) -> dict:
    """CAS writes *only to an injected test store*, NEVER to the real MCP D1."""
    preflight = plan_migration(store, report_key)
    if preflight['status'] == 'NO_UPDATE':
        return preflight
    original = store.read(report_key)
    if (original is None or original.version != preflight['source_revision'] or
        original.value != preflight['source_value'] or
        original.content_sha != preflight['source_content_sha']):
        raise Conflict('SOURCE_CHANGED_BEFORE_CAS')
    request_id = f'isolated-migrate-r{original.version}-{sha256(original.value.encode()).hexdigest()[:16]}'
    try:
        acknowledgment = store.write(report_key, preflight['candidate'],
                                     expected_version=original.version, request_id=request_id)
    except Conflict as exc:
        raise Conflict('MIGRATION_CAS_CONFLICT_NO_RETRY') from exc
    if (not isinstance(acknowledgment, Evidence) or
            acknowledgment.key != report_key or
            acknowledgment.version != original.version + 1 or
            acknowledgment.value != preflight['candidate']):
        raise FailClosed('MIGRATION_CAS_ACK_MISMATCH_STOP')
    final = _validated_record(store.read(report_key), report_key, original.version + 1)
    if final.value != preflight['candidate']:
        raise FailClosed('MIGRATION_READBACK_MISMATCH_STOP')
    return {
        'status': 'PASS_ISOLATED', 'source_revision': original.version,
        'result_revision': final.version, 'current_units': preflight['current_units'],
        'result_units': preflight['candidate_units'],
        'verified_archive_revisions': preflight['verified_archive_revisions'],
    }

"""Read-only evidence reconciler for a protected ChatGPT scheduled task.

Designed using OpenTelemetry tool spans and GitHub Actions' documented per-run
identity separation. It NEVER fabricates a native ChatGPT task run ID and can
only check the format and consistency of supplied execution evidence.

No network, credentials, provider APIs, scheduling, or writes to external apps.
Python 3.10+, standard library only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

AUTOMATION_ID = '6acb017062a08191a4136238b78b313a'
# R16 source-of-truth: current GitHub handoff first, then authorized Slack
# collaboration. Older R13 reports are NOT mandatory for an R16 run.
REQUIRED = {
    'current_handoff': ('mcp__GitHub__fetch_file', 'docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md', 'sha'),
    'slack_thread': ('mcp__Slack__slack_read_thread', 'C0C9649RQAZ/1792416391.631669', 'slack_ts'),
}
# Ancillary R16 references may be fetched when needed but are optional.
OPTIONAL = {
    'memory_index': ('mcp__GitHub__fetch_file', 'docs/ai/PROJECT_MEMORY_INDEX.md', 'sha'),
    'execution_standard': ('mcp__GitHub__fetch_file', 'docs/ai/AI_EXECUTION_STANDARD_2026-10-21.md', 'sha'),
    'plugin_v050': ('mcp__GitHub__fetch_file', 'docs/ai/AI_CONNECTED_APPS_PLUGIN_V050_2026-10-22.md', 'sha'),
}

SHA = re.compile(r'^[a-f0-9]{40}$')
SLACK_TS = re.compile(r'^\d{10}\.\d{6}$')


def parsed_time(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo is not None and dt.utcoffset() is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def check(payload: dict) -> dict:
    """Reject unverifiable claims by default, including all self-reported run IDs.

    Fields:
      schedule: original task status/last_run_time from automations.peek
      native_run: **original** ChatGPT scheduler-per-run raw record (if supplied)
      tool_calls: **original** scheduler tool-call audit records (if supplied)
      external: independently observed external reads / marker rows (optional)

    A format pass NEVER authenticates that JSON really came from a trusted provider.
    """
    outcome = {'status': '미검증', 'native_run_id': None, 'verified_targets': [],
               'missing': list(REQUIRED), 'authenticity': '실행 증거 입력의 원본 진위 별도 확인 필요'}
    if not isinstance(payload, dict):
        outcome['reason'] = '입력 형식 오류'
        return outcome
    target = parsed_time(payload.get('target_slot'))
    task = payload.get('schedule') or {}
    if not isinstance(task, dict) or task.get('id') != AUTOMATION_ID or task.get('is_enabled') is not True:
        outcome['reason'] = '보호 예약 ID·활성 상태 불일치'
        return outcome
    if not target or target.minute != 0 or target.second != 0:
        outcome['reason'] = '정각 슬롯/시간대가 확인되지 않음'
        return outcome
    last_run = parsed_time(task.get('last_run_time'))
    # last_run_time is latest-task metadata, not an individual historical run.
    # A later hourly run must never invalidate official evidence for an older slot.
    metadata_matches_slot = bool(last_run and target <= last_run < target + timedelta(hours=1))
    outcome['trigger'] = ('예약 실행 시각 메타 확인 (완료/성공 증거 아님)'
                          if metadata_matches_slot else
                          '마지막 실행 메타데이터만으로 이 회차 실행 여부 확인 불가')
    native = payload.get('native_run') or {}
    if not isinstance(native, dict) or native.get('origin') != 'official_task_run_details':
        outcome['reason'] = ('공식 개별 회차 원본 로그 미제공' if metadata_matches_slot else
                             '공식 개별 회차 원본 로그 미제공; 최신 예약 시각은 과거 회차 원본 증거가 아님')
        return outcome
    run_id = native.get('run_id')
    if not isinstance(run_id, str) or not run_id.strip():
        outcome['reason'] = '공식 개별 회차 ID 미제공'
        return outcome
    if native.get('automation_id') != AUTOMATION_ID or parsed_time(native.get('scheduled_for')) != target:
        outcome['reason'] = '공식 개별 회차의 예약 ID 또는 슬롯 불일치'
        return outcome
    start, end = parsed_time(native.get('started_at')), parsed_time(native.get('completed_at'))
    if not start or not end or not target <= start <= end <= target + timedelta(hours=1):
        outcome['reason'] = '공식 실행 시작·종료 시각 불일치'
        return outcome
    if native.get('status') not in ('completed', 'no_update'):
        outcome['reason'] = '공식 개별 회차 종료 성공 여부 미확인'
        return outcome
    outcome['native_run_id'] = run_id
    tool_calls = payload.get('tool_calls') or []
    if not isinstance(tool_calls, list):
        outcome['reason'] = '원본 호출 형식 오류'
        return outcome
    accepted = {}
    invocation_ids = set()
    for c in tool_calls:
        if not isinstance(c, dict):
            continue
        t = c.get('target')
        if t not in REQUIRED or t in accepted:
            continue
        tool, locator, version_type = REQUIRED[t]
        invocation = c.get('invocation_id')
        observed = parsed_time(c.get('observed_at'))
        version = c.get('version')
        is_valid_version = isinstance(version, str) and bool((SHA if version_type == 'sha' else SLACK_TS).fullmatch(version))
        if (c.get('origin') != 'official_task_tool_call' or c.get('run_id') != run_id
                or c.get('success') is not True or c.get('tool') != tool
                or c.get('locator') != locator or not isinstance(invocation, str) or not invocation
                or invocation in invocation_ids or observed is None
                or not (start <= observed <= end) or not is_valid_version):
            continue
        accepted[t] = c
        invocation_ids.add(invocation)
    outcome['verified_targets'] = list(accepted)
    outcome['missing'] = [t for t in REQUIRED if t not in accepted]
    if outcome['missing']:
        outcome['reason'] = '동일 회차 공식 도구 호출 증거 부족'
        return outcome
    outcome['status'] = '형식 통과 · 진위 미검증'
    outcome['reason'] = ('R16 필수 인계·Slack의 동일 회차 형식 일치. '
                         '실제 업무 목표 수행·원본 진위·부가 문서 조회는 별도 확인 필요')
    return outcome


def main():
    parser = argparse.ArgumentParser(description='Pure local read-only scheduled AI evidence consistency checker')
    parser.add_argument('--input', required=True, type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding='utf-8'))
        output = check(payload)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output['status'].startswith('형식 통과') else 2


if __name__ == '__main__':
    raise SystemExit(main())

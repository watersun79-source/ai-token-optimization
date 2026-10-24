#!/usr/bin/env python3
"""R16 v8.1 offline provenance gate. No network, secrets or schedule writes.

This validates a local result's shape; it never authenticates source snapshots,
ChatGPT native scheduled runs, or GitHub/Slack tool-call ledgers.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re

PREFIXES = 'SGPLAOCMTE'
EXPECTED_IDS = {f'{p}{n:02}' for p in PREFIXES for n in range(1, 11)}
REPLACEMENTS = {f'E{n:02}' for n in range(1, 11)} | {'L06','L07','L08','L09','L10','A07','A08','A09'}
SHA = re.compile(r'[0-9a-f]{64}\Z')

class EvidenceError(ValueError):
    pass

def _require(ok: bool, msg: str) -> None:
    if not ok:
        raise EvidenceError(msg)

def inspect_local_report(data: dict) -> dict:
    """Verify exact offline-v8.1 report schema, not the truth of snapshot inputs."""
    _require(isinstance(data, dict), 'report must be an object')
    _require(data.get('kind') == 'LOCAL_RULE_CHECK_REPORT_NOT_NATIVE_SCHEDULE_ATTESTATION', 'wrong report kind')
    _require(data.get('goal') == 'all', 'must inspect all roles')
    _require(type(data.get('catalog_total')) is int and data['catalog_total'] == 100, 'catalog count mismatch')
    _require(type(data.get('executed_rules')) is int and data['executed_rules'] == 100, 'executed count mismatch')
    _require(type(data.get('executed_independent_llms')) is int and data['executed_independent_llms'] == 0, 'unsupported independent model claim')
    _require(data.get('official_same_run_github_slack_verified') is False, 'native app success must not be self-attested')
    _require(data.get('deployed_to_chatgpt_scheduler') is False, 'native scheduler installation not verified')
    _require(data.get('scheduled_task_changed') is False, 'scheduler change is forbidden')
    _require(data.get('official_same_run_raw_ledger') == 'NOT_PROVIDED', 'official raw ledger is not available')
    results = data.get('results')
    _require(isinstance(results, list) and len(results) == 100, 'expected 100 result objects')
    _require(all(isinstance(row, dict) for row in results), 'invalid result row')
    ids = [row.get('id') for row in results]
    _require(set(ids) == EXPECTED_IDS and len(ids) == len(set(ids)), 'missing/extra/duplicate BOT IDs')
    counts = Counter(row.get('status') for row in results)
    _require(dict(counts) == {'PASS': 100}, 'not every local rule passed')
    _require(data.get('rule_statuses') == {'PASS': 100}, 'reported counts do not match rows')
    for row in results:
        if row['id'] in REPLACEMENTS:
            _require(row.get('scope') == 'LOCAL_FIXTURE_ONLY', 'replacement BOT source must be labelled synthetic')
            _require(row.get('source') == 'SYNTHETIC_LOCAL_FIXTURE_NOT_PROVIDER_EVIDENCE', 'synthetic source relabelled')
    hashes = data.get('input_sha256')
    _require(isinstance(hashes, dict) and len(hashes) >= 5, 'missing local input hashes')
    for path in ('runner.py','replacement_bots.py','catalog.json','evidence.json','fixture_SYNTHETIC.json'):
        _require(isinstance(hashes.get(path), str) and SHA.fullmatch(hashes[path]) is not None, 'missing/invalid hash '+path)
    return {
        'offline_v81_rules': 'PASS_LOCAL_STRUCTURAL_ONLY',
        'rule_count': 100,
        'synthetic_replacements': 18,
        'executed_independent_llms': 0,
        'chatgpt_native_run': 'UNVERIFIED',
        'same_run_github_slack_calls': 'UNVERIFIED',
        'deployed_to_chatgpt_scheduler': False,
        'production_change': False,
    }

def inspect_schedule_run(run: dict, expected_sha: str) -> dict:
    """Validate supplied metadata; authenticated provider read-back is still required."""
    _require(isinstance(run, dict), 'run metadata must be object')
    _require(isinstance(expected_sha, str) and re.fullmatch(r'[0-9a-f]{40}', expected_sha) is not None, 'invalid expected HEAD')
    _require(type(run.get('id')) is int and run['id'] > 0, 'invalid GitHub run id')
    _require(run.get('event') == 'schedule', 'push/manual CI is not a scheduled run')
    _require(run.get('head_sha') == expected_sha, 'run not linked to expected HEAD')
    _require(run.get('status') == 'completed' and run.get('conclusion') == 'success', 'scheduled job did not succeed')
    _require(run.get('path') == '.github/workflows/ai-r16-hourly.yml', 'incorrect workflow provenance')
    return {
        'github_scheduled_workflow': 'METADATA_MATCHES_EXPECTATIONS',
        'github_run_id': run['id'],
        'chatgpt_native_run': 'UNVERIFIED',
        'note': 'Only authenticated GitHub read-back plus job logs establishes actual GitHub execution, not native ChatGPT app calls',
    }

def main() -> int:
    p=argparse.ArgumentParser(description='Offline v8.1 provenance check; no external API')
    p.add_argument('report',type=Path)
    args=p.parse_args()
    try:
        result=inspect_local_report(json.loads(args.report.read_text(encoding='utf8')))
    except (EvidenceError,OSError,ValueError,TypeError) as exc:
        print(json.dumps({'status':'FAIL','reason':str(exc)},ensure_ascii=False))
        return 1
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

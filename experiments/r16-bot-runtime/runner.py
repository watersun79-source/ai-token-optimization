#!/usr/bin/env python3
"""Rule-based offline specialist BOT dispatcher. No network, subprocess, model or remote calls.

Intentionally fail-closed: unknown platform evidence => UNVERIFIED, not PASS.
Each BOT ID is a unique task/cross-check; there are NOT 100 generative LLMs.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
from typing import Any
ROOT = Path(__file__).resolve().parent
_MISSING = object()
# Pin official native-evidence roles by identity, not mutable catalog metadata.
# The offline runner cannot authenticate a real ChatGPT scheduled execution.
NATIVE_ROLE_IDS = frozenset(
    [f'E{i:02d}' for i in range(1, 11)]
    + [f'L{i:02d}' for i in range(6, 11)]
    + [f'A{i:02d}' for i in range(7, 10)]
)
# Reviewed public isolated-branch catalog, not the unavailable private ZIP.
# Any catalog modification must be separately reviewed and this pin updated.
ISOLATED_CATALOG_SHA256 = "afcef031e77fc517fa7964386d7aeeffadcd9fad09605e2a6d68c278098b2abe"


def require_trusted_catalog(catalog):
    """Reject catalog rule rewrites even when all 100 IDs remain unchanged."""
    try:
        source = (ROOT / 'catalog.json').read_bytes()
        if hashlib.sha256(source).hexdigest() != ISOLATED_CATALOG_SHA256:
            raise ValueError('unreviewed catalog source digest')
        baseline = json.loads(source)
        if (not isinstance(catalog, list) or len(catalog) != 100
                or not all(isinstance(x, dict) and isinstance(x.get('id'), str)
                           for x in catalog)):
            raise ValueError('invalid catalog structure')
        if (len({x['id'] for x in catalog}) != 100
                or sorted(catalog, key=lambda x: x['id'])
                != sorted(baseline, key=lambda x: x['id'])):
            raise ValueError('catalog rules differ from pinned baseline')
    except (OSError, json.JSONDecodeError, TypeError, KeyError) as exc:
        raise ValueError('catalog integrity cannot be verified') from None


RECEIPT_INPUT_FILES = (
    'runner.py', 'measure_runtime.py', 'catalog.json', 'test_runtime.py',
    'UtcStrictOracle.java', 'utc_strict_oracle.js', 'utc_strict_oracle_cases.tsv',
)


def runtime_input_hashes():
    """Bind executable/test inputs; generated count outputs are compared separately."""
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in RECEIPT_INPUT_FILES}
    evidence = json.loads((ROOT / 'evidence.json').read_text(encoding='utf8'))
    if not isinstance(evidence, dict):
        raise ValueError('evidence must be an object')
    # These two fields are measurement outputs, not test configuration.
    inputs = {k: v for k, v in evidence.items() if k not in ('polyglot', 'notice')}
    hashes['evidence_inputs'] = hashlib.sha256(json.dumps(
        inputs, sort_keys=True, ensure_ascii=False, separators=(',', ':')
    ).encode('utf8')).hexdigest()
    return hashes

def strict_hourly_rrule_part(value: Any, expected: Any) -> bool:
    """Reject ambiguous or restricted schedule RRULEs (RFC 5545)."""
    if type(value) is not str or type(expected) is not str:
        return False
    raw = value.removeprefix('RRULE:')
    parts = raw.split(';')
    if any(re.fullmatch(r'(?:FREQ|BYMINUTE|BYSECOND|INTERVAL)=[A-Z0-9]+', part) is None
           for part in parts):
        return False
    entries = [part.split('=', 1) for part in parts]
    values = dict(entries)
    if len(values) != len(entries):
        return False
    return (values.get('FREQ') == 'HOURLY'
            and values.get('BYMINUTE') == '0'
            and values.get('BYSECOND') == '0'
            and values.get('INTERVAL', '1') == '1'
            and expected in parts)


def read_path(data:dict,path:str):
    node = data
    for p in path.split('.'):
        if not isinstance(node,dict) or p not in node: return _MISSING
        node=node[p]
    return node

def read_runtime_receipt():
    """Offline code-hash/freshness attestation (NOT a trusted provider signature)."""
    try:
        receipt=json.loads((ROOT/'runtime_proof.json').read_text(encoding='utf8'))
        if not isinstance(receipt,dict):
            return None,'invalid local test receipt structure'
        if receipt.get('format')!='LOCAL_TEST_RECEIPT_V6':
            return None,'local test receipt format missing'
        stamp=receipt.get('measured_at_utc')
        if not isinstance(stamp, str):
            return None,'local test receipt timestamp missing'
        measured=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        now=datetime.now(timezone.utc)
        if measured.tzinfo is None or not (timedelta(0)<=now-measured<=timedelta(hours=24)):
            return None,'local test receipt expired or future-dated'
        source_files={
            'python':'test_runtime.py',
            'java':'UtcStrictOracle.java',
            'js':'utc_strict_oracle.js',
        }
        if receipt.get('input_sha256') != runtime_input_hashes():
            return None,'local runtime/test inputs changed since tested'
        if not isinstance(receipt.get('source_sha256'), dict):
            return None,'local oracle hashes malformed'
        for key,filename in source_files.items():
            file=ROOT/filename
            if not file.is_file():return None,'local oracle source missing'
            actual=hashlib.sha256(file.read_bytes()).hexdigest()
            if receipt.get('source_sha256',{}).get(key)!=actual:
                return None,'local oracle source changed since tested'
        counts=receipt.get('counts',{})
        if not isinstance(counts, dict):
            return None,'local regression counts malformed'
        if not all(isinstance(counts.get(lang),dict) and
                   type(counts[lang].get('passed')) is int and
                   type(counts[lang].get('total')) is int and
                   0<counts[lang]['passed']==counts[lang]['total']
                   for lang in source_files):
            return None,'one or more local regressions failed or missing'
        total=sum(counts[k]['passed'] for k in source_files)
        if receipt.get('total_passed')!=total:return None,'receipt aggregate mismatched'
        return receipt,'local measured test evidence consistent (not platform auth)'
    except (OSError,ValueError,TypeError,KeyError,OverflowError):
        return None,'local test receipt inaccessible or malformed'

def validate(bot:dict, evidence:dict)->dict:
    v=read_path(evidence,bot['field']); op=bot['operator']; expect=bot['expected']
    result={'id':bot['id'],'category':bot['category'],'name':bot['name'],
            'source':bot['evidence_source'],'status':'UNVERIFIED','detail':'required source evidence unavailable'}
    # Offline JSON has no verified scheduler provenance. Do not allow caller-
    # supplied native.* fields to masquerade as platform-authenticated records.
    # A trusted, platform-backed adapter needs its own attestation verification
    # before any of these gates can be considered passed.
    if (bot['id'] in NATIVE_ROLE_IDS or bot['field'].startswith('native.')
            or bot['evidence_source'] == 'ChatGPT.native_per_run_raw_ledger'):
        result['detail'] = 'original scheduler tool-call ledger not authenticated by this offline runner'
        return result
    if v is _MISSING or v is None:
        return result
    valid=False
    try:
        if op=='eq': valid=type(v) is type(expect) and v==expect
        elif op=='eq_field':
            other=read_path(evidence,expect)
            if other is _MISSING or other is None: return result
            valid=type(v) is type(other) and v==other
        elif op=='contains': valid=isinstance(v,str) and expect in v
        elif op=='rrule_part': valid=strict_hourly_rrule_part(v, expect)
        elif op=='starts': valid=isinstance(v,str) and v.startswith(expect)
        elif op=='git_sha': valid=isinstance(v,str) and re.fullmatch('[0-9a-f]{40}',v) is not None
        elif op=='slack_ts': valid=isinstance(v,str) and re.fullmatch(r'\d{10}\.\d{6}',v) is not None
        elif op=='positive_id': valid=type(v) is int and v > 0
        elif op=='nonnegative_count': valid=type(v) is int and v >= 0
        elif op=='ci_url_run_id':
            repo=read_path(evidence,'github.repo')
            run_id=read_path(evidence,'github.ci_run_id')
            valid=(isinstance(v,str) and repo=='watersun79-source/ai-token-optimization'
                   and type(run_id) is int and run_id > 0
                   and v==f'https://github.com/{repo}/actions/runs/{run_id}')
        elif op=='kst_slot':
            # This checks only timestamp syntax/calendar validity, not whether
            # a record is the freshest observation from a real provider.
            if isinstance(v,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2} Asia/Seoul',v):
                datetime.strptime(v[:-11],'%Y-%m-%d %H:%M')
                valid=True
        elif op=='utc_datetime':
            # Portable, strict UTC-offset ISO 8601 subset for cross-language
            # evidence checks. Python's fromisoformat is intentionally liberal:
            # it accepts lowercase separators, normalizes +09:60, and can
            # silently discard digits beyond its 6-digit microsecond precision.
            if isinstance(v,str):
                stamp=re.fullmatch(
                    r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'
                    r'(?:\.[0-9]{1,9})?(?:Z|([+-])([0-9]{2}):([0-9]{2}))',v)
                if stamp:
                    hour=int(stamp.group(2) or 0)
                    minute=int(stamp.group(3) or 0)
                    if hour<=18 and minute<=59 and (hour<18 or minute==0):
                        dt=datetime.fromisoformat(v.replace('Z','+00:00'))
                        valid=dt.tzinfo is not None and dt.utcoffset() is not None
        elif op=='runtime_receipt':
            receipt,why=read_runtime_receipt()
            if receipt is None:
                result['detail']=why
                return result
            target=receipt['total_passed'] if expect=='total' else receipt['counts'][expect]['passed']
            valid=type(v) is int and v==target
            result['scope']='LOCAL_TEST_RECEIPT_NOT_PROVIDER_AUTHENTICATED'
            result['detail']='local code-hash/freshness receipt agrees with measured regressions' if valid else 'local evidence count disagrees with measured regression'
        elif op=='present': valid=v not in ('',[],{})
        else: raise ValueError('unsupported operator')
        result['status']='PASS' if valid else 'FAIL'
        if op!='runtime_receipt':
            result['detail']='snapshot rule satisfied; origin not independently authenticated' if valid else 'rule mismatch or bad shape'
    except (ValueError,TypeError,OverflowError):
        result['status']='FAIL';result['detail']='invalid value or datatype'
    return result

def main(args=None):
    p=argparse.ArgumentParser(description='R16 no-cost local BOT task verifier')
    p.add_argument('--bot',required=True)
    p.add_argument('--evidence',default=str(ROOT/'evidence.json'))
    a=p.parse_args(args)
    catalog=json.loads((ROOT/'catalog.json').read_text(encoding='utf8'))
    require_trusted_catalog(catalog)
    evidence=json.loads(Path(a.evidence).read_text(encoding='utf8'))
    item=next((x for x in catalog if x['id']==a.bot),None)
    if item is None: p.error('unregistered bot')
    print(json.dumps(validate(item,evidence),ensure_ascii=False,sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())

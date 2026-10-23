#!/usr/bin/env python3
"""Fast read-only batch of 100 policy checks. No 100 model or subprocess calls."""
import csv,hashlib,json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from runner import ROOT,validate

def main():
    catalog=json.loads((ROOT/'catalog.json').read_text(encoding='utf8'))
    evidence=json.loads((ROOT/'evidence.json').read_text(encoding='utf8'))
    ids=[b['id'] for b in catalog]
    if len(ids)!=100 or len(set(ids))!=100:raise RuntimeError('BOT IDs inconsistent')
    # Installer generated actual wrappers, but this is batch execution,
    # not 100 independent Python OS processes.
    bindir=ROOT/'.local_install'/'bin'
    installed={p.name for p in bindir.glob('ai-bot-*')}
    expected={'ai-bot-'+i for i in ids}
    if installed!=expected:raise RuntimeError('CLI wrapper install mismatch')
    checked={}
    for fn in ('runner.py','catalog.json','evidence.json','runtime_proof.json','test_runtime.py',
               'UtcStrictOracle.java','utc_strict_oracle.js','measure_runtime.py','utc_strict_oracle_cases.tsv'):
        local=(ROOT/fn).read_bytes()
        actual=(ROOT/'.local_install'/fn).read_bytes()
        checked[fn]=hashlib.sha256(local).hexdigest()
        if local!=actual:raise RuntimeError('installed source differs: '+fn)
    results=sorted((validate(bot,evidence) for bot in catalog),key=lambda x:x['id'])
    statuses=Counter(x['status'] for x in results)
    by_group=defaultdict(Counter)
    for x in results:by_group[x['category']][x['status']]+=1
    rows=[]
    for x in results:
        rows.append({k:x.get(k,'') for k in ('id','category','name','status','source','scope','detail')})
    with (ROOT/'results_batch_v6.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    with (ROOT/'results_batch_v6.jsonl').open('w',encoding='utf8') as f:
        for x in results:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
    out={
       'mode':'OFFLINE_SINGLE_PROCESS_100_RULE_CHECKS_NOT_100_LLM_MODELS',
       'timestamp_utc':datetime.now(timezone.utc).isoformat(),
       'installed_command_wrappers':len(expected),
       'executed_rule_checks':len(results),
       'executed_isolated_cli_processes':0,
       'statuses':dict(statuses),
       'by_group':{k:dict(v) for k,v in by_group.items()},
       'fresh_local_runtime_receipt_checks':sum(x.get('scope')=='LOCAL_TEST_RECEIPT_NOT_PROVIDER_AUTHENTICATED' and x['status']=='PASS' for x in results),
       'official_unattended_app_call_success':'UNVERIFIED',
       'note':'PASS in other categories means snapshot rule satisfied, NOT authenticated external app read or platform scheduled run.',
       'source_hashes_sha256':checked,
       'external_provider_model_calls':0,
       'remote_writes':0
    }
    (ROOT/'summary_v6.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:out[k] for k in ('mode','installed_command_wrappers','executed_rule_checks','statuses','fresh_local_runtime_receipt_checks','official_unattended_app_call_success')},ensure_ascii=False))
    if statuses.get('FAIL') or statuses.get('ERROR'):raise SystemExit(2)
if __name__=='__main__':main()

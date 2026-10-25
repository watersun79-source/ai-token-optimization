#!/usr/bin/env python3
"""Re-measure local tests before installing BOTs; no network, external models, or production writes."""
import hashlib,json,re,shutil,subprocess,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
from runner import runtime_input_hashes
ROOT=Path(__file__).resolve().parent

def execute(argv,cwd=None,timeout=30):
    p=subprocess.run(argv,cwd=cwd or ROOT,capture_output=True,text=True,timeout=timeout,check=False)
    if p.returncode:raise RuntimeError(f"local test failed: {argv[0]} exit {p.returncode}: {(p.stderr+p.stdout)[-900:]}")
    return p.stdout+p.stderr

def main():
    before = runtime_input_hashes()
    counts={}
    py=execute([sys.executable,'-m','unittest','-q','test_runtime'])
    m=re.search(r'Ran ([0-9]+) tests?',py)
    if m is None or not re.search(r'\bOK\b',py):raise RuntimeError('Python tests not verifiable')
    counts['python']={'passed':int(m.group(1)),'total':int(m.group(1))}
    # Pin the trusted fixture path: Java must not pick a different TSV from cwd.
    fixture=str(ROOT/'utc_strict_oracle_cases.tsv')
    if shutil.which('javac'):
        with tempfile.TemporaryDirectory(prefix='r16-v6-java-') as d:
            execute(['javac','-d',d,str(ROOT/'UtcStrictOracle.java')])
            java=execute(['java','-cp',d,'UtcStrictOracle',fixture],cwd=d)
    else:
        # OpenJDK source launcher; also test outside the checkout.
        with tempfile.TemporaryDirectory(prefix='r16-v6-java-source-') as d:
            java=execute(['java',str(ROOT/'UtcStrictOracle.java'),fixture],cwd=d)
    js=execute(['node',str(ROOT/'utc_strict_oracle.js')])
    for lang,out in [('java',java),('js',js)]:
        match=re.search(r'PASS ([0-9]+)/([0-9]+)',out)
        if match is None:raise RuntimeError(f'{lang} test counts unavailable')
        a,b=map(int,match.groups())
        if a<1 or a!=b:raise RuntimeError(f'{lang} tests not all passing')
        counts[lang]={'passed':a,'total':b}
    after = runtime_input_hashes()
    if before != after:
        raise RuntimeError('runtime/test inputs changed during measurement')
    receipt={'format':'LOCAL_TEST_RECEIPT_V6',
             'input_sha256':after,
             'measured_at_utc':datetime.now(timezone.utc).isoformat(),
             'counts':counts,'total_passed':sum(x['passed'] for x in counts.values()),
             'source_sha256':{lang:hashlib.sha256((ROOT/fn).read_bytes()).hexdigest() for lang,fn in
                  [('python','test_runtime.py'),('java','UtcStrictOracle.java'),('js','utc_strict_oracle.js')]},
             'scope':'offline local test counts only; not provider-authenticated scheduled execution'}
    (ROOT/'runtime_proof.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    evidence_file=ROOT/'evidence.json'
    evidence=json.loads(evidence_file.read_text(encoding='utf8'))
    evidence['polyglot'].update(python_passed=counts['python']['passed'],java_passed=counts['java']['passed'],
       js_passed=counts['js']['passed'],total_passed=receipt['total_passed'])
    evidence['notice']='Read-only connector snapshot + v5 measured local regression receipt. Snapshot PASS is NOT authenticated current provider state.'
    evidence_file.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'source':'local_measured_tests','counts':counts,'total':receipt['total_passed'],
                     'source_sha256':receipt['source_sha256']},ensure_ascii=False))
if __name__=='__main__':main()

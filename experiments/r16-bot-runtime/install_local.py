#!/usr/bin/env python3
"""Install 100 isolated offline command wrappers under a local directory only."""
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent
DEST=ROOT/'.local_install'

def install():
    bots=json.loads((ROOT/'catalog.json').read_text(encoding='utf8'))
    assert len(bots)==100 and len({x['id'] for x in bots})==100
    (DEST/'bin').mkdir(parents=True,exist_ok=True)
    for fname in ('runner.py','catalog.json','evidence.json','runtime_proof.json','test_runtime.py','UtcStrictOracle.java','utc_strict_oracle.js','measure_runtime.py','utc_strict_oracle_cases.tsv'):
        shutil.copyfile(ROOT/fname,DEST/fname)
    for bot in bots:
        dest=DEST/'bin'/('ai-bot-'+bot['id'])
        dest.write_text('''#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runner import main
if __name__ == '__main__':
    raise SystemExit(main(['--bot', 'BOT_ID', *sys.argv[1:]]))
'''.replace('BOT_ID',bot['id']),encoding='utf8')
        dest.chmod(0o755)
    wrappers=list((DEST/'bin').glob('ai-bot-*'))
    assert len(wrappers)==100
    print(json.dumps({'installed_wrappers':len(wrappers),'location':str(DEST),'external_dependencies':0,'external_model_calls':0}))
if __name__=='__main__':install()

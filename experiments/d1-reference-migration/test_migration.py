"""Contract tests using SYNTHETIC D1 fixture data and an in-memory CAS adapter.

These tests do not invoke native ChatGPT schedules or production D1.
"""
from __future__ import annotations
import copy
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import threading
import unittest

from guard import Conflict, FailClosed, utf16_units
from migration import Evidence, REPORT_KEY, plan_migration, migrate

ARCHIVE_KEYS = {
    27: REPORT_KEY+'.archive-r27-20261103-1948',
    28: REPORT_KEY+'.archive-r28-20261103-1950',
    29: REPORT_KEY+'.archive-r29-20261103-1952',
    30: REPORT_KEY+'.archive-r30-20261103',
    31: REPORT_KEY+'.archive-r31-20261103',
    36: REPORT_KEY+'.archive-r36-20261104-0605',
}
AUDIT_KEY = 'project.ai-bot.render-trace-path-20261103'
TRACEREF = AUDIT_KEY+'@1'
OWNER = '6ae8db67fef081919af59fecbf162552'


def dump(x):
    return json.dumps(x, ensure_ascii=False, separators=(',',':'))


def receipt(value):
    # Model opaque server metadata, not the SHA256(value) digest itself.
    return sha256(('server-receipt@'+value).encode()).hexdigest()


def ev(key, body, ver):
    value=body if isinstance(body,str) else dump(body)
    return Evidence(key,value,ver,receipt(value))


def snapshots(tag='old'):
    names=('coordinator','render','dev','site','neon')
    return [{'component':name, 'task_id':'task-'+name, 'enabled':True,
             'run_id':f'{tag}-{name}-uuid', 'result_state':'NO_UPDATE' if name=='site' else 'NATIVE_MATCHED',
             'started_at':'2026-11-03T21:00:00Z'} for name in names]


def report(tag='old'):
    snaps=snapshots(tag)
    return {'schema':'AI_BOT_UNIFIED_REPORT_V1','owner_task_id':OWNER,
            'observed_snapshots':snaps,'source_runs':'|'.join(x['component']+':'+x['run_id'] for x in snaps),
            'summary':{'total':5,'enabled':5,'official_same_run_result':4,'no_update':1,
                       'result_missing':0, 'in_progress':0, 'result_mismatch':0},
            'provider_ledger':'UNVERIFIED','direct_external_model_execution':'NOT_RUN',
            'software_promotion':'NONE'}


class FakeStore:
    def __init__(self):
        self.data = {}
        self.hist = {}
        self.writes = []
        self.lock = threading.RLock()
        self.before_write = None
        self.change_on_prewrite = None
        self.after_write_tamper = False

    def read(self,key):
        with self.lock:
            if key==REPORT_KEY and self.change_on_prewrite is not None:
                callback=self.change_on_prewrite
                self.change_on_prewrite=None
                callback(self)
            return self.data.get(key)

    def history_at(self,key,revision):
        with self.lock:
            return self.hist.get((key,revision))

    def write(self,key,value,*,expected_version,request_id):
        with self.lock:
            if self.before_write:
                cb=self.before_write
                self.before_write=None
                cb(self)
            current=self.data.get(key)
            rev=current.version if current else 0
            if rev != expected_version:
                raise Conflict('EXPECTED_VERSION_MISMATCH')
            ack=ev(key,value,rev+1)
            stored=ev(key,value+' MALICIOUS_CHANGE',rev+1) if self.after_write_tamper else ack
            self.data[key]=stored
            self.writes.append((key, expected_version, request_id))
            return ack


def make_store():
    store=FakeStore()
    base={n:report(tag='older-'+str(n)) for n in range(27,32)}
    for n in (30,31):
        base[n]['observed_snapshots'][1]['run_id']='old-render-uuid'
        base[n]['source_runs']='|'.join(x['component']+':'+x['run_id'] for x in base[n]['observed_snapshots'])
        base[n]['render_trace_evidence']=TRACEREF
    for n in (27,28,29,30,31):
        src=ev(REPORT_KEY,base[n],n)
        arc=ev(ARCHIVE_KEYS[n],base[n],1)
        store.hist[(REPORT_KEY,n)]=src
        store.data[ARCHIVE_KEYS[n]]=arc
    meta={
        'r27':ARCHIVE_KEYS[27], 'r28':ARCHIVE_KEYS[28], 'r29':ARCHIVE_KEYS[29],
        'source_rev':29, 'source_sha':store.hist[(REPORT_KEY,29)].content_sha,
        'archived_sha':store.data[ARCHIVE_KEYS[29]].content_sha, 'verbatim_readback':True,
        'r30':ARCHIVE_KEYS[30],
        'r31':{'key':ARCHIVE_KEYS[31], 'source_revision':31,'archive_revision':1,
               'source_content_sha':store.hist[(REPORT_KEY,31)].content_sha,
               'archive_content_sha':store.data[ARCHIVE_KEYS[31]].content_sha,
               'original_chars':len(store.hist[(REPORT_KEY,31)].value), 'exact_readback':True},
    }
    pointer={
        'key':ARCHIVE_KEYS[31], 'source_revision':31, 'archive_revision':1,
        'source_content_sha':store.hist[(REPORT_KEY,31)].content_sha,
        'archive_content_sha':store.data[ARCHIVE_KEYS[31]].content_sha,
        'original_chars':len(store.hist[(REPORT_KEY,31)].value),'verbatim':True,
    }
    hist32=report('snapshot32');hist32.update(report_archives=meta,history_archive=pointer,render_trace_evidence=TRACEREF)
    hist33=copy.deepcopy(hist32);hist33['observed_at_utc']='2026-11-03T11:02:00Z'
    store.hist[(REPORT_KEY,32)]=ev(REPORT_KEY,hist32,32)
    store.hist[(REPORT_KEY,33)]=ev(REPORT_KEY,hist33,33)
    recent=report('recent36')
    store.hist[(REPORT_KEY,36)]=ev(REPORT_KEY,recent,36)
    store.data[ARCHIVE_KEYS[36]]=ev(ARCHIVE_KEYS[36],recent,1)
    store.data[AUDIT_KEY]=ev(AUDIT_KEY,{
        'schema':'AI_BOT_RENDER_TRACE_SOURCE_AUDIT_V1',
        'target_native_run_id':'old-render-uuid',
        'native_run_status':'completed', 'observed_native_provider_trace':'UNVERIFIED'
    },1)
    current=report('NEW_CURRENT37')
    current['observed_at_utc']='2026-11-03T21:07:40Z'
    current['provider_source_window_check']={'neon':'UNVERIFIED','render':'UNVERIFIED'}
    current['archive_before_provider_audit']={
        'key':ARCHIVE_KEYS[36], 'source_revision':36,
        'source_sha':store.hist[(REPORT_KEY,36)].content_sha,
        'archive_sha':store.data[ARCHIVE_KEYS[36]].content_sha,
        'verbatim_readback':True,
    }
    store.data[REPORT_KEY]=ev(REPORT_KEY,current,37)
    return store


def modify_json_record(db,key,fn,history_rev=None):
    if history_rev is not None:
        old=db.hist[(key,history_rev)]
    else:
        old=db.data[key]
    v=json.loads(old.value)
    fn(v)
    new=ev(old.key,v,old.version)
    if history_rev is not None:
        db.hist[(key,history_rev)]=new
    else:
        db.data[key]=new


class MigrationTests(unittest.TestCase):
    def test_migrate_preserves_every_current_value_and_six_verified_archives(self):
        db=make_store();old=json.loads(db.read(REPORT_KEY).value)
        r=migrate(db);self.assertEqual(r['status'],'PASS_ISOLATED')
        self.assertEqual(r['verified_archive_revisions'],[27,28,29,30,31,36])
        self.assertEqual(db.data[REPORT_KEY].version,38)
        now=json.loads(db.data[REPORT_KEY].value)
        for k,v in old.items():self.assertEqual(now[k],v,k)
        self.assertEqual(now['report_archives']['r31'],ARCHIVE_KEYS[31])
        self.assertEqual(now['report_archives']['r36'],ARCHIVE_KEYS[36])
        self.assertEqual(now['history_archive']['source_revision'],36)
        self.assertEqual(now['render_trace_evidence'],TRACEREF)
        self.assertEqual(now['archive_reference_scope'],'HISTORICAL_VERIFIED_ONLY_NOT_CURRENT_NATIVE_RENDER_CAUSALITY')
        self.assertEqual([w[0] for w in db.writes],[REPORT_KEY])

    def test_offline_plan_has_no_writes(self):
        db=make_store();p=plan_migration(db)
        self.assertEqual(p['status'],'READY_OFFLINE')
        self.assertEqual(db.writes,[])
        self.assertLess(p['candidate_units'],9300)

    def test_idempotent_second_call_makes_no_write(self):
        db=make_store();migrate(db);old=len(db.writes)
        self.assertEqual(migrate(db)['status'],'NO_UPDATE')
        self.assertEqual(len(db.writes),old)

    def test_r30_r31_backups_remain_exact_and_untouched(self):
        db=make_store();before={k:v.value for k,v in db.data.items() if k!=REPORT_KEY}
        migrate(db)
        self.assertEqual(before,{k:v.value for k,v in db.data.items() if k!=REPORT_KEY})
        for r in (30,31):self.assertEqual(db.data[ARCHIVE_KEYS[r]].value,db.hist[(REPORT_KEY,r)].value)

    def test_content_sha_is_opaque_server_receipt(self):
        db=make_store();r=db.hist[(REPORT_KEY,31)]
        self.assertNotEqual(r.content_sha,sha256(r.value.encode()).hexdigest())
        self.assertEqual(migrate(db)['status'],'PASS_ISOLATED')

    def test_missing_r30_archive_blocks_no_writes(self):
        db=make_store();del db.data[ARCHIVE_KEYS[30]]
        with self.assertRaisesRegex(FailClosed,'EVIDENCE_MISSING'):migrate(db)
        self.assertFalse(db.writes)

    def test_missing_r31_archive_blocks(self):
        db=make_store();del db.data[ARCHIVE_KEYS[31]]
        with self.assertRaisesRegex(FailClosed,'EVIDENCE_MISSING'):migrate(db)
        self.assertFalse(db.writes)

    def test_tampered_r31_archive_blocks(self):
        db=make_store();modify_json_record(db,ARCHIVE_KEYS[31],lambda x:x.__setitem__('note','forged'))
        with self.assertRaisesRegex(FailClosed,'ARCHIVE_SOURCE_NOT_EXACT'):migrate(db)
        self.assertFalse(db.writes)

    def test_r30_archive_rewritten_revision_blocks(self):
        db=make_store();old=db.data[ARCHIVE_KEYS[30]]
        db.data[ARCHIVE_KEYS[30]]=ev(old.key,old.value,2)
        with self.assertRaisesRegex(FailClosed,'EVIDENCE_IDENTITY_MISMATCH'):migrate(db)

    def test_missing_history_r32_blocks(self):
        db=make_store();del db.hist[(REPORT_KEY,32)]
        with self.assertRaisesRegex(FailClosed,'EVIDENCE_MISSING'):migrate(db)

    def test_r33_reference_disagrees_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x.__setitem__('render_trace_evidence','wrong'),33)
        with self.assertRaisesRegex(FailClosed,'OFFICIAL_REFERENCES_DISAGREE'):migrate(db)

    def test_r29_index_source_sha_tamper_blocks(self):
        db=make_store()
        def tamper(x):x['report_archives']['source_sha']='0'*64
        modify_json_record(db,REPORT_KEY,tamper,32)
        modify_json_record(db,REPORT_KEY,tamper,33)
        with self.assertRaisesRegex(FailClosed,'LEGACY_R29_INDEX_RECEIPT_MISMATCH'):migrate(db)

    def test_r32_pointer_wrong_source_sha_blocks(self):
        db=make_store()
        def tamper(x):x['report_archives']['r31']['source_content_sha']='0'*64
        modify_json_record(db,REPORT_KEY,tamper,32)
        modify_json_record(db,REPORT_KEY,tamper,33)
        with self.assertRaisesRegex(FailClosed,'LEGACY_ARCHIVE_RECEIPT_MISMATCH'):migrate(db)

    def test_r32_pointer_wrong_archive_sha_blocks(self):
        db=make_store()
        def tamper(x):x['report_archives']['r31']['archive_content_sha']='f'*64
        modify_json_record(db,REPORT_KEY,tamper,32)
        modify_json_record(db,REPORT_KEY,tamper,33)
        with self.assertRaisesRegex(FailClosed,'LEGACY_ARCHIVE_RECEIPT_MISMATCH'):migrate(db)

    def test_r32_history_pointer_wrong_blocks(self):
        db=make_store()
        def tamper(x):x['history_archive']['source_revision']=30
        modify_json_record(db,REPORT_KEY,tamper,32)
        modify_json_record(db,REPORT_KEY,tamper,33)
        with self.assertRaisesRegex(FailClosed,'R31_HISTORY_POINTER_INVALID'):migrate(db)

    def test_wrong_owner_in_archive_history_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x.__setitem__('owner_task_id','attacker'),31)
        with self.assertRaisesRegex(FailClosed,'HISTORY_SCHEMA_OR_OWNER_MISMATCH'):migrate(db)

    def test_unverified_archive_reference_key_is_rejected(self):
        db=make_store()
        def tamper(x):x['report_archives']['r30']='another-service.archive-r30-fake'
        modify_json_record(db,REPORT_KEY,tamper,32)
        modify_json_record(db,REPORT_KEY,tamper,33)
        with self.assertRaisesRegex(FailClosed,'ARCHIVE_KEY_NOT_IN_TRUSTED_NAMESPACE'):migrate(db)

    def test_missing_trace_audit_blocks(self):
        db=make_store();del db.data[AUDIT_KEY]
        with self.assertRaisesRegex(FailClosed,'EVIDENCE_MISSING'):migrate(db)

    def test_trace_wrong_historical_run_blocks(self):
        db=make_store();modify_json_record(db,AUDIT_KEY,lambda x:x.__setitem__('target_native_run_id','not-history-run'))
        with self.assertRaisesRegex(FailClosed,'TRACE_PAYLOAD_WRONG_HISTORICAL_RUN'):migrate(db)

    def test_trace_audit_wrong_version_blocks(self):
        db=make_store();r=db.data[AUDIT_KEY];db.data[AUDIT_KEY]=ev(r.key,r.value,2)
        with self.assertRaisesRegex(FailClosed,'EVIDENCE_IDENTITY_MISMATCH'):migrate(db)

    def test_r36_archive_missing_blocks(self):
        db=make_store();del db.data[ARCHIVE_KEYS[36]]
        with self.assertRaisesRegex(FailClosed,'EVIDENCE_MISSING'):migrate(db)

    def test_r36_archive_source_receipt_wrong_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x['archive_before_provider_audit'].__setitem__('source_sha','0'*64))
        with self.assertRaisesRegex(FailClosed,'RECENT_ARCHIVE_RECEIPT_MISMATCH'):migrate(db)

    def test_r36_archive_absent_pointer_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x.pop('archive_before_provider_audit'))
        with self.assertRaisesRegex(FailClosed,'RECENT_ARCHIVE_OR_PROVENANCE_MISSING'):migrate(db)

    def test_live_without_source_runs_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x.pop('source_runs'))
        with self.assertRaisesRegex(FailClosed,'INVALID_CURRENT_RUN_SCHEMA'):migrate(db)

    def test_run_reference_tamper_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x.__setitem__('source_runs','invalid-run'))
        with self.assertRaisesRegex(FailClosed,'SOURCE_RUN_REFERENCE_COUNT_MISMATCH'):migrate(db)

    def test_summary_count_tamper_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x['summary'].__setitem__('total',4))
        with self.assertRaisesRegex(FailClosed,'SUMMARY_SNAPSHOT_COUNT_MISMATCH'):migrate(db)

    def test_enabled_mismatch_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x['observed_snapshots'][0].__setitem__('enabled',False))
        with self.assertRaisesRegex(FailClosed,'LATEST_ENABLED_STATUS_INVALID'):migrate(db)

    def test_existing_forged_archive_ref_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x.__setitem__('report_archives',{'r30':'fake'}))
        with self.assertRaisesRegex(FailClosed,'EXISTING_ARCHIVE_INDEX_CONFLICT'):migrate(db)

    def test_existing_trace_ref_conflict_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x.__setitem__('render_trace_evidence','project.ai-bot.fake@1'))
        with self.assertRaisesRegex(FailClosed,'EXISTING_TRACE_POINTER_CONFLICT'):migrate(db)

    def test_existing_history_ref_conflict_blocks(self):
        db=make_store();modify_json_record(db,REPORT_KEY,lambda x:x.__setitem__('history_archive',{'key':'unknown'}))
        with self.assertRaisesRegex(FailClosed,'EXISTING_HISTORY_POINTER_CONFLICT'):migrate(db)

    def test_readonly_preflight_fails_if_over_cap(self):
        db=make_store();original=json.loads(db.read(REPORT_KEY).value)
        original['giant_dynamic']='X'*10000
        db.data[REPORT_KEY]=ev(REPORT_KEY,original,37)
        with self.assertRaisesRegex(FailClosed,'LIVE_ABOVE_HARD_LIMIT'):plan_migration(db)

    def test_compaction_after_migration_must_not_be_implied(self):
        db=make_store();p=plan_migration(db)
        self.assertGreater(p['candidate_units'],p['current_units'])
        self.assertEqual(db.data[REPORT_KEY].version,37)

    def test_live_source_changed_before_cas_blocks(self):
        db=make_store()
        count={'n':0}
        orig=db.read
        def read(key):
            if key==REPORT_KEY:
                count['n']+=1
                if count['n']==2:
                    old=db.data[REPORT_KEY]
                    db.data[REPORT_KEY]=ev(REPORT_KEY,old.value+' new producer revision',38)
            return orig(key)
        db.read=read
        with self.assertRaisesRegex(Conflict,'SOURCE_CHANGED_BEFORE_CAS'):migrate(db)
        self.assertFalse(db.writes)

    def test_concurrent_cas_winner_conflict(self):
        db=make_store()
        def competing(store):
            now=store.data[REPORT_KEY]
            store.data[REPORT_KEY]=ev(REPORT_KEY,now.value,38)
        db.before_write=competing
        with self.assertRaisesRegex(Conflict,'MIGRATION_CAS_CONFLICT_NO_RETRY'):migrate(db)
        self.assertFalse(db.writes)

    def test_live_readback_tamper_stops(self):
        db=make_store();db.after_write_tamper=True
        with self.assertRaisesRegex(FailClosed,'MIGRATION_READBACK_MISMATCH_STOP'):migrate(db)
        self.assertEqual(len(db.writes),1)

    def test_bad_cas_acknowledgment_stops_without_retry(self):
        db=make_store()
        original_write=db.write
        def bad_ack(key,value,*,expected_version,request_id):
            original_write(key,value,expected_version=expected_version,request_id=request_id)
            return ev(key,value,expected_version+2)
        db.write=bad_ack
        with self.assertRaisesRegex(FailClosed,'MIGRATION_CAS_ACK_MISMATCH_STOP'):migrate(db)
        self.assertEqual(len(db.writes),1)

    def test_source_receipt_changed_same_value_and_version_blocks(self):
        db=make_store();count={'n':0};old_read=db.read
        def changed_receipt(key):
            item=old_read(key)
            if key==REPORT_KEY:
                count['n']+=1
                if count['n']==2:return Evidence(item.key,item.value,item.version,'0'*64)
            return item
        db.read=changed_receipt
        with self.assertRaisesRegex(Conflict,'SOURCE_CHANGED_BEFORE_CAS'):migrate(db)
        self.assertEqual(db.writes,[])

    def test_real_parallel_writers_exactly_one_cas(self):
        db=make_store()
        def task(i):
            try:return migrate(db)['status']
            except Conflict:return 'CONFLICT'
        with ThreadPoolExecutor(max_workers=8) as pool:res=list(pool.map(task,range(8)))
        self.assertEqual(res.count('PASS_ISOLATED'),1,res)
        self.assertTrue(all(x in ('PASS_ISOLATED','CONFLICT','NO_UPDATE') for x in res),res)
        self.assertEqual(len(db.writes),1)

    def test_wrong_history_key_is_rejected(self):
        db=make_store();row=db.hist[(REPORT_KEY,31)]
        db.hist[(REPORT_KEY,31)]=ev('different-key',row.value,31)
        with self.assertRaisesRegex(FailClosed,'EVIDENCE_IDENTITY_MISMATCH'):migrate(db)

    def test_wrong_source_archive_content_same_version_rejected(self):
        db=make_store();row=db.data[ARCHIVE_KEYS[27]]
        db.data[ARCHIVE_KEYS[27]]=ev(row.key,row.value+'extra',1)
        with self.assertRaisesRegex(FailClosed,'ARCHIVE_SOURCE_NOT_EXACT'):migrate(db)

    def test_offline_readonly_no_side_effects_on_failure(self):
        db=make_store();before={k:v for k,v in db.data.items()}
        del db.hist[(REPORT_KEY,27)]
        with self.assertRaises(FailClosed):migrate(db)
        self.assertEqual(before,db.data)
        self.assertFalse(db.writes)


if __name__=='__main__':
    unittest.main()

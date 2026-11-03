"""Offline-only contract tests: all backend state is synthetic/in-memory."""
import json
import unittest
from guard import Conflict, FailClosed, Record, rotate, inspect, digest, utf16_units, WARNING_AT

KEY='project.ai-bot.unified-report'
RUNS=['7de85fa5', 'fd2d6a0b', 'fa5dae54', '17126cca', '0197c015']


def fixture(over_limit=True):
    state={
        'schema':'AI_BOT_UNIFIED_REPORT_V1', 'owner_task_id':'6ae8db67fef081919af59fecbf162552',
        'source_runs':'|'.join(f'{component}:{run}' for component,run in zip(('coordinator','render','dev','site','neon'),RUNS)),
        'observed_snapshots':[{'component':k, 'last_run_id':v, 'state':'NO_UPDATE' if k=='site' else 'NATIVE_MATCHED'} for k,v in zip(('coordinator','render','dev','site','neon'),RUNS)],
        'summary':{'total':5,'enabled':5,'native_result_verified':4,'no_update':1},
        'render_trace_evidence':'project.ai-bot.render-trace-path-20261103@1',
        'metadata_drift_observation':{'result_missing':1,'time_conflicts':3},
        'report_archives':{'r30':'project.ai-bot.unified-report.archive-r30-20261103',
                           'r31':'project.ai-bot.unified-report.archive-r31-20261103'},
        'cross_system_receipt_check':{'historical_events':'X'*3600},
        'traceability_audit':{'samples':'Y'*2200},
        'developer_result_diagnostic':{'notes':'Z'*1700},
    }
    if over_limit:
        # Tailor source close to the 10000 UTF-16 unit API maximum.
        while True:
            raw=json.dumps(state,ensure_ascii=False,separators=(',',':'))
            if utf16_units(raw)>=9350:
                break
            state['cross_system_receipt_check']['historical_events']+='H'*min(400,9350-utf16_units(raw))
        assert utf16_units(json.dumps(state,ensure_ascii=False,separators=(',',':')))<=10000
    return json.dumps(state,ensure_ascii=False,separators=(',',':'))


class FakeStore:
    def __init__(self,body=None):
        self.data={KEY:Record(KEY,body,30)} if body is not None else {}
        self.writes=[]
        self.on_archive_read=None
        self.on_live_write=None
        self.drop_archive_read=False
        self.corrupt_archive_read=False
        self.readback_tamper=False

    def read(self,key):
        r=self.data.get(key)
        if r is None:return None
        if '.archive-auto-' in key and self.drop_archive_read:return None
        if '.archive-auto-' in key and self.corrupt_archive_read:return Record(key,r.value+'CORRUPT',r.version)
        if key==KEY and self.readback_tamper and len(self.writes)>=2:
            return Record(key,'INCONSISTENT',r.version)
        return r

    def write(self,key,value,*,expected_version,request_id):
        current=self.data.get(key)
        version=current.version if current else 0
        if key==KEY and self.on_live_write:
            self.on_live_write(self)
            current=self.data.get(key)
            version=current.version if current else 0
        if version!=expected_version:
            raise Conflict('STALE_EXPECTED_VERSION')
        if key.endswith('') and len(value.encode('utf-16-le'))//2>10000:
            raise FailClosed('TOO_BIG')
        rr=Record(key,value,version+1)
        self.data[key]=rr
        self.writes.append((key,expected_version,request_id))
        return rr


class GuardTests(unittest.TestCase):
    def test_archives_before_live_and_exact_data(self):
        original=fixture(); db=FakeStore(original)
        result=rotate(db,KEY)
        self.assertEqual(result['status'],'PASS_ISOLATED')
        self.assertEqual([w[0] for w in db.writes],[result['archive_key'],KEY])
        self.assertEqual(db.read(result['archive_key']).value,original)
        self.assertEqual(digest(db.read(result['archive_key']).value),digest(original))
        self.assertEqual(db.read(KEY).version,31)
        self.assertTrue(result['retained_run_ids'] and result['retained_summary'] and result['retained_snapshots'])
        reduced=json.loads(db.read(KEY).value)
        self.assertEqual(reduced['render_trace_evidence'],'project.ai-bot.render-trace-path-20261103@1')
        self.assertIn('r30',reduced['report_archives']);self.assertIn('r31',reduced['report_archives'])
        self.assertEqual(reduced['metadata_drift_observation'],json.loads(original)['metadata_drift_observation'])

    def test_duplicate_run_has_no_extra_writes(self):
        db=FakeStore(fixture());rotate(db,KEY)
        first=len(db.writes)
        self.assertEqual(rotate(db,KEY)['status'],'NO_UPDATE')
        self.assertEqual(len(db.writes),first)

    def test_under_warning_never_writes(self):
        db=FakeStore(fixture(False))
        self.assertEqual(rotate(db,KEY)['status'],'NO_UPDATE')
        self.assertEqual(db.writes,[])

    def test_latest_compact_schema_drift_detected_read_only(self):
        compact={'schema':'AI_BOT_UNIFIED_REPORT_V1','owner_task_id':'X',
                 'observed_snapshots':[{'run_id':'current'}],'provider_ledger':'UNVERIFIED'}
        db=FakeStore(json.dumps(compact))
        out=rotate(db,KEY)
        self.assertEqual(out['status'],'NO_UPDATE')
        self.assertEqual(out['inspection']['status'],'SCHEMA_DRIFT')
        self.assertTrue(out['inspection']['archive_refs_missing'])
        self.assertIn('source_runs',out['inspection']['missing_required'])
        self.assertEqual(db.writes,[])

    def test_source_missing_fails(self):
        with self.assertRaisesRegex(FailClosed,'SOURCE_MISSING'):rotate(FakeStore(),KEY)

    def test_bad_json_fails_before_writes(self):
        db=FakeStore('x'*9400)
        with self.assertRaisesRegex(FailClosed,'INVALID_JSON'):rotate(db,KEY)
        self.assertEqual(db.writes,[])

    def test_drift_above_warning_fails_closed_before_archive(self):
        db=FakeStore(json.dumps({'schema':'A','observed_snapshots':[],'x':'Q'*9500}))
        with self.assertRaisesRegex(FailClosed,'SCHEMA_DRIFT'):rotate(db,KEY)
        self.assertEqual(db.writes,[])

    def test_preexisting_corrupt_archive_fails(self):
        db=FakeStore(fixture());src=db.read(KEY)
        archive=f'{KEY}.archive-auto-r{src.version}-{digest(src.value)[:12]}'
        db.data[archive]=Record(archive,'CORRUPTED',1)
        with self.assertRaisesRegex(FailClosed,'ARCHIVE_MISMATCH'):rotate(db,KEY)
        self.assertEqual(db.read(KEY).version,30)
        self.assertEqual(db.writes,[])

    def test_archive_missing_after_write_fails_closed(self):
        db=FakeStore(fixture());db.drop_archive_read=True
        with self.assertRaisesRegex(FailClosed,'ARCHIVE_MISSING'):rotate(db,KEY)
        self.assertEqual([w[0] for w in db.writes if w[0]==KEY],[])

    def test_archive_readback_corruption_fails_closed(self):
        db=FakeStore(fixture());db.corrupt_archive_read=True
        with self.assertRaisesRegex(FailClosed,'ARCHIVE_MISMATCH'):rotate(db,KEY)
        self.assertEqual([w[0] for w in db.writes if w[0]==KEY],[])

    def test_competing_writer_live_cas_fails_and_preserves_their_update(self):
        db=FakeStore(fixture())
        def concurrent(other):
            other.on_live_write=None
            r=other.data[KEY]
            other.data[KEY]=Record(KEY,r.value+' new-authenticated-write',r.version+1)
        db.on_live_write=concurrent
        with self.assertRaisesRegex(Conflict,'LIVE_CAS_CONFLICT_NO_RETRY'):rotate(db,KEY)
        self.assertEqual(db.read(KEY).version,31)
        self.assertTrue(db.read(KEY).value.endswith('new-authenticated-write'))
        self.assertFalse(any(w[0]==KEY for w in db.writes))

    def test_archive_name_collision_newer_revision_rejected(self):
        db=FakeStore(fixture());r=db.read(KEY)
        key=f'{KEY}.archive-auto-r{r.version}-{digest(r.value)[:12]}'
        db.data[key]=Record(key,r.value,2)
        with self.assertRaisesRegex(FailClosed,'ARCHIVE_WAS_MODIFIED'):rotate(db,KEY)
        self.assertEqual(db.read(KEY).version,30)

    def test_live_readback_corruption_fails_stop(self):
        db=FakeStore(fixture());db.readback_tamper=True
        with self.assertRaisesRegex(FailClosed,'LIVE_READBACK_MISMATCH_STOP'):rotate(db,KEY)
        self.assertEqual(len(db.writes),2)

    def test_large_uncompactable_unknown_current_field_rejected(self):
        original={
            'schema':'AI_BOT_UNIFIED_REPORT_V1','owner_task_id':'task',
            'source_runs':'a:run1','observed_snapshots':[{'component':'a','run_id':'run1'}],
            'summary':{'total':1},'report_archives':{},
            'giant_active_data':'',
        }
        before=json.dumps(original,ensure_ascii=False,separators=(',',':'))
        original['giant_active_data']='D'*(9600-utf16_units(before))
        raw=json.dumps(original,ensure_ascii=False,separators=(',',':'))
        self.assertEqual(utf16_units(raw),9600)
        db=FakeStore(raw)
        with self.assertRaisesRegex(FailClosed,'COMPACT_(NOT_BELOW_WARNING|EXCEEDS_HARD_LIMIT)'):
            rotate(db,KEY)
        self.assertEqual(db.read(KEY).version,30)
        self.assertFalse(any(w[0]==KEY for w in db.writes))

    def test_missing_old_archive_refs_preserved_if_present(self):
        db=FakeStore(fixture()); result=rotate(db,KEY)
        current=json.loads(db.read(KEY).value)
        self.assertTrue(all(k in current['report_archives'] for k in ('r30','r31')))
        self.assertEqual(current['history_archive']['key'],result['archive_key'])

    def test_utf16_emoji_counts_two(self):
        self.assertEqual(utf16_units('A😀B'),4)
        self.assertEqual(utf16_units('한글'),2)

    def test_incomplete_archive_cannot_enable_live_cas(self):
        db=FakeStore(fixture());db.drop_archive_read=True
        with self.assertRaises(FailClosed):rotate(db,KEY)
        self.assertFalse(any(key==KEY for key,_,_ in db.writes))

    def test_replay_existing_exact_archive_no_second_archive_write(self):
        db=FakeStore(fixture());r=db.read(KEY)
        ak=f'{KEY}.archive-auto-r{r.version}-{digest(r.value)[:12]}'
        db.data[ak]=Record(ak,r.value,1)
        result=rotate(db,KEY)
        self.assertEqual(result['archive_key'],ak)
        self.assertEqual(len(db.writes),1)
        self.assertEqual(db.writes[0][0],KEY)

    def test_source_updated_before_first_archive_write_fails_closed(self):
        db=FakeStore(fixture())
        before=db.read(KEY)
        # Simulate an authenticated competing source update between initial read
        # and archive preflight by injecting a stale reader.
        original_read=db.read
        count={'source_reads':0}
        def stale_read(key):
            if key==KEY:
                count['source_reads']+=1
                if count['source_reads']==2:
                    db.data[KEY]=Record(KEY,before.value+' new producer record',31)
            return original_read(key)
        db.read=stale_read
        with self.assertRaisesRegex(Conflict,'SOURCE_CHANGED'):rotate(db,KEY)
        self.assertFalse(db.writes)
        self.assertEqual(db.data[KEY].version,31)

    def test_existing_prior_history_pointer_retained(self):
        data=json.loads(fixture())
        data['history_archive']={'key':'project.old.archive','revision':1,'source_revision':28}
        db=FakeStore(json.dumps(data,ensure_ascii=False,separators=(',',':')))
        if utf16_units(db.read(KEY).value)>10000:
            self.skipTest('fixture exceeds hard max')
        rotate(db,KEY)
        current=json.loads(db.read(KEY).value)
        self.assertEqual(current.get('prior_history_archive'),data['history_archive'])

    def test_policy_threshold_immutable(self):
        db=FakeStore(fixture())
        with self.assertRaisesRegex(FailClosed,'POLICY_THRESHOLD_MISMATCH'):
            rotate(db,KEY,warning_at=9299)
        self.assertFalse(db.writes)

    def test_real_concurrent_eight_writers_only_one_live_cas_success(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Lock, Barrier, local
        class ConcurrentStore(FakeStore):
            def __init__(self,body):
                super().__init__(body)
                self.lock=Lock()
                self.barrier=Barrier(8)
                self.local=local()
            def read(self,key):
                with self.lock:
                    v=super().read(key)
                if key==KEY and not getattr(self.local,'initial',False):
                    self.local.initial=True
                    self.barrier.wait(timeout=4)
                return v
            def write(self,key,value,*,expected_version,request_id):
                with self.lock:
                    return super().write(key,value,expected_version=expected_version,request_id=request_id)
        original=fixture();db=ConcurrentStore(original)
        def run(_):
            try:return rotate(db,KEY)['status']
            except Conflict:return 'CONFLICT'
        with ThreadPoolExecutor(max_workers=8) as pool:
            result=list(pool.map(run,range(8)))
        self.assertEqual(result.count('PASS_ISOLATED'),1,result)
        self.assertEqual(result.count('CONFLICT'),7,result)
        self.assertEqual(db.data[KEY].version,31)
        self.assertEqual(sum(1 for k,_,_ in db.writes if k==KEY),1)
        archived=[v for k,v in db.data.items() if '.archive-auto-' in k]
        self.assertEqual(len(archived),1)
        self.assertEqual(archived[0].value,original)

    def test_r36_style_current_without_archive_links_flags_drift(self):
        old=json.loads(fixture(False))
        old.pop('report_archives')
        old.pop('cross_system_receipt_check')
        old.pop('traceability_audit')
        old.pop('developer_result_diagnostic')
        old['incremental_audit']={'observed_run_count':5}
        db=FakeStore(json.dumps(old,ensure_ascii=False,separators=(',',':')))
        out=rotate(db,KEY)
        self.assertEqual(out['status'],'NO_UPDATE')
        self.assertTrue(out['inspection']['archive_refs_missing'])
        self.assertEqual(out['inspection']['missing_required'],[])
        self.assertEqual(db.writes,[])

    def test_r36_style_grown_above_warning_blocks_without_archive_reference(self):
        old={
            'schema':'AI_BOT_UNIFIED_REPORT_V1',
            'owner_task_id':'6ae8db67fef081919af59fecbf162552',
            'source_runs':'run1|run2|run3|run4|run5',
            'observed_snapshots':[{'component':'coordinator','run_id':'run1'}],
            'summary':{'total':5,'enabled':5},
            'incremental_audit':{'large':''},
        }
        baseline=json.dumps(old,ensure_ascii=False,separators=(',',':'))
        old['incremental_audit']['large']='R'*(9500-utf16_units(baseline))
        body=json.dumps(old,ensure_ascii=False,separators=(',',':'))
        self.assertEqual(utf16_units(body),9500)
        db=FakeStore(body)
        with self.assertRaisesRegex(FailClosed,'SCHEMA_DRIFT_ARCHIVE_POINTERS_MISSING'):
            rotate(db,KEY)
        self.assertEqual(db.writes,[])

    def test_run_id_snapshot_and_source_reference_mismatch_blocks(self):
        obj=json.loads(fixture())
        obj['observed_snapshots'][0]['last_run_id']='different-run'
        db=FakeStore(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
        with self.assertRaisesRegex(FailClosed,'SOURCE_RUN_ID_MISMATCH'):
            rotate(db,KEY)
        self.assertEqual(db.writes,[])

    def test_summary_count_mismatch_blocks(self):
        obj=json.loads(fixture())
        obj['summary']['total']=99
        db=FakeStore(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
        with self.assertRaisesRegex(FailClosed,'SUMMARY_SNAPSHOT_COUNT_MISMATCH'):
            rotate(db,KEY)
        self.assertEqual(db.writes,[])

    def test_preserve_prior_archived_fields_in_next_rotation(self):
        obj=json.loads(fixture())
        obj['archived_fields']=['historical_gate','old_timeline']
        db=FakeStore(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
        rotate(db,KEY)
        compact=json.loads(db.read(KEY).value)
        self.assertIn('historical_gate',compact['archived_fields'])
        self.assertIn('old_timeline',compact['archived_fields'])
        self.assertIn('cross_system_receipt_check',compact['archived_fields'])


    def test_duplicate_component_with_distinct_run_ids_fails_closed(self):
        obj=json.loads(fixture());obj['observed_snapshots'][1]['component']='coordinator'
        obj['source_runs']='|'.join(
            f"{row['component']}:{row['last_run_id']}" for row in obj['observed_snapshots'])
        db=FakeStore(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
        with self.assertRaisesRegex(FailClosed,'DUPLICATE_OR_INVALID_COMPONENT'):
            rotate(db,KEY)
        self.assertEqual(db.writes,[])

    def test_conflicting_dual_run_ids_fails_closed(self):
        obj=json.loads(fixture());obj['observed_snapshots'][1]['run_id']='different-run'
        db=FakeStore(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
        with self.assertRaisesRegex(FailClosed,'CONFLICTING_SNAPSHOT_RUN_IDS'):
            rotate(db,KEY)
        self.assertEqual(db.writes,[])

if __name__=='__main__':unittest.main(verbosity=2)

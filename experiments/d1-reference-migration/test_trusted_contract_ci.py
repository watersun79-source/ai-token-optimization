"""Small CI gate for the isolated signed-evidence and recovery contract (no D1 I/O)."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import hmac
import json
from pathlib import Path
import tempfile
import unittest

from guard import Conflict, FailClosed
from migration import REPORT_KEY, plan_migration
from test_migration import make_store, ev
from trusted_adapter import (SealedReceipt, TrustedAdapter, FileRecoveryJournal,
                             canonical, receipt_payload, prepare, apply, recover)

TEST_KEY = b'only-a-synthetic-cryptographic-test-key-without-access'
TEST_JOURNAL = b'only-a-synthetic-journal-authentication-key-no-access'
ISSUER, AUDIENCE = 'synthetic-test-authority', 'offline-test-consumer'


class FixtureSignedBackend:
    def __init__(self):
        self.db = make_store()
        self.fail_after_commit = False
        self.bad_mac = False
        self.fake_nonce = False

    def seal(self, evidence, kind, nonce, request_id='', expected_version=None):
        if evidence is None:
            return None
        challenge = '0'*32 if self.fake_nonce else nonce
        token = SealedReceipt(evidence,kind,challenge,ISSUER,AUDIENCE,'',request_id,expected_version)
        mac = hmac.new(TEST_KEY,canonical(receipt_payload(token)),sha256).hexdigest()
        return replace(token,mac='0'*64 if self.bad_mac else mac)

    def read_signed(self,key,nonce):
        return self.seal(self.db.read(key),'read',nonce)

    def history_signed(self,key,revision,nonce):
        return self.seal(self.db.history_at(key,revision),'history',nonce)

    def write_signed(self,key,value,*,expected_version,request_id,nonce):
        evidence=self.db.write(key,value,expected_version=expected_version,request_id=request_id)
        if self.fail_after_commit:
            raise OSError('SYNTHETIC_LOST_ACK')
        return self.seal(evidence,'write',nonce,request_id,expected_version)


class TrustedContractCITests(unittest.TestCase):
    def setUp(self):
        self.backend=FixtureSignedBackend()
        self.client=TrustedAdapter(self.backend,authority=ISSUER,audience=AUDIENCE,
                                   verification_key=TEST_KEY,allow_isolated_writes=True)
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal=FileRecoveryJournal(Path(self.temp.name),signing_key=TEST_JOURNAL)

    def test_authentic_history_is_read_only(self):
        plan=plan_migration(self.client)
        self.assertEqual(plan['status'],'READY_OFFLINE')
        self.assertEqual(self.backend.db.writes,[])

    def test_rejected_forged_mac(self):
        self.backend.bad_mac=True
        with self.assertRaisesRegex(FailClosed,'UNAUTHENTICATED_RECEIPT'):
            plan_migration(self.client)

    def test_rejected_replayed_challenge(self):
        self.backend.fake_nonce=True
        with self.assertRaisesRegex(FailClosed,'RECEIPT_CONTEXT_MISMATCH'):
            plan_migration(self.client)

    def test_wrong_verification_key_rejected(self):
        wrong=TrustedAdapter(self.backend,authority=ISSUER,audience=AUDIENCE,
                             verification_key=b'wrong-synthetic-verifier-key-without-access')
        with self.assertRaisesRegex(FailClosed,'UNAUTHENTICATED_RECEIPT'):
            wrong.read(REPORT_KEY)

    def test_readonly_default_cannot_write(self):
        reader=TrustedAdapter(self.backend,authority=ISSUER,audience=AUDIENCE,
                              verification_key=TEST_KEY)
        with self.assertRaisesRegex(FailClosed,'ISOLATED_WRITE_DENIED'):
            reader.write(REPORT_KEY,'{}',expected_version=37,request_id='isolated-test')

    def test_journal_precedes_any_live_write(self):
        ticket,path=prepare(self.client,self.journal)
        self.assertEqual(self.journal.load(path),ticket)
        self.assertEqual(self.backend.db.writes,[])

    def test_exact_cas_rollback_and_readback(self):
        original=self.backend.db.read(REPORT_KEY)
        _,path=prepare(self.client,self.journal)
        self.assertEqual(apply(self.client,self.journal,path)['status'],'APPLIED_OFFLINE')
        self.assertEqual(recover(self.client,self.journal,path)['status'],'RESTORED_EXACT_OFFLINE')
        final=self.client.read(REPORT_KEY)
        self.assertEqual(final.value,original.value)
        self.assertEqual(final.version,original.version+2)

    def test_write_ack_lost_after_commit_recoverable(self):
        _,path=prepare(self.client,self.journal)
        self.backend.fail_after_commit=True
        with self.assertRaises(OSError):apply(self.client,self.journal,path)
        self.backend.fail_after_commit=False
        self.assertEqual(recover(self.client,self.journal,path)['status'],'RESTORED_EXACT_OFFLINE')

    def test_original_unchanged_before_commit(self):
        _,path=prepare(self.client,self.journal)
        self.assertEqual(recover(self.client,self.journal,path)['status'],'NO_WRITE_OCCURRED')

    def test_rollback_must_not_clobber_foreign_write(self):
        _,path=prepare(self.client,self.journal)
        apply(self.client,self.journal,path)
        self.backend.db.data[REPORT_KEY]=ev(REPORT_KEY,'another-writer',39)
        with self.assertRaises(Conflict):recover(self.client,self.journal,path)
        self.assertEqual(self.backend.db.read(REPORT_KEY).value,'another-writer')

    def test_tampered_ticket_rejected_without_write(self):
        _,path=prepare(self.client,self.journal)
        obj=json.loads(path.read_text())
        obj['source_value']='forged'
        path.write_text(json.dumps(obj))
        with self.assertRaisesRegex(FailClosed,'ROLLBACK_TICKET_TAMPERED'):
            recover(self.client,self.journal,path)
        self.assertEqual(self.backend.db.writes,[])

    def test_parallel_cas_one_winner(self):
        _,path=prepare(self.client,self.journal)
        def worker(_):
            try:
                return apply(self.client,self.journal,path)['status']
            except Conflict:
                return 'CONFLICT'
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(worker,range(8)))
        self.assertEqual(results.count('APPLIED_OFFLINE'),1)
        self.assertEqual(len(self.backend.db.writes),1)


if __name__=='__main__':unittest.main()

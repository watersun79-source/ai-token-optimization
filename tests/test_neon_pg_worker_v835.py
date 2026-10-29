"""v8.3.5 SQL-parameter-bound worker regression (no real secrets/connection)."""
import unittest
from tools.neon_pg_worker_v835 import VERSION, enqueue, is_synthetic_job, run_once, summary


class FakeDb:
    """DB-API stand-in. The actual Neon SQL functions are tested separately."""
    def __init__(self):
        self.jobs = {}
        self.sequence = 0
        self.executed = []
    def __call__(self, url):
        if url != "postgresql://fake/test":
            raise ValueError("UNEXPECTED_URL")
        return FakeSession(self)


class FakeSession:
    description = object()
    def __init__(self, db):
        self.db = db
        self.rows = []
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def cursor(self):
        return self
    def execute(self, sql, params=()):
        self.db.executed.append((sql,params))
        if "INSERT INTO" in sql:
            job_id = params[0]
            is_new = job_id not in self.db.jobs
            if is_new:
                self.db.jobs[job_id] = ["QUEUED",0,None,None]
            self.rows = [(job_id,)] if is_new else []
        elif "ai_v835_claim_synthetic" in sql:
            claimed = next(((k,v) for k,v in self.db.jobs.items() if v[0]=="QUEUED"),None)
            if claimed is None:
                self.rows = []
            else:
                key,data=claimed
                self.db.sequence+=1
                data[:]=["CLAIMED",data[1]+1,params[0],"synthetic-token-"+str(self.db.sequence)]
                self.rows = [(key,data[1],params[0],data[3],None)]
        elif "ai_v835_complete_synthetic" in sql:
            key,owner,token,ok=params
            data=self.db.jobs[key]
            if data[0]!="CLAIMED" or data[2]!=owner or data[3]!=token:
                self.rows=[]
            else:
                data[0]="SUCCEEDED" if ok else "DEAD"
                self.rows=[(key,data[0],data[1],"SYNTHETIC_OK")]
        elif "SELECT state,count(*)" in sql:
            counts = {}
            for state,*_ in self.db.jobs.values():
                counts[state]=counts.get(state,0)+1
            self.rows=list(counts.items())
        else:
            raise AssertionError("SQL_OUT_OF_SCOPE")
    def fetchall(self):
        return self.rows


class WorkerV835Tests(unittest.TestCase):
    url="postgresql://fake/test"

    def test_version_and_scope(self):
        self.assertEqual(VERSION,"8.3.5")
        self.assertTrue(is_synthetic_job("synthetic-v83-example"))
        self.assertFalse(is_synthetic_job("real-user-job"))

    def test_submit_run_and_persist(self):
        db=FakeDb()
        self.assertTrue(enqueue(self.url,"synthetic-v83-unit",factory=db))
        result=run_once(self.url,worker="test-worker",factory=db)
        self.assertEqual(result["claimed"],1)
        self.assertEqual(result["succeeded"],1)
        self.assertFalse(result["always_on_verified"])
        self.assertEqual(summary(self.url,factory=db),{"SUCCEEDED":1})

    def test_duplicate_job_no_second_execution(self):
        db=FakeDb()
        self.assertTrue(enqueue(self.url,"synthetic-v83-duplicate",factory=db))
        self.assertFalse(enqueue(self.url,"synthetic-v83-duplicate",factory=db))
        self.assertEqual(run_once(self.url,factory=db)["succeeded"],1)
        self.assertEqual(run_once(self.url,factory=db)["claimed"],0)

    def test_all_database_values_are_parameter_bound(self):
        db=FakeDb()
        enqueue(self.url,"synthetic-v83-bound",factory=db)
        run_once(self.url,worker="safe-worker",factory=db)
        self.assertTrue(all("%s" in sql for sql,params in db.executed
                            if params))
        self.assertTrue(all("safe-worker" not in sql and
                            "synthetic-v83-bound" not in sql for sql,_ in db.executed))

    def test_bounded_two_job_parallel_batch(self):
        db=FakeDb()
        for i in range(3):
            enqueue(self.url,"synthetic-v83-multi-"+str(i),factory=db)
        result=run_once(self.url,limit=2,concurrency=2,factory=db)
        self.assertEqual(result["succeeded"],2)
        self.assertEqual(summary(self.url,factory=db),{"SUCCEEDED":2,"QUEUED":1})

    def test_unsafe_job_rejected_without_sql(self):
        db=FakeDb()
        with self.assertRaisesRegex(ValueError,"UNSAFE_JOB_ID"):
            enqueue(self.url,"admin-work",factory=db)
        self.assertFalse(db.executed)

    def test_fails_closed_on_invalid_settings(self):
        db=FakeDb()
        for options in ({"limit":100},{"concurrency":0},{"worker":"../../bad"},
                        {"worker":"x"*90},{"limit":True}):
            with self.assertRaises(ValueError):
                run_once(self.url,factory=db,**options)
        with self.assertRaisesRegex(ValueError,"DATABASE_NOT_CONFIGURED"):
            run_once("")
        self.assertFalse(db.executed)

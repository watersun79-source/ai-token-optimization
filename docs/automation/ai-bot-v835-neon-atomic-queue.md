# AI BOT v8.3.5 · Neon atomic lease and isolated HTTP gateway

## Verified in live Neon
- Free Neon project `autumn-frog-53985417`, Singapore `aibot_isolated`, synthetic-only table `public.isolated_synthetic_jobs_v834`. **Do not write any password, token or URL into this repository.**
- `sql/ai_v835_neon_atomic_queue.sql` is deployed as 3 `SECURITY INVOKER` PostgreSQL functions. Atomic claim uses `FOR UPDATE SKIP LOCKED`, attempts limit 5, 30–900s lease and fresh UUID token; completion requires correct owner/token AND unexpired lease. Exhausted expired attempts can be marked DEAD.
- Live Neon test synthetic task `synthetic-v83-neonv835-fence-20261030`: 2 simultaneous workers, 1 claimed and 1 empty; after a **simulated expired lease timestamp** new owner recovered attempt 2; previous owner's completion was rejected 0 rows; new owner completed SUCCEEDED attempt 2, result SYNTHETIC_OK persisted and read back.
- `tools/neon_pg_worker_v835.py`: bounded parallel one-shot CPU-only synthetic worker backed by the same Neon table and functions. Actual DB-API driver `psycopg[binary]==3.3.6` required in hosted environment.
- `tools/isolated_neon_gateway_v835.py`: HTTP endpoints GET healthz, GET private/state, POST private/submit, POST private/recover. Requires both a 32+ character header secret `ISOLATED_JOB_KEY` and `NEON_QUEUE_DATABASE_URL`. **No cron/polling**. If missing, refuses all private work.

## Security and unresolved limitations
- Do not reuse a Neon owner/admin connection string for public Render gateway. Create a dedicated minimally privileged database role for the single synthetic table and three functions; secret must only flow through connected tool invocation into Render service env. Never print connection strings or tokens.
- A user request and Free plan do not by themselves establish zero unexpected Render build/bandwidth overage; verify usage limits/spend guard before deploying or triggering traffic.
- The production Render v8.3.4 gateway is unchanged, has no Neon credentials, and stays fail closed. v8.3.5 is a **draft isolated branch**, not merged.
- The Free Render host sleeps after 15 minutes idle and cannot be certified as a continuously running 24-hour worker. Neon Free Postgres persists data but compute scales to zero and may suspend at quota.
- An end-to-end **real Render crash → automatic resume → same job completes** has NOT been observed; local SQL lease expiration simulation is a different kind of evidence.
- Activepieces Tables has no proven atomic claim and is not joined with Neon queue.

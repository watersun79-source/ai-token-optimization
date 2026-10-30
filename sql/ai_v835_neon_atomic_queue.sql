-- AI BOT v8.3.5: synthetic-only, transactional Neon PostgreSQL queue.
-- Owner-run only until a separately approved least-privilege application role exists.
-- Existing work remains untouched; functions are additive and SECURITY INVOKER.
-- The queue never calls external AI, Slack, GitHub or Render.
CREATE OR REPLACE FUNCTION public.ai_v835_claim_synthetic(
  p_worker text, p_lease_seconds integer DEFAULT 90
)
RETURNS TABLE (task_id text, attempt integer, lease_owner text, lease_token uuid, lease_until timestamptz)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public
AS $ai$
BEGIN
  IF p_worker IS NULL OR p_worker !~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$'
     OR p_lease_seconds IS NULL OR p_lease_seconds < 30 OR p_lease_seconds > 900 THEN
    RAISE EXCEPTION 'INVALID_LEASE_INPUT' USING ERRCODE = '22023';
  END IF;
  RETURN QUERY
  WITH next_job AS (
    SELECT j.task_id
    FROM public.isolated_synthetic_jobs_v834 AS j
    WHERE (j.state = 'QUEUED'
       OR (j.state = 'CLAIMED' AND j.lease_until < clock_timestamp()))
      AND j.attempt < 5
    ORDER BY j.created_at, j.task_id
    FOR UPDATE SKIP LOCKED
    LIMIT 1
  )
  UPDATE public.isolated_synthetic_jobs_v834 AS j
  SET state='CLAIMED', attempt=j.attempt+1, lease_owner=p_worker,
      lease_token=gen_random_uuid(),
      lease_until=clock_timestamp() + make_interval(secs => p_lease_seconds),
      updated_at=clock_timestamp(), result_code='NOT_STARTED'
  FROM next_job AS n
  WHERE j.task_id=n.task_id
  RETURNING j.task_id, j.attempt, j.lease_owner, j.lease_token, j.lease_until;
END
$ai$;

CREATE OR REPLACE FUNCTION public.ai_v835_complete_synthetic(
  p_task_id text, p_worker text, p_lease_token uuid, p_success boolean
)
RETURNS TABLE (task_id text, state text, attempt integer, result_code text)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public
AS $ai$
BEGIN
  IF p_task_id IS NULL OR p_task_id !~ '^synthetic-v83-[a-z0-9-]{1,52}$'
     OR p_worker IS NULL OR p_worker !~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$'
     OR p_lease_token IS NULL OR p_success IS NULL THEN
    RAISE EXCEPTION 'INVALID_COMPLETION_INPUT' USING ERRCODE = '22023';
  END IF;
  RETURN QUERY
  UPDATE public.isolated_synthetic_jobs_v834 AS j
  SET state = CASE WHEN p_success THEN 'SUCCEEDED' ELSE 'DEAD' END,
      result_code = CASE WHEN p_success THEN 'SYNTHETIC_OK' ELSE 'SYNTHETIC_FAILED' END,
      lease_owner = NULL, lease_token = NULL, lease_until = NULL,
      updated_at = clock_timestamp()
  WHERE j.task_id=p_task_id AND j.state='CLAIMED'
    AND j.lease_owner=p_worker AND j.lease_token=p_lease_token
    AND j.lease_until>clock_timestamp()
  RETURNING j.task_id, j.state, j.attempt, j.result_code;
END
$ai$;

CREATE OR REPLACE FUNCTION public.ai_v835_reap_exhausted()
RETURNS integer
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public
AS $ai$
DECLARE count_updated integer;
BEGIN
  UPDATE public.isolated_synthetic_jobs_v834 AS j
  SET state='DEAD', lease_owner=NULL, lease_token=NULL, lease_until=NULL,
      result_code='MAX_ATTEMPTS_EXHAUSTED', updated_at=clock_timestamp()
  WHERE j.state='CLAIMED' AND j.attempt >= 5
    AND j.lease_until < clock_timestamp();
  GET DIAGNOSTICS count_updated = ROW_COUNT;
  RETURN count_updated;
END
$ai$;

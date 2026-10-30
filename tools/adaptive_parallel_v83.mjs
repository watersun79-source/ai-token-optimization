/** AI BOT v8.3.0 - in-process bounded event-driven parallel executor.
 * NO hosting, remote transport, paid models, persistent state or side effects.
 * A trusted read-only handler must be explicitly injected by the caller. */
export const PARALLEL_VERSION = "8.3.0";
const ID = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,79}$/;
const KINDS = new Set(["offline_check", "read_only"]);
const ERROR_CODES = new Set(["RATE_LIMIT","TEMPORARY","TIMEOUT","WORKER_FAILURE"]);
const int = (x, fallback, lo, hi) =>
  Number.isSafeInteger(x) && x >= lo && x <= hi ? x : fallback;

export function createAdaptiveParallelEngine(options = {}) {
  if (typeof options.handler !== "function") throw new TypeError("TRUSTED_HANDLER_REQUIRED");
  const handler = options.handler;
  const min = int(options.minConcurrency, 1, 1, 16);
  const max = int(options.maxConcurrency, 8, min, 16);
  let concurrency = int(options.initialConcurrency, Math.min(2,max), min,max);
  const capacity = int(options.capacity, 64, 1, 1024);
  const retries = int(options.maxRetries, 1, 0, 2);
  const retention = int(options.historyLimit, 256, 1, 4096);
  const clock = typeof options.clock === "function" ? options.clock : () => Date.now();
  const onEvent = typeof options.onEvent === "function" ? options.onEvent : null;
  const queue = [], records = new Map(), history = [], idleWaiters = [];
  const stats = { accepted:0, succeeded:0, failed:0, cancelled:0,
    duplicates:0, rejected:0, attempts:0, peakActive:0, peakQueue:0 };
  let active=0, closed=false, scheduled=false, sample=[];
  const snapshot = () => Object.freeze({ version:PARALLEL_VERSION, active,
    queued:queue.length, concurrency, maxConcurrency:max, closed,
    productionConnected:false, durable:false, ...stats });
  function emit(type,fields={}) {
    if (!onEvent) return;
    try { onEvent(Object.freeze({type,time:clock(),active,queued:queue.length,
      concurrency,...fields})); } catch { /* noncritical observability */ }
  }
  function idle() {
    if (active || queue.length) return;
    for (const resolve of idleWaiters.splice(0)) resolve(snapshot());
  }
  function settle(entry,status,extras={}) {
    stats[status==="SUCCEEDED"?"succeeded":status==="FAILED"?"failed":"cancelled"]++;
    entry.resolve(Object.freeze({id:entry.task.id,status,attempts:entry.attempts,...extras}));
    history.push(entry.task.id);
    while (history.length > retention) records.delete(history.shift());
    emit("task_complete",{id:entry.task.id,status,attempts:entry.attempts});
  }
  function tune(ok) {
    sample.push(ok);
    if (sample.length < 4) return;
    const failures=sample.filter(x=>!x).length; sample=[];
    const old=concurrency;
    if (failures>=2) concurrency=Math.max(min,Math.floor(concurrency/2));
    else if (!failures && queue.length) concurrency=Math.min(max,concurrency+1);
    if(old!==concurrency) emit("concurrency_changed",{from:old,to:concurrency});
  }
  function pump() {
    while(active<concurrency && queue.length) {
      const entry=queue.shift();
      active++; entry.attempts++; stats.attempts++;
      stats.peakActive=Math.max(stats.peakActive,active);
      emit("task_started",{id:entry.task.id,attempt:entry.attempts});
      Promise.resolve().then(()=>handler(entry.task,Object.freeze({
        attempt:entry.attempts,readonly:true
      }))).then(value=>{
        active--;
        settle(entry,"SUCCEEDED",{value});
        tune(true); pump(); idle();
      },err=>{
        active--;
        const errorCode=ERROR_CODES.has(err?.code)?err.code:"WORKER_FAILURE";
        if(err?.retryable===true && entry.attempts<=retries && !closed) {
          queue.push(entry);
          stats.peakQueue=Math.max(stats.peakQueue,queue.length);
          emit("task_retry",{id:entry.task.id,errorCode,attempt:entry.attempts});
        } else {
          settle(entry,"FAILED",{errorCode});
          tune(false);
        }
        pump(); idle();
      });
    }
    idle();
  }
  function enqueue(task) {
    if (closed) return Promise.reject(new Error("ENGINE_CLOSED"));
    if (!task || typeof task!=="object" || !ID.test(task.id||"") ||
        !KINDS.has(task.kind) || task.execute!==undefined) {
      stats.rejected++;
      return Promise.reject(new Error("UNSAFE_OR_INVALID_TASK"));
    }
    const existing=records.get(task.id);
    if (existing) { stats.duplicates++; return existing.promise; }
    if (active+queue.length>=capacity) {
      stats.rejected++; emit("backpressure",{id:task.id});
      return Promise.reject(new Error("QUEUE_CAPACITY_EXCEEDED"));
    }
    const entry={task:Object.freeze({...task}),attempts:0};
    const promise=new Promise(resolve=>{entry.resolve=resolve});
    entry.promise=promise; records.set(task.id,entry); queue.push(entry);
    stats.accepted++; stats.peakQueue=Math.max(stats.peakQueue,queue.length);
    emit("task_accepted",{id:task.id,kind:task.kind});
    if(!scheduled) {
      scheduled=true;
      Promise.resolve().then(()=>{scheduled=false;pump()});
    }
    return promise;
  }
  const whenIdle=()=>active===0 && !queue.length ?
    Promise.resolve(snapshot()) : new Promise(resolve=>idleWaiters.push(resolve));
  function close() {
    if(closed) return;
    closed=true;
    while(queue.length) settle(queue.shift(),"CANCELLED");
    emit("closed");idle();
  }
  return Object.freeze({enqueue,whenIdle,snapshot,close});
}

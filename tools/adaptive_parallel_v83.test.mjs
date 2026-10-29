import test from "node:test";
import assert from "node:assert/strict";
import {PARALLEL_VERSION,createAdaptiveParallelEngine} from "./adaptive_parallel_v83.mjs";
const task=(id,kind="offline_check")=>({id,kind,payload:id});
function gate(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}
test("version and explicitly offline executor",()=>{
  const e=createAdaptiveParallelEngine({handler:x=>x.id});
  assert.equal(PARALLEL_VERSION,"8.3.0");
  assert.equal(e.snapshot().productionConnected,false);
  assert.equal(e.snapshot().durable,false);e.close();
});
test("trusted handler, kinds and task source restrictions",async()=>{
  assert.throws(()=>createAdaptiveParallelEngine(),/TRUSTED_HANDLER_REQUIRED/);
  const e=createAdaptiveParallelEngine({handler:x=>x.id});
  await assert.rejects(e.enqueue(task("../oops")),/UNSAFE_OR_INVALID_TASK/);
  await assert.rejects(e.enqueue(task("bill","paid_model")),/UNSAFE_OR_INVALID_TASK/);
  await assert.rejects(e.enqueue({id:"code",kind:"read_only",execute:()=>1}),/UNSAFE_OR_INVALID_TASK/);
});
test("real async overlap with hard cap and result join",async()=>{
  const gates=[gate(),gate(),gate(),gate()];
  let started=0,inside=0,peak=0;
  const e=createAdaptiveParallelEngine({initialConcurrency:2,maxConcurrency:2,
    handler:async()=>{
      const idx=started++;inside++;peak=Math.max(inside,peak);
      await gates[idx].promise;inside--;return idx;
    }});
  const r=[0,1,2,3].map(i=>e.enqueue(task("overlap-"+i)));
  await new Promise(done=>setImmediate(done));
  assert.equal(started,2);assert.equal(peak,2);
  gates[0].resolve();gates[1].resolve();
  await new Promise(done=>setImmediate(done));
  assert.equal(started,4);
  gates[2].resolve();gates[3].resolve();
  assert.deepEqual((await Promise.all(r)).map(x=>x.status),Array(4).fill("SUCCEEDED"));
  assert.equal(e.snapshot().peakActive,2);
});
test("duplicate request id joins same promise, no second execution",async()=>{
  let hits=0;const e=createAdaptiveParallelEngine({handler:()=>++hits});
  const a=e.enqueue(task("same")),b=e.enqueue(task("same"));
  assert.strictEqual(a,b);assert.equal((await b).value,1);assert.equal(hits,1);
  assert.equal(e.snapshot().duplicates,1);
});
test("read-only idempotent retry succeeds at second bounded attempt",async()=>{
  const e=createAdaptiveParallelEngine({maxRetries:1,handler:async(_t,c)=>{
    if(c.attempt===1)throw Object.assign(new Error("secret"),{retryable:true,code:"TEMPORARY"});
    return "ok";
  }});
  const r=await e.enqueue(task("transient","read_only"));
  assert.equal(r.status,"SUCCEEDED");assert.equal(r.attempts,2);
});
test("nonretryable failure never exposes exception content",async()=>{
  const events=[];
  const e=createAdaptiveParallelEngine({handler:()=>{throw new Error("TOKEN_SECRET_PRIVATE")},onEvent:x=>events.push(x)});
  const r=await e.enqueue(task("no-token"));
  assert.equal(r.status,"FAILED");assert.equal(r.errorCode,"WORKER_FAILURE");
  assert.doesNotMatch(JSON.stringify({r,events}),/TOKEN_SECRET_PRIVATE/);
});
test("capacity rejects third outstanding work, close drains queued",async()=>{
  const blocker=gate();const e=createAdaptiveParallelEngine({
    handler:()=>blocker.promise,capacity:2,initialConcurrency:1,maxConcurrency:1
  });
  const a=e.enqueue(task("a")),b=e.enqueue(task("b"));
  await assert.rejects(e.enqueue(task("c")),/QUEUE_CAPACITY_EXCEEDED/);
  await new Promise(done=>setImmediate(done));
  e.close();blocker.resolve(2);
  assert.equal((await a).status,"SUCCEEDED");
  assert.equal((await b).status,"CANCELLED");
  assert.equal(e.snapshot().rejected,1);
});
test("close before dispatch safely cancels accepted request",async()=>{
  const e=createAdaptiveParallelEngine({handler:t=>t.id});
  const p=e.enqueue(task("queued"));e.close();
  assert.equal((await p).status,"CANCELLED");
  await assert.rejects(e.enqueue(task("late")),/ENGINE_CLOSED/);
});
test("adaptive concurrency grows with backed-up clean work",async()=>{
  const e=createAdaptiveParallelEngine({handler:x=>x.id,initialConcurrency:1,maxConcurrency:4});
  const r=await Promise.all(Array.from({length:12},(_,i)=>e.enqueue(task("grow-"+i))));
  assert.equal(r.length,12);assert.ok(e.snapshot().concurrency>1);
  assert.ok(e.snapshot().peakActive<=4);
});
test("adaptive concurrency shrinks after repeated failures",async()=>{
  const e=createAdaptiveParallelEngine({handler:()=>Promise.reject(new Error("x")),
    initialConcurrency:4,maxConcurrency:4,minConcurrency:1});
  await Promise.all(Array.from({length:8},(_,i)=>e.enqueue(task("fail-"+i))));
  assert.equal(e.snapshot().concurrency,1);
});
test("whenIdle resolves only after outstanding promises settle",async()=>{
  const blocker=gate();const e=createAdaptiveParallelEngine({handler:()=>blocker.promise});
  const r=e.enqueue(task("slow")),idle=e.whenIdle();
  blocker.resolve("finished");
  assert.equal((await r).value,"finished");
  assert.equal((await idle).active,0);
});
test("monitoring callback failure cannot stop work",async()=>{
  const e=createAdaptiveParallelEngine({handler:x=>x.id,onEvent:()=>{throw Error("monitor")}});
  assert.equal((await e.enqueue(task("mon"))).status,"SUCCEEDED");
});
test("unbounded settings collapse to safe finite defaults",async()=>{
  const e=createAdaptiveParallelEngine({handler:x=>x.id,maxConcurrency:999,capacity:999999,initialConcurrency:999});
  assert.equal(e.snapshot().maxConcurrency,8);assert.equal(e.snapshot().concurrency,2);
  assert.equal((await e.enqueue(task("bounded"))).status,"SUCCEEDED");
});
test("in-memory dedup retention is bounded rather than durable",async()=>{
  const e=createAdaptiveParallelEngine({handler:x=>x.id,historyLimit:2});
  await Promise.all(["a","b","c"].map(x=>e.enqueue(task(x))));
  assert.equal((await e.enqueue(task("a"))).status,"SUCCEEDED");
  assert.equal(e.snapshot().accepted,4);
});

/** New-only offline adversarial tests. No connector import/network/previous 6/6 replay. */
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const src=readFileSync(new URL('./inhost_readonly_bundle_DISABLED.mjs',import.meta.url),'utf8');
const sha=s=>createHash('sha256').update(s).digest('hex');
assert.equal(sha(src),'3bd27cd054745c802d85cf38f6f3e0b199d621199f54b56de4dde09ac57d715b');
assert.equal(src.split('enabled: false').length,2);
const ID='6ae8db67fef081919af59fecbf162552';
const RUN='749bfbc9-73b8-8324-808c-5e3bf7d0592b';
const EVENT='github.pr30.1605ec459634f37cf5c30d7c3eba8b0ff5e8757de609e90326481e652e58fa33';
const SHA17='d573de1ee07d1fa68924728e6c549d4ade44d1e8a995c3a6b09d4d75b82c6dd5';
const SHA18='e530a6361e8ce3657a9f270c56840018def83e14798e5b55427634c9ab6dc7a9';
const CANARY='CANARY_SHOULD_NOT_LEAK';
function makePeek(){
 const last={id:RUN,recorded_status:'completed',scheduled_for:'2026-11-17T01:00:00Z',started_at:'2026-11-17T01:03:37Z',completed_at:'2026-11-17T01:04:19Z'};
 const latest={run_id:RUN,scheduled_for:last.scheduled_for,created_at:'2026-11-17T01:04:18Z',completed_at:last.completed_at,content_text:'',content_truncated:false,requires_user_action:false,is_failure_message:false};
 return {automations:[{id:ID,is_enabled:true,default_timezone:'Asia/Seoul',timing_mode:'exact_schedule',run_details:{last_run:last,latest_result:latest}}]};
}
function makeD1(){return {found:true,receipt_status:'PASS',record_version:17,record:{updated_at:'2026-11-16T21:30:42.987Z',content_sha:SHA17,value:JSON.stringify({latest_evolution_cycle:{event_key:EVENT,observed_at:'2026-11-15T06:57:30.992Z',observation:{head_sha:'b6247c697157126c381feab9abfd0799b25a1571',security_run_id:43679644021,security_conclusion:'success'}},secret:CANARY})}};}
async function run({p=makePeek(),d=makeD1(),active=true,throwPeek=null,repeat=1}={}){
 const reads={peek:0,d1:0,get:0,other:0},out=[];
 const tools=new Proxy({mcp__Automations__peek:async a=>{reads.peek++;assert.equal(a.jawbone_id,ID);if(throwPeek)throw throwPeek;return p;},mcp__AI_________memory_read:async a=>{reads.d1++;assert.deepEqual(JSON.parse(JSON.stringify(a)),{key:'automation.evolving-ai.github-toolkit',history:false});return d;}},{get(o,k){reads.get++;if(!(k in o)){reads.other++;throw Error('UNEXPECTED_TOOL');}return o[k];}});
 for(let i=0;i<repeat;i++){
  const context={tools,text:x=>out.push(x)};
  const code=active?src.replace('enabled: false','enabled: true'):src;
  await vm.runInNewContext('(async()=>{\n'+code+'\n})()',context,{timeout:3000});
 }
 assert.equal(out.length,repeat);
 assert.ok(reads.peek<=repeat&&reads.d1<=repeat&&!reads.other);
 const results=out.map(s=>{
  assert.ok(s.startsWith('IN_HOST_READONLY '));
  assert.ok(!s.includes(CANARY)&&!s.includes('ghp_NOT_REAL'));
  const r=JSON.parse(s.slice(17));
  assert.equal(r.verdict.auth,'AUTH_UNVERIFIED');
  assert.equal(r.verdict.remote_write,'NO_WRITE');
  return r;
 });
 return {results,reads};
}
const cases=[
 ['repeated import-style evaluation stays disabled without ANY tool property probes',x=>{x.active=false;x.repeat=2;},'BLOCKED',null,[0,0,0]],
 ['failed scheduled run never triggers memory',x=>{x.p.automations[0].run_details.last_run.recorded_status='failed';},'UNVERIFIED',null,[1,0]],
 ['older completed slot never triggers memory',x=>{const y=x.p.automations[0].run_details;y.last_run.scheduled_for='2026-11-16T20:00:00Z';y.latest_result.scheduled_for=y.last_run.scheduled_for;},'NO_UPDATE',null,[1,0]],
 ['requires_user_action blocks before memory',x=>{x.p.automations[0].run_details.latest_result.requires_user_action=true;},'BLOCKED','PEEK_RESULT_INCOMPLETE_OR_ACTION_REQUIRED',[1,0]],
 ['failure_message blocks before memory',x=>{x.p.automations[0].run_details.latest_result.is_failure_message=true;},'BLOCKED','PEEK_RESULT_INCOMPLETE_OR_ACTION_REQUIRED',[1,0]],
 ['run/result ID mismatch blocks before memory',x=>{x.p.automations[0].run_details.latest_result.run_id='6e6c80b6-67f4-832f-86fe-2e47207a4075';},'BLOCKED','RUN_RESULT_ID_MISMATCH',[1,0]],
 ['official error envelope cannot cause D1 or retry',x=>{x.p={status:'ERROR',error_code:'stale_actor_biscuit',automations:null};},'BLOCKED','PEEK_ERROR_STALE_ACTOR_BISCUIT',[1,0]],
 ['exception containing token canary cannot be leaked or retried',x=>{x.throwPeek=new Error('ghp_NOT_REAL '+CANARY);},'BLOCKED','HOST_READ_OR_VALIDATION_FAILED',[1,0]],
 ['D1 revision rollback fail closes',x=>{x.d.record_version=16;},'BLOCKED','D1_REVISION_ROLLBACK',[1,1]],
 ['D1 receipt conflict fail closes',x=>{x.d.mcp_receipt={status:'FAIL'};},'BLOCKED','D1_RECEIPT_STATUS_CONFLICT',[1,1]],
 ['CURRENT 403 with stale PASS and canary must report error only',x=>{x.p.automations[0].run_details.latest_result.content_text='**BLOCKED GITHUB_HTTP_403** '+CANARY+'\nprevious **PASS** ghp_NOT_REAL';},'ERROR_REPORTED','GITHUB_HTTP_403_REPORTED_NO_D1_WRITE',[1,1]],
 ['same D1 revision with altered content SHA now blocks, not NO_UPDATE',x=>{x.d.record.content_sha=SHA18;},'BLOCKED','D1_CONTENT_SHA_CHANGED_SAME_REVISION',[1,1]]
];
for(const [title,mutate,status,reason,counts] of cases){
 test(title,async()=>{
  const args={p:makePeek(),d:makeD1(),active:true,repeat:1};mutate(args);
  const r=await run(args),v=r.results[0];
  assert.equal(v.verdict.status,status);
  if(reason)assert.equal(v.verdict.reason,reason);
  assert.deepEqual([r.reads.peek,r.reads.d1],counts.slice(0,2));
  if(counts.length===3)assert.equal(r.reads.get,counts[2]);
  if(title.includes('CURRENT 403')){assert.equal(v.normalized.audit.reported_git_access,'GITHUB_HTTP_403_REPORTED');assert.equal(v.normalized.audit.direct_http_log_verified,false);}
 });
}

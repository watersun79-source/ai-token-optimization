/* Evolving AI in-host read-only adapter v1.0.
 * Host invokes two already-connected tools in ONE JS run; no Python, disk, network
 * API, persistent state, remote writes, GitHub 403 retry, or additional scheduling.
 * Never print raw tool outputs or tokens; only explicit allowlist projections.
 * Cryptographic hash is for normalized output BYTES only, NOT MCP origin authentication.
 */
const TASK_ID='6ae8db67fef081919af59fecbf162552';
const BASELINE={run_id:'7ca1c18d-e45c-8322-b4c9-e56d87d15c3f',scheduled_for:'2026-11-16T05:00:00Z',record_version:17,content_sha:'d573de1ee07d1fa68924728e6c549d4ade44d1e8a995c3a6b09d4d75b82c6dd5',event_key:'github.pr30.1605ec459634f37cf5c30d7c3eba8b0ff5e8757de609e90326481e652e58fa33'};
const UUID=/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/;
const HASH40=/^[0-9a-f]{40}$/,HASH64=/^[0-9a-f]{64}$/,EVENT=/^github\.pr30\.[0-9a-f]{64}$/;
const ISOTIME=/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,9})?(?:Z|[+-]\d\d:\d\d)$/;
const KEYS = new Set(['record','automations']);
function fail(code){ const e=new Error(code);e.name='BlockedInput'; throw e; }
function validTime(x){return typeof x==='string'&&ISOTIME.test(x)&&!Number.isNaN(Date.parse(x));}
function requireTime(x){if(!validTime(x))fail('INVALID_TIMESTAMP');return x;}
function requireMatch(x,re,code){if(typeof x!=='string'||!re.test(x))fail(code);return x;}
function unwrap(obj){
  let x=obj;
  for(let i=0;i<5;i++){
    if(typeof x==='string'){if(x.length>2000000)fail('INPUT_TOO_LARGE');try{x=JSON.parse(x)}catch{fail('INVALID_JSON')};continue;}
    if(x&&typeof x==='object'&&!Array.isArray(x)&&!('record' in x)&&!('automations' in x)){
      if(Object.keys(x).length===1&&typeof x.text==='string'){x=x.text;continue;}
      if(Array.isArray(x.content)){
        const texts=x.content.filter(v=>v&&v.type==='text'&&typeof v.text==='string');
        if(texts.length!==1)fail('MCP_CONTENT_AMBIGUOUS');x=texts[0].text;continue;
      }
    }
    break;
  }
  if(!x||typeof x!=='object'||Array.isArray(x))fail('OBJECT_REQUIRED');
  return x;
}
// v1.0.3-peek.1: classify official peek's error envelope BEFORE considering
// its optional automations field. Neither a null array nor a returned error
// independently proves permission denial; auth state always remains UNVERIFIED.
function checkedPeekEnvelope(data){
  let peek;
  try { peek=unwrap(data); }
  catch (_) { fail('PEEK_RESPONSE_STRUCTURE_INVALID'); }
  if(peek.status==='ERROR'){
    if(peek.error_code===undefined||peek.error_code===null)
      fail('PEEK_STATUS_ERROR_NO_CODE');
    const known=new Set(['too_many_active_automations','too_many_active_goals',
      'automation_schedule_not_available','stale_actor_biscuit']);
    if(typeof peek.error_code!=='string'||!known.has(peek.error_code))
      fail('PEEK_ERROR_CODE_UNKNOWN');
    fail('PEEK_ERROR_'+peek.error_code.toUpperCase());
  }
  if(peek.status!==undefined&&peek.status!==null)
    fail('PEEK_RESPONSE_STRUCTURE_INVALID');
  if(peek.error_code!==undefined&&peek.error_code!==null)
    fail('PEEK_ERROR_CODE_WITHOUT_ERROR_STATUS');
  if(!Object.prototype.hasOwnProperty.call(peek,'automations'))
    fail('PEEK_AUTOMATIONS_MISSING');
  if(peek.automations===null)fail('PEEK_AUTOMATIONS_NULL');
  if(!Array.isArray(peek.automations))fail('PEEK_AUTOMATIONS_TYPE_INVALID');
  if(!peek.automations.every(a=>a&&typeof a==='object'&&!Array.isArray(a)&&
    typeof a.id==='string'&&
    (a.run_details===undefined||a.run_details===null||
      (typeof a.run_details==='object'&&!Array.isArray(a.run_details)))))
    fail('PEEK_RESPONSE_STRUCTURE_INVALID');
  return peek;
}
function sanitizeConnected(peekData,d1Data,baseline=BASELINE){
  const peek=checkedPeekEnvelope(peekData);
  const matches=peek.automations.filter(a=>a&&a.id===TASK_ID);
  if(matches.length!==1)fail('TASK_NOT_UNIQUE');
  const a=matches[0],last=a.run_details?.last_run,result=a.run_details?.latest_result;
  if(!last||!result)fail('RUN_RESULT_MISSING');
  const runId=requireMatch(last.id,UUID,'RUN_ID_INVALID');
  const resultId=requireMatch(result.run_id,UUID,'RESULT_ID_INVALID');
  if(runId!==resultId)fail('RUN_RESULT_ID_MISMATCH');
  if(requireTime(last.scheduled_for)!==requireTime(result.scheduled_for))fail('SCHEDULE_CONFLICT');
  requireTime(last.started_at);requireTime(result.created_at);
  if(last.completed_at!==null)requireTime(last.completed_at);
  if(result.completed_at!==null)requireTime(result.completed_at);
  if(last.recorded_status==='completed'&&(!last.completed_at||!result.completed_at))fail('COMPLETION_TIMESTAMP_MISSING');
  if(last.completed_at&&Date.parse(last.started_at)>Date.parse(last.completed_at))fail('RUN_TIME_ORDER_INVALID');
  if(result.completed_at&&Date.parse(result.created_at)>Date.parse(result.completed_at))fail('RESULT_TIME_ORDER_INVALID');
  if(!['completed','failed','in_progress','no_update'].includes(last.recorded_status))fail('RUN_STATUS_INVALID');
  if(a.is_enabled!==true||a.default_timezone!=='Asia/Seoul')fail('TASK_CONFIGURATION_NOT_EXPECTED');
  if(!['exact_schedule','flexible_schedule','condition_watch'].includes(a.timing_mode))fail('MODE_INVALID');
  const str=typeof result.content_text==='string'?result.content_text:'';
  // Fail-closed classification: an older success mention must never override
  // a CURRENT 403. Korean prose PASS is accepted only when it is bound to
  // this run, the exact D1 HEAD, the same-HEAD security run and direct cycle.
  const reported403=/(?:^\s*\*\*BLOCKED\b[^\n]{0,180}(?:GITHUB_HTTP_403|GitHub\s+HTTP\s+403)|^\s*\|\s*DEBUG\s*\|\s*(?:GITHUB_HTTP_403|BLOCKED[^|\n]{0,120}(?:GITHUB_HTTP_403|GitHub\s+HTTP\s+403)))/im.test(str);
  const d=unwrap(d1Data),rec=d.record;
  if(d.found!==true||!rec||typeof rec!=='object'||d.receipt_status!=='PASS')fail('D1_READ_NOT_PASS');
  if(d.mcp_receipt&&['PASS','FAIL'].includes(d.mcp_receipt.status)&&d.mcp_receipt.status!==d.receipt_status)fail('D1_RECEIPT_STATUS_CONFLICT');
  if(!Number.isSafeInteger(d.record_version)||d.record_version<1)fail('D1_REVISION_INVALID');
  requireMatch(rec.content_sha,HASH64,'D1_CONTENT_SHA_INVALID');
  const inner=unwrap(rec.value),event=inner.latest_evolution_cycle,observation=event?.observation;
  if(!event||!observation)fail('D1_EVENT_MISSING');
  requireMatch(event.event_key,EVENT,'EVENT_KEY_INVALID');
  requireMatch(observation.head_sha,HASH40,'HEAD_SHA_INVALID');
  requireTime(rec.updated_at);requireTime(event.observed_at);
  if(Date.parse(event.observed_at)>Date.parse(rec.updated_at))fail('D1_TIME_ORDER_INVALID');
  if(!Number.isSafeInteger(observation.security_run_id)||observation.security_run_id<1)fail('SECURITY_RUN_INVALID');
  const reportHead='GitHub PR #30 HEAD `'+observation.head_sha+'`';
  const headAt=str.indexOf(reportHead);
  const auditText=headAt>=0?str.slice(headAt,headAt+340):'';
  const currentCycleProse=/`evolution_cycle`.{0,45}(?:실제\s*1회\s*실행|직접\s*실행)/.test(str);
  const currentAuditProse=headAt>=0 &&
    auditText.includes('`'+String(observation.security_run_id)+'`') &&
    /동일\s*SHA\s*보안\s*감사\s*실행/.test(auditText) &&
    /성공을\s*확인/.test(auditText) &&
    str.includes('`'+runId+'`') && currentCycleProse;
  // v1.0.2: a completed host run may still report a CURRENT source-discovery
  // BLOCKED / UNVERIFIED condition without HTTP 403. Require current top-level
  // status, exact PR #30 empty-search evidence and skipped evolution/CAS.
  // Do not infer a direct HTTP error or a new D1 event.
  const currentPrSearchBlocked=!reported403 &&
    /^\s*진화하는 AI[^\n]{0,160}:\s*\*\*BLOCKED\s*\/\s*UNVERIFIED\*\*/m.test(str.slice(0,350)) &&
    /GitHub PR #30 공식 검색은 결과 0건/.test(str) &&
    /evolution_cycle 호출과 D1 CAS 쓰기를 보류/.test(str);
  const reportedSuccess=!reported403&&!currentPrSearchBlocked&&(
    /(?:^\s*\*\*PASS(?:\s|\b)|^\s*\|\s*DEBUG\s*\|\s*PASS)/im.test(str) || currentAuditProse
  );
  const normalized={
    schema:'EVOLVING_AI_IN_HOST_V1',
    source:'DIRECT_CONNECTED_OBJECTS_NOT_TRANSPORT_BYTES',
    source_authentication:'TOOL_RETURN_OBJECT_ONLY_NOT_CRYPTOGRAPHIC_ORIGIN',
    raw_mcp_transport_bytes_verified:false,
    sensitive_raw_response_retained:false,
    automation:{id:TASK_ID,run_id:runId,result_run_id:resultId,recorded_status:last.recorded_status,
      scheduled_for:last.scheduled_for,started_at:last.started_at,completed_at:last.completed_at,
      result_created_at:result.created_at,result_completed_at:result.completed_at,
      timing_mode:a.timing_mode,enabled:a.is_enabled},
    audit:{reported_git_access:reported403?'GITHUB_HTTP_403_REPORTED':currentPrSearchBlocked?'PR_SOURCE_BLOCKED_REPORTED':reportedSuccess?'PASS_REPORTED':'UNVERIFIED',direct_http_log_verified:false},
    d1:{record_version:d.record_version,content_sha:rec.content_sha,event_key:event.event_key,
      observed_at:event.observed_at,record_updated_at:rec.updated_at,head_sha:observation.head_sha,
      security_run_id:observation.security_run_id,security_conclusion:['success','failure','cancelled','skipped'].includes(observation.security_conclusion)?observation.security_conclusion:'UNVERIFIED'}
  };
  const newRun=runId!==baseline.run_id;
  const newEvent=event.event_key!==baseline.event_key;
  const recordRevisionChanged=d.record_version!==baseline.record_version;
  requireMatch(baseline.content_sha,HASH64,'BASELINE_CONTENT_SHA_INVALID');
  if(d.record_version===baseline.record_version&&rec.content_sha!==baseline.content_sha)
    fail('D1_CONTENT_SHA_CHANGED_SAME_REVISION');
  if(d.record_version<baseline.record_version)fail('D1_REVISION_ROLLBACK');
  if(newEvent&&!recordRevisionChanged)fail('EVENT_CHANGED_WITHOUT_RECORD_REVISION');
  let status='NO_UPDATE',reason='SAME_OFFICIAL_RUN_AND_EVENT';
  if(last.recorded_status!=='completed'){status='UNVERIFIED';reason='NATIVE_NOT_COMPLETED';}
  else if(reported403){status='ERROR_REPORTED';reason=newEvent?'ERROR_AND_NEW_EVENT_CAUSAL_CHECK_REQUIRED':recordRevisionChanged?'GITHUB_HTTP_403_REPORTED_D1_REV_CHANGED_EVENT_UNCHANGED':'GITHUB_HTTP_403_REPORTED_NO_D1_WRITE';}
  else if(currentPrSearchBlocked){status='BLOCKED_REPORTED';reason='GITHUB_PR_SEARCH_ZERO_REPORTED_NO_D1_WRITE';}
  else if(newEvent){status='CHANGED';reason='NEW_D1_EVENT_RECORDED';}
  else if(recordRevisionChanged){status='UNVERIFIED';reason='D1_REV_CHANGED_EVENT_UNCHANGED_CAUSE_UNVERIFIED';}
  else if(newRun){status='NO_UPDATE';reason='NEW_RUN_WITH_UNCHANGED_EVENT';}
  return {normalized,verdict:{status,reason,new_run:newRun,new_event:newEvent,record_revision_changed:recordRevisionChanged,causal_attribution_verified:false},normalized_sha256:sha256Ascii(JSON.stringify(normalized))};
}

// Pure JS SHA-256 of ASCII-only allowlisted output, compared against independent
// Node crypto in offline tests. Host must not receive secrets in normalized data.
function sha256Ascii(str){
  const ks=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  const h=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  const bytes=[];for(let i=0;i<str.length;i++){const n=str.charCodeAt(i);if(n>127)fail('NON_ASCII_NORMALIZED');bytes.push(n);}
  const n=bytes.length;bytes.push(0x80);while(bytes.length%64!==56)bytes.push(0);
  const hi=Math.floor(n/0x20000000),lo=(n*8)>>>0;
  for(let i=3;i>=0;i--)bytes.push((hi>>>(8*i))&255);
  for(let i=3;i>=0;i--)bytes.push((lo>>>(8*i))&255);
  const rotr=(x,n)=>(x>>>n)|(x<<(32-n));
  for(let offset=0;offset<bytes.length;offset+=64){
    const w=new Array(64);
    for(let t=0;t<16;t++)w[t]=((bytes[offset+4*t]<<24)|(bytes[offset+4*t+1]<<16)|(bytes[offset+4*t+2]<<8)|bytes[offset+4*t+3])>>>0;
    for(let t=16;t<64;t++){
      const x=w[t-15],y=w[t-2],s0=rotr(x,7)^rotr(x,18)^(x>>>3),s1=rotr(y,17)^rotr(y,19)^(y>>>10);
      w[t]=(w[t-16]+s0+w[t-7]+s1)>>>0;
    }
    let [a,b,c,d,e,f,g,z]=h;
    for(let t=0;t<64;t++){
      const S1=rotr(e,6)^rotr(e,11)^rotr(e,25),ch=(e&f)^(~e&g),temp1=(z+S1+ch+ks[t]+w[t])>>>0;
      const S0=rotr(a,2)^rotr(a,13)^rotr(a,22),maj=(a&b)^(a&c)^(b&c),temp2=(S0+maj)>>>0;
      z=g;g=f;f=e;e=(d+temp1)>>>0;d=c;c=b;b=a;a=(temp1+temp2)>>>0;
    }
    const v=[a,b,c,d,e,f,g,z];for(let i=0;i<8;i++)h[i]=(h[i]+v[i])>>>0;
  }
  return h.map(v=>v.toString(16).padStart(8,'0')).join('');
}
function gateOnNewCompleted(peekData,baseline=BASELINE){
  // One official peek must establish a NEW, MATCHED, COMPLETED scheduled run
  // before ANY D1 read. This gate performs no writes and never retries.
  const peek=checkedPeekEnvelope(peekData);
  const matches=peek.automations.filter(a=>a&&a.id===TASK_ID);
  if(matches.length!==1)fail('TASK_NOT_UNIQUE');
  const task=matches[0],last=task.run_details?.last_run,result=task.run_details?.latest_result;
  if(!last||!result)fail('RUN_RESULT_MISSING');
  if(task.is_enabled!==true||task.default_timezone!=='Asia/Seoul')fail('TASK_CONFIGURATION_NOT_EXPECTED');
  if(!['exact_schedule','flexible_schedule','condition_watch'].includes(task.timing_mode))fail('MODE_INVALID');
  const rid=requireMatch(last.id,UUID,'RUN_ID_INVALID');
  if(rid!==requireMatch(result.run_id,UUID,'RESULT_ID_INVALID'))fail('RUN_RESULT_ID_MISMATCH');
  if(requireTime(last.scheduled_for)!==requireTime(result.scheduled_for))fail('SCHEDULE_CONFLICT');
  if(last.recorded_status!=='completed')
    return {eligible:false,reason:'LATEST_RUN_NOT_COMPLETED',run_id:rid,run_status:last.recorded_status};
  requireTime(last.started_at);requireTime(last.completed_at);
  requireTime(result.created_at);requireTime(result.completed_at);
  if(Date.parse(last.started_at)>Date.parse(last.completed_at)||
     Date.parse(result.created_at)>Date.parse(result.completed_at))fail('COMPLETION_TIME_ORDER_INVALID');
  if(!validTime(baseline.scheduled_for))fail('BASELINE_SCHEDULE_INVALID');
  if(rid===baseline.run_id||Date.parse(last.scheduled_for)<=Date.parse(baseline.scheduled_for))
    return {eligible:false,reason:'NO_NEW_COMPLETED_RUN',run_id:rid,run_status:'completed'};
  return {eligible:true,run_id:rid,scheduled_for:last.scheduled_for};
}
async function runConnected(readPeek,readD1){
  // Fixed v1.0.3: no eager Promise.all; 1 peek, conditional 0/1 D1.
  const peek=await readPeek();
  const gate=gateOnNewCompleted(peek);
  if(!gate.eligible)return {normalized:null,verdict:{status:gate.run_status==='completed'?'NO_UPDATE':'UNVERIFIED',
    reason:gate.reason,new_run:false,new_event:false,record_revision_changed:false,
    causal_attribution_verified:false},normalized_sha256:null,tool_reads:{peek:1,d1:0}};
  const d1=await readD1();
  const result=sanitizeConnected(peek,d1);
  return {...result,tool_reads:{peek:1,d1:1}};
}

// v1.0.3-peek.1 in-host read-only guard.1
// This segment replaces ONLY the original auto-executing Host entry in a derived
// bundle. Source core above is an identical byte prefix from the source ZIP.
// Activation defaults to false. A future authorized turn must explicitly review
// the current baseline and flip enabled to true before any live connected read.
const HOST_READONLY_GUARD = Object.freeze({
  enabled: false,
  expected_automation_id: '6ae8db67fef081919af59fecbf162552',
  expected_d1_key: 'automation.evolving-ai.github-toolkit',
  baseline: Object.freeze({
    run_id: '0476e7b0-cf9c-8322-8233-fdc0409c8d7e',
    scheduled_for: '2026-11-16T21:00:00Z',
    record_version: 17,
    content_sha: 'd573de1ee07d1fa68924728e6c549d4ade44d1e8a995c3a6b09d4d75b82c6dd5',
    event_key: 'github.pr30.1605ec459634f37cf5c30d7c3eba8b0ff5e8757de609e90326481e652e58fa33'
  })
});

// No network, SDK, filesystem, module imports, retries, or writes.
async function guardedInHostReadOnly() {
  const counters = {peek:0,d1:0};
  const block = (code) => ({
    normalized:null,
    verdict:{status:'BLOCKED',reason:code,auth:'AUTH_UNVERIFIED',
      remote_write:'NO_WRITE',causal_attribution_verified:false},
    normalized_sha256:null, tool_reads:{peek:counters.peek,d1:counters.d1}
  });
  // MUST be first. The built bundle is safe to inspect or paste as-is.
  if (HOST_READONLY_GUARD.enabled !== true)
    return block('HOST_READS_DISABLED_BY_DEFAULT');
  if (TASK_ID !== HOST_READONLY_GUARD.expected_automation_id ||
      HOST_READONLY_GUARD.expected_d1_key !== 'automation.evolving-ai.github-toolkit' ||
      !validTime(HOST_READONLY_GUARD.baseline.scheduled_for) ||
      !UUID.test(HOST_READONLY_GUARD.baseline.run_id) ||
      !EVENT.test(HOST_READONLY_GUARD.baseline.event_key) ||
      !HASH64.test(HOST_READONLY_GUARD.baseline.content_sha) ||
      !Number.isSafeInteger(HOST_READONLY_GUARD.baseline.record_version) ||
      HOST_READONLY_GUARD.baseline.record_version < 1)
    return block('HOST_PREFLIGHT_POLICY_INVALID');
  // Capability existence is not an authentication/permission proof.
  if (typeof tools === 'undefined' ||
      typeof tools.mcp__Automations__peek !== 'function' ||
      typeof tools.mcp__AI_________memory_read !== 'function')
    return block('HOST_READ_CAPABILITY_UNAVAILABLE');
  try {
    // One official peek only, fixed ID, no generic tool-name dispatch.
    counters.peek++;
    const peek = await tools.mcp__Automations__peek({jawbone_id:TASK_ID});
    const gate = gateOnNewCompleted(peek,HOST_READONLY_GUARD.baseline);
    if (!gate.eligible) return {
      normalized:null,
      verdict:{status:gate.run_status==='completed'?'NO_UPDATE':'UNVERIFIED',
        reason:gate.reason,new_run:false,new_event:false,
        record_revision_changed:false,causal_attribution_verified:false,
        auth:'AUTH_UNVERIFIED',remote_write:'NO_WRITE'},
      normalized_sha256:null,tool_reads:{peek:1,d1:0}
    };
    // Validate report completeness before accessing D1. These are official
    // latest_result fields. Missing or truncated evidence fails closed.
    const checked = checkedPeekEnvelope(peek);
    const matches = checked.automations.filter(a=>a.id===TASK_ID);
    if (matches.length !== 1) fail('TASK_NOT_UNIQUE');
    const result = matches[0].run_details?.latest_result;
    if (!result || result.content_truncated !== false ||
        result.requires_user_action !== false ||
        result.is_failure_message !== false ||
        typeof result.content_text !== 'string')
      fail('PEEK_RESULT_INCOMPLETE_OR_ACTION_REQUIRED');
    // D1 may be called exactly once only AFTER official new-completed gate.
    counters.d1++;
    const d1 = await tools.mcp__AI_________memory_read({
      key:HOST_READONLY_GUARD.expected_d1_key,history:false
    });
    const computed = sanitizeConnected(peek,d1,HOST_READONLY_GUARD.baseline);
    return {...computed,verdict:{...computed.verdict,
      auth:'AUTH_UNVERIFIED',remote_write:'NO_WRITE'},
      tool_reads:{peek:counters.peek,d1:counters.d1}};
  } catch (e) {
    // Preserve only controlled codes; never serialize exception contents,
    // tool responses, auth tokens, raw report, or diagnostic stack traces.
    const code = e?.name==='BlockedInput' && /^[A-Z][A-Z0-9_]{1,100}$/.test(e.message)
      ? e.message : 'HOST_READ_OR_VALIDATION_FAILED';
    return block(code);
  }
}

// One user-visible summary, no scheduler, background work, or second attempt.
try {
  const result = await guardedInHostReadOnly();
  if (typeof text === 'function')
    text('IN_HOST_READONLY '+JSON.stringify(result));
} catch (_) {
  if (typeof text === 'function')
    text('IN_HOST_READONLY '+JSON.stringify({verdict:{status:'BLOCKED',
      reason:'HOST_OUTPUT_FAILURE',auth:'AUTH_UNVERIFIED',remote_write:'NO_WRITE'}}));
}

import test from 'node:test';
import assert from 'node:assert/strict';
import {sign,verify,createApp,probe,snapshot} from './realtime_dashboard_v842.mjs';

const secret='TEST_ONLY_FAKE_NO_REAL_SECRETS_012345678901';
const yes=async()=>({ok:true,status:200});
const no=async()=>({ok:false,status:503});

test('session HMAC valid only with right secret and fresh timestamp',()=>{
  const now=Date.now(),v=sign(now,secret);
  assert.equal(verify(v,secret,now+2000),true);
  assert.equal(verify(v,'bad-secret',now+2000),false);
  assert.equal(verify(v,secret,now+13*3600000),false);
  assert.equal(verify('wrong',secret,now),false);
});
test('Render 200 is UP, HTTP 503 is DOWN, network errors are UNVERIFIED',async()=>{
  assert.equal((await probe(yes)).status,'UP');
  assert.equal((await probe(no)).status,'DOWN');
  assert.equal((await probe(async()=>{throw Error('offline')})).status,'UNVERIFIED');
});
test('Neon and native never inherit Render success',async()=>{
  const v=await snapshot(yes);
  assert.equal(v.render.status,'UP');
  assert.equal(v.neon.status,'UNVERIFIED');
  assert.equal(v.native.status,'UNVERIFIED');
  assert.equal(v.paid_model_calls,0);
});
test('state fingerprint identical on equal results; changes on failures',async()=>{
  const a=await snapshot(yes),b=await snapshot(yes),c=await snapshot(no);
  assert.equal(a.change_id,b.change_id);
  assert.notEqual(a.change_id,c.change_id);
});
test('server health public; snapshot requires valid session; no token leaks',async()=>{
  const s=createApp({secret,fetcher:yes});
  await new Promise(r=>s.listen(0,'127.0.0.1',r));
  const base='http://127.0.0.1:'+s.address().port;
  try{
    const r=await fetch(base+'/healthz');assert.equal(r.status,200);
    assert.equal((await r.json()).scope,'isolated-no-secrets');
    assert.equal((await fetch(base+'/api/snapshot')).status,401);
    assert.equal((await fetch(base+'/login',{method:'POST',body:new URLSearchParams({key:'BAD'})})).status,401);
    const login=await fetch(base+'/login',{method:'POST',body:new URLSearchParams({key:secret}),redirect:'manual'});
    assert.equal(login.status,303);
    const cookie=login.headers.get('set-cookie').split(';')[0];
    assert.ok(!cookie.includes(secret));
    const resp=await fetch(base+'/api/snapshot',{headers:{cookie}});
    assert.equal(resp.status,200);
    const data=await resp.json();
    assert.equal(data.render.status,'UP');
    assert.ok(!JSON.stringify(data).includes(secret));
  }finally{s.close();}
});
test('SSE emits valid authenticated snapshot event',async()=>{
  const s=createApp({secret,fetcher:yes});
  await new Promise(r=>s.listen(0,'127.0.0.1',r));
  const base='http://127.0.0.1:'+s.address().port;
  const cookie='watch_session='+sign(Date.now(),secret);
  const controller=new AbortController();
  try{
    const r=await fetch(base+'/events',{headers:{cookie},signal:controller.signal});
    assert.equal(r.status,200);
    assert.match(r.headers.get('content-type'),/text\/event-stream/);
    const {value}=await r.body.getReader().read();
    const data=new TextDecoder().decode(value);
    assert.match(data,/event: snapshot\n/);
    assert.match(data,/"render":\{"status":"UP"/);
  }finally{controller.abort();s.closeAllConnections();s.close();}
});

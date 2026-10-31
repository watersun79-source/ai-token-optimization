import test from 'node:test';
import assert from 'node:assert/strict';
import {runInNewContext} from 'node:vm';
import {sign,verify,createApp,probe,snapshot} from './realtime_dashboard_v842.mjs';

const secret='TEST_ONLY_FAKE_NO_REAL_SECRETS_012345678901';
const yes=async()=>({ok:true,status:200,json:async()=>({status:'UP',database_connection_verified:true,intake_enabled:true,boot_id:'boot-1'})});
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
    const unicodeBad='é'+secret.slice(1);
    assert.equal(unicodeBad.length,secret.length);
    assert.equal((await fetch(base+'/login',{method:'POST',body:new URLSearchParams({key:unicodeBad})})).status,401);
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

test('SSE session expires and closes an already-open stream',async()=>{
  const s=createApp({secret,fetcher:yes});
  await new Promise(r=>s.listen(0,'127.0.0.1',r));
  const base='http://127.0.0.1:'+s.address().port;
  const controller=new AbortController();
  try{
    const issuedAt=Date.now()-12*3600*1000+1500;
    const r=await fetch(base+'/events',{headers:{cookie:'watch_session='+sign(issuedAt,secret)},signal:controller.signal});
    assert.equal(r.status,200);
    const reader=r.body.getReader();
    const first=await reader.read();
    assert.equal(first.done,false);
    assert.match(new TextDecoder().decode(first.value),/event: snapshot\n/);
    const terminated=await Promise.race([
      reader.read().then(v=>({done:v.done})),
      new Promise(resolve=>setTimeout(()=>resolve({timedOut:true}),3000))
    ]);
    assert.deepEqual(terminated,{done:true},'SSE stream must end when the signed cookie expires');
  }finally{controller.abort();s.closeAllConnections();await new Promise(r=>s.close(r));}
});


test('browser SSE reconnect handles expired authentication without repeated requests',async()=>{
  const server=createApp({secret,fetcher:yes});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try{
    const js=await (await fetch('http://127.0.0.1:'+server.address().port+'/app.js')).text();
    const elements=new Map();
    const fakeDocument={
      getElementById(id){if(!elements.has(id))elements.set(id,{textContent:'',prepend(){}});return elements.get(id);},
      createElement(){return {textContent:''};}
    };
    let sse,interval,requests=0;
    class FakeEventSource{
      static OPEN=1;
      static CLOSED=2;
      constructor(){this.readyState=FakeEventSource.OPEN;sse=this;}
      addEventListener(){}
      close(){this.readyState=FakeEventSource.CLOSED;this.closed=true;}
    }
    runInNewContext(js,{
      document:fakeDocument,EventSource:FakeEventSource,
      setInterval(fn){interval=fn;return 1;},
      fetch:async()=>{requests++;return {status:401,ok:false};}
    });
    assert.equal(typeof interval,'function');
    interval();
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(requests,0,'healthy SSE must not duplicate snapshot polling');
    sse.readyState=0;
    sse.onerror();
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(requests,1,'one unauthorized probe on a disconnect');
    assert.equal(sse.closed,true,'expired auth must close automatic SSE reconnect');
    assert.match(fakeDocument.getElementById('connection').textContent,/세션 만료/);
    interval();sse.onerror();
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(requests,1,'expired session must not keep polling');
  }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});

test('browser SSE fallback reuses a single in-flight request and recovers status',async()=>{
  const server=createApp({secret,fetcher:yes});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try{
    const js=await (await fetch('http://127.0.0.1:'+server.address().port+'/app.js')).text();
    const elements=new Map();
    const fakeDocument={
      getElementById(id){if(!elements.has(id))elements.set(id,{textContent:'',prepend(){}});return elements.get(id);},
      createElement(){return {textContent:''};}
    };
    let sse,interval,requests=0,resolveRequest;
    class FakeEventSource{
      static OPEN=1;
      static CLOSED=2;
      constructor(){this.readyState=FakeEventSource.OPEN;sse=this;}
      addEventListener(){}
      close(){this.readyState=FakeEventSource.CLOSED;}
    }
    runInNewContext(js,{
      document:fakeDocument,EventSource:FakeEventSource,
      setInterval(fn){interval=fn;return 1;},
      fetch(){requests++;return new Promise(resolve=>{resolveRequest=resolve;});}
    });
    sse.readyState=0;sse.onerror();
    interval();
    assert.equal(requests,1,'reconnect and timer should share one in-flight snapshot');
    resolveRequest({status:200,ok:true,json:async()=>({
      render:{status:'UP',http_status:200,database_ready:true,boot_id:'boot-1'},
      change_id:'reconnect-1',observed_at:'2026-10-31T10:00:00Z'
    })});
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(fakeDocument.getElementById('render').textContent,'백엔드 준비 보고');
    sse.readyState=FakeEventSource.OPEN;
    interval();
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(requests,1,'connected SSE should suppress fallback requests');
  }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});

test('HTTP 200 is degraded when underlying Neon DB is unavailable',async()=>{
  const falseDb=async()=>({ok:true,status:200,json:async()=>({status:'UP',intake_enabled:false,database_connection_verified:false,boot_id:'boot-2'})});
  const result=await probe(falseDb);
  assert.equal(result.status,'DEGRADED');
  assert.equal(result.http_status,200);
  assert.equal(result.database_ready,false);
  assert.equal((await snapshot(falseDb)).render.status,'DEGRADED');
});
test('HTTP 200 with missing/broken health evidence must remain unverified',async()=>{
  const unknown=async()=>({ok:true,status:200,json:async()=>({status:'UP'})});
  const badJson=async()=>({ok:true,status:200,json:async()=>{throw new Error('bad json')}});
  assert.equal((await probe(unknown)).status,'UNVERIFIED');
  assert.equal((await probe(badJson)).status,'UNVERIFIED');
});
test('new Render boot_id produces a change event even while otherwise healthy',async()=>{
  const fake=(boot_id)=>async()=>({ok:true,status:200,json:async()=>({status:'UP',database_connection_verified:true,intake_enabled:true,boot_id})});
  const first=await snapshot(fake('boot-1'));
  const rebooted=await snapshot(fake('boot-2'));
  assert.equal(first.render.status,'UP');
  assert.equal(rebooted.render.status,'UP');
  assert.notEqual(first.change_id,rebooted.change_id);
});


test('iPhone dashboard treats HTTP 502 as target failure while SSE remains connected',async()=>{
  const server=createApp({secret,fetcher:yes});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try {
    const base='http://127.0.0.1:'+server.address().port;
    const js=await (await fetch(base+'/app.js')).text();
    const html=await (await fetch(base+'/',{headers:{cookie:'watch_session='+sign(Date.now(),secret)}})).text();
    const css=await (await fetch(base+'/style.css')).text();
    assert.match(html,/id="render-guide"/);
    assert.match(html,/감시 대상 Render v8\.3\.5/);
    assert.match(css,/#render\[data-state="DOWN"\]\{color:#c43242\}/);
    const elements=new Map();
    const doc={
      getElementById(id){if(!elements.has(id))elements.set(id,{textContent:'',dataset:{},prepend(){}});return elements.get(id);},
      createElement(){return {textContent:''};}
    };
    let callback;
    class TestEventSource{
      static OPEN=1;
      static CLOSED=2;
      constructor(){this.readyState=TestEventSource.OPEN;}
      addEventListener(type,cb){if(type==='snapshot')callback=cb;}
      close(){this.readyState=TestEventSource.CLOSED;}
    }
    runInNewContext(js,{
      document:doc,EventSource:TestEventSource,
      setInterval(){return 1;},
      fetch(){throw Error('no client HTTP requests expected while SSE connected');}
    });
    assert.equal(typeof callback,'function');
    callback({data:JSON.stringify({
      render:{status:'DOWN',http_status:502,database_ready:null,intake_ready:null,boot_id:null},
      change_id:'target-502-1',observed_at:'2026-10-31T11:11:50Z'
    })});
    assert.equal(doc.getElementById('render').dataset.state,'DOWN');
    assert.match(doc.getElementById('render').textContent,/HTTP 오류/);
    assert.match(doc.getElementById('render-guide').textContent,/절전 해제 또는 일시적 장애/);
    assert.match(doc.getElementById('connection').textContent,/관제 연결됨 · 대상 상태 별도/);
    assert.doesNotMatch(doc.getElementById('render').textContent,/정상/);
  }finally{
    server.closeAllConnections();
    await new Promise(resolve=>server.close(resolve));
  }
});

import http from 'node:http';
import { createHmac, timingSafeEqual, createHash } from 'node:crypto';

const PORT = Number(process.env.PORT || 8787);
const TOKEN = process.env.REALTIME_VIEW_SECRET || '';
const TARGET = 'https://ai-bot-v835-neon-isolated-20261030.onrender.com/healthz';
const MAX_AGE = 12 * 3600 * 1000;
let activeStreams = 0;

export const sign = (ts, secret) => String(ts) + '.' + createHmac('sha256', secret).update('v842:' + ts).digest('hex');
export function verify(cookie, secret, now=Date.now()) {
  const m = /^(\d{13})\.([a-f0-9]{64})$/.exec(cookie || '');
  if (!secret || !m) return false;
  const timestamp = Number(m[1]);
  if (timestamp > now + 60000 || now-timestamp > MAX_AGE) return false;
  return timingSafeEqual(Buffer.from(cookie),Buffer.from(sign(timestamp,secret)));
}
const auth = (req,key) => {
  const cookie=(req.headers.cookie||'').split(';').map(v=>v.trim()).find(v=>v.startsWith('watch_session='));
  return verify(cookie?.slice(14),key);
};
const headers={
  'Cache-Control':'no-store',
  'X-Content-Type-Options':'nosniff',
  'Referrer-Policy':'no-referrer',
  'X-Frame-Options':'DENY',
  'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
};
function reply(res,code,type,data,extras={}){
  res.writeHead(code,{...headers,'Content-Type':type,...extras});res.end(data);
}
const htmlLogin = '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AI 실시간 관제</title><link rel="stylesheet" href="/style.css"><main><section class="card"><h1>AI 실시간 관제</h1><p>비공개 읽기 전용 관제야. Render 환경변수 REALTIME_VIEW_SECRET 값으로 로그인해.</p><form action="/login" method="POST"><label>접근키<input type="password" name="key" required minlength="24" autocomplete="off"></label><button>접속하기</button></form></section></main></html>';
const htmlApp = '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AI 실시간 관제</title><link rel="stylesheet" href="/style.css"><main><h1>AI 실시간 관제</h1><p>화면을 열어둔 동안 읽기 전용 확인 · Render Free 유휴 절전은 유지</p><div class="badge" id="connection">연결 중</div><section class="cards"><article><small>Render 상태</small><h2 id="render">조회 중</h2><p id="rt"></p></article><article><small>Neon</small><h2>미검증</h2><p>이 서버에 DB 자격증명을 설치하지 않았어. ChatGPT Neon 접속은 별도야.</p></article><article><small>ChatGPT 예약 / D1</small><h2>미검증</h2><p>공식 동일 회차 MCP 원장이 없어 성공으로 추정하지 않아.</p></article></section><section class="card"><h3>상태 변경</h3><div id="feed">아직 이벤트 없음</div></section><form action="/logout" method="POST"><button>로그아웃</button></form></main><script src="/app.js" defer></script></html>';
const css='*{box-sizing:border-box}body{margin:0;background:#ecf2f7;color:#172535;font-family:-apple-system,BlinkMacSystemFont,system-ui,sans-serif}main{max-width:760px;margin:auto;padding:28px 16px}h1{font-size:32px}p{font-size:13px;color:#63798a;line-height:1.5}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0}.card,article{background:white;border:1px solid #d8e1ec;border-radius:20px;padding:20px;box-shadow:0 5px 22px #4c61740b}small{color:#63798a}h2{font-size:23px;color:#1a8655}.badge{background:#dce9f5;border-radius:12px;padding:8px;display:inline-block;font-size:13px}input{display:block;padding:12px;width:100%;border:1px solid #bbcbd9;border-radius:12px;margin:8px 0 12px}button{background:#1967c4;color:white;border:0;border-radius:12px;padding:12px 20px;margin-top:16px}#feed{font-size:12px;color:#4c657a}';
const script='let last="";const el=(id)=>document.getElementById(id);function update(s){const r=s.render;el("render").textContent=r.status==="UP"?"백엔드 준비 보고":r.status==="DEGRADED"?"DB 연결 미준비":r.status==="DOWN"?"HTTP 오류":"미확인";el("rt").textContent="HTTP "+(r.http_status??"-")+" · DB "+(r.database_ready===true?"준비 보고":r.database_ready===false?"미준비":"미검증")+" · "+new Date(s.observed_at).toLocaleTimeString("ko-KR");if(s.change_id!==last){last=s.change_id;const div=document.createElement("div");div.textContent=new Date().toLocaleTimeString("ko-KR")+"  "+el("render").textContent+(r.boot_id?" · 부팅 "+r.boot_id.slice(0,8):"");el("feed").prepend(div)}}const sse=new EventSource("/events");sse.addEventListener("snapshot",e=>{update(JSON.parse(e.data));el("connection").textContent="실시간 연결"});sse.onerror=()=>el("connection").textContent="재연결 중";setInterval(()=>fetch("/api/snapshot",{cache:"no-store"}).then(r=>r.ok?r.json():null).then(s=>s&&update(s)).catch(()=>{}),45000);';

export async function probe(fetcher=fetch) {
  const t=Date.now();
  try {
    const r=await fetcher(TARGET,{method:'GET',redirect:'error',signal:AbortSignal.timeout(7500),headers:{'User-Agent':'IsolatedRealtime842'}});
    if (!r.ok) {
      return {status:'DOWN',http_status:r.status,database_ready:null,intake_ready:null,boot_id:null,latency_ms:Date.now()-t};
    }
    let health;
    try { health=await r.json(); }
    catch {
      return {status:'UNVERIFIED',reason:'HEALTH_BODY_UNREADABLE',http_status:r.status,database_ready:null,intake_ready:null,boot_id:null,latency_ms:Date.now()-t};
    }
    // HTTP 200 is NOT proof of a functioning Neon backend. Trust only the
    // isolated service's explicit public health contract; it is a claim,
    // not an independent authenticated Neon database read.
    const dbReady=health?.database_connection_verified===true;
    const intakeReady=health?.intake_enabled===true;
    const explicitlyUnready=health?.database_connection_verified===false || health?.intake_enabled===false;
    const status=dbReady && intakeReady && health?.status==='UP' ? 'UP'
      : explicitlyUnready ? 'DEGRADED' : 'UNVERIFIED';
    const bootId=typeof health?.boot_id==='string' && /^[A-Za-z0-9_-]{1,64}$/.test(health.boot_id)
      ? health.boot_id : null;
    return {status,http_status:r.status,database_ready:dbReady,intake_ready:intakeReady,boot_id:bootId,latency_ms:Date.now()-t};
  } catch {return {status:'UNVERIFIED',reason:'NETWORK_OR_TIMEOUT',http_status:null,database_ready:null,intake_ready:null,boot_id:null,latency_ms:null};}
}
export async function snapshot(fetcher=fetch){
  const render=await probe(fetcher);
  return {
    version:'8.4.2',observed_at:new Date().toISOString(),
    change_id:createHash('sha256').update(JSON.stringify([render.status,render.http_status,render.database_ready,render.intake_ready,render.boot_id])).digest('hex').slice(0,16),
    render,neon:{status:'UNVERIFIED',reason:'NO_DATABASE_CREDENTIALS'},
    native:{status:'UNVERIFIED',reason:'NO_NATIVE_PROVENANCE'},
    source:'ISOLATED_LIVE_READ_ONLY',paid_model_calls:0
  };
}
export function createApp({secret=TOKEN,fetcher=fetch}={}){
  const server=http.createServer(async(req,res)=>{
    try{
      const url=new URL(req.url,'http://localhost');
      if (req.method==='GET'&&url.pathname==='/healthz') {reply(res,200,'application/json',JSON.stringify({status:'ok',scope:'isolated-no-secrets',version:'8.4.2'}));return;}
      if (req.method==='GET'&&url.pathname==='/style.css') {reply(res,200,'text/css',css);return;}
      if (req.method==='GET'&&url.pathname==='/app.js') {reply(res,200,'text/javascript',script);return;}
      if (req.method==='POST'&&url.pathname==='/login'){
        let data='';for await(const chunk of req){data+=chunk;if(data.length>4096)break;}
        const key=new URLSearchParams(data).get('key')||'';
        if(data.length>4096||secret.length<24||Buffer.byteLength(secret)!==Buffer.byteLength(key)||!timingSafeEqual(Buffer.from(secret),Buffer.from(key))){reply(res,401,'application/json',JSON.stringify({error:'UNAUTHORIZED'}));return;}
        res.writeHead(303,{...headers,Location:'/', 'Set-Cookie':'watch_session='+sign(Date.now(),secret)+'; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=43200'});res.end();return;
      }
      if(req.method==='POST'&&url.pathname==='/logout'){
        res.writeHead(303,{...headers,Location:'/', 'Set-Cookie':'watch_session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0'});res.end();return;
      }
      if(req.method==='GET'&&url.pathname==='/'){reply(res,200,'text/html',auth(req,secret)?htmlApp:htmlLogin);return;}
      if(!auth(req,secret)){reply(res,401,'application/json',JSON.stringify({error:'AUTH_REQUIRED'}));return;}
      if(req.method==='GET'&&url.pathname==='/api/snapshot'){reply(res,200,'application/json',JSON.stringify(await snapshot(fetcher)));return;}
      if(req.method==='GET'&&url.pathname==='/events'){
        if(activeStreams>=5){reply(res,429,'application/json',JSON.stringify({error:'TOO_MANY_STREAMS'}));return;}
        activeStreams++;
        res.writeHead(200,{...headers,'Content-Type':'text/event-stream','X-Accel-Buffering':'no',Connection:'keep-alive'});
        let closed=false,previous='';
        const timer=setInterval(()=>tick().catch(()=>{}),30000);timer.unref();
        // A successful handshake must not keep streaming after its 12h signed session expires.
        const sessionCookie=(req.headers.cookie||'').split(';').map(v=>v.trim()).find(v=>v.startsWith('watch_session='))?.slice(14)||'';
        const issuedAt=Number(sessionCookie.slice(0,13)); // Already authenticated above.
        const remainingMs=Math.max(1,issuedAt+MAX_AGE-Date.now()+1);
        const expiryTimer=setTimeout(()=>{if(!closed)res.end();},remainingMs);
        const cleanup=()=>{if(!closed){closed=true;activeStreams--;clearInterval(timer);clearTimeout(expiryTimer);}};
        req.on('close',cleanup);res.on('close',cleanup);
        async function tick(){if(closed)return;const data=await snapshot(fetcher);if(closed)return;if(data.change_id!==previous){previous=data.change_id;res.write('event: snapshot\n'+'data: '+JSON.stringify(data)+'\n\n');}else{res.write(': heartbeat\n\n');}}
        await tick();return;
      }
      reply(res,404,'application/json',JSON.stringify({error:'NOT_FOUND'}));
    }catch{if(!res.headersSent)reply(res,500,'application/json',JSON.stringify({error:'UNEXPECTED'}));else res.destroy();}
  });
  return server;
}
if(process.argv[1]&&import.meta.url===new URL('file://'+process.argv[1]).href){
  if(TOKEN.length<24){console.error('MISSING_VIEW_SECRET');process.exit(1);}
  createApp().listen(PORT,'0.0.0.0',()=>console.log('V842_SERVER_READY_PORT='+PORT));
}

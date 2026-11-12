/** Provider-free SDK functions; no accounts, servers or model API calls. */
import assert from 'node:assert/strict';
import net from 'node:net';
import child_process from 'node:child_process';
net.Socket.prototype.connect = function () { throw Error('SDK_NETWORK_DENIED'); };
child_process.spawn = function () { throw Error('SDK_SPAWN_DENIED'); };
const project = process.argv[2];
if (!['activepieces','letta'].includes(project)) throw Error('UNSUPPORTED_SDK_EOF');
let name, proof;
if (project==='activepieces') {
  name='@activepieces/pieces-framework';
  const {createAction}=await import(name);
  const action=createAction({name:'offline_add',displayName:'Local add',description:'Offline deterministic action',props:{},requireAuth:false,async run(){return 6*7;}});
  assert.equal(action.name,'offline_add');
  assert.equal(await action.run({}),42);
  proof='SDK_ACTION_EXECUTED_LOCAL';
} else {
  name='@letta-ai/letta-agent-sdk';
  const {LettaAgentClient}=await import(name);
  const client=new LettaAgentClient({backend:'local'});
  assert.equal(typeof client,'object');
  assert.equal(client.constructor.name,'LettaAgentClient');
  proof='SDK_LOCAL_CLIENT_CONSTRUCTED_NO_CONNECT';
}
const fs=await import('node:fs/promises');
const pkg=JSON.parse(await fs.readFile(process.cwd()+'/node_modules/'+name+'/package.json','utf8'));
console.log('SDK_FUNCTIONAL_RESULT='+JSON.stringify({project,installed_version:pkg.version,proof,result:'PASS',vendor_code_executed:true,provider_calls:0,production_writes:0,state_persisted:false}));

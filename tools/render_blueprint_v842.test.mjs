import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const blueprint = readFileSync(new URL('../render.yaml', import.meta.url), 'utf8');
const guide = readFileSync(new URL('../docs/AI_V842_RENDER_MANUAL_DEPLOY_KO.md', import.meta.url), 'utf8');

test('Render Blueprint only declares one isolated web service', () => {
  assert.match(blueprint, /^services:\s*$/m);
  assert.equal((blueprint.match(/^\s+- type: web$/gm) ?? []).length, 1);
  assert.match(blueprint, /^\s+name: ai-bot-v842-live-readonly-20261031$/m);
  assert.doesNotMatch(blueprint, /^databases:|^envVarGroups:|fromDatabase:|fromService:/m);
});
test('Blueprint keeps FREE plan, original production branch untouched, and auto-deploy off', () => {
  assert.match(blueprint, /^\s+plan: free$/m);
  assert.match(blueprint, /^\s+branch: ai\/v842-live-readonly-20261031$/m);
  assert.match(blueprint, /^\s+autoDeployTrigger: off$/m);
  assert.match(blueprint, /^\s+healthCheckPath: \/healthz$/m);
  assert.match(blueprint, /^\s+startCommand: node tools\/realtime_dashboard_v842\.mjs$/m);
});
test('Blueprint requires human-provided secret, never commits a value', () => {
  assert.match(blueprint, /- key: REALTIME_VIEW_SECRET\n\s+sync: false/);
  assert.doesNotMatch(blueprint, /generateValue:|REALTIME_VIEW_SECRET.*value:|^\s+value:\s+/m);
  assert.doesNotMatch(blueprint, /DATABASE_URL|NEON_AI_GATEWAY_TOKEN|OPENAI_API_KEY/);
});
test('deployment remains explicitly opt-in and requires post-deploy 401 security check', () => {
  assert.match(guide, /https:\/\/render\.com\/deploy\?repo=/);
  assert.match(guide, /Deploy Blueprint/);
  assert.match(guide, /401/);
});

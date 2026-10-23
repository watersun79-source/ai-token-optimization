// Test the actual GitHub-committed JS code, not a mocked replacement.
// Fixture outcomes are FORMAT ONLY; no scheduler provenance is established.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { code } from '../activepieces_mock_guard_2026-10-23.js';

const dir = path.dirname(fileURLToPath(import.meta.url));
const lines = fs.readFileSync(path.join(dir, 'time_vectors.tsv'), 'utf8')
  .split(/\r?\n/).filter(line => line && !line.startsWith('#'));
const automation = '6acb017062a08191a4136238b78b313a';
const runId = 'SYNTHETIC-TEST-NOT-A-CHATGPT-RUN';

for (const line of lines) {
  const [name, slot, start, end, observed, expected] = line.split('|');
  test('R16 actual JS guard UTC/nanoseconds ' + name, async () => {
    const toolCalls = [
      { target: 'current_handoff', tool: 'mcp__GitHub__fetch_file',
        locator: 'docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md',
        version: 'a'.repeat(40), invocation_id: 'SYNTHETIC-GH' },
      { target: 'slack_thread', tool: 'mcp__Slack__slack_read_thread',
        locator: 'C0C9649RQAZ/1792416391.631669',
        version: '1792416391.631669', invocation_id: 'SYNTHETIC-SLACK' },
    ].map(item => ({ ...item, run_id: runId, observed_at: observed,
        success: true, origin: 'official_task_tool_call' }));
    const request = { automation_id: automation, scheduled_for: slot,
      official_run: { origin: 'official_task_run_details',
        automation_id: automation, scheduled_for: slot, run_id: runId,
        started_at: start, completed_at: end, status: 'completed' },
      tool_calls: toolCalls };
    const result = await code({ request });
    assert.equal(result.status, 'UNVERIFIED');
    assert.equal(result.official_success_verified, false);
    assert.equal(result.external_calls, 0);
    assert.equal(result.format_check === 'PASS', expected === 'PASS',
      name + ': ' + JSON.stringify(result));
  });
}

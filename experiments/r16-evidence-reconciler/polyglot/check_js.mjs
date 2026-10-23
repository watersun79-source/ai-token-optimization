// Offline checks of the original Activepieces MOCK-only JS verifier.
// No network, external model API, webhook trigger, secrets or persistent writes.
import { readFileSync } from 'node:fs';
import { code } from '../activepieces_mock_guard_2026-10-23.js';
const task = '6acb017062a08191a4136238b78b313a';
const synthetic = 'SYNTHETIC-CROSS-LANGUAGE-NOT-OFFICIAL';
const rows = readFileSync(process.argv[2], 'utf8').trim().split(/\r?\n/).slice(1);
let passed = 0;
for (const row of rows) {
  const [name, slot, start, end, observed, expected] = row.split('\t');
  const make = (target, tool, locator, version, id) => ({
    origin: 'official_task_tool_call', run_id: synthetic, target, tool, locator,
    success: true, observed_at: observed, version, invocation_id: id,
  });
  const result = await code({request: {
    automation_id: task, scheduled_for: slot,
    official_run: {origin: 'official_task_run_details', automation_id: task,
      run_id: synthetic, scheduled_for: slot, started_at: start, completed_at: end,
      status: 'completed'},
    tool_calls: [
      make('current_handoff', 'mcp__GitHub__fetch_file',
        'docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md', 'a'.repeat(40), 'SYNTHETIC-1'),
      make('slack_thread', 'mcp__Slack__slack_read_thread',
        'C0C9649RQAZ/1792416391.631669', '1792416391.631669', 'SYNTHETIC-2'),
    ],
  }});
  const actual = result.format_check === 'PASS' ? 'FORMAT' : 'REJECT';
  if (actual !== expected) throw new Error(name + ': ' + actual + ' instead of ' + expected);
  if (result.official_success_verified !== false || result.external_calls !== 0 || result.status !== 'UNVERIFIED')
    throw new Error(name + ': unsafe authenticity status');
  passed++;
}
console.log('JS time-order fixtures PASS ' + passed + '/' + rows.length + ' (all authenticity UNVERIFIED)');

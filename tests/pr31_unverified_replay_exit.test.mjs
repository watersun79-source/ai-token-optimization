import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {join, dirname, resolve} from 'node:path';

const directory = dirname(fileURLToPath(import.meta.url));
const replay = resolve(directory, '../experiments/oss-top10-safe-adoption/chat_github_connector_replay.mjs');

// New regression only. A JSON fixture is NOT an authenticated GitHub event.
test('local replay cannot return Exit 0 or assert an authenticated Chat tool call', () => {
  const dir = mkdtempSync(join(tmpdir(), 'pr31-unverified-'));
  try {
    const file = join(dir, 'snapshot.json');
    writeFileSync(file, JSON.stringify({
      provider: 'mcp__GitHub__fetch_pr', call_count: 1,
      repository: 'watersun79-source/ai-token-optimization', number: 30,
      head_sha: 'b6247c697157126c381feab9abfd0799b25a1571',
      state: 'open', merged: false,
    }));
    const p = spawnSync(process.execPath, [replay, file], {
      encoding: 'utf8', timeout: 2000, env: {PATH: process.env.PATH},
    });
    assert.equal(p.error, undefined);
    assert.equal(p.status, 2, 'untrusted replay must never exit 0');
    const output = JSON.parse(p.stdout);
    assert.equal(output.status, 'OBSERVED_UNVERIFIED');
    assert.equal(output.operationalClearance, 'BLOCKED');
    assert.equal(output.allowWrite, false);
    assert.equal(output.liveConnectorCallsByReplay, 0);
    assert.equal(output.connectedSourceOriginalCallExternallyObserved, 'UNVERIFIED_BY_REPLAY');
  } finally {
    rmSync(dir, {recursive: true, force: true});
  }
});

/** Replay exactly one previously read, sanitized Chat connector result. No HTTP. */
import { readFileSync } from 'node:fs';
import { fromSanitizedSnapshot } from './chat_github_connector_adapter.mjs';

// No default path/URL: require an explicitly supplied local input file.
if (process.argv.length !== 3) {
  console.log(JSON.stringify({status:'BLOCKED',reason:'EXPLICIT_LOCAL_SNAPSHOT_REQUIRED',allowWrite:false}));
  process.exitCode = 2;
} else {
  try {
    const input = readFileSync(process.argv[2]);
    if (input.length > 4096 || input.length === 0) throw Error('input too large');
    const snapshot = JSON.parse(input.toString('utf8'));
    const adapter = fromSanitizedSnapshot(snapshot);
    const outcome = await adapter.observe();
    // Never print incoming data or error text. The read is a replay, not a tool call.
    console.log(JSON.stringify({
      ...outcome,
      replayOnly: true,
      liveConnectorCallsByReplay: 0,
      connectedSourceOriginalCallExternallyObserved: 'SEPARATE_CHAT_TOOL_CALL',
    }));
    process.exitCode = outcome.status === 'OBSERVED_UNVERIFIED' ? 0 : 2;
  } catch {
    console.log(JSON.stringify({status:'BLOCKED',reason:'SNAPSHOT_INVALID',allowWrite:false,
      replayOnly:true,liveConnectorCallsByReplay:0}));
    process.exitCode = 2;
  }
}

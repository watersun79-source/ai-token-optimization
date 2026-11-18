/**
 * Chat connector -> isolated rate-limited reader adaptation, NOT a Site plugin.
 *
 * The caller supplies an actual authorized connector function. This module does
 * not import connector APIs, make HTTP calls, load credentials or prove the
 * caller's identity. A serialized replay is never authentication evidence.
 */
import { createConnectedReadGate } from './site_github_connected_read_gate.mjs';

export const REPO = 'watersun79-source/ai-token-optimization';
export const PR_NUMBER = 30;

/**
 * Wrap an actual Chat GitHub fetch_pr function. The return code 200 is a local
 * adapter sentinel indicating a structurally successful connector response;
 * it is NOT an observed GitHub HTTP status. The existing gate rejects all
 * operating permissions even if the SHA is well formed.
 */
export function createChatGithubAdapter({fetchPr, clock = Date.now} = {}) {
  const gate = createConnectedReadGate({clock});
  let invocationCount = 0;
  const reader = typeof fetchPr !== 'function' ? undefined : async (request) => {
    if (request.repository !== REPO || request.pull_request !== PR_NUMBER || request.method !== 'GET') {
      return {status: 422};
    }
    invocationCount += 1;
    const envelope = await fetchPr({repo_full_name: REPO, pr_number: PR_NUMBER});
    const pr = envelope?.result?.pull_request;
    if (pr === null || typeof pr !== 'object' || Array.isArray(pr)) return {status: 422};
    if (pr.number !== PR_NUMBER || pr.state !== 'open' || pr.merged !== false) return {status: 422};
    return {status: 200, data: {number: pr.number, head: {sha: pr.head_sha}}};
  };
  return Object.freeze({
    async observe() {
      const result = await gate.observe(reader);
      return Object.freeze({
        ...result,
        connectedReaderInvocations: invocationCount,
        connectorAuthProvenance: 'UNVERIFIED_LOCAL_ADAPTER',
        actualGithubHttpStatus: null,
        connectorResultMapping: 'LOCAL_SENTINEL_NOT_HTTP',
      });
    },
  });
}

/**
 * Offline-only replay: records are untrusted local input, never tool calls.
 * This accepts ONLY the minimal redacted shape exported by a Chat operator.
 */
export function fromSanitizedSnapshot(snapshot, {clock = Date.now} = {}) {
  const valid = snapshot && !Array.isArray(snapshot) && typeof snapshot === 'object' &&
    snapshot.repository === REPO && snapshot.number === PR_NUMBER &&
    snapshot.provider === 'mcp__GitHub__fetch_pr' && snapshot.call_count === 1 &&
    snapshot.state === 'open' && snapshot.merged === false &&
    typeof snapshot.head_sha === 'string' && /^[a-f0-9]{40}$/.test(snapshot.head_sha);
  const fetchPr = valid ? async ({repo_full_name, pr_number}) => {
    if (repo_full_name !== REPO || pr_number !== PR_NUMBER) throw new Error('scoped request mismatch');
    return {result: {pull_request: {
      number: snapshot.number, head_sha: snapshot.head_sha,
      state: snapshot.state, merged: snapshot.merged,
    }}};
  } : undefined;
  return createChatGithubAdapter({fetchPr, clock});
}

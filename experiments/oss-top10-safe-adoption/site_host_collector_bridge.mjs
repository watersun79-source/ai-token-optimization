/**
 * Isolated Site-host integration seam for PR #31; NOT a deployed Site module.
 *
 * The Site owner must bind an authorized, host-provided GitHub read function.
 * A Chat connector, JSON replay, HTTP fetch or untrusted callback is never
 * authenticated by this module. No fallback requests, credentials, Site API,
 * background work, writes or operational clearance are provided.
 */
import { createChatGithubAdapter } from './chat_github_connector_adapter.mjs';

export const ORIGINAL_SITE_PROJECT_ID = 'appgprj_6ae20fb4b2b08191b0f4b44438fc0237';
export const READ_SCOPE = Object.freeze({
  repository: 'watersun79-source/ai-token-optimization',
  pullRequest: 30,
  method: 'GET',
});

function safeVerdict(reason, result = null) {
  const state = result?.status === 'DEFERRED' ? 'DEFERRED'
    : result?.status === 'OBSERVED_UNVERIFIED' ? 'UNVERIFIED' : 'BLOCKED';
  return Object.freeze({
    schema: 'PR31_SITE_HOST_COLLECTOR_BRIDGE_V1',
    projectId: ORIGINAL_SITE_PROJECT_ID,
    status: state,
    reason,
    source: Object.freeze({
      status: result?.status ?? 'BLOCKED',
      sha: result?.sha ?? null,
      nextAllowedAt: result?.nextAllowedAt ?? null,
      connectedReaderInvocations: result?.connectedReaderInvocations ?? 0,
    }),
    stages: Object.freeze({
      debug: state === 'UNVERIFIED' ? 'UNVERIFIED' : 'BLOCKED',
      analysis: 'SKIP', fix: 'SKIP', update: 'SKIP', verify: 'SKIP',
    }),
    siteRuntimeAuthentication: 'UNVERIFIED',
    connectedCredentialProvenance: 'UNVERIFIED',
    originalSiteSourceInspection: 'NOT_PERFORMED',
    operationalClearance: 'BLOCKED',
    allowUnauthenticatedFallback: false,
    allowRetry: false, allowWrite: false,
    externalMutations: 0,
  });
}

/**
 * @param {{projectId:string, hostReadPr?:Function, clock?:Function}} options
 * @returns {{readOnce:()=>Promise<object>}}
 *
 * hostReadPr is executed ONLY when supplied by the Site host. The module
 * cannot establish its provenance; an authorized host binding is required
 * separately. This function deliberately cannot mark the native goal PASS.
 */
export function createSiteHostCollector({projectId, hostReadPr, clock = Date.now} = {}) {
  if (projectId !== ORIGINAL_SITE_PROJECT_ID) {
    return Object.freeze({
      readOnce: async () => safeVerdict('SITE_PROJECT_ID_MISMATCH'),
    });
  }
  if (typeof hostReadPr !== 'function') {
    return Object.freeze({
      readOnce: async () => safeVerdict('SITE_HOST_CONNECTED_READER_NOT_AVAILABLE'),
    });
  }
  const adapter = createChatGithubAdapter({fetchPr: hostReadPr, clock});
  return Object.freeze({
    async readOnce() {
      // No direct GitHub HTTP, credential extraction, Site writes or fallback.
      const outcome = await adapter.observe();
      return safeVerdict(outcome.reason, outcome);
    },
  });
}

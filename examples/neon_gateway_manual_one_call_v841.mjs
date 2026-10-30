/**
 * Manual operator example ONLY. Never run from CI, reservations or autonomous agents.
 * GPT model calls can cost Neon prepaid credits. Free plan is not eligible.
 *
 * Before a human explicitly approves ONE billable request:
 * 1. Confirm Launch/Scale plan, prepaid credit balance, and permitted model in Neon Console.
 * 2. Put a branch-scoped credential in your OWN environment, never in Git/replies.
 * 3. npm install openai
 * 4. Provide the approval gates below AND --run-live yourself.
 *
 * The approval flags below are manual attestations, NOT a billing lookup.
 */
import { buildCompletionRequest, validateHost } from '../tools/neon_gateway_preflight_v841.mjs';

async function main() {
  const approved = process.argv.includes('--run-live') &&
    process.env.NEON_GATEWAY_APPROVE_ONE_BILLABLE_REQUEST === 'I_APPROVE_ONE_CALL' &&
    process.env.NEON_GATEWAY_PREPAID_CREDITS_MANUALLY_CONFIRMED === 'yes' &&
    ['launch', 'scale'].includes((process.env.NEON_GATEWAY_PLAN_MANUALLY_CONFIRMED ?? '').toLowerCase());

  if (!approved) {
    console.log('BLOCKED_NO_EXPLICIT_ONE_CALL_APPROVAL_AND_PAID_PLAN_CREDITS_CHECK');
    return;
  }

  const url = validateHost(process.env.NEON_AI_GATEWAY_BASE_URL);
  const token = process.env.NEON_AI_GATEWAY_TOKEN;
  if (!url.ok || typeof token !== 'string' || token.length === 0) {
    console.log('BLOCKED_GATEWAY_HOST_OR_TOKEN_NOT_CONFIGURED');
    return;
  }

  // No imported SDK or paid network request before explicit approval checks.
  try {
    const { default: OpenAI } = await import('openai');
    const client = new OpenAI({
      apiKey: token,
      baseURL: url.endpoint,
      maxRetries: 0,
      timeout: 15000,
    });
    // Exactly ONE request, no retry, finite token limit.
    const response = await client.chat.completions.create(buildCompletionRequest());
    console.log(response.choices[0]?.message?.content ?? 'EMPTY_MODEL_CONTENT');
  } catch {
    // Avoid printing error objects; SDK error logs may contain request metadata.
    console.error('ONE_CALL_FAILED_DETAILS_SUPPRESSED');
    process.exitCode = 1;
  }
}

await main();

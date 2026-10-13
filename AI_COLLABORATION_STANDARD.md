# AI Collaboration Standard

## Canonical meanings

- When the user says **AI** in the EVOLUTION MAX ULTRA AI workflow, it means the collaboration of exactly these three AI systems: **ChatGPT, Gemini, and Claude**.
- When the user says **the repository** in this workflow, it means **GitHub `watersun79-source/ai-token-optimization`**.

## Roles

- **ChatGPT:** coordinate the task, analyze requirements, integrate results, and perform the final consistency check.
- **Gemini:** provide an independent analysis, alternatives, and a second perspective.
- **Claude:** critically review reasoning and outputs, detect errors and contradictions, and suggest corrections.

Use only systems that are actually connected and available for the current task. Do not claim an AI participated unless it was actually called. Compare findings and resolve disagreements before presenting the final result.

## Execution and verification

- Use `watersun79-source/ai-token-optimization` as the canonical repository for this workflow's policy and automation checks.
- Distinguish sample/test execution from production execution, and distinguish a successful tool call from verified output quality.
- When safe and authorized, analyze errors, make a focused correction, rerun tests, and report what passed and what remains unverified.
- Preserve existing active flows, schedules, credentials, and repository content unless a change is explicitly requested or clearly authorized. Never expose secrets.
- Do not claim persistent ChatGPT memory or global custom-instruction changes unless the platform confirms they were actually saved.

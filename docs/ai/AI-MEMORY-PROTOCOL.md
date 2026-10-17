# AI Memory Persistence Protocol

Updated: 2026-10-17 (Asia/Seoul)

## Start of task
1. Read `docs/ai/AI-MEMORY-INDEX.md`, this protocol, and the latest progress log.
2. Read relevant recent Slack messages in channel `C0C9649RQAZ`.
3. Verify current external state before relying on stored notes.
4. Attempt Gemini/Claude only via a genuinely available free route; no API generation if billing or free quota is unknown.
5. Keep credentials out of logs and files.

## End of meaningful task
1. Record changes, evidence, validation, actual run IDs, real model usage, costs/API calls, blockers, cleanup, and next goal in the GitHub progress log.
2. Post a concise Slack update with links.
3. Read back the changed GitHub content and verify the Slack post.
4. If any operation failed or was not run, say so explicitly.

## Data model
- GitHub Markdown is the canonical source of truth for decisions, policies, and progress.
- Activepieces Tables stores searchable memory records and compact retrieval metadata. It is not authoritative if it disagrees with GitHub.
- Slack mirrors operational status, errors, and next actions.
- ChatGPT Custom Instructions express short stable preferences but do not automatically load the full GitHub/Slack history into each chat.

## Memory entry fields
Each record should include: `memoryId`, `createdAt`, `category`, `title`, `content`, `tags`, `sourceUrl`, `status`, `supersedes`.
Use a stable caller-supplied ID where possible. Tables do not currently guarantee atomic unique-key upsert, so duplicate/race safety must not be assumed.

## Save / search / restore behavior
- SAVE: validate required fields; append a canonical dated note to GitHub (human-reviewed or through a verified GitHub file-write path); create a searchable Activepieces index row; report both outcomes separately.
- SEARCH: filter the index by category/status and keyword; return concise matches with source links; if index results are incomplete, retrieve canonical GitHub files.
- RESTORE: return the current index/protocol, latest progress, relevant matching records, and source links; include only facts marked verified and label unknowns clearly.
- A request may never write secrets or sensitive account credentials to memory.
- Do not publish the service until webhook authentication, input validation, error paths, and sample-only tests pass.

## Safety / rollout
- New flows must stay disabled and unpublished during construction.
- Never test with Gemini/Claude generation or any billable API until free/cost-safe access is proven.
- Do not modify existing production flows or the hourly Asia/Seoul automation.
- Any production rollout requires a separate explicit approval after evidence-based validation.

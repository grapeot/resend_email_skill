# Working Notes

## Changelog

### 2026-09-26

- Added `skills/skill_suppression_analysis.md`, a focused companion skill teaching agents how to analyze team-wide suppression lists: funnel overview, bounce-rate denominators from the `/emails` send log (with retention-window caveats), complaint tracing via `source_id`, heuristic bounce classification (typos/malformed, internal, genuine hard bounces), and three fixed conclusion questions.
- The analysis skill defines a Markdown report contract (`suppression_report_<date>.md`, uncommitted by default) and a guarded reset SOP: backup, batch dry-run, per-address `--confirm-remove` execution, audit file, and complaint re-add verification. Complaints are never reset candidates.
- Registered the new skill in `docs/prd.md` and the `docs/rfc.md` repo structure.

### 2026-05-20

- Created the self-contained Resend Email Skill repository scaffold.
- Rewrote README, PRD, RFC, test strategy, AGENTS, and canonical skill docs in English for public publication.
- Added Chinese README as a secondary guide linked from the English README.
- Removed workspace-private routing notes from the repository; provider routing belongs in the parent workspace, not this public repo.
- Implemented package modules for configuration, Resend SDK client wrapping, send payload construction, received email normalization, Markdown export, attachment downloads, and CLI routing.
- Added offline unit and mocked integration tests plus default-skipped live/e2e tests.
- Added local `.env` support for direct keys or externally resolved 1Password references; `.env` is ignored by git.
- Validated `op run --env-file=.env` resolves the private local key without putting private references in public docs.
- Ran offline tests: `18 passed, 3 skipped`.
- Ran Ruff: `All checks passed!`.
- Ran live received-email list test successfully.
- Ran live send-to-self e2e successfully using explicit live/send/e2e opt-in flags.
- Added repeatable `send --header "Name: Value"` support. Headers are parsed locally, validated before network calls, included in dry-run payload summaries, and passed through as Resend `headers` objects only when provided.
- Added opt-in transient send retries through `--max-attempts`. Retry-enabled sends require a stable idempotency key, stop after at most five total attempts, and fail fast on permanent API errors.

### 2026-07-28

- Added Resend managed suppression support using Python SDK 2.35.0: paginated list/all, origin filtering, single-entry retrieval, and guarded add/remove operations.
- Kept suppression reads ephemeral. Add/remove require dry-run or operation-specific confirmation because suppressions affect every sending domain in the team.
- Expanded the privacy gate to prohibit committed suppression exports and recipient lists.

## Lessons Learned

- Resend receiving is not webhook-only. The Python SDK exposes `Emails.Receiving.list`, `Emails.Receiving.get`, and `Emails.Receiving.Attachments` helpers.
- Attachment content retrieval is two-step: get attachment metadata from Resend, then download bytes from the signed `download_url`.
- The CLI should accept `--format` at the end of commands because public examples naturally put output controls last. Argparse needs the flag registered on subcommands to support that shape.
- Send-to-self e2e tests consume quota for both send and receive, so they need separate opt-in flags beyond the base live test flag.
- Outgoing custom headers are send-payload metadata, not received-side mutation or MIME editing. Keeping them as repeatable `Name: Value` flags preserves the CLI contract without widening scope into a full MIME editor.
- Retries and idempotency are one safety feature, not independent options. Retrying without a stable key can duplicate an email after an ambiguous timeout, so both the CLI and library reject that combination before sending.
- Private 1Password references are not API keys, but still reveal vault/item structure; public docs should use placeholder references only.
- Suppressions are team-wide recipient controls, so their email addresses are private runtime output and mutation needs a stricter gate than ordinary reads.

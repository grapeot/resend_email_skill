# Working Notes

## Changelog

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

## Lessons Learned

- Resend receiving is not webhook-only. The Python SDK exposes `Emails.Receiving.list`, `Emails.Receiving.get`, and `Emails.Receiving.Attachments` helpers.
- Attachment content retrieval is two-step: get attachment metadata from Resend, then download bytes from the signed `download_url`.
- The CLI should accept `--format` at the end of commands because public examples naturally put output controls last. Argparse needs the flag registered on subcommands to support that shape.
- Send-to-self e2e tests consume quota for both send and receive, so they need separate opt-in flags beyond the base live test flag.
- Outgoing custom headers are send-payload metadata, not received-side mutation or MIME editing. Keeping them as repeatable `Name: Value` flags preserves the CLI contract without widening scope into a full MIME editor.
- Private 1Password references are not API keys, but still reveal vault/item structure; public docs should use placeholder references only.

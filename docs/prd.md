# Resend Email Skill PRD

## 1. Product Definition

Resend Email Skill is a local, AI-first email automation project. It wraps Resend send and receiving APIs behind a stable Python library, CLI, and agent skill document. The core capabilities are sending email, listing received email, retrieving received email content, exporting received email to Markdown, and reading attachment metadata or downloading attachments.

The project is not a general email client. It targets repeatable agent workflows: sending transactional or notification email from a verified sender, using Resend receiving addresses for end-to-end verification, converting received email into Markdown for agent consumption, and proving the send/receive path with explicit opt-in live tests.

## 2. Users and Use Cases

The primary user is an AI agent running in a developer workspace. The agent needs a discoverable skill document and a deterministic CLI rather than ad hoc SDK snippets.

The second user is a developer maintaining the tool. The developer needs clear installation, dry-run behavior, offline tests, live tests with explicit gates, and enough diagnostics to fix configuration or API failures quickly.

The third user is a downstream project that depends on email delivery. Such projects need a reusable way to send mail and verify delivery without embedding Resend glue code in each application.

The repository is intended to be public. Public docs, examples, fixtures, and `.env.example` must not include private vault names, private item paths, real API keys, real received email payloads, real attachments, raw MIME, or personal mailbox data.

## 3. Version Scope

Version 1 covers five surfaces.

First, email sending. The CLI supports `RESEND_FROM_EMAIL` as the default sender, `--from` as an override, and recipient/body controls including `--to`, `--cc`, `--bcc`, `--reply-to`, `--subject`, `--html`, `--text`, `--body-file`, `--body-format`, `--attach`, `--idempotency-key`, `--dry-run`, and `--confirm-send`. Real sends require `--confirm-send`.

Second, received email listing. The CLI wraps Resend's received email list API with `--limit`, `--after`, `--before`, and JSON output. The normalized result includes message id, sender, recipients, subject, creation time, and attachment metadata.

Third, received email retrieval. The CLI retrieves a single received email by id and returns HTML, text, headers, and attachment metadata. It intentionally omits raw MIME from normalized CLI output. Markdown export writes local files with YAML frontmatter, and batch export can pull recent received emails to local Markdown files.

Fourth, attachment handling. The CLI lists received email attachments and downloads attachment content through signed download URLs. Signed URLs are treated as short-lived transfer links, not durable references.

Fifth, verification. Offline tests cover payload construction and response normalization. Live tests can send a uniquely identified email to a receiving address, poll the received email API, retrieve the message, and verify subject/body matching. These tests are skipped unless explicitly enabled.

## 4. Non-Goals

Version 1 does not provide a background sync daemon, web UI, mailbox state management, multi-profile account switching, full MIME parsing, dashboard management, contact management, bulk marketing features, or arbitrary Resend API passthrough.

Version 1 does not treat Resend receiving as a personal mailbox replacement. Receiving support exists for testing, debugging, and agent-readable automation.

Version 1 does not implement a public webhook server. Polling is enough for local CLI and e2e test workflows. A webhook receiver can be added later if a production workflow needs it.

## 5. Success Criteria

A successful v1 satisfies these conditions.

First, an agent can read `skills/skill_resend_email.md` and reliably send, dry-run, list received email, retrieve received email, export Markdown, and handle attachments.

Second, CLI stdout is machine-readable JSON. Progress, warnings, and diagnostics go to stderr.

Third, the default test suite is offline. It does not send email, poll the real API, download real attachments, or consume quota.

Fourth, live and e2e tests require explicit environment flags, and write operations require a separate send-allow flag.

Fifth, installation instructions are self-contained and explain how to integrate the skill into an agent workspace that discovers skills from a global skills directory or from agent configuration files.

Sixth, the repository passes a privacy review before publication: no real keys, no real `op://` private paths, no received email payloads, no attachments, no raw MIME, no token cache, and no local data directory in git.

## 6. Risks

The main product risk is scope creep into a general email client. The project should expose only the operations agents repeatedly need.

The main safety risk is accidentally running live tests by default. Sending and receiving both count against Resend quotas, so all live behavior must be opt-in.

The main privacy risk is publishing local infrastructure details. A 1Password reference is not an API key, but private vault and item names still leak internal structure. Public docs must use placeholders.

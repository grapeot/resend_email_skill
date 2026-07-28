# Resend Email Skill

AI-first Resend email automation: send and receive email, handle attachments, and safely inspect or manage team-wide suppressions from a local CLI.

This repository is self-contained. It is not a vendor-specific packaged skill format. It provides a plain Markdown skill contract at `skills/skill_resend_email.md` plus a Python package and CLI that agents can call.

[中文说明](README.zh.md)

## What It Does

- Send email through Resend with dry-run and custom header support.
- List received email through Resend receiving APIs.
- Retrieve received email HTML/text/headers/attachment metadata.
- Export received email to Markdown for AI agents.
- List and download received email attachments.
- List, retrieve, add, and remove team-wide suppressions with guarded mutations.
- Run offline tests by default and explicit opt-in live/e2e tests.

## Install

From this repository root:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

You can also ask Codex, Claude Code, OpenCode, or another coding agent to run those commands for you.

## Configure

Copy `.env.example` to `.env` and choose one credential mode.

Direct private key:

```bash
RESEND_API_KEY=replace-with-your-resend-api-key
RESEND_FROM_EMAIL="Example Sender <no-reply@example.com>"
RESEND_RECEIVING_ADDRESS=anything@example.resend.app
```

1Password reference resolved outside Python:

```bash
RESEND_API_KEY=op://your-vault/your-item/resend_api_key
op run --env-file=.env -- resend-email doctor config --format json
```

The Python package only reads resolved environment variables. It does not call 1Password itself.

## Use the CLI

Dry-run a send:

```bash
resend-email send --to user@example.com --subject "Hello" --body-file body.md --body-format markdown --header "X-Custom: value" --dry-run --format json
```

`--header "Name: Value"` can be repeated. Header names and values are trimmed, and the dry-run JSON payload includes the resulting `headers` object for review.

Send for real after review:

```bash
resend-email send --to user@example.com --subject "Hello" --body-file body.md --body-format markdown --confirm-send --format json
```

For automated workflows, transient retries are opt-in and require a stable idempotency key. `--max-attempts` includes the initial request and accepts 1-5:

```bash
resend-email send --to user@example.com --subject "Hello" --text "Body" --idempotency-key "workflow:message-123" --max-attempts 3 --confirm-send --format json
```

List received email:

```bash
resend-email received list --limit 20 --format json
```

Retrieve and export:

```bash
resend-email received get <email_id> --format json
resend-email received export-md <email_id> --output-dir data/received/markdown --format json
resend-email received export-all-md --limit 20 --output-dir data/received/markdown --format json
```

Attachments:

```bash
resend-email received attachments list <email_id> --format json
resend-email received attachments download <email_id> <attachment_id> --output-dir data/received/attachments --format json
```

Suppressions:

```bash
resend-email suppressions list --all --limit 100 --format json
resend-email suppressions get user@example.com --format json
resend-email suppressions add user@example.com --dry-run --format json
resend-email suppressions remove user@example.com --dry-run --format json
```

Replace dry-run with `--confirm-add` or `--confirm-remove` only after review and explicit authorization. Suppressions apply across the entire Resend team.

## Install the Agent Skill

This project uses a plain Markdown skill contract, not a traditional Codex or Claude Code packaged skill format.

1. Put `skills/skill_resend_email.md` somewhere your agent can discover, usually a global or workspace `skills/` directory.
2. Look at the workspace's root guidance files such as `AGENTS.md`, `CLAUDE.md`, or equivalent.
3. If those files point to a skill index or discovery document, add this skill there.
4. If no discovery file exists, add a short note to the root guidance file telling the agent to read `skills/skill_resend_email.md` for Resend email tasks.

Example guidance:

```text
For Resend email sending, received email handling, or suppression management, read skills/skill_resend_email.md and follow its CLI contract.
```

## Test

Default tests are offline:

```bash
.venv/bin/python -m pytest -v
```

Live tests are opt-in:

```bash
RESEND_ENABLE_LIVE_TESTS=1 .venv/bin/python -m pytest -v -m live_integration
```

Real sends from the CLI require `--confirm-send`. Live tests that send email require `RESEND_LIVE_ALLOW_SEND=1`. E2E send-to-self tests also require `RESEND_LIVE_ALLOW_E2E=1` and `RESEND_RECEIVING_ADDRESS`.

## Privacy

Do not commit `.env`, API keys, private 1Password paths, suppression exports, recipient lists, received email bodies, raw MIME, attachments, local SQLite databases, or token caches. The repository is designed to be publishable with only fake examples.

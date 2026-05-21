# Resend Email Skill

## Purpose

Use Resend for agent-controlled email sending, received email listing, received email retrieval, Markdown export, and attachment handling. This file is the canonical agent contract for this repository.

This is a plain Markdown skill document, not a vendor-specific packaged skill format. Agents should read it when the user asks for Resend email operations.

## Project Setup

From the repository root:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

Configuration can be direct environment variables or 1Password references resolved before Python starts:

```bash
# Direct private .env value. Do not commit real keys.
RESEND_API_KEY=replace-with-your-resend-api-key
RESEND_FROM_EMAIL="Example Sender <no-reply@example.com>"
RESEND_RECEIVING_ADDRESS=anything@example.resend.app

# Or use 1Password references resolved by op run.
RESEND_API_KEY=op://your-vault/your-item/resend_api_key
op run --env-file=.env -- .venv/bin/python -m resend_email_skill.cli doctor config --format json
```

Do not commit `.env`, received email data, attachments, raw MIME, local SQLite databases, or token caches.

## Send Email

Always dry-run before a real send unless the user has already given clear send authorization. Real sends require `--confirm-send`.

```bash
.venv/bin/python -m resend_email_skill.cli send \
  --to user@example.com \
  --subject "Subject" \
  --body-file body.md \
  --body-format markdown \
  --dry-run \
  --format json
```

For a real send, remove `--dry-run` and add `--confirm-send`:

```bash
.venv/bin/python -m resend_email_skill.cli send \
  --to user@example.com \
  --subject "Subject" \
  --body-file body.md \
  --body-format markdown \
  --confirm-send \
  --format json
```

Override the default sender with `--from` when needed:

```bash
.venv/bin/python -m resend_email_skill.cli send \
  --from "Example Sender <no-reply@example.com>" \
  --to user@example.com \
  --subject "Subject" \
  --html "<p>Hello</p>" \
  --format json
```

## Received Email

List recent received email:

```bash
.venv/bin/python -m resend_email_skill.cli received list --limit 20 --format json
```

Retrieve a received email:

```bash
.venv/bin/python -m resend_email_skill.cli received get <email_id> --format json
```

Export a received email to Markdown:

```bash
.venv/bin/python -m resend_email_skill.cli received export-md <email_id> --output-dir data/received/markdown --format json
```

Export recent received email to local Markdown files:

```bash
.venv/bin/python -m resend_email_skill.cli received export-all-md --limit 20 --output-dir data/received/markdown --format json
```

## Attachments

List attachment metadata:

```bash
.venv/bin/python -m resend_email_skill.cli received attachments list <email_id> --format json
```

Download an attachment:

```bash
.venv/bin/python -m resend_email_skill.cli received attachments download <email_id> <attachment_id> --output-dir data/received/attachments --format json
```

Signed attachment URLs expire. Use them only for immediate downloads.

## Tests

Default tests are offline:

```bash
.venv/bin/python -m pytest -v
```

Live/e2e tests are skipped unless explicitly enabled:

```bash
RESEND_ENABLE_LIVE_TESTS=1 \
RESEND_LIVE_ALLOW_SEND=1 \
RESEND_LIVE_ALLOW_E2E=1 \
RESEND_RECEIVING_ADDRESS=anything@example.resend.app \
.venv/bin/python -m pytest -v -m live_integration tests/test_live_e2e.py
```

## Boundaries

- Do not send real email unless the user clearly asked for a real send and the command includes `--confirm-send`.
- Do not treat Resend receiving as a personal mailbox replacement.
- Do not commit private email data.
- Do not add dashboard administration, contact management, bulk marketing, or background sync behavior to this skill.

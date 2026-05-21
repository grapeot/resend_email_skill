# Resend Email Skill RFC

## 1. Background

Resend supports both sending and receiving email. The receiving surface includes listing received emails, retrieving received email content, listing received email attachments, and retrieving attachment metadata with signed download URLs. This makes a package-style project more appropriate than a pair of standalone scripts.

The repository is designed to be self-contained and public. It must not depend on a parent workspace path, private routing rules, or private infrastructure names. Workspace-specific routing belongs outside this repository.

## 2. Repository Layout

```text
resend_email_skill/
├── AGENTS.md
├── README.md
├── README.zh.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── docs/
│   ├── prd.md
│   ├── rfc.md
│   ├── test.md
│   └── working.md
├── skills/
│   └── skill_resend_email.md
├── src/
│   └── resend_email_skill/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── client.py
│       ├── sender.py
│       ├── receiver.py
│       ├── markdown.py
│       ├── attachments.py
│       └── errors.py
├── scripts/
│   └── resend-email
└── tests/
```

`config.py` loads `.env` files and environment variables into a small settings object. The supported variables are `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_RECEIVING_ADDRESS`, `RESEND_API_BASE_URL`, and `RESEND_DATA_DIR`.

`client.py` owns HTTP transport and Resend SDK integration. It exposes a narrow interface: send, list received, get received, list attachments, get attachment, and download signed URLs.

`sender.py` builds send payloads, validates required fields, loads body files, converts Markdown to HTML when requested, encodes attachments, and handles dry-run output.

`receiver.py` normalizes received email responses and implements polling for e2e tests.

`markdown.py` converts received email content into AI-readable Markdown with YAML frontmatter.

`attachments.py` handles received email attachment metadata and downloads.

`cli.py` is a thin argparse shell. It parses arguments, calls library functions, and emits JSON. Business logic belongs in library modules.

## 3. Authentication

The package consumes a resolved `RESEND_API_KEY` from the environment. It also supports `.env` loading for local development.

Two key-injection modes are supported:

```bash
# Direct private .env value
RESEND_API_KEY=replace-with-your-resend-api-key

# 1Password reference resolved outside Python
RESEND_API_KEY=op://your-vault/your-item/resend_api_key
op run --env-file=.env -- resend-email doctor config --format json
```

The Python code does not call 1Password. This keeps the implementation portable and avoids GUI or service-account assumptions. Environments that use 1Password should resolve `op://...` references before invoking the CLI.

## 4. CLI Contract

The CLI uses subcommands so sending, receiving, reading, and attachment operations share configuration and error handling.

```bash
resend-email doctor config --format json

resend-email send \
  --to user@example.com \
  --subject "Subject" \
  --body-file body.md \
  --body-format markdown \
  --dry-run \
  --format json

resend-email received list --limit 20 --format json
resend-email received get <email_id> --format json
resend-email received export-md <email_id> --output-dir data/received/markdown --format json
resend-email received attachments list <email_id> --format json
resend-email received attachments download <email_id> <attachment_id> --output-dir data/received/attachments --format json
resend-email received poll --subject-prefix "[resend-e2e]" --timeout 60 --format json
```

When `--format json` is set, stdout contains exactly one JSON object. Progress and polling messages go to stderr. Errors include `error`, `error_type`, `status_code`, and `response` when available.

## 5. Send Design

Sending requires `from`, at least one `to` recipient, `subject`, and at least one body field. `RESEND_FROM_EMAIL` provides the default sender. `--from` overrides it.

`--body-file` supports Markdown, HTML, and plain text. `--body-format` can override suffix inference. Markdown is converted to email-safe HTML for the `html` field. Text files populate `text`. Explicit `--html` and `--text` are also supported.

Attachments are read from local files and encoded as Resend-compatible attachment dictionaries with filename, content, and content type. Missing attachment files fail before any network call.

Dry-run mode builds and validates the payload but does not call Resend.

## 6. Receive Design

The default receive workflow is polling. The CLI calls the received email list API, optionally follows cursors, and can poll for a subject prefix during e2e tests. This avoids requiring a public webhook endpoint for local development.

Received email is not synchronized by default. `received list` and `received get` read remote data and return JSON. `export-md` and attachment download are the operations that write local files.

Local private data lives under `data/` and is ignored by git:

```text
data/received/
├── markdown/
├── raw/
├── attachments/
└── received.db   # deferred until a local index is needed
```

## 7. Agent Installation Model

This repository does not use a vendor-specific skill format. It ships a plain Markdown skill contract at `skills/skill_resend_email.md`.

For Codex, Claude Code, OpenCode, or similar agents, installation means:

1. Clone or copy this repository.
2. Install the Python package in its project virtual environment.
3. Copy or reference `skills/skill_resend_email.md` from the agent's global skills directory.
4. Update the agent's workspace guidance file so it knows to read that skill when the user asks for Resend email operations.

If the workspace has a skill index or discovery file, add the skill there. If not, add a short note to the root `AGENTS.md`, `CLAUDE.md`, or equivalent file used by that agent.

## 8. Privacy Review

Before publishing or pushing, run a privacy check:

```bash
git status --short
rg -n "re_[A-Za-z0-9]{20,}|op://[^\s]+/[^\s]+/[^\s]+|RESEND_API_KEY=.*re_|BEGIN PRIVATE|@.*resend\.app" .
```

Expected examples should use placeholders. Private `.env`, local data, raw MIME, attachments, SQLite databases, and token caches must remain out of git.

## 9. Deferred

Deferred features include webhook server support, background sync, multiple named profiles, message delete/archive semantics, full MIME parsing, full-text indexing, and dashboard administration.

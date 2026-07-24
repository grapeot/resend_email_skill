# Resend Email Skill Test Strategy

## 1. Goals

The tests verify three properties. First, the default suite is offline and never sends email or consumes quota. Second, the CLI/library contract is stable enough for agents to consume JSON output. Third, live tests can prove the real Resend send/receive path when explicitly enabled.

## 2. Unit Tests

Unit tests cover local logic:

- `.env` and environment parsing.
- Missing `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and `RESEND_RECEIVING_ADDRESS` errors.
- Send payload construction: default sender, explicit sender, recipients, cc/bcc/reply-to, subject, HTML, text, body files, custom headers, and attachments.
- Markdown, HTML, and text body-file handling.
- Attachment content-type inference and byte encoding.
- Custom header parsing for single headers, multiple headers, invalid missing-colon input, empty names, and empty values.
- Resend API error mapping.
- Retry safety: idempotency-key requirement, 1-5 attempt bound, transient status/connection retries, permanent-error fail-fast behavior, and retry exhaustion.
- Received email response normalization.
- Markdown export frontmatter and body-source selection.

## 3. Mocked Integration Tests

Mocked integration tests verify CLI-to-library seams with fake clients:

- `doctor config --format json` prints masked configuration status.
- `send --dry-run --format json` builds payloads without network calls.
- `send --header "X-Custom: value" --dry-run --format json` includes parsed headers in the dry-run payload.
- `send` with a fake client returns a stable email id JSON object.
- `send --max-attempts N` passes the bounded attempt count to the client and rejects retries without `--idempotency-key`, including in dry-run mode.
- `received list` handles empty and populated results.
- `received get` returns normalized body/header/attachment fields.
- `received export-md` writes Markdown and returns its path.
- `received attachments download` writes bytes from a fake signed URL.
- `received poll` succeeds when a fake list response eventually includes the subject and fails clearly on timeout.

## 4. Live Integration Tests

Live tests are skipped by default.

```bash
RESEND_ENABLE_LIVE_TESTS=1 .venv/bin/python -m pytest -v -m live_integration
```

Live tests may get credentials either from a direct private environment variable or from a 1Password reference resolved by `op run`:

```bash
op run --env-file=.env -- .venv/bin/python -m pytest -v -m live_integration
```

Real sending requires an additional flag:

```bash
RESEND_ENABLE_LIVE_TESTS=1 \
RESEND_LIVE_ALLOW_SEND=1 \
.venv/bin/python -m pytest -v -m live_integration tests/test_live_send.py
```

End-to-end send-to-self requires all live flags plus a receiving address:

```bash
RESEND_ENABLE_LIVE_TESTS=1 \
RESEND_LIVE_ALLOW_SEND=1 \
RESEND_LIVE_ALLOW_E2E=1 \
RESEND_RECEIVING_ADDRESS=anything@example.resend.app \
.venv/bin/python -m pytest -v -m live_integration tests/test_live_e2e.py
```

E2E tests send a real email and poll the received email API. They consume quota. The subject must include a unique token such as `[resend-e2e:<uuid>]`.

## 5. E2E Acceptance Criteria

An e2e test passes only when:

1. The send API returns an email id.
2. The received email list shows the unique subject within the timeout.
3. The retrieved message matches expected from/to/subject fields.
4. The text or HTML body contains the unique test token.
5. If attachments are included, the downloaded attachment hash matches the source file.

## 6. Smoke Checks

After implementation changes, run:

```bash
.venv/bin/python -m pytest -v
.venv/bin/python -m resend_email_skill.cli doctor config --format json
.venv/bin/python -m resend_email_skill.cli send --to test@example.com --subject "Dry run" --body-file docs/test.md --body-format markdown --header "X-Custom: value" --dry-run --format json
```

If live credentials are not available, stop at offline tests and dry-run smoke checks.

## 7. Public Repository Privacy Gate

Before publishing:

```bash
git status --short
rg -n "re_[A-Za-z0-9]{20,}|op://[^\s]+/[^\s]+/[^\s]+|RESEND_API_KEY=.*re_|BEGIN PRIVATE|@.*resend\.app" .
```

Clean any real key, real 1Password path, real receiving address, real email body, attachment sample, raw MIME, or private data path before committing.

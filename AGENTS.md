# Resend Email Skill

## Project role

This repository provides an AI-first Resend email skill: a Python library, CLI, and skill document for sending email, handling received email and attachments, and safely inspecting or managing team-wide suppressions.

It is not a general email client, a dashboard replacement, or a broad Resend API passthrough. Every command should serve an agent workflow with a stable contract and clear safety boundaries.

## Project structure

- `README.md`: public installation and usage guide, English first with a link to Chinese.
- `README.zh.md`: Chinese usage guide.
- `docs/prd.md`: product scope and success criteria.
- `docs/rfc.md`: architecture, CLI, configuration, and privacy decisions.
- `docs/test.md`: unit, mocked integration, live integration, and e2e strategy.
- `docs/working.md`: changelog and lessons learned.
- `skills/skill_resend_email.md`: canonical agent skill document.
- `src/resend_email_skill/`: reusable Python package.
- `scripts/`: stable wrappers for humans and agents.
- `tests/`: default offline tests plus opt-in live/e2e tests.

## Environment rules

- Use the project virtual environment: `uv venv .venv`, then `source .venv/bin/activate`.
- Install dependencies with `uv pip install -e '.[dev]'`; do not use bare `pip install`.
- Never commit real API keys, webhook secrets, received email bodies, attachments, raw MIME, token caches, SQLite data, or private `.env` files.
- This repository is intended to be publishable. Public docs, examples, and fixtures must use fake addresses, fake domains, and fake 1Password references.
- Authentication supports both direct `RESEND_API_KEY` values and `op://...` references resolved by `op run --env-file=.env -- <command>`. The Python code consumes environment variables after resolution; it must not call 1Password itself.

## Safety boundaries

- Real sends, real receive polling, real attachment downloads, and e2e tests are disabled by default.
- Live tests require `RESEND_ENABLE_LIVE_TESTS=1`.
- Write tests require `RESEND_LIVE_ALLOW_SEND=1` in addition to the base live flag.
- End-to-end send-to-self tests require `RESEND_LIVE_ALLOW_E2E=1` and must use unique subject tokens to avoid matching old email.

## Maintenance

- Update `docs/working.md` after meaningful design or implementation changes.
- Keep `docs/rfc.md`, `docs/test.md`, and `skills/skill_resend_email.md` aligned with CLI contract changes.
- This directory is an independent git repository. Commit from this repository root, not from a parent workspace.

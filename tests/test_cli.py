from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from resend_email_skill import cli


class FakeClient:
    def __init__(self, settings) -> None:
        self.settings = settings

    def send_email(self, payload, idempotency_key=None):
        return {"id": "sent-1", "idempotency_key": idempotency_key, "payload_subject": payload["subject"], "payload": payload}

    def list_received(self, *, limit=20, after=None, before=None):
        _ = (limit, after, before)
        return {"object": "list", "data": [{"id": "email-1", "subject": "Hello"}, {"id": "email-2", "subject": "World"}], "has_more": False}

    def get_received(self, email_id):
        return {"id": email_id, "from": "a@example.com", "to": ["b@example.com"], "subject": f"Hello {email_id}", "text": "Body", "attachments": [], "raw": "private mime"}

    def list_received_attachments(self, email_id, *, limit=100, after=None, before=None):
        _ = (email_id, limit, after, before)
        return {"object": "list", "data": [{"id": "att-1", "filename": "hello.txt"}], "has_more": False}

    def get_received_attachment(self, email_id, attachment_id):
        _ = email_id
        return {"id": attachment_id, "filename": "hello.txt", "download_url": "https://example.com/hello.txt"}

    def download_url(self, url):
        _ = url
        return b"hello"


def parse_stdout(stdout: str) -> dict[str, Any]:
    return json.loads(stdout)


def test_cli_doctor_masks_config(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "Example <no-reply@example.com>")
    assert cli.main(["doctor", "config", "--format", "json"]) == 0
    payload = parse_stdout(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["config"]["api_key_ready"] is True
    assert payload["config"]["api_key"] == "test...-key"


def test_cli_send_dry_run(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "Example <no-reply@example.com>")
    assert cli.main(["send", "--to", "user@example.com", "--subject", "Hi", "--text", "Body", "--dry-run", "--format", "json"]) == 0
    payload = parse_stdout(capsys.readouterr().out)
    assert payload["status"] == "dry_run"
    assert payload["payload"]["to"] == ["user@example.com"]


def test_cli_send_dry_run_includes_single_header(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "Example <no-reply@example.com>")
    assert (
        cli.main(
            [
                "send",
                "--to",
                "user@example.com",
                "--subject",
                "Hi",
                "--text",
                "Body",
                "--header",
                "X-Custom: value",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = parse_stdout(capsys.readouterr().out)
    assert payload["payload"]["headers"] == {"X-Custom": "value"}


def test_cli_send_uses_multiple_headers(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "Example <no-reply@example.com>")
    monkeypatch.setattr(cli, "ResendClient", FakeClient)
    assert (
        cli.main(
            [
                "send",
                "--to",
                "user@example.com",
                "--subject",
                "Hi",
                "--text",
                "Body",
                "--header",
                "X-Trace: abc",
                "--header",
                "X-Campaign: launch",
                "--confirm-send",
            ]
        )
        == 0
    )
    payload = parse_stdout(capsys.readouterr().out)
    assert payload["response"]["payload"]["headers"] == {"X-Trace": "abc", "X-Campaign": "launch"}


def test_cli_send_rejects_invalid_header(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "Example <no-reply@example.com>")
    assert cli.main(["send", "--to", "user@example.com", "--subject", "Hi", "--text", "Body", "--header", "X-Custom", "--dry-run"]) == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_type"] == "validation_error"


def test_cli_send_uses_client(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "Example <no-reply@example.com>")
    monkeypatch.setattr(cli, "ResendClient", FakeClient)
    assert cli.main(["send", "--to", "user@example.com", "--subject", "Hi", "--text", "Body", "--idempotency-key", "idem-1", "--confirm-send"]) == 0
    payload = parse_stdout(capsys.readouterr().out)
    assert payload["response"]["id"] == "sent-1"
    assert payload["response"]["idempotency_key"] == "idem-1"


def test_cli_real_send_requires_confirmation(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "Example <no-reply@example.com>")
    monkeypatch.setattr(cli, "ResendClient", FakeClient)
    assert cli.main(["send", "--to", "user@example.com", "--subject", "Hi", "--text", "Body"]) == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_type"] == "send_not_confirmed"


def test_cli_received_list(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setattr(cli, "ResendClient", FakeClient)
    assert cli.main(["received", "list", "--limit", "5"]) == 0
    payload = parse_stdout(capsys.readouterr().out)
    assert payload["data"][0]["id"] == "email-1"


def test_cli_export_markdown(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setattr(cli, "ResendClient", FakeClient)
    assert cli.main(["received", "export-md", "email-1", "--output-dir", str(tmp_path)]) == 0
    payload = parse_stdout(capsys.readouterr().out)
    assert Path(payload["path"]).exists()
    assert "raw" not in payload["email"]


def test_cli_export_all_markdown(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setattr(cli, "ResendClient", FakeClient)
    assert cli.main(["received", "export-all-md", "--limit", "2", "--output-dir", str(tmp_path)]) == 0
    payload = parse_stdout(capsys.readouterr().out)
    assert payload["count"] == 2
    assert len(payload["paths"]) == 2
    assert all(Path(path).exists() for path in payload["paths"])


def test_cli_attachment_download(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setattr(cli, "ResendClient", FakeClient)
    assert cli.main(["received", "attachments", "download", "email-1", "att-1", "--output-dir", str(tmp_path)]) == 0
    payload = parse_stdout(capsys.readouterr().out)
    assert Path(payload["path"]).read_bytes() == b"hello"

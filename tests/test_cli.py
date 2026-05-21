from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from resend_email_skill import cli


class FakeClient:
    def __init__(self, settings) -> None:
        self.settings = settings

    def send_email(self, payload, idempotency_key=None):
        return {"id": "sent-1", "idempotency_key": idempotency_key, "payload_subject": payload["subject"]}

    def list_received(self, *, limit=20, after=None, before=None):
        return {"object": "list", "data": [{"id": "email-1", "subject": "Hello"}], "has_more": False}

    def get_received(self, email_id):
        return {"id": email_id, "from": "a@example.com", "to": ["b@example.com"], "subject": "Hello", "text": "Body", "attachments": []}

    def list_received_attachments(self, email_id, *, limit=100, after=None, before=None):
        return {"object": "list", "data": [{"id": "att-1", "filename": "hello.txt"}], "has_more": False}

    def get_received_attachment(self, email_id, attachment_id):
        return {"id": attachment_id, "filename": "hello.txt", "download_url": "https://example.com/hello.txt"}

    def download_url(self, url):
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


def test_cli_send_uses_client(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "Example <no-reply@example.com>")
    monkeypatch.setattr(cli, "ResendClient", FakeClient)
    assert cli.main(["send", "--to", "user@example.com", "--subject", "Hi", "--text", "Body", "--idempotency-key", "idem-1"]) == 0
    payload = parse_stdout(capsys.readouterr().out)
    assert payload["response"]["id"] == "sent-1"
    assert payload["response"]["idempotency_key"] == "idem-1"


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


def test_cli_attachment_download(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "test-secret-key")
    monkeypatch.setattr(cli, "ResendClient", FakeClient)
    assert cli.main(["received", "attachments", "download", "email-1", "att-1", "--output-dir", str(tmp_path)]) == 0
    payload = parse_stdout(capsys.readouterr().out)
    assert Path(payload["path"]).read_bytes() == b"hello"

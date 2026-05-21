from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from resend_email_skill.attachments import normalize_attachment_list, write_attachment
from resend_email_skill.errors import ValidationError
from resend_email_skill.markdown import email_to_markdown, export_markdown
from resend_email_skill.receiver import normalize_email, normalize_list_response, poll_for_subject


def test_normalize_list_response_handles_missing_optional_fields() -> None:
    response: dict[str, Any] = {"object": "list", "has_more": False, "data": [{"id": "e1", "from": "a@example.com", "to": ["b@example.com"]}]}
    normalized = normalize_list_response(response)
    data = normalized["data"]
    assert isinstance(data, list)
    assert data[0]["id"] == "e1"
    assert data[0]["attachments"] == []
    assert normalized["has_more"] is False


def test_email_to_markdown_prefers_text() -> None:
    content = email_to_markdown(
        {
            "id": "email-1",
            "from": "a@example.com",
            "to": ["b@example.com"],
            "subject": "Hello",
            "text": "Plain body",
            "html": "<p>HTML body</p>",
            "attachments": [],
        }
    )
    assert "body_source: text" in content
    assert "Plain body" in content
    assert "HTML body" not in content


def test_export_markdown_writes_file(tmp_path: Path) -> None:
    path = export_markdown({"id": "email-1", "subject": "Hello World", "html": "<p>Hi</p>"}, tmp_path)
    assert path.exists()
    assert path.name.startswith("hello-world_email-1")
    assert "Hi" in path.read_text(encoding="utf-8")


def test_normalize_attachment_list() -> None:
    response: dict[str, Any] = {"data": [{"id": "a1", "filename": "x.pdf", "download_url": "https://example.com/x"}], "has_more": False}
    normalized = normalize_attachment_list(response)
    data = normalized["data"]
    assert isinstance(data, list)
    assert data[0]["filename"] == "x.pdf"
    assert data[0]["download_url"] == "https://example.com/x"


def test_write_attachment(tmp_path: Path) -> None:
    path = write_attachment(b"abc", tmp_path, "hello world.txt", "att-1")
    assert path.name == "hello-world.txt"
    assert path.read_bytes() == b"abc"


class FakePollClient:
    def __init__(self) -> None:
        self.calls = 0

    def list_received(self, *, limit: int = 20, after: str | None = None, before: str | None = None) -> dict[str, Any]:
        self.calls += 1
        if self.calls < 2:
            return {"data": [], "has_more": False}
        return {"data": [{"id": "e1", "subject": "[token] hello"}], "has_more": False}

    def get_received(self, email_id: str) -> dict[str, Any]:
        return normalize_email({"id": email_id})


def test_poll_for_subject_finds_message() -> None:
    found = poll_for_subject(FakePollClient(), "[token]", timeout=5, interval=0)
    assert found["id"] == "e1"


def test_poll_for_subject_requires_prefix() -> None:
    with pytest.raises(ValidationError, match="subject-prefix"):
        poll_for_subject(FakePollClient(), "", timeout=1, interval=0)

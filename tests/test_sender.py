from __future__ import annotations

from pathlib import Path

import pytest

from resend_email_skill.config import Settings
from resend_email_skill.errors import ValidationError
from resend_email_skill.sender import build_send_payload, split_addresses


def settings() -> Settings:
    return Settings(
        api_key="test-key",
        from_email="Example <no-reply@example.com>",
        receiving_address=None,
        api_base_url="https://api.resend.com",
        data_dir=Path("data"),
    )


def test_split_addresses_accepts_commas_and_repeated_flags() -> None:
    assert split_addresses(["a@example.com,b@example.com", "c@example.com"]) == [
        "a@example.com",
        "b@example.com",
        "c@example.com",
    ]


def test_build_send_payload_from_markdown_file(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text("# Hello\n\nThis is **fine**.", encoding="utf-8")

    payload = build_send_payload(
        settings=settings(),
        from_email=None,
        to=["user@example.com"],
        subject="Hello",
        body_file=str(body),
        body_format="markdown",
    )

    assert payload["from"] == "Example <no-reply@example.com>"
    assert payload["to"] == ["user@example.com"]
    assert payload["subject"] == "Hello"
    assert "<h1>Hello</h1>" in payload["html"]


def test_build_send_payload_encodes_attachments(tmp_path: Path) -> None:
    attachment = tmp_path / "hello.txt"
    attachment.write_text("hi", encoding="utf-8")

    payload = build_send_payload(
        settings=settings(),
        from_email="Sender <sender@example.com>",
        to=["user@example.com"],
        subject="With attachment",
        text="body",
        attach=[str(attachment)],
    )

    assert payload["from"] == "Sender <sender@example.com>"
    assert payload["attachments"][0]["filename"] == "hello.txt"
    assert payload["attachments"][0]["content"] == list(b"hi")
    assert payload["attachments"][0]["content_type"] == "text/plain"


def test_build_send_payload_requires_body() -> None:
    with pytest.raises(ValidationError, match="Email body is required"):
        build_send_payload(settings=settings(), from_email=None, to=["user@example.com"], subject="No body")


def test_build_send_payload_requires_sender() -> None:
    no_sender = Settings(None, None, None, "https://api.resend.com", Path("data"))
    with pytest.raises(ValidationError, match="Sender is required"):
        build_send_payload(settings=no_sender, from_email=None, to=["user@example.com"], subject="Hi", text="Body")

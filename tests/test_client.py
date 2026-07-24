from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from resend_email_skill.client import ResendClient
from resend_email_skill.config import Settings
from resend_email_skill.errors import ApiError, ValidationError


class FakeSdkError(Exception):
    def __init__(self, message: str, *, code: int | None = None, error_type: str = "api_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.error_type = error_type


def make_client() -> ResendClient:
    return ResendClient(
        Settings(
            api_key="test-key",
            from_email="Example <no-reply@example.com>",
            receiving_address=None,
            api_base_url="https://api.resend.com",
            data_dir=Path("data"),
        )
    )


def install_fake_resend(monkeypatch, send):
    fake_resend = SimpleNamespace(api_key=None, api_url=None, Emails=SimpleNamespace(send=send))
    monkeypatch.setitem(sys.modules, "resend", fake_resend)
    monkeypatch.setattr("resend_email_skill.client.time.sleep", lambda _: None)
    return fake_resend


def test_send_retries_transient_error_with_same_idempotency_key(monkeypatch) -> None:
    calls = []

    def send(payload, options):
        calls.append((payload, options))
        if len(calls) == 1:
            raise FakeSdkError("busy", code=503)
        return {"id": "sent-1"}

    install_fake_resend(monkeypatch, send)
    response = make_client().send_email({"subject": "Hello"}, idempotency_key="stable-key", max_attempts=3)

    assert response == {"id": "sent-1"}
    assert len(calls) == 2
    assert all(options == {"idempotency_key": "stable-key"} for _, options in calls)


def test_send_does_not_retry_non_transient_error(monkeypatch) -> None:
    calls = []

    def send(payload, options):
        calls.append((payload, options))
        raise FakeSdkError("invalid", code=422)

    install_fake_resend(monkeypatch, send)
    with pytest.raises(ApiError) as exc_info:
        make_client().send_email({"subject": "Hello"}, idempotency_key="stable-key", max_attempts=3)

    assert exc_info.value.status_code == 422
    assert len(calls) == 1


def test_send_stops_after_max_attempts(monkeypatch) -> None:
    calls = []

    def send(payload, options):
        calls.append((payload, options))
        raise FakeSdkError("rate limited", code=429)

    install_fake_resend(monkeypatch, send)
    with pytest.raises(ApiError) as exc_info:
        make_client().send_email({"subject": "Hello"}, idempotency_key="stable-key", max_attempts=3)

    assert exc_info.value.status_code == 429
    assert len(calls) == 3


def test_send_retries_connection_error(monkeypatch) -> None:
    calls = []

    def send(payload, options):
        calls.append((payload, options))
        if len(calls) == 1:
            raise FakeSdkError("connection reset", error_type="ConnectionError")
        return {"id": "sent-1"}

    install_fake_resend(monkeypatch, send)
    assert make_client().send_email({"subject": "Hello"}, idempotency_key="stable-key", max_attempts=2) == {"id": "sent-1"}
    assert len(calls) == 2


def test_send_retries_require_idempotency_key() -> None:
    with pytest.raises(ValidationError, match="idempotency key"):
        make_client().send_email({"subject": "Hello"}, max_attempts=2)


@pytest.mark.parametrize("max_attempts", [0, 6])
def test_send_rejects_attempt_count_outside_safety_bound(max_attempts) -> None:
    with pytest.raises(ValidationError, match="between 1 and 5"):
        make_client().send_email({"subject": "Hello"}, idempotency_key="stable-key", max_attempts=max_attempts)

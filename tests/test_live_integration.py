from __future__ import annotations

import os
import uuid

import pytest

from resend_email_skill.config import load_settings
from resend_email_skill.client import ResendClient
from resend_email_skill.markdown import export_markdown
from resend_email_skill.receiver import poll_for_subject
from resend_email_skill.sender import build_send_payload


pytestmark = pytest.mark.live_integration


def require_live() -> None:
    if os.getenv("RESEND_ENABLE_LIVE_TESTS") != "1":
        pytest.skip("Set RESEND_ENABLE_LIVE_TESTS=1 to run live Resend tests.")


def require_send() -> None:
    require_live()
    if os.getenv("RESEND_LIVE_ALLOW_SEND") != "1":
        pytest.skip("Set RESEND_LIVE_ALLOW_SEND=1 to send real email.")


def require_e2e() -> None:
    require_send()
    if os.getenv("RESEND_LIVE_ALLOW_E2E") != "1":
        pytest.skip("Set RESEND_LIVE_ALLOW_E2E=1 to run send-to-self e2e tests.")


def test_live_list_received() -> None:
    require_live()
    client = ResendClient(load_settings())
    response = client.list_received(limit=1)
    assert "data" in response


def test_live_list_suppressions() -> None:
    require_live()
    client = ResendClient(load_settings())
    response = client.list_suppressions(limit=1)
    assert "data" in response


def test_live_export_recent_received_to_markdown(tmp_path) -> None:
    require_live()
    client = ResendClient(load_settings())
    response = client.list_received(limit=5)
    exported = []
    for item in response.get("data", []):
        email_id = item.get("id")
        if not email_id:
            continue
        exported.append(export_markdown(client.get_received(str(email_id)), tmp_path))
    assert len(exported) == len(response.get("data", []))
    assert all(path.exists() for path in exported)


def test_live_send_dry_payload_only() -> None:
    require_live()
    settings = load_settings()
    payload = build_send_payload(
        settings=settings,
        from_email=None,
        to=["user@example.com"],
        subject="Dry payload only",
        text="This test does not send.",
    )
    assert payload["subject"] == "Dry payload only"


def test_live_send_to_receiving_address_e2e() -> None:
    require_e2e()
    settings = load_settings()
    assert settings.receiving_address, "RESEND_RECEIVING_ADDRESS is required for e2e."
    token = f"[resend-e2e:{uuid.uuid4()}]"
    client = ResendClient(settings)
    payload = build_send_payload(
        settings=settings,
        from_email=None,
        to=[settings.receiving_address],
        subject=f"{token} delivery check",
        text=f"Token: {token}",
    )
    send_response = client.send_email(payload, idempotency_key=token)
    assert send_response.get("id")
    listed = poll_for_subject(client, token, timeout=90, interval=3, limit=20)
    received = client.get_received(str(listed["id"]))
    assert token in str(received.get("subject"))
    assert token in str(received.get("text") or received.get("html"))

from __future__ import annotations

import time
from typing import Any, Protocol

from resend_email_skill.errors import ValidationError

JsonObject = dict[str, Any]


class ReceivedClient(Protocol):
    def list_received(self, *, limit: int = 20, after: str | None = None, before: str | None = None) -> JsonObject: ...
    def get_received(self, email_id: str) -> JsonObject: ...


def normalize_email(email: JsonObject) -> JsonObject:
    return {
        "id": email.get("id"),
        "from": email.get("from"),
        "to": email.get("to") or [],
        "cc": email.get("cc") or [],
        "bcc": email.get("bcc") or [],
        "reply_to": email.get("reply_to") or [],
        "subject": email.get("subject"),
        "created_at": email.get("created_at"),
        "message_id": email.get("message_id"),
        "html": email.get("html"),
        "text": email.get("text"),
        "headers": email.get("headers") or {},
        "attachments": email.get("attachments") or [],
    }


def normalize_list_response(response: JsonObject) -> JsonObject:
    data = [normalize_email(item) for item in response.get("data", [])]
    return {"object": response.get("object", "list"), "data": data, "has_more": bool(response.get("has_more", False))}


def poll_for_subject(client: ReceivedClient, subject_prefix: str, timeout: int, interval: float = 2.0, limit: int = 20) -> JsonObject:
    if not subject_prefix:
        raise ValidationError("--subject-prefix is required for polling.")
    deadline = time.time() + timeout
    while time.time() <= deadline:
        response = normalize_list_response(client.list_received(limit=limit))
        for item in response["data"]:
            if str(item.get("subject") or "").startswith(subject_prefix):
                return item
        time.sleep(interval)
    raise ValidationError(f"No received email found with subject prefix {subject_prefix!r} within {timeout}s.")

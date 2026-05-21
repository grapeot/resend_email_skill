from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from markdown import markdown

from resend_email_skill.config import Settings
from resend_email_skill.errors import ValidationError


@dataclass(frozen=True)
class BodyContent:
    html: str | None = None
    text: str | None = None


def split_addresses(values: list[str] | None) -> list[str]:
    addresses: list[str] = []
    for value in values or []:
        addresses.extend(part.strip() for part in value.split(",") if part.strip())
    return addresses


def load_body(body_file: str | None, body_format: str | None, html: str | None, text: str | None) -> BodyContent:
    if html and text:
        return BodyContent(html=html, text=text)
    if html:
        return BodyContent(html=html)
    if text:
        return BodyContent(text=text)
    if not body_file:
        return BodyContent()

    path = Path(body_file)
    if not path.exists():
        raise ValidationError(f"--body-file not found: {body_file}")
    content = path.read_text(encoding="utf-8")
    fmt = (body_format or path.suffix.lstrip(".") or "text").lower()
    if fmt in {"md", "markdown"}:
        return BodyContent(html=markdown(content, extensions=["extra", "sane_lists"]))
    if fmt in {"html", "htm"}:
        return BodyContent(html=content)
    if fmt in {"txt", "text", "plain"}:
        return BodyContent(text=content)
    raise ValidationError(f"Unsupported body format: {fmt}")


def build_attachments(paths: list[str] | None) -> list[dict[str, Any]]:
    attachments: list[dict[str, Any]] = []
    for item in paths or []:
        path = Path(item)
        if not path.exists():
            raise ValidationError(f"Attachment not found: {item}")
        content_type, _ = mimetypes.guess_type(path.name)
        attachment: dict[str, Any] = {
            "filename": path.name,
            "content": list(path.read_bytes()),
        }
        if content_type:
            attachment["content_type"] = content_type
        attachments.append(attachment)
    return attachments


def build_send_payload(
    *,
    settings: Settings,
    from_email: str | None,
    to: list[str],
    subject: str,
    html: str | None = None,
    text: str | None = None,
    body_file: str | None = None,
    body_format: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: list[str] | None = None,
    attach: list[str] | None = None,
) -> dict[str, Any]:
    sender = from_email or settings.from_email
    if not sender:
        raise ValidationError("Sender is required. Set RESEND_FROM_EMAIL or pass --from.")
    recipients = split_addresses(to)
    if not recipients:
        raise ValidationError("At least one --to recipient is required.")
    if not subject:
        raise ValidationError("--subject is required.")
    body = load_body(body_file, body_format, html, text)
    if not body.html and not body.text:
        raise ValidationError("Email body is required. Pass --html, --text, or --body-file.")

    payload: dict[str, Any] = {"from": sender, "to": recipients, "subject": subject}
    if body.html:
        payload["html"] = body.html
    if body.text:
        payload["text"] = body.text
    cc_values = split_addresses(cc)
    bcc_values = split_addresses(bcc)
    reply_to_values = split_addresses(reply_to)
    attachments = build_attachments(attach)
    if cc_values:
        payload["cc"] = cc_values
    if bcc_values:
        payload["bcc"] = bcc_values
    if reply_to_values:
        payload["reply_to"] = reply_to_values
    if attachments:
        payload["attachments"] = attachments
    return payload


def summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload)
    if "html" in summary:
        summary["html"] = f"<html {len(payload['html'])} chars>"
    if "text" in summary:
        summary["text"] = f"<text {len(payload['text'])} chars>"
    if "attachments" in summary:
        summary["attachments"] = [
            {"filename": item.get("filename"), "content_type": item.get("content_type"), "size": len(item.get("content", []))}
            for item in summary["attachments"]
        ]
    return summary

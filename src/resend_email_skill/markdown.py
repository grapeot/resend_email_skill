from __future__ import annotations

from pathlib import Path
from re import sub
from typing import Any

import yaml
from markdownify import markdownify as html_to_markdown

from resend_email_skill.receiver import normalize_email


def _slug(value: str) -> str:
    slug = sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-").lower()
    return slug[:80] or "email"


def email_to_markdown(email: dict[str, Any]) -> str:
    normalized = normalize_email(email)
    body_source = "text" if normalized.get("text") else "html"
    body = normalized.get("text") or html_to_markdown(normalized.get("html") or "")
    frontmatter = {
        "resend_email_id": normalized.get("id"),
        "from": normalized.get("from"),
        "to": normalized.get("to"),
        "cc": normalized.get("cc"),
        "subject": normalized.get("subject"),
        "created_at": normalized.get("created_at"),
        "message_id": normalized.get("message_id"),
        "body_source": body_source,
        "attachments": normalized.get("attachments"),
    }
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_text}---\n\n{body.strip()}\n"


def export_markdown(email: dict[str, Any], output_dir: Path) -> Path:
    normalized = normalize_email(email)
    output_dir.mkdir(parents=True, exist_ok=True)
    email_id = str(normalized.get("id") or "email")
    subject = str(normalized.get("subject") or "email")
    path = output_dir / f"{_slug(subject)}_{_slug(email_id)}.md"
    path.write_text(email_to_markdown(email), encoding="utf-8")
    return path

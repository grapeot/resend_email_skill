from __future__ import annotations

from pathlib import Path
from re import sub
from typing import Any

JsonObject = dict[str, Any]


def normalize_attachment(attachment: JsonObject) -> JsonObject:
    return {
        "id": attachment.get("id"),
        "filename": attachment.get("filename"),
        "content_type": attachment.get("content_type"),
        "content_disposition": attachment.get("content_disposition"),
        "content_id": attachment.get("content_id"),
        "size": attachment.get("size"),
        "download_url": attachment.get("download_url"),
        "expires_at": attachment.get("expires_at"),
    }


def normalize_attachment_list(response: JsonObject) -> JsonObject:
    return {
        "object": response.get("object", "list"),
        "data": [normalize_attachment(item) for item in response.get("data", [])],
        "has_more": bool(response.get("has_more", False)),
    }


def safe_filename(value: str | None, fallback: str) -> str:
    raw = value or fallback
    name = sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-")
    if name in {".", ".."}:
        return fallback
    return name or fallback


def write_attachment(content: bytes, output_dir: Path, filename: str | None, attachment_id: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / safe_filename(filename, f"{attachment_id}.bin")
    path.write_bytes(content)
    return path

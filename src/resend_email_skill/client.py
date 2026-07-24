from __future__ import annotations

import time
from typing import Any

import requests

from resend_email_skill.config import Settings, require_api_key
from resend_email_skill.errors import ApiError, ValidationError


RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def is_retryable_api_error(error: ApiError) -> bool:
    try:
        if error.status_code is not None and int(error.status_code) in RETRYABLE_STATUS_CODES:
            return True
    except (TypeError, ValueError):
        pass
    error_name = error.error_type.lower()
    return "timeout" in error_name or "connection" in error_name


class ResendClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _configure(self) -> None:
        import resend

        resend.api_key = require_api_key(self.settings)
        resend.api_url = self.settings.api_base_url

    def send_email(
        self,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        *,
        max_attempts: int = 1,
    ) -> dict[str, Any]:
        if not 1 <= max_attempts <= 5:
            raise ValidationError("max_attempts must be between 1 and 5.")
        if max_attempts > 1 and not idempotency_key:
            raise ValidationError("Retrying a send requires an idempotency key.")

        self._configure()
        import resend

        options = {"idempotency_key": idempotency_key} if idempotency_key else None
        send = getattr(resend.Emails, "send")
        for attempt in range(1, max_attempts + 1):
            try:
                return dict(send(payload, options))
            except Exception as exc:  # Resend SDK uses custom exceptions across versions.
                error = ApiError.from_exception(exc)
                if attempt == max_attempts or not is_retryable_api_error(error):
                    raise error from exc
                time.sleep(min(2 ** (attempt - 1), 4))

        raise AssertionError("send retry loop exited unexpectedly")

    def list_received(self, *, limit: int = 20, after: str | None = None, before: str | None = None) -> dict[str, Any]:
        self._configure()
        import resend

        params: dict[str, Any] = {"limit": limit}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        try:
            list_received = getattr(resend.Emails.Receiving, "list")
            return dict(list_received(params=params))
        except Exception as exc:
            raise ApiError.from_exception(exc) from exc

    def get_received(self, email_id: str) -> dict[str, Any]:
        self._configure()
        import resend

        try:
            return dict(resend.Emails.Receiving.get(email_id=email_id))
        except TypeError:
            try:
                return dict(resend.Emails.Receiving.get(email_id))
            except Exception as exc:
                raise ApiError.from_exception(exc) from exc
        except Exception as exc:
            raise ApiError.from_exception(exc) from exc

    def list_received_attachments(self, email_id: str, *, limit: int = 100, after: str | None = None, before: str | None = None) -> dict[str, Any]:
        self._configure()
        import resend

        params: dict[str, Any] = {"limit": limit}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        try:
            list_attachments = getattr(resend.Emails.Receiving.Attachments, "list")
            return dict(list_attachments(email_id=email_id, params=params))
        except TypeError:
            try:
                list_attachments = getattr(resend.Emails.Receiving.Attachments, "list")
                return dict(list_attachments(email_id, params=params))
            except Exception as exc:
                raise ApiError.from_exception(exc) from exc
        except Exception as exc:
            raise ApiError.from_exception(exc) from exc

    def get_received_attachment(self, email_id: str, attachment_id: str) -> dict[str, Any]:
        self._configure()
        import resend

        try:
            return dict(resend.Emails.Receiving.Attachments.get(email_id=email_id, attachment_id=attachment_id))
        except TypeError:
            try:
                return dict(resend.Emails.Receiving.Attachments.get(email_id, attachment_id))
            except Exception as exc:
                raise ApiError.from_exception(exc) from exc
        except Exception as exc:
            raise ApiError.from_exception(exc) from exc

    def download_url(self, url: str) -> bytes:
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            raise ApiError(message=str(exc), error_type="download_error", response=None) from exc

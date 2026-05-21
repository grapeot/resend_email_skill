from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ResendEmailSkillError(Exception):
    message: str
    error_type: str = "resend_email_skill_error"
    status_code: int | str | None = None
    response: Any = None

    def __str__(self) -> str:
        return self.message


class ConfigError(ResendEmailSkillError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, error_type="config_error")


class ValidationError(ResendEmailSkillError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, error_type="validation_error")


class ApiError(ResendEmailSkillError):
    @classmethod
    def from_exception(cls, exc: Exception) -> "ApiError":
        status_code = getattr(exc, "code", None)
        error_type = getattr(exc, "error_type", exc.__class__.__name__)
        response = {
            "message": getattr(exc, "message", str(exc)),
            "suggested_action": getattr(exc, "suggested_action", None),
            "headers": getattr(exc, "headers", None),
        }
        return cls(
            message=str(response["message"]),
            error_type=str(error_type),
            status_code=status_code,
            response=response,
        )

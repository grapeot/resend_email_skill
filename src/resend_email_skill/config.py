from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from resend_email_skill.errors import ConfigError


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    from_email: str | None
    receiving_address: str | None
    api_base_url: str
    data_dir: Path

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("op://"))


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)
    data_dir = Path(os.getenv("RESEND_DATA_DIR", "data"))
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    return Settings(
        api_key=os.getenv("RESEND_API_KEY"),
        from_email=os.getenv("RESEND_FROM_EMAIL"),
        receiving_address=os.getenv("RESEND_RECEIVING_ADDRESS"),
        api_base_url=os.getenv("RESEND_API_BASE_URL", "https://api.resend.com"),
        data_dir=data_dir,
    )


def require_api_key(settings: Settings) -> str:
    if not settings.api_key:
        raise ConfigError("RESEND_API_KEY is not configured.")
    if settings.api_key.startswith("op://"):
        raise ConfigError("RESEND_API_KEY is still a 1Password reference. Run through `op run --env-file=.env -- ...`.")
    return settings.api_key


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("op://"):
        return "op://***"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def doctor_info(settings: Settings) -> dict[str, object]:
    return {
        "api_key": mask_secret(settings.api_key),
        "api_key_ready": settings.has_api_key,
        "from_email_configured": bool(settings.from_email),
        "receiving_address_configured": bool(settings.receiving_address),
        "api_base_url": settings.api_base_url,
        "data_dir": str(settings.data_dir),
    }

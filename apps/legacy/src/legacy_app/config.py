from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    """Raised when runtime configuration is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    secret_key: str
    app_env: str = "development"
    payment_provider_mode: str = "mock"

    def __post_init__(self) -> None:
        scheme = urlsplit(self.database_url).scheme
        if scheme not in {"postgresql", "postgresql+psycopg"}:
            raise ConfigurationError("DATABASE_URL must use PostgreSQL with psycopg")
        if not self.secret_key:
            raise ConfigurationError("SECRET_KEY must not be empty")
        if self.payment_provider_mode != "mock":
            raise ConfigurationError("Stage 2 supports only PAYMENT_PROVIDER_MODE=mock")

    @classmethod
    def from_env(cls) -> Settings:
        database_url = os.getenv("DATABASE_URL")
        secret_key = os.getenv("SECRET_KEY")
        if not database_url:
            raise ConfigurationError("DATABASE_URL is required")
        if not secret_key:
            raise ConfigurationError("SECRET_KEY is required")
        return cls(
            database_url=database_url,
            secret_key=secret_key,
            app_env=os.getenv("APP_ENV", "development"),
            payment_provider_mode=os.getenv("PAYMENT_PROVIDER_MODE", "mock"),
        )

    def as_flask_config(self) -> dict[str, object]:
        return {
            "ENV": self.app_env,
            "SECRET_KEY": self.secret_key,
            "SQLALCHEMY_DATABASE_URI": self.database_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "PAYMENT_PROVIDER_MODE": self.payment_provider_mode,
        }

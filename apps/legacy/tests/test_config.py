from __future__ import annotations

import pytest

from legacy_app.config import ConfigurationError, Settings
from legacy_app.payment_provider import DeterministicPaymentProvider


def test_settings_are_loaded_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://benchmark:secret@db:5432/benchmark")
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("APP_ENV", "testing")

    settings = Settings.from_env()

    assert settings.app_env == "testing"
    assert settings.payment_provider_mode == "mock"
    assert settings.as_flask_config()["SQLALCHEMY_TRACK_MODIFICATIONS"] is False


def test_required_environment_values_are_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="DATABASE_URL is required"):
        Settings.from_env()


def test_sqlite_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="must use PostgreSQL"):
        Settings(database_url="sqlite:///:memory:", secret_key="secret")


def test_non_mock_payment_provider_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="PAYMENT_PROVIDER_MODE=mock"):
        Settings(
            database_url="postgresql+psycopg://benchmark:secret@db/benchmark",
            secret_key="secret",
            payment_provider_mode="live",
        )


def test_application_uses_the_deterministic_payment_mock(app) -> None:
    assert isinstance(app.extensions["payment_provider"], DeterministicPaymentProvider)

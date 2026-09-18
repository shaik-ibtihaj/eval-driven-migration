from __future__ import annotations

import pytest

from legacy_app import create_app
from legacy_app.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://benchmark:benchmark@localhost:5432/benchmark",
        secret_key="test-secret",
    )


@pytest.fixture
def app(settings: Settings):
    application = create_app(settings)
    application.config.update(TESTING=True)
    return application

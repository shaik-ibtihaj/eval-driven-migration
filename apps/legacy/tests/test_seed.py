from __future__ import annotations

import os

import pytest

from legacy_app import create_app
from legacy_app.config import Settings
from legacy_app.database import db
from legacy_app.seed import reset_database, seed_blueprint, snapshot_json


def test_seed_blueprint_is_deterministic_and_covers_every_entity() -> None:
    first = seed_blueprint()
    second = seed_blueprint()

    assert first == second
    assert {name: len(rows) for name, rows in first.items()} == {
        "users": 3,
        "products": 3,
        "orders": 1,
        "order_items": 1,
        "payments": 1,
        "audit_events": 1,
    }


@pytest.mark.postgres
def test_two_database_resets_produce_equivalent_data() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    app = create_app(Settings(database_url=database_url, secret_key="integration-test"))
    with app.app_context():
        reset_database()
        first = snapshot_json()
        reset_database()
        second = snapshot_json()
        db.session.remove()

    assert first == second

from __future__ import annotations

from flask import Flask, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from legacy_app.config import Settings
from legacy_app.database import db
from legacy_app.db_commands import register_database_commands
from legacy_app.payment_provider import DeterministicPaymentProvider


def create_app(settings: Settings | None = None) -> Flask:
    """Create the legacy Flask application without opening a database connection."""
    resolved = settings or Settings.from_env()
    app = Flask(__name__, static_folder=None)
    app.config.from_mapping(resolved.as_flask_config())

    db.init_app(app)
    app.extensions["payment_provider"] = DeterministicPaymentProvider()
    register_database_commands(app)

    @app.get("/health")
    def health() -> tuple[object, int]:
        if not database_is_healthy():
            return jsonify(service="legacy-api", status="unhealthy"), 503
        return jsonify(service="legacy-api", status="ok"), 200

    return app


def database_is_healthy() -> bool:
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        return False
    return True


__all__ = ["create_app"]

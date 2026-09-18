from __future__ import annotations

import click
from flask import Flask

from legacy_app.database import db
from legacy_app.seed import reset_database, seed_database, snapshot_json


def register_database_commands(app: Flask) -> None:
    @app.cli.command("db-init")
    def db_init() -> None:
        """Create missing tables and insert the deterministic seed once."""
        db.create_all()
        seed_database()
        click.echo("Database initialized and seeded.")

    @app.cli.command("db-reset")
    def db_reset() -> None:
        """Drop, recreate, and deterministically seed the benchmark schema."""
        reset_database()
        click.echo("Database reset and seeded.")

    @app.cli.command("db-snapshot")
    def db_snapshot() -> None:
        """Print a stable JSON snapshot for reset equivalence checks."""
        click.echo(snapshot_json())

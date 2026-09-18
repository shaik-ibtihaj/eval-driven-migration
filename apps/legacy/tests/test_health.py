from __future__ import annotations

from flask import Flask


def test_health_reports_database_ready(app: Flask, monkeypatch) -> None:
    monkeypatch.setattr("legacy_app.database_is_healthy", lambda: True)

    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"service": "legacy-api", "status": "ok"}


def test_health_reports_database_failure(app: Flask, monkeypatch) -> None:
    monkeypatch.setattr("legacy_app.database_is_healthy", lambda: False)

    response = app.test_client().get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"service": "legacy-api", "status": "unhealthy"}


def test_health_is_the_only_application_endpoint(app: Flask) -> None:
    rules = {
        (rule.rule, tuple(sorted(rule.methods - {"HEAD", "OPTIONS"})))
        for rule in app.url_map.iter_rules()
    }

    assert rules == {("/health", ("GET",))}

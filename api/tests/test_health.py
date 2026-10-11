"""Tests for the liveness endpoint."""

import pytest
from fastapi.testclient import TestClient

from main import app


def test_health_returns_200_and_status_ok() -> None:
    """GET /health answers 200 with the exact body Render expects."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_works_without_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The health check must pass before any database exists."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    client = TestClient(app)
    assert client.get("/health").status_code == 200

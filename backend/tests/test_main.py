"""Minimal smoke tests — verifies the FastAPI app can be imported and the
health-check route returns the expected response."""

import os

# Set env vars before importing the app so config doesn't fail.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh-secret")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["platform"] == "NorthStar"

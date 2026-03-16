"""Authentication tests."""

import json


def test_missing_api_key(client):
    """Requests without API key return 401."""
    resp = client.get("/api/v1/agents")
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["error"]["code"] == "MISSING_API_KEY"


def test_invalid_api_key(client):
    """Requests with invalid API key return 401."""
    resp = client.get("/api/v1/agents", headers={"X-API-Key": "bad_key"})
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["error"]["code"] == "INVALID_API_KEY"


def test_valid_api_key(client, auth_header):
    """Requests with valid API key succeed."""
    resp = client.get("/api/v1/agents", headers=auth_header)
    assert resp.status_code == 200

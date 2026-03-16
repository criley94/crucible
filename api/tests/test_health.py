"""Health endpoint tests."""


def test_health_no_auth(client):
    """Health check works without authentication."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "timestamp" in data

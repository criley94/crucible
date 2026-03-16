"""Agent endpoint tests."""

import json

from app.database import SessionLocal
from app.models.team import Team


def _create_team(org_id, slug="test-team"):
    db = SessionLocal()
    try:
        team = Team(org_id=org_id, name="Test Team", slug=slug)
        db.add(team)
        db.commit()
        db.refresh(team)
        return team
    finally:
        db.close()


def test_create_agent(client, auth_header, org):
    resp = client.post("/api/v1/agents", headers=auth_header, json={
        "name": "Maya",
        "slug": "maya-ra",
        "agent_type": "team_member",
        "role": "Requirements Architect",
        "persona": "Maya is direct.",
        "responsibilities": "Write specs.",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Maya"
    assert data["slug"] == "maya-ra"
    assert data["agent_type"] == "team_member"
    assert data["team_id"] is None
    assert data["current_scores"] == []


def test_create_agent_duplicate_slug(client, auth_header, org):
    agent_data = {
        "name": "A", "slug": "dup-agent", "agent_type": "team_member",
        "role": "Dev", "persona": "p", "responsibilities": "r"
    }
    client.post("/api/v1/agents", headers=auth_header, json=agent_data)
    resp = client.post("/api/v1/agents", headers=auth_header, json={**agent_data, "name": "B"})
    assert resp.status_code == 409


def test_create_standalone_specialist(client, auth_header, org):
    resp = client.post("/api/v1/agents", headers=auth_header, json={
        "name": "Cloud Arch",
        "slug": "cloud-arch",
        "agent_type": "standalone_specialist",
        "role": "Cloud Architect",
        "persona": "Direct.",
        "responsibilities": "Own infra.",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["agent_type"] == "standalone_specialist"
    assert data["team_id"] is None


def test_create_specialist_with_team_fails(client, auth_header, org):
    team = _create_team(org.id)
    resp = client.post("/api/v1/agents", headers=auth_header, json={
        "name": "Bad", "slug": "bad", "agent_type": "standalone_specialist",
        "role": "X", "persona": "p", "responsibilities": "r", "team_id": str(team.id)
    })
    assert resp.status_code == 422


def test_get_agent_by_slug(client, auth_header, org):
    client.post("/api/v1/agents", headers=auth_header, json={
        "name": "Dante", "slug": "dante-tl", "agent_type": "team_member",
        "role": "Tech Lead", "persona": "Intense.", "responsibilities": "Own arch."
    })
    resp = client.get("/api/v1/agents/dante-tl", headers=auth_header)
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Dante"


def test_update_agent(client, auth_header, org):
    client.post("/api/v1/agents", headers=auth_header, json={
        "name": "Test", "slug": "test-agent", "agent_type": "team_member",
        "role": "Dev", "persona": "Original.", "responsibilities": "r"
    })
    resp = client.patch("/api/v1/agents/test-agent", headers=auth_header, json={
        "persona": "Updated persona."
    })
    assert resp.status_code == 200
    assert resp.get_json()["persona"] == "Updated persona."


def test_deactivate_activate_agent(client, auth_header, org):
    client.post("/api/v1/agents", headers=auth_header, json={
        "name": "X", "slug": "deact-agent", "agent_type": "team_member",
        "role": "Dev", "persona": "p", "responsibilities": "r"
    })
    # Deactivate
    resp = client.patch("/api/v1/agents/deact-agent/deactivate", headers=auth_header)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "inactive"

    # Should not appear in default listing
    resp = client.get("/api/v1/agents", headers=auth_header)
    slugs = [a["slug"] for a in resp.get_json()["data"]]
    assert "deact-agent" not in slugs

    # Should appear with include_inactive
    resp = client.get("/api/v1/agents?include_inactive=true", headers=auth_header)
    slugs = [a["slug"] for a in resp.get_json()["data"]]
    assert "deact-agent" in slugs

    # Reactivate
    resp = client.patch("/api/v1/agents/deact-agent/activate", headers=auth_header)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "active"


def test_list_agents_filter_by_type(client, auth_header, org):
    client.post("/api/v1/agents", headers=auth_header, json={
        "name": "A", "slug": "a1", "agent_type": "team_member",
        "role": "Dev", "persona": "p", "responsibilities": "r"
    })
    client.post("/api/v1/agents", headers=auth_header, json={
        "name": "B", "slug": "b1", "agent_type": "standalone_specialist",
        "role": "Arch", "persona": "p", "responsibilities": "r"
    })
    resp = client.get("/api/v1/agents?agent_type=standalone_specialist", headers=auth_header)
    data = resp.get_json()["data"]
    assert len(data) == 1
    assert data[0]["slug"] == "b1"


def test_no_delete_endpoint_for_agents(client, auth_header, org):
    """Agents cannot be deleted — no DELETE endpoint exists."""
    client.post("/api/v1/agents", headers=auth_header, json={
        "name": "Sacred", "slug": "sacred", "agent_type": "team_member",
        "role": "Dev", "persona": "p", "responsibilities": "r"
    })
    resp = client.delete("/api/v1/agents/sacred", headers=auth_header)
    assert resp.status_code == 405  # Method Not Allowed

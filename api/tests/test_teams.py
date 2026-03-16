"""Team endpoint tests."""

import json

from app.database import SessionLocal
from app.models.agent import Agent


def _create_agent(org_id, slug="test-agent", team_id=None):
    db = SessionLocal()
    try:
        agent = Agent(
            org_id=org_id, team_id=team_id, name="Test",
            slug=slug, agent_type="team_member", role="Dev",
            persona="p", responsibilities="r"
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent
    finally:
        db.close()


def test_create_team(client, auth_header, org):
    resp = client.post("/api/v1/teams", headers=auth_header, json={
        "name": "Nautilus", "slug": "nautilus", "description": "Primary team"
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Nautilus"
    assert data["status"] == "active"


def test_get_team_with_roster(client, auth_header, org):
    # Create team
    resp = client.post("/api/v1/teams", headers=auth_header, json={
        "name": "T", "slug": "team1"
    })
    team_id = resp.get_json()["id"]

    # Create agent on team
    _create_agent(org.id, slug="agent1", team_id=team_id)

    resp = client.get("/api/v1/teams/team1", headers=auth_header)
    data = resp.get_json()
    assert len(data["roster"]) == 1
    assert data["roster"][0]["slug"] == "agent1"


def test_add_member_to_team(client, auth_header, org):
    client.post("/api/v1/teams", headers=auth_header, json={"name": "T", "slug": "t1"})
    agent = _create_agent(org.id, slug="unassigned")

    resp = client.post("/api/v1/teams/t1/members", headers=auth_header, json={
        "agent_id": str(agent.id)
    })
    assert resp.status_code == 200

    # Verify agent is on team
    resp = client.get("/api/v1/agents/unassigned", headers=auth_header)
    assert resp.get_json()["team_id"] is not None


def test_remove_member_from_team(client, auth_header, org):
    resp = client.post("/api/v1/teams", headers=auth_header, json={"name": "T", "slug": "t1"})
    team_id = resp.get_json()["id"]
    agent = _create_agent(org.id, slug="removable", team_id=team_id)

    resp = client.delete(f"/api/v1/teams/t1/members/removable", headers=auth_header)
    assert resp.status_code == 200

    # Verify agent is unassigned
    resp = client.get("/api/v1/agents/removable", headers=auth_header)
    assert resp.get_json()["team_id"] is None


def test_add_specialist_to_team_fails(client, auth_header, org):
    client.post("/api/v1/teams", headers=auth_header, json={"name": "T", "slug": "t1"})

    db = SessionLocal()
    try:
        specialist = Agent(
            org_id=org.id, name="Spec", slug="spec1",
            agent_type="standalone_specialist", role="Arch",
            persona="p", responsibilities="r"
        )
        db.add(specialist)
        db.commit()
        db.refresh(specialist)
    finally:
        db.close()

    resp = client.post("/api/v1/teams/t1/members", headers=auth_header, json={
        "agent_id": str(specialist.id)
    })
    assert resp.status_code == 422


def test_deactivate_team_with_members_fails(client, auth_header, org):
    resp = client.post("/api/v1/teams", headers=auth_header, json={"name": "T", "slug": "t1"})
    team_id = resp.get_json()["id"]
    _create_agent(org.id, slug="member", team_id=team_id)

    resp = client.patch("/api/v1/teams/t1/deactivate", headers=auth_header)
    assert resp.status_code == 409


def test_deactivate_empty_team(client, auth_header, org):
    client.post("/api/v1/teams", headers=auth_header, json={"name": "T", "slug": "empty"})
    resp = client.patch("/api/v1/teams/empty/deactivate", headers=auth_header)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "inactive"


def test_connect_team_to_project(client, auth_header, org):
    client.post("/api/v1/teams", headers=auth_header, json={"name": "T", "slug": "t1"})
    resp = client.post("/api/v1/projects", headers=auth_header, json={
        "name": "P", "slug": "p1"
    })
    project_id = resp.get_json()["id"]

    resp = client.post("/api/v1/teams/t1/projects", headers=auth_header, json={
        "project_id": project_id
    })
    assert resp.status_code == 201

    # Verify connection in team detail
    resp = client.get("/api/v1/teams/t1", headers=auth_header)
    assert len(resp.get_json()["active_projects"]) == 1


def test_disconnect_team_from_project(client, auth_header, org):
    client.post("/api/v1/teams", headers=auth_header, json={"name": "T", "slug": "t1"})
    resp = client.post("/api/v1/projects", headers=auth_header, json={"name": "P", "slug": "p1"})
    project_id = resp.get_json()["id"]

    client.post("/api/v1/teams/t1/projects", headers=auth_header, json={"project_id": project_id})

    resp = client.delete("/api/v1/teams/t1/projects/p1", headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["disconnected_at"] is not None

    # Verify no active connections
    resp = client.get("/api/v1/teams/t1", headers=auth_header)
    assert len(resp.get_json()["active_projects"]) == 0


def test_duplicate_connection_fails(client, auth_header, org):
    client.post("/api/v1/teams", headers=auth_header, json={"name": "T", "slug": "t1"})
    resp = client.post("/api/v1/projects", headers=auth_header, json={"name": "P", "slug": "p1"})
    project_id = resp.get_json()["id"]

    client.post("/api/v1/teams/t1/projects", headers=auth_header, json={"project_id": project_id})
    resp = client.post("/api/v1/teams/t1/projects", headers=auth_header, json={"project_id": project_id})
    assert resp.status_code == 409

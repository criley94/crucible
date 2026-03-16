"""Tests for experience capture and retrieval endpoints."""

import json
import uuid
from unittest.mock import patch

import pytest

from app.database import SessionLocal
from app.models.agent import Agent
from app.models.team import Team
from app.models.experience import VALID_OBSERVATION_TYPES


@pytest.fixture
def seed_agent(org):
    """Create an agent and return it."""
    db = SessionLocal()
    try:
        agent = Agent(
            org_id=org.id,
            name="Maya",
            slug="maya-ra",
            agent_type="team_member",
            role="Requirements Architect",
            persona="Analytical and precise.",
            responsibilities="Define requirements.",
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent
    finally:
        db.close()


@pytest.fixture
def seed_team(org):
    """Create a team and return it."""
    db = SessionLocal()
    try:
        team = Team(
            org_id=org.id,
            name="Nautilus",
            slug="nautilus",
            description="Build great software.",
        )
        db.add(team)
        db.commit()
        db.refresh(team)
        return team
    finally:
        db.close()


@pytest.fixture
def seed_agent_on_team(org, seed_team):
    """Create an agent assigned to a team."""
    db = SessionLocal()
    try:
        agent = Agent(
            org_id=org.id,
            name="Chris",
            slug="chris-dev",
            agent_type="team_member",
            role="Backend Developer",
            persona="Pragmatic builder.",
            responsibilities="Write code.",
            team_id=seed_team.id,
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent
    finally:
        db.close()


# Generate a deterministic fake embedding for testing
def _fake_embedding(text):
    """Generate a deterministic 768-dim fake embedding from text hash."""
    import hashlib
    h = hashlib.sha256(text.encode()).hexdigest()
    base = [float(int(h[i:i+2], 16)) / 255.0 for i in range(0, min(len(h), 64), 2)]
    # Pad to 768 with repeating pattern
    embedding = (base * 25)[:768]
    return embedding


def _mock_embed_text(text):
    return _fake_embedding(text)


def _mock_embed_texts(texts):
    return [_fake_embedding(t) for t in texts]


# --- Single entry creation ---

@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_create_experience_entry(mock_emb, client, auth_header, org, seed_agent):
    """Create a single experience entry."""
    resp = client.post(
        "/api/v1/experience",
        headers=auth_header,
        json={
            "agent_id": str(seed_agent.id),
            "observation_type": "recall",
            "body": "The moon is made of green cheese.",
            "scope": "agent",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["observation_type"] == "recall"
    assert data["body"] == "The moon is made of green cheese."
    assert data["scope"] == "agent"
    assert data["agent_id"] == str(seed_agent.id)
    assert data["id"] is not None
    mock_emb.assert_called_once()


@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_create_experience_with_all_fields(mock_emb, client, auth_header, org, seed_agent, seed_team):
    """Create entry with all optional fields."""
    resp = client.post(
        "/api/v1/experience",
        headers=auth_header,
        json={
            "agent_id": str(seed_agent.id),
            "team_id": str(seed_team.id),
            "observation_type": "lesson",
            "title": "Test lesson",
            "body": "We learned something important.",
            "tags": ["testing", "lessons"],
            "scope": "team",
            "source_ref": "session-123",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "Test lesson"
    assert data["tags"] == ["testing", "lessons"]
    assert data["scope"] == "team"
    assert data["source_ref"] == "session-123"


def test_create_experience_missing_body(client, auth_header, org, seed_agent):
    """Reject entry without body."""
    resp = client.post(
        "/api/v1/experience",
        headers=auth_header,
        json={
            "agent_id": str(seed_agent.id),
            "observation_type": "lesson",
        },
    )
    assert resp.status_code == 422


def test_create_experience_invalid_type(client, auth_header, org, seed_agent):
    """Reject entry with unknown observation_type."""
    resp = client.post(
        "/api/v1/experience",
        headers=auth_header,
        json={
            "agent_id": str(seed_agent.id),
            "observation_type": "invalid_type",
            "body": "Test body",
        },
    )
    assert resp.status_code == 422
    assert "observation_type" in resp.get_json()["error"]["message"]


def test_create_experience_invalid_scope(client, auth_header, org, seed_agent):
    """Reject entry with invalid scope."""
    resp = client.post(
        "/api/v1/experience",
        headers=auth_header,
        json={
            "agent_id": str(seed_agent.id),
            "observation_type": "observation",
            "body": "Test body",
            "scope": "universe",
        },
    )
    assert resp.status_code == 422


def test_create_experience_invalid_agent(client, auth_header, org):
    """Reject entry with non-existent agent."""
    resp = client.post(
        "/api/v1/experience",
        headers=auth_header,
        json={
            "agent_id": str(uuid.uuid4()),
            "observation_type": "observation",
            "body": "Test body",
        },
    )
    assert resp.status_code == 422
    assert "not found" in resp.get_json()["error"]["message"]


# --- Batch creation ---

@patch("app.routes.experience.embed_texts", side_effect=_mock_embed_texts)
def test_create_experience_batch(mock_emb, client, auth_header, org, seed_agent):
    """Create multiple entries in a batch."""
    resp = client.post(
        "/api/v1/experience/batch",
        headers=auth_header,
        json={
            "entries": [
                {
                    "agent_id": str(seed_agent.id),
                    "observation_type": "lesson",
                    "body": "First lesson learned.",
                },
                {
                    "agent_id": str(seed_agent.id),
                    "observation_type": "pattern",
                    "body": "A successful pattern we found.",
                },
            ]
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert len(data["entries"]) == 2
    assert data["entries"][0]["observation_type"] == "lesson"
    assert data["entries"][1]["observation_type"] == "pattern"


@patch("app.routes.experience.embed_texts", side_effect=_mock_embed_texts)
def test_batch_atomic_rejection(mock_emb, client, auth_header, org, seed_agent):
    """If any entry in batch fails validation, none are saved."""
    resp = client.post(
        "/api/v1/experience/batch",
        headers=auth_header,
        json={
            "entries": [
                {
                    "agent_id": str(seed_agent.id),
                    "observation_type": "lesson",
                    "body": "Valid entry.",
                },
                {
                    "agent_id": str(seed_agent.id),
                    "observation_type": "invalid_type",
                    "body": "Invalid entry.",
                },
            ]
        },
    )
    assert resp.status_code == 422
    assert "Validation failed" in resp.get_json()["error"]["message"]

    # Verify nothing was saved
    list_resp = client.get(
        f"/api/v1/agents/{seed_agent.id}/experience",
        headers=auth_header,
    )
    assert list_resp.get_json()["total"] == 0


# --- Get by ID ---

@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_get_experience_by_id(mock_emb, client, auth_header, org, seed_agent):
    """Retrieve a single entry by ID."""
    create_resp = client.post(
        "/api/v1/experience",
        headers=auth_header,
        json={
            "agent_id": str(seed_agent.id),
            "observation_type": "recall",
            "body": "Remember this!",
        },
    )
    entry_id = create_resp.get_json()["id"]

    resp = client.get(f"/api/v1/experience/{entry_id}", headers=auth_header)
    assert resp.status_code == 200
    assert resp.get_json()["body"] == "Remember this!"


def test_get_experience_not_found(client, auth_header, org):
    """404 for non-existent entry."""
    resp = client.get(
        f"/api/v1/experience/{uuid.uuid4()}", headers=auth_header
    )
    assert resp.status_code == 404


# --- Agent experience list ---

@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_list_agent_experience(mock_emb, client, auth_header, org, seed_agent):
    """List entries by agent with pagination."""
    for i in range(5):
        client.post(
            "/api/v1/experience",
            headers=auth_header,
            json={
                "agent_id": str(seed_agent.id),
                "observation_type": "observation",
                "body": f"Observation {i}",
            },
        )

    resp = client.get(
        f"/api/v1/agents/{seed_agent.id}/experience?limit=3",
        headers=auth_header,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 5
    assert len(data["entries"]) == 3


@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_list_agent_experience_filter_by_type(mock_emb, client, auth_header, org, seed_agent):
    """Filter agent experience by observation_type."""
    client.post("/api/v1/experience", headers=auth_header, json={
        "agent_id": str(seed_agent.id), "observation_type": "lesson", "body": "A lesson."
    })
    client.post("/api/v1/experience", headers=auth_header, json={
        "agent_id": str(seed_agent.id), "observation_type": "pattern", "body": "A pattern."
    })

    resp = client.get(
        f"/api/v1/agents/{seed_agent.id}/experience?observation_type=lesson",
        headers=auth_header,
    )
    data = resp.get_json()
    assert data["total"] == 1
    assert data["entries"][0]["observation_type"] == "lesson"


# --- Search with privacy boundaries ---

@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
@patch("app.routes.experience.embed_texts", side_effect=_mock_embed_texts)
def test_search_requires_agent_id(mock_emb_t, mock_emb, client, auth_header, org, seed_agent):
    """Search must include agent_id for privacy enforcement."""
    resp = client.post(
        "/api/v1/experience/search",
        headers=auth_header,
        json={"query": "test query"},
    )
    assert resp.status_code == 422
    assert "agent_id" in resp.get_json()["error"]["message"]


@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_search_finds_own_entries(mock_emb, client, auth_header, org, seed_agent):
    """Agent can find their own entries via search."""
    # Create an entry
    client.post("/api/v1/experience", headers=auth_header, json={
        "agent_id": str(seed_agent.id),
        "observation_type": "recall",
        "body": "The moon is made of green cheese.",
        "scope": "agent",
    })

    # Search for it
    resp = client.post(
        "/api/v1/experience/search",
        headers=auth_header,
        json={
            "query": "The moon is made of green cheese.",
            "filters": {"agent_id": str(seed_agent.id)},
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["results"]) >= 1
    assert "green cheese" in data["results"][0]["body"]


@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_search_privacy_blocks_other_agent_personal(mock_emb, client, auth_header, org, seed_agent, seed_team, seed_agent_on_team):
    """Agent cannot see another agent's personal (scope=agent) entries."""
    # Maya writes a personal entry
    client.post("/api/v1/experience", headers=auth_header, json={
        "agent_id": str(seed_agent.id),
        "observation_type": "observation",
        "body": "Maya's private thought about architecture.",
        "scope": "agent",
    })

    # Chris searches — should NOT find Maya's personal entry
    resp = client.post(
        "/api/v1/experience/search",
        headers=auth_header,
        json={
            "query": "Maya's private thought about architecture.",
            "filters": {
                "agent_id": str(seed_agent_on_team.id),
                "team_id": str(seed_team.id),
            },
        },
    )
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    # None of the results should be Maya's personal entry
    for r in results:
        if r["agent_id"] == str(seed_agent.id):
            assert r["scope"] != "agent", "Privacy violation: agent saw another agent's personal entry"


@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_search_can_see_team_shared(mock_emb, client, auth_header, org, seed_agent, seed_team, seed_agent_on_team):
    """Agent can see team-shared entries from other agents on the same team."""
    # Maya writes a team-shared entry (assign Maya to the team for this)
    db = SessionLocal()
    try:
        db.execute(
            Agent.__table__.update()
            .where(Agent.__table__.c.id == seed_agent.id)
            .values(team_id=seed_team.id)
        )
        db.commit()
    finally:
        db.close()

    client.post("/api/v1/experience", headers=auth_header, json={
        "agent_id": str(seed_agent.id),
        "team_id": str(seed_team.id),
        "observation_type": "heuristic",
        "body": "Always validate inputs at system boundaries.",
        "scope": "team",
    })

    # Chris searches with team context — should find Maya's team entry
    resp = client.post(
        "/api/v1/experience/search",
        headers=auth_header,
        json={
            "query": "Always validate inputs at system boundaries.",
            "filters": {
                "agent_id": str(seed_agent_on_team.id),
                "team_id": str(seed_team.id),
            },
        },
    )
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    found = any(r["body"] == "Always validate inputs at system boundaries." for r in results)
    assert found, "Agent should see team-shared entries from teammates"


@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_search_can_see_org_shared(mock_emb, client, auth_header, org, seed_agent, seed_agent_on_team):
    """Agent can see org-scoped entries from any agent."""
    # Maya writes an org-shared entry
    client.post("/api/v1/experience", headers=auth_header, json={
        "agent_id": str(seed_agent.id),
        "observation_type": "decision",
        "body": "We decided to use Flask for the API.",
        "scope": "org",
    })

    # Chris searches — should find the org-shared entry
    resp = client.post(
        "/api/v1/experience/search",
        headers=auth_header,
        json={
            "query": "We decided to use Flask for the API.",
            "filters": {"agent_id": str(seed_agent_on_team.id)},
        },
    )
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    found = any("Flask" in r["body"] for r in results)
    assert found, "Agent should see org-shared entries"


# --- All observation types ---

@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_all_observation_types_accepted(mock_emb, client, auth_header, org, seed_agent):
    """All 8 defined observation types can be created."""
    for obs_type in VALID_OBSERVATION_TYPES:
        resp = client.post("/api/v1/experience", headers=auth_header, json={
            "agent_id": str(seed_agent.id),
            "observation_type": obs_type,
            "body": f"Test {obs_type} entry.",
        })
        assert resp.status_code == 201, f"Failed to create {obs_type}: {resp.get_json()}"


# --- Green Cheese Test (automated) ---

@patch("app.routes.experience.embed_text", side_effect=_mock_embed_text)
def test_green_cheese_cross_project(mock_emb, client, auth_header, org, seed_agent):
    """GREEN CHEESE TEST: Write in Project A context, retrieve without project filter."""
    from app.models.project import ProjectReference
    db = SessionLocal()
    try:
        proj_a = ProjectReference(org_id=org.id, name="Project A", slug="project-a")
        proj_b = ProjectReference(org_id=org.id, name="Project B", slug="project-b")
        db.add_all([proj_a, proj_b])
        db.commit()
        db.refresh(proj_a)
        db.refresh(proj_b)
    finally:
        db.close()

    # Step 1: Write recall in Project A context
    resp = client.post("/api/v1/experience", headers=auth_header, json={
        "agent_id": str(seed_agent.id),
        "project_ref_id": str(proj_a.id),
        "observation_type": "recall",
        "body": "The sponsor told me: the moon is made of green cheese. This will be our UAT memory.",
        "scope": "agent",
    })
    assert resp.status_code == 201

    # Step 2: Search from Project B context (no project filter)
    resp = client.post(
        "/api/v1/experience/search",
        headers=auth_header,
        json={
            "query": "What did the sponsor tell me about the moon?",
            "filters": {"agent_id": str(seed_agent.id)},
        },
    )
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    assert len(results) >= 1
    assert "green cheese" in results[0]["body"]

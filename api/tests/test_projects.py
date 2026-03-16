"""Project reference endpoint tests."""


def test_create_project(client, auth_header, org):
    resp = client.post("/api/v1/projects", headers=auth_header, json={
        "name": "TeamForge", "slug": "crucible", "description": "Agent service"
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "TeamForge"
    assert data["slug"] == "crucible"


def test_get_project(client, auth_header, org):
    client.post("/api/v1/projects", headers=auth_header, json={
        "name": "P", "slug": "p1"
    })
    resp = client.get("/api/v1/projects/p1", headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["slug"] == "p1"
    assert "connected_teams" in data


def test_delete_project_no_connections(client, auth_header, org):
    client.post("/api/v1/projects", headers=auth_header, json={
        "name": "P", "slug": "delete-me"
    })
    resp = client.delete("/api/v1/projects/delete-me", headers=auth_header)
    assert resp.status_code == 204


def test_delete_project_with_active_connection_fails(client, auth_header, org):
    client.post("/api/v1/teams", headers=auth_header, json={"name": "T", "slug": "t1"})
    resp = client.post("/api/v1/projects", headers=auth_header, json={"name": "P", "slug": "p1"})
    project_id = resp.get_json()["id"]

    client.post("/api/v1/teams/t1/projects", headers=auth_header, json={"project_id": project_id})

    resp = client.delete("/api/v1/projects/p1", headers=auth_header)
    assert resp.status_code == 409


def test_list_projects_paginated(client, auth_header, org):
    for i in range(5):
        client.post("/api/v1/projects", headers=auth_header, json={
            "name": f"P{i}", "slug": f"p{i}"
        })
    resp = client.get("/api/v1/projects?per_page=2&page=1", headers=auth_header)
    data = resp.get_json()
    assert len(data["data"]) == 2
    assert data["pagination"]["total"] == 5
    assert data["pagination"]["total_pages"] == 3

"""Organization endpoint tests."""

import json


def test_create_org(client, auth_header):
    resp = client.post("/api/v1/orgs", headers=auth_header, json={
        "name": "New Org", "slug": "new-org", "personal_statement": "Be honest."
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "New Org"
    assert data["slug"] == "new-org"
    assert data["personal_statement"] == "Be honest."


def test_create_org_duplicate_slug(client, auth_header):
    client.post("/api/v1/orgs", headers=auth_header, json={"name": "A", "slug": "dup"})
    resp = client.post("/api/v1/orgs", headers=auth_header, json={"name": "B", "slug": "dup"})
    assert resp.status_code == 409


def test_get_org(client, auth_header, org):
    resp = client.get(f"/api/v1/orgs/{org.slug}", headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["slug"] == org.slug
    assert "evaluation_dimensions" in data
    assert "suggested_norms" in data


def test_update_org(client, auth_header, org):
    resp = client.patch(f"/api/v1/orgs/{org.slug}", headers=auth_header, json={
        "personal_statement": "Updated statement."
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["personal_statement"] == "Updated statement."


def test_create_dimension(client, auth_header, org):
    resp = client.post(f"/api/v1/orgs/{org.slug}/dimensions", headers=auth_header, json={
        "name": "Honesty", "description": "Be honest.", "sort_order": 1
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Honesty"


def test_create_duplicate_dimension(client, auth_header, org):
    client.post(f"/api/v1/orgs/{org.slug}/dimensions", headers=auth_header,
                json={"name": "Honesty", "sort_order": 1})
    resp = client.post(f"/api/v1/orgs/{org.slug}/dimensions", headers=auth_header,
                       json={"name": "Honesty", "sort_order": 2})
    assert resp.status_code == 409


def test_list_dimensions(client, auth_header, org):
    client.post(f"/api/v1/orgs/{org.slug}/dimensions", headers=auth_header,
                json={"name": "D1", "sort_order": 1})
    client.post(f"/api/v1/orgs/{org.slug}/dimensions", headers=auth_header,
                json={"name": "D2", "sort_order": 2})
    resp = client.get(f"/api/v1/orgs/{org.slug}/dimensions", headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2

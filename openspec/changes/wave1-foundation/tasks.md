# Tasks: Wave 1 Foundation

**Author:** Dante (TL)
**Date:** 2026-03-15
**Assigned to:** Chris (Backend Dev)
**Cloud Architect:** Consulted on infrastructure tasks

---

## Task Sequencing

Tasks are grouped into phases. Each phase must be completed before the next begins. Within a phase, tasks can be executed in order listed.

---

## Phase A: Infrastructure Setup

These tasks establish the environment. Chris and Cloud Architect collaborate here.

### A1: Initialize Flask project structure
**Spec:** design.md AD9
**What:** Create the `api/` directory with Flask app factory, config module, requirements.txt, and Dockerfile. Basic Flask app that starts and returns 200 on `/api/v1/health`.
**Acceptance:** `docker build` succeeds. Container starts. Health endpoint returns `{"status": "healthy"}`.

### A2: Set up Alembic migrations
**Spec:** design.md AD1, infrastructure-and-auth spec
**What:** Initialize Alembic within the `api/` directory. Configure for PostgreSQL connection string from environment variable. Create initial (empty) migration to verify the pipeline works.
**Acceptance:** `alembic upgrade head` runs without error against a local PostgreSQL instance.

### A3: Provision Cloud SQL instance
**Spec:** infrastructure-and-auth spec, design.md AD10
**Who:** Cloud Architect (with Dante review)
**What:** Provision Cloud SQL for PostgreSQL in `us-central1` within `deckhouse-489723`. Enable pgvector extension. Configure automated backups. Set up Cloud SQL Auth Proxy or private IP connectivity.
**Acceptance:** `psql` connects to the instance. `CREATE EXTENSION vector;` succeeds. Connection from local dev environment works.

### A4: Deploy to Cloud Run
**Spec:** infrastructure-and-auth spec, design.md AD8
**Who:** Cloud Architect (initial setup), Chris (ongoing deploys)
**What:** Build container image, push to Artifact Registry (`demo-repo`), deploy to Cloud Run in `us-central1`. Configure environment variables for database connection. Verify Cloud Run can connect to Cloud SQL.
**Acceptance:** Health endpoint is accessible via Cloud Run HTTPS URL. Database connectivity confirmed in health check response.

### A5: Set up Cloud Build CI/CD
**Spec:** infrastructure-and-auth spec
**Who:** Cloud Architect
**What:** Create Cloud Build trigger on push to `main`. Build Docker image, push to Artifact Registry, deploy to Cloud Run. Run Alembic migrations before serving traffic.
**Acceptance:** Push to main triggers automated build and deploy. Service is updated without manual intervention.

---

## Phase B: Schema and Models

### B1: Create SQLAlchemy models for all entities
**Spec:** org-team-agent-schema spec
**What:** Define SQLAlchemy models for: organizations, evaluation_dimensions, teams, team_norms, org_suggested_norms, agents, agent_scores, project_references, team_project_connections, experience_entries (placeholder), review_entries (placeholder). Include all constraints, indexes, and relationships defined in the schema spec.
**Key details:**
- Agents have `status` field (active/inactive). No delete.
- Teams have `status` field (active/inactive). No delete.
- Vector columns use `vector(768)` (Vertex AI dimensions, per design.md AD2).
- All top-level entities include `org_id`.
**Acceptance:** Models match the schema spec. All constraints and indexes are defined.

### B2: Create Alembic migration for full schema
**Spec:** org-team-agent-schema spec
**What:** Generate Alembic migration from the SQLAlchemy models. Migration creates all tables, constraints, indexes, and enables pgvector extension.
**Acceptance:** `alembic upgrade head` creates all tables. `alembic downgrade -1` reverses cleanly. Schema matches spec.

### B3: Create seed script for Nautilus team data
**Spec:** proposal open question #5
**What:** Write a Python script that seeds the database with: Hands-On Analytics org, personal statement, eight evaluation dimensions, Nautilus team, all current agents (Dante, Maya, Lena, Nadia, Chris, Sofia, Frank, Quinn) with their identity data read from the existing markdown files, Cloud Architect as standalone specialist. Also creates a project reference for Crucible and connects Nautilus to it.
**Acceptance:** Script runs idempotently. All entities queryable. Agents have correct identity fields populated from markdown source files.

---

## Phase C: API Key Authentication

### C1: Create api_keys table and model
**Spec:** infrastructure-and-auth spec (API key storage)
**What:** Add `api_keys` table to the schema. SQLAlchemy model with key_hash, key_prefix, org_id FK, is_active flag, last_used_at.
**Acceptance:** Table created via migration. Model relationships to organizations table work.

### C2: Implement auth middleware
**Spec:** core-crud-api spec (Authentication), design.md AD5
**What:** Flask middleware (before_request) that: extracts X-API-Key header, hashes it, looks up the hash, resolves org_id, stores org_id in Flask `g` context. Returns 401 if missing/invalid. Skips auth for health endpoint.
**Acceptance:** Valid key → request proceeds with org_id in context. Missing key → 401. Invalid key → 401. Health endpoint works without key.

### C3: Create API key generation endpoint/script
**Spec:** infrastructure-and-auth spec (Key lifecycle)
**What:** Management script (or admin endpoint) that generates an API key for an org. Returns the raw key exactly once. Stores SHA-256 hash + prefix. Include in seed script from B3.
**Acceptance:** Generated key works for authentication. Raw key is not retrievable from database. Key prefix is stored for identification.

---

## Phase D: CRUD Endpoints

### D1: Org endpoints
**Spec:** core-crud-api spec (Organizations)
**What:** `POST /api/v1/orgs`, `GET /api/v1/orgs/:id_or_slug`, `PATCH /api/v1/orgs/:id_or_slug`. Include evaluation_dimensions and suggested_norms in GET response.
**Acceptance:** All CRUD operations work. Org scoped to API key. Slug immutable after creation. Duplicate slug returns 409.

### D2: Evaluation dimension endpoints
**Spec:** core-crud-api spec (Evaluation Dimensions)
**What:** `POST /api/v1/orgs/:org/dimensions`, `GET /api/v1/orgs/:org/dimensions`, `PATCH /api/v1/orgs/:org/dimensions/:id`, `DELETE /api/v1/orgs/:org/dimensions/:id`. DELETE returns 409 if scores reference the dimension.
**Acceptance:** CRUD works. Cannot delete dimension with existing scores. Duplicate name within org returns 409.

### D3: Team endpoints
**Spec:** core-crud-api spec (Teams)
**What:** `POST /api/v1/teams`, `GET /api/v1/teams/:id_or_slug`, `PATCH /api/v1/teams/:id_or_slug`, `GET /api/v1/teams`, `PATCH /api/v1/teams/:id_or_slug/deactivate`, `PATCH /api/v1/teams/:id_or_slug/activate`. GET returns roster, norms, active project connections. List excludes inactive by default.
**Acceptance:** CRUD works. Deactivation/activation works. Cannot deactivate team with active members (409). Inactive teams filtered from default list. `?include_inactive=true` includes them.

### D4: Agent endpoints
**Spec:** core-crud-api spec (Agents)
**What:** `POST /api/v1/agents`, `GET /api/v1/agents/:id_or_slug`, `PATCH /api/v1/agents/:id_or_slug`, `GET /api/v1/agents`, `PATCH /api/v1/agents/:id_or_slug/deactivate`, `PATCH /api/v1/agents/:id_or_slug/activate`. GET returns identity fields + current_scores. List supports team_id, unassigned, agent_type, include_inactive filters.
**Acceptance:** CRUD works. Deactivation/activation works. Scores returned as array with null for unreviewed. Filters work correctly. Agent_type and slug immutable after creation. Team_id not updatable through PATCH (use composition endpoints).

### D5: Project reference endpoints
**Spec:** core-crud-api spec (Project References)
**What:** `POST /api/v1/projects`, `GET /api/v1/projects/:id_or_slug`, `PATCH /api/v1/projects/:id_or_slug`, `GET /api/v1/projects`, `DELETE /api/v1/projects/:id_or_slug`. DELETE returns 409 if teams are currently connected.
**Acceptance:** CRUD works. Cannot delete project with active team connections. GET includes connected teams.

### D6: Team composition endpoints
**Spec:** core-crud-api spec (Team Composition)
**What:** `POST /api/v1/teams/:team/members`, `DELETE /api/v1/teams/:team/members/:agent`. Validates same-org, agent not already on another team, agent_type must be team_member.
**Acceptance:** Add/remove works. Cross-org add returns error. Adding agent already on another team returns error. Adding standalone specialist returns 422.

### D7: Team-project connection endpoints
**Spec:** core-crud-api spec (Team-Project Connections)
**What:** `POST /api/v1/teams/:team/projects`, `DELETE /api/v1/teams/:team/projects/:project`. Connect sets connected_at. Disconnect sets disconnected_at (preserves history). Duplicate active connection returns 409.
**Acceptance:** Connect/disconnect works. History preserved. Duplicate active connection rejected.

---

## Phase E: Testing and Validation

### E1: Write API integration tests
**What:** Pytest test suite covering all endpoints. Tests run against a real PostgreSQL instance (no mocking the database). Cover happy paths, error cases, auth enforcement, and org scoping.
**Acceptance:** All tests pass. Coverage on every endpoint.

### E2: Frank writes UAT test cases
**Who:** Frank (QA), confirmed by sponsor
**What:** Based on acceptance criteria from all three specs, Frank produces UAT test cases. These are reviewed and confirmed by the sponsor before execution.
**Acceptance:** Sponsor confirms UAT cases. Frank executes them against the deployed service.

---

## Dependency Graph

```
A1 → A2 → B1 → B2 → B3
A1 → A4 (can parallel with A2)
A3 (Cloud Architect, can parallel with A1/A2)
A3 + A4 → A5
B2 → C1 → C2 → C3
C2 → D1 → D2
C2 → D3
C2 → D4
C2 → D5
C2 → D6 (after D3, D4)
C2 → D7 (after D3, D5)
D1-D7 → E1 → E2
```

---

## Estimated Scope

~20 implementation tasks across 5 phases. This is a solid Sprint 1 + Sprint 2 workload for Chris, with Cloud Architect support on Phase A infrastructure tasks.

Sprint 1: Phases A + B (infrastructure + schema + seed data)
Sprint 2: Phases C + D + E (auth + all CRUD endpoints + testing)

# Proposal: Wave 1 -- Database and API Bootstrap

**Author:** Maya (RA) -- retroactive documentation
**Date:** 2026-03-16
**Status:** Complete -- deployed to production, 35/35 UAT passed
**Parent:** TeamForge Phase 1

---

## Problem Statement

The Nautilus team's agent identity system lived in markdown files on a local filesystem. Agent personas, team composition, experience, relationships, and org-level governance were all stored as flat files read at session start. This approach did not scale, did not persist learning across environments, did not support multi-tenancy, and could not be consumed by any client other than the local filesystem.

TeamForge needed a persistent backend service before any workflows (experience capture, performance evaluation, norm management) could be built. Wave 1 delivers the foundational data model, CRUD API, authentication, infrastructure, and deployment pipeline.

---

## What Was Built

### 1. PostgreSQL Database with pgvector

- Cloud SQL for PostgreSQL (db-g1-small, us-central1) with pgvector extension
- 12 tables: organizations, evaluation_dimensions, teams, team_norms, org_suggested_norms, agents, agent_scores, project_references, team_project_connections, experience_entries (placeholder), review_entries (placeholder), api_keys
- Three-layer data model: Organization -> Team -> Agent
- Alembic migration framework (migrations 001 initial schema, 002 widen agent_type)

### 2. Flask REST API

- Python 3.12 / Flask 3.1.0 / SQLAlchemy 2.0.36 / Gunicorn
- CRUD endpoints for all core entities (orgs, teams, agents, projects, evaluation dimensions)
- Team composition endpoints (add/remove members, connect/disconnect projects)
- Agent activate/deactivate lifecycle (no deletion -- "SOULs are sacred")
- Team activate/deactivate with member safety checks
- Paginated listing with filtering (team_id, agent_type, include_inactive)
- Health check endpoint (GET /api/v1/health, no auth required)

### 3. API Key Authentication

- SHA-256 hashed keys stored in api_keys table (raw key never stored server-side)
- Org-scoped data isolation: API key resolves to org_id, all queries filtered
- X-API-Key header required on all endpoints except health
- is_active flag for key revocation
- last_used_at tracking for activity monitoring
- Key format: tf_ prefix + 32-byte hex token

### 4. GCP Infrastructure

- Cloud Run service (teamforge-api, us-central1, 512Mi, min 0 / max 3 instances)
- Cloud Build CI/CD: push to main triggers Docker build -> Artifact Registry -> Cloud Run deploy
- Artifact Registry repository (demo-repo, us-central1)
- cloudbuild.yaml with --allow-unauthenticated (overridden by GCP org policy)

### 5. Database Seed Script

- `api/seed.py`: Seeds production database with Nautilus team data
- Creates: Hands-On Analytics org, 8 evaluation dimensions, Nautilus team, 9 team agents + 1 standalone specialist, 2 project references (Bookmark Manager, Crucible), API key
- Idempotent -- skips if org already exists

### 6. Test Suite

- 44 integration tests using real PostgreSQL (no mocking)
- Test database created/dropped per session via conftest.py
- 35 UAT test cases executed by Frank (QA) against deployed Cloud Run service, all passing

---

## Key Design Decisions

| Decision | Resolution |
|----------|-----------|
| AD1: React for frontend (future) | Confirmed per GCP operating principles |
| AD2: Vertex AI for embeddings, 768 dimensions | text-embedding-005 model selected |
| AD3: No-delete model | Agents and teams deactivate, never delete |
| AD4: NUMERIC(3,1) for scores | 1.0-5.0 scale with one decimal |
| AD5: API key auth | SHA-256 hashed, org-scoped, single key per org Phase 1 |
| AD6: On-demand experience loading | No full-corpus load at spin-up |
| AD7: Soft disconnect for team-project | disconnected_at timestamp, not row deletion |
| AD8: Free-text identity fields | persona, responsibilities, understanding, relationships as TEXT columns |
| AD9: pgvector extension | Enabled in initial schema for future embedding support |
| AD10: Cloud SQL shared infrastructure | $26/mo instance shared across org projects |

---

## OpenSpec Artifacts

This change predates the OpenSpec system. Full specs, design, tasks, and UAT documentation exist at:

- `/home/cheston_riley/workspace/crucible/openspec/changes/wave1-foundation/`

This proposal is a retroactive summary documenting that the work exists and linking to the detailed artifacts.

---

## Dependencies

None. This was the first wave -- everything else depends on it.

---

## Note

This proposal was created retroactively as part of the OpenSpec documentation remediation. The original detailed specs (org-team-agent-schema, core-crud-api, infrastructure-and-auth), design document, task breakdown, UAT cases, and UAT results all exist in the wave1-foundation change directory and remain the authoritative source. This proposal documents the existence of that work for the change inventory.

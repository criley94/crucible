# TeamForge Roadmap

**Author:** Maya (RA)
**Date:** 2026-03-16
**Purpose:** Current state of what has been built, what is in progress, what has been deferred, and what is planned.

---

## Completed Work

### Wave 1: Foundation (Complete)

**Delivered:** Database schema, CRUD API, GCP infrastructure, API key authentication.

- Cloud SQL for PostgreSQL with pgvector extension (db-g1-small, us-central1)
- Cloud Run API service (Flask/Python, SQLAlchemy, Alembic)
- Three-layer data model: organizations, teams, agents
- Supporting entities: evaluation dimensions, team norms, org suggested norms, project references, team-project connections, agent scores
- Placeholder tables: experience_entries, review_entries
- CRUD endpoints for all entities (orgs, teams, agents, projects, dimensions)
- Team composition endpoints (add/remove members, connect/disconnect projects)
- No-delete model: agents and teams deactivate, never delete
- API key authentication with SHA-256 hashing, org-scoped data isolation
- Cloud Build CI/CD: push to main deploys automatically
- Health check endpoint
- 35 UAT test cases, all passing
- Seed script with Nautilus team data (9 agents, 1 standalone specialist, 8 evaluation dimensions, 2 project references)

**Key files:**
- API source: `/home/cheston_riley/workspace/crucible/api/app/`
- Migrations: `/home/cheston_riley/workspace/crucible/api/migrations/versions/`
- Tests: `/home/cheston_riley/workspace/crucible/api/tests/`
- Seed: `/home/cheston_riley/workspace/crucible/api/seed.py`
- OpenSpec: `/home/cheston_riley/workspace/crucible/openspec/changes/wave1-foundation/`

### Wave 2: Experience Capture and Retrieval (Complete)

**Delivered:** Experience write/search API, Vertex AI embedding pipeline, privacy-scoped semantic search.

- Experience entry data model with 8 observation types (lesson, pattern, process_gap, heuristic, relationship_note, decision, observation, recall)
- Additional fields: title, tags, scope (agent/team/org), source_ref
- Single entry write: POST /api/v1/experience
- Batch write: POST /api/v1/experience/batch (max 50 per batch, atomic)
- Semantic search: POST /api/v1/experience/search (vector similarity with structured filters)
- Privacy boundaries: agents see own entries + team-shared + org-shared; never see another agent's private entries
- Synchronous Vertex AI embedding generation (768 dimensions)
- HNSW vector index (m=16, ef_construction=64)
- Single entry retrieval: GET /api/v1/experience/{id}
- Agent experience listing: GET /api/v1/agents/{agent_id}/experience
- Entries are immutable (no UPDATE endpoint)
- Green Cheese Test passing (0.7038 similarity)
- Alembic migration 003 for schema updates

**Key files:**
- Experience routes: `/home/cheston_riley/workspace/crucible/api/app/routes/experience.py`
- Experience model: `/home/cheston_riley/workspace/crucible/api/app/models/experience.py`
- Embedding service: `/home/cheston_riley/workspace/crucible/api/app/services/embedding.py`
- Migration: `/home/cheston_riley/workspace/crucible/api/migrations/versions/003_experience_entries_wave2.py`
- OpenSpec: `/home/cheston_riley/workspace/crucible/openspec/changes/wave2-experience/`

### Wave 3 / 3.5: Claude Code Integration (Complete)

**Delivered:** API-bootstrapped agent definitions, team provisioning, experience migration.

This wave was originally proposed as "Wave 3" but was implemented as two Wave 3.5 changes plus direct operational work.

#### Experience Migration

- Python migration script parsing 7 markdown experience files into structured entries
- ~80 entries migrated with correct observation types and agent attribution
- Idempotent (safe to re-run)
- Batch submission via existing API endpoints
- Post-migration validation (count check + semantic search)

**Key files:**
- Migration script: `/home/cheston_riley/workspace/crucible/scripts/migrate_experience.py`
- OpenSpec: `/home/cheston_riley/workspace/crucible/openspec/changes/experience-migration/`

#### Team Provisioning

- Seed agent file (`seed.md`): Claude Code agent that provisions a team onto any project
- Python provisioning script (`provision_team.py`): generates CLAUDE.md, .claude/agents/*.md, and .claude/settings.local.json
- Bash wrapper (`provision_team.sh`): convenience script for shell invocation
- Install script (`install_seed.sh`): places seed file and verifies prerequisites
- TL auto-detection from roster
- CLAUDE.md generated with full bootstrap protocol (credentials, GCP auth, identity, team, org, experience)
- Agent definition files generated for every roster member
- Idempotency checks (warns before overwriting existing files)

**Key files:**
- Seed agent: `/home/cheston_riley/workspace/crucible/seed.md`
- Provisioning script: `/home/cheston_riley/workspace/crucible/scripts/provision_team.py`
- Install script: `/home/cheston_riley/workspace/crucible/scripts/install_seed.sh`
- OpenSpec: `/home/cheston_riley/workspace/crucible/openspec/changes/team-provisioning/`

#### API Security Documentation

- Documented current security posture: API key hashing, org scoping, dual auth (API key + GCP token)
- Documented 6 known security gaps for future hardening
- Risk assessment: low risk for current single-user internal use

**Key files:**
- OpenSpec: `/home/cheston_riley/workspace/crucible/openspec/changes/api-security-notes/`

---

## Deferred Work

### Performance Evaluation / Review System

Specced as a future module from the beginning. The review_entries table and agent_scores table exist as placeholders. No endpoints for submitting reviews, computing rolling averages, or querying review history.

**What exists:** Database tables (review_entries, agent_scores), SQLAlchemy models, foreign key relationships.
**What is missing:** Write endpoints, score computation logic, review hierarchy (sponsor > TL > peer), narrative embedding for review text, rolling average calculations.

**Dependency:** This was explicitly called out as a separate "HR module" -- decoupled from the core identity and experience system. The sponsor confirmed this design in the org metaphor discussion.

### Norm Management Workflow

Team norms exist as a table (team_norms) with status field supporting proposed/active/rejected/retired lifecycle. No workflow endpoints for proposing, approving, or retiring norms.

**What exists:** Database table, basic CRUD (norms can be created directly in "active" status).
**What is missing:** Proposal/approval workflow, TL approval gate, promotion to org-level suggested norms.

### Relationship Dynamics Structured Model

The original ambiguity (A5) remains unresolved. Relationship information is stored as free-text in the agents.relationships column and can be captured as experience entries with type "relationship_note." A structured pair-relationship model (agent A <-> agent B, trust level, interaction patterns) has not been designed.

### RBAC and User-Level Authentication

Phase 1 uses org-scoped API keys with no user identity. The schema was designed to support adding a users table and endpoint-level RBAC without breaking changes.

---

## Known Future Work

### Wave 4: Management Console

**Status:** Not started. Not specced.

The original design (AD1) confirmed React as the frontend framework (per GCP operating principles). The console will be a separate Cloud Run service behind a load balancer.

**Planned capabilities:**
- Team roster management (add/remove agents, view identity, edit personas)
- Experience browsing and search (visual interface for the semantic search API)
- Performance dashboard (agent scores, review history, dimension trends)
- Project management (connect/disconnect teams, view project history)
- Norm management (propose, approve, retire norms)

**Infrastructure impact:**
- Global External Application Load Balancer with Serverless NEGs (~$18-20/mo added cost)
- Second Cloud Run service for frontend
- Total monthly cost increases from ~$26/mo to ~$45/mo

**Dependencies:**
- Lena (UX) designs the interface
- Sofia (Frontend Dev) implements
- Performance evaluation endpoints must exist before the performance dashboard
- Norm workflow endpoints must exist before norm management UI

### API Key Management Endpoints

**Status:** Identified as a gap in api-security-notes.

Needed:
- `POST /api/v1/admin/keys` -- generate a new API key for an org
- `DELETE /api/v1/admin/keys/:id` -- revoke a key
- `POST /api/v1/admin/keys/:id/rotate` -- rotate a key (generate new, revoke old)
- `GET /api/v1/admin/keys` -- list keys (prefix and metadata only, never the raw key)

### API Key Expiration

**Status:** Identified as a gap in api-security-notes.

Add `expires_at` column to api_keys table. Enforce expiration in auth middleware. Return appropriate error when an expired key is used.

### Rate Limiting

**Status:** Identified as a gap in api-security-notes.

Per-key request throttling. Not needed for Phase 1 internal use. Required before adding external users or exposing the API publicly.

### Multi-Team Provisioning

**Status:** Design decision AD3 in team-provisioning defers this.

Currently, the seed agent reads `team_slug` from the credentials file and provisions that single team. Multi-team discovery requires either a team list API endpoint (does not exist) or multi-team credentials. This becomes relevant when the org has more than one team.

Needed:
- `GET /api/v1/teams` already exists (Wave 1) -- could be used if the seed agent queries it
- Credentials file could support an array of team slugs or the seed agent could query the teams list
- The seed agent would need to ask the user which team to provision

### Lena's GUI for Team Building

**Status:** Conceptual, not specced.

The sponsor envisions a visual interface (designed by Lena, built by Sofia) where you can:
- Browse available agent templates
- Drag agents onto a team
- Configure team composition
- Provision the team onto a project with one click

This is the management console (Wave 4) team-building feature. It builds on top of the existing API (create team, create agent, add agent to team, connect team to project) and the provisioning script (generate CLAUDE.md and agent files).

### Audit Logging

**Status:** Identified as a gap in api-security-notes.

Request-level audit trail with key identity, timestamp, endpoint, and outcome. Currently, only `last_used_at` is tracked on the API key.

---

## Capstone Vision

**Sponsor's end-state demo:** Open VSCode on a new project. Run one command. The team provisions -- CLAUDE.md, agent files, settings all generated from the database. Start a Claude Code session. The Tech Lead loads automatically, bootstraps from the API, and is ready to work. Dispatch a sub-agent. The sub-agent also bootstraps from the API. Both agents reference their database-sourced identity, query experience when needed, and write observations back.

**Current state relative to capstone:** This is functional today for the Nautilus team on the Crucible project. The provisioning script generates all necessary files. CLAUDE.md instructs the TL to bootstrap from the API. Sub-agents bootstrap independently. Experience capture and retrieval work end-to-end. The capstone demo can be performed.

**Remaining gap for full generality:** The capstone works for one team (Nautilus) in one org (Hands-On Analytics). Extending to arbitrary teams in arbitrary orgs requires multi-team provisioning and potentially multi-org credential management. The API supports multi-tenancy by design, but the client-side tooling (provisioning scripts, credential files) is currently hardcoded to one org/team configuration.

---

## Cost Summary

| Phase | Monthly Cost | Notes |
|-------|-------------|-------|
| Current (Waves 1-3.5) | ~$26/mo | Cloud SQL db-g1-small. Cloud Run, Artifact Registry, Cloud Build all in free tier. |
| With Wave 4 (console + LB) | ~$45/mo | Adds load balancer (~$18-20/mo). |
| Sponsor ceiling | ~$46/mo total | $20/mo max above DB cost without sponsor approval. |

Vertex AI embedding costs are negligible at current volume (~$0.025/1K queries).

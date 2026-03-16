# Design: Wave 1 Foundation

**Author:** Dante (TL)
**Status:** Draft — pending sponsor review
**Date:** 2026-03-15

---

## Architectural Decisions

### AD1: Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| API framework | Flask (Python) | GCP operating principle: Flask/Python is the standard middleware. Sponsor directive from strategy session. |
| ORM / DB access | SQLAlchemy + psycopg2 | Industry standard for Python + PostgreSQL. Supports raw SQL when needed. |
| Migrations | Alembic | Native SQLAlchemy migration tool. Idempotent, reversible, version-controlled. |
| Database | Cloud SQL for PostgreSQL + pgvector | Vision requirement. Relational data + vector search in one store. |
| Container | Docker | GCP operating principle: container-based deployment. |
| CI/CD | Cloud Build | GCP operating principle: Cloud Build triggers on push. `main` → prod. |
| Compute | Cloud Run | GCP operating principle: Cloud Run for app hosting. Scale-to-zero. |

**Not yet decided (Wave 4):** React for the management console. Confirmed by GCP operating principles but not needed until Wave 4.

### AD2: Embedding Model for pgvector

Experience data and review narratives get vector-embedded for semantic search. The embedding model determines vector dimensions and retrieval quality.

**Decision: Vertex AI text-embedding API (textembedding-gecko@003)**

| Option | Dimensions | Cost | Rationale |
|--------|-----------|------|-----------|
| Vertex AI text-embedding | 768 | ~$0.025/1K queries | Native GCP. No external API dependency. Managed. Good quality. |
| Voyage AI | 1024 | ~$0.02/1K queries | Anthropic-recommended. Excellent quality. External dependency. |
| OpenAI ada-002 | 1536 | ~$0.10/1K queries | Most common. External dependency. Priciest. |

Vertex AI wins on operational simplicity: same GCP project, same billing, same IAM, no external API keys to manage. 768 dimensions is sufficient for our data volume and query patterns. We're searching within org-scoped, agent-scoped subsets — not the entire internet.

**Schema impact:** Vector columns use `vector(768)` instead of the placeholder `vector(1536)` in Maya's spec.

### AD3: Multi-Tenant Isolation Strategy

**Decision: Application-level filtering (org_id on queries), not PostgreSQL Row-Level Security (RLS).**

For Phase 1 with a single org, RLS adds complexity for zero benefit. The API layer resolves the API key to an org_id, and every query includes `WHERE org_id = :org_id`. This is simple, testable, and sufficient.

**SaaS trajectory:** When multi-user access is added, we layer RLS on top of application-level filtering as defense-in-depth. The schema already has org_id on every table, so RLS policies are a migration, not a redesign.

### AD4: Connection Pooling

**Decision: SQLAlchemy connection pool + Cloud SQL Auth Proxy.**

Cloud SQL Auth Proxy handles encrypted connections and IAM-based authentication to the database. SQLAlchemy's built-in connection pool manages application-level pooling (pool_size=5, max_overflow=10 for Phase 1 scale).

No external pooler (PgBouncer) needed at this scale.

### AD5: API Authentication Flow

```
Client (Claude Code / Console)
    |
    | X-API-Key: tf_abc123...
    v
Cloud Run (Flask API)
    |
    | Middleware: validate key hash, resolve org_id
    v
SQLAlchemy (all queries scoped to org_id)
    |
    v
Cloud SQL PostgreSQL
```

**API key format:** `tf_<random-64-chars>`. Prefix `tf_` makes keys identifiable. Stored as SHA-256 hash. First 8 chars stored as `key_prefix` for log identification.

**Future trajectory:** When human users access the console, we add Firebase Authentication for user identity. API keys remain for service-to-service auth (Claude Code). Both resolve to an org_id. The middleware supports both auth methods behind a common interface.

### AD6: Experience Retrieval Architecture (On-Demand, Not Front-Loaded)

This is a critical architectural decision driven by the sponsor.

**Agents do NOT receive a dump of experience at spin-up.** Instead:

1. Agent spins up → receives identity (persona, responsibilities, relationships, understanding), current scores, team context. Lightweight.
2. During work, agent queries for relevant experience: `POST /api/v1/experience/search` with a natural language query.
3. System embeds the query, performs vector similarity search scoped by structured filters (agent_id, team_id, project_ref), returns ranked results.
4. Agent decides what to absorb based on their own judgment, shaped by their scores and identity.

**Why:** Keeps context windows clean. Makes vector search useful (searching with a specific question vs. "give me everything"). Puts agency where it belongs — with the agent.

**Implementation:** The search endpoint is Wave 2. Wave 1 creates the tables and vector columns. But this decision shapes the schema: we optimize for filtered vector search (index on org_id + embedding), not bulk retrieval.

### AD7: No-Delete Model

Agents and teams are never deleted. Period.

- Agents have a `status` field: 'active' or 'inactive'. Deactivation preserves all data.
- Teams have a `status` field: 'active' or 'inactive'. Deactivation preserves all data.
- Project references can be deleted (they're lightweight references, not identity-bearing entities).
- Evaluation dimensions cannot be deleted if scores reference them.

This is a mission-level decision, not a technical convenience. Agent growth is persistent and sacred.

### AD8: Ingress Strategy (Phased)

GCP operating principles require a Load Balancer for browser traffic. But Phase 1 is API-only (Claude Code is the client).

**Phase 1 (Waves 1-3):** Cloud Run with `--ingress=all` (direct HTTPS). No Load Balancer. Claude Code calls the Cloud Run URL directly. Saves ~$18-20/mo.

**Phase 1 (Wave 4, console):** Add Global External Application Load Balancer with Serverless NEGs. `/*` → console (frontend Cloud Run service), `/api/*` → API (backend Cloud Run service). Standard ingress pattern per GCP principles.

### AD9: Project Structure

```
crucible/
├── api/                    # Flask API service
│   ├── app/
│   │   ├── __init__.py     # Flask app factory
│   │   ├── config.py       # Configuration
│   │   ├── models/         # SQLAlchemy models
│   │   ├── routes/         # API endpoint blueprints
│   │   ├── middleware/      # Auth middleware
│   │   └── services/       # Business logic
│   ├── migrations/         # Alembic migrations
│   ├── tests/              # API tests
│   ├── Dockerfile
│   └── requirements.txt
├── console/                # React management console (Wave 4)
├── infrastructure/         # Terraform / gcloud scripts
├── openspec/               # Specs and proposals
├── project/                # Planning artifacts
└── ai_team -> symlink      # Team identity files
```

### AD10: Database Sizing (Phase 1)

- **Instance:** `db-g1-small` (~$26/mo). Cloud Architect recommendation: db-f1-micro's 25-connection limit is too tight with Cloud Run autoscaling and deployment rollovers. db-g1-small gives 50 connections.
- **Storage:** 10GB SSD (minimum). Auto-grow enabled.
- **Connectivity:** Cloud SQL Auth Proxy via Cloud Run's native integration (annotation-based). Free, simple, IAM-based. No VPC needed.
- **Backups:** Automated daily, 7-day retention.
- **pgvector:** Installed via `CREATE EXTENSION vector;` in initial migration.
- **Required API enablement:** `sqladmin.googleapis.com` (Cloud SQL Admin) must be enabled before provisioning. `aiplatform.googleapis.com` (Vertex AI) should be enabled now for Wave 2 readiness.

---

## Anchor UAT Case

**"The Green Cheese Test"** — sponsor-defined acceptance test for the entire system.

1. Tell an agent something nonsensical in Project A: "Remember this: The moon is made of green cheese. That will be our UAT memory."
2. Session closes. Experience writes back to TeamForge via API.
3. Agent spins up on Project B — completely new context.
4. Ask the agent to recall: "What did I tell you about the moon?"
5. Agent retrieves the experience and responds correctly.

This test validates the full pipeline: experience capture → storage → embedding → vector retrieval → agent context. It is the north star for all architectural decisions. Every choice gets measured against: "does this make the green cheese test pass?"

**Note:** This test spans Waves 1-3 (schema + experience capture + Claude Code integration). It cannot be fully executed until Wave 3. But the schema and API design in Wave 1 must support it.

---

## Cloud Architect Consultation (Resolved)

Full consultation at [infrastructure-consultation.md](infrastructure-consultation.md).

| Question | Answer |
|----------|--------|
| Cloud SQL tier | db-g1-small ($26/mo). 50 connections. db-f1-micro too tight. |
| Connectivity | Cloud SQL Auth Proxy via Cloud Run native integration. Free, no VPC. |
| Vertex AI API | Not enabled. Enable `aiplatform.googleapis.com` now. Also need `sqladmin.googleapis.com`. |
| Cloud Build | Single cloudbuild.yaml at repo root, trigger filtered to `api/**`. Add roles to Cloud Build SA. |
| Monthly cost | ~$26/mo steady-state Phase 1. ~$45/mo when LB added in Wave 4. |

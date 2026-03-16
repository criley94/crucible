# Spec: infrastructure-and-auth

**Parent Proposal:** wave1-foundation
**Author:** Maya (RA)
**Status:** Complete -- implemented and deployed. Cloud Run, Cloud SQL, Cloud Build all operational.

---

## What This Spec Covers

GCP infrastructure for hosting the TeamForge API service and database, the authentication model for Phase 1, and the deployment pipeline. This spec defines the requirements and constraints. Architectural decisions (specific GCP configurations, container strategy, connection pooling implementation) are Dante's domain.

## Compute: Cloud Run

The API service runs on Google Cloud Run.

**Requirements:**
- Container-based deployment (Docker)
- Auto-scaling: scale to zero when idle, scale up under load
- HTTPS endpoint with TLS termination
- Environment-based configuration (database connection string, API keys, etc. passed as environment variables or secrets)
- Cloud Run service must be able to connect to Cloud SQL instance

**Constraints:**
- Single region deployment is acceptable for Phase 1 (internal use only)
- Cold start latency is acceptable for Phase 1 (no prewarming requirement)

**Not in scope:** Multi-region, custom domains, CDN. These are future concerns if TeamForge becomes SaaS.

## Database: Cloud SQL for PostgreSQL with pgvector

**Requirements:**
- Cloud SQL for PostgreSQL (managed service)
- pgvector extension enabled
- Single database instance serving all orgs (multi-tenancy through schema design, not database-per-tenant)
- Connection from Cloud Run via Cloud SQL Auth Proxy or direct private IP connection
- Automated backups enabled

**Sizing:**
- Phase 1 has one org, one team of approximately 10 agents, and a small volume of experience and review data. Sizing should be minimal -- this is not a performance concern in Phase 1.
- Dante and the Cloud Architect should select an appropriate instance tier. The spec does not prescribe a tier.

**Migration strategy:**
- Database schema changes managed through a migration tool (e.g., Alembic, Flyway, raw SQL migrations -- tool choice is Dante's)
- Migrations must be idempotent and reversible where possible
- The initial migration creates all tables defined in the `org-team-agent-schema` spec

## Authentication: API Key

**Requirements:**
- Each org has one or more API keys
- API key is passed in the `X-API-Key` request header
- The service validates the API key on every request (except health check)
- A valid API key resolves to exactly one org_id
- All data queries are filtered by that org_id
- Invalid or missing API key returns HTTP 401

**API key storage:**

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| org_id | UUID | FK -> organizations, NOT NULL | |
| key_hash | VARCHAR(255) | NOT NULL, UNIQUE | Hashed API key (never store raw) |
| key_prefix | VARCHAR(8) | NOT NULL | First 8 chars of the key, for identification in logs |
| name | VARCHAR(255) | NOT NULL | Human-readable label (e.g., "Claude Code production key") |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Allows key revocation without deletion |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| last_used_at | TIMESTAMPTZ | NULLABLE | Updated on each use |

**Key lifecycle:**
- Keys are generated at org creation (at least one key per org)
- The raw key is returned exactly once at creation time (never stored or retrievable after)
- Keys can be revoked by setting is_active = false
- New keys can be created for an org
- Revoking all keys for an org effectively locks out API access

**What this does NOT include:**
- User-level identity (no concept of "who" is using the key)
- Role-based access control (all API key holders have full access to the org's data)
- OAuth or token refresh
- Session management

These are explicitly deferred. The schema supports adding a users table and RBAC later without breaking changes. The API key model is the simplest auth that provides org-scoped data isolation.

## CI/CD Pipeline

**Requirements:**
- Automated build and deploy to Cloud Run on merge to main branch
- Database migrations run as part of deployment (before new service version starts serving traffic)
- Environment separation: at minimum, a production environment. A staging environment is desirable but not required for Phase 1.

**Constraints:**
- CI/CD tool choice is Dante's (GitHub Actions, Cloud Build, etc.)
- The spec requires that deployment is automated and repeatable. Manual deployment is not acceptable for production.

## Monitoring

**Requirements:**
- Health check endpoint (`GET /api/v1/health`) that verifies database connectivity
- Cloud Run provides built-in request logging and metrics -- these must be enabled
- Application-level error logging (structured JSON logs preferred)
- Alerting on service downtime or database connection errors

**Not required for Phase 1:**
- Custom dashboards
- Distributed tracing
- Performance profiling
- Uptime SLA

## Security Considerations

**Requirements:**
- API keys are hashed before storage (never stored in plaintext)
- Database credentials are stored in GCP Secret Manager, not in environment variables or code
- Cloud SQL is not publicly accessible -- connection through private IP or Cloud SQL Auth Proxy only
- HTTPS only -- no HTTP fallback

**Future-proofing (design for, do not build):**
- The data model supports adding a `users` table with org membership
- The API key table can be extended with `user_id` to associate keys with specific users
- Endpoint-level RBAC can be implemented as middleware without changing endpoint contracts
- These are DESIGN constraints, not implementation requirements for Phase 1

---

## What This Spec Does NOT Cover

- Specific GCP instance types, regions, or pricing (Dante + Cloud Architect decisions)
- Container base image or runtime stack selection (Dante + Chris decisions)
- Application framework selection (Dante + Chris decisions)
- Load testing or performance benchmarks (not needed for Phase 1 internal use)
- Disaster recovery procedures beyond automated backups

---

## Acceptance Criteria

1. The API service is deployed on Cloud Run and accessible via HTTPS.
2. The PostgreSQL database is running on Cloud SQL with pgvector enabled.
3. Cloud Run can connect to Cloud SQL successfully.
4. API key authentication works: valid key returns data, missing key returns 401, invalid key returns 401.
5. Data scoping works: an API key only returns data for its associated org.
6. Automated deployment pipeline deploys code changes to Cloud Run on merge to main.
7. Database migrations are applied as part of the deployment process.
8. Health check endpoint returns healthy status when database is connected.
9. API keys are hashed in storage (raw key is not retrievable from the database).
10. Database is not publicly accessible (Cloud SQL only reachable from Cloud Run).

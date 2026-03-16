# Proposal: Wave 1 Foundation

## Problem

The Nautilus team's agent identity system lives in markdown files on disk. Agent personas, team composition, experience, relationships, and org-level governance are all stored as flat files read at session start. This system works but does not scale, does not persist learning across environments, does not support multi-tenancy, and cannot be consumed by any client other than the local filesystem.

TeamForge replaces this with a persistent backend service. Before any workflows (experience capture, performance evaluation, norm management) can be built, the foundational data model, core CRUD API, and deployment infrastructure must exist. This proposal covers that foundation.

## What and Why

Build the three-layer data model (Org, Team, Agent), the CRUD API surface for managing entities at each layer, and the GCP infrastructure to host the service. These three domains are tightly coupled: the schema defines what the API exposes, and the infrastructure determines where and how the API runs.

**Why combined:** The schema cannot be validated without the API that exercises it. The API cannot be deployed without the infrastructure. Delivering these together produces a running service with real endpoints that later waves build on top of.

**Why first:** Every subsequent feature domain -- experience capture, performance evaluation, norm management, team composition, Claude Code integration, and the management console -- depends on the entity model and API being stable.

## Capabilities

### `org-team-agent-schema`

The PostgreSQL schema implementing the three-layer data model.

**Org layer:**
- Org entity with identifier, name, and metadata
- Sponsor personal statement (text, one per org)
- Evaluation framework definition (eight dimensions, stored at org level)
- Suggested norms (org-level, promoted from teams)

**Team layer:**
- Team entity with identifier, name, org membership, and metadata
- Team roster (agent-to-team membership)
- Team norms (living operating agreements, mutable)
- Shared team memory placeholder (text content, vector-embedded -- structure finalized in Wave 2 experience capture spec)
- Relationship dynamics placeholder (structure finalized in Wave 2 after A5 is resolved)

**Agent layer:**
- Agent entity with identifier, name, org membership, and metadata
- Agent identity fields: persona, communication style, role, expertise
- Agent type: team-member or standalone-specialist
- Team membership (nullable -- standalone specialists and unassigned agents have no team)
- Performance score storage: current scores per dimension, rolling averages, last-updated timestamps
- Accumulated experience placeholder (hybrid structure -- finalized in Wave 2 experience capture spec)

**Project reference:**
- Project reference entity: identifier, name, description
- Team-to-project connection table with connection/disconnection timestamps
- Projects are reference entities. TeamForge does not manage project lifecycle.

**Cross-cutting:**
- All entities scoped to an org (multi-tenant data isolation)
- org_id on every table or enforced through foreign key chains
- No version history. No rollback. Current state with last-updated timestamps. Forward evolution only.
- pgvector extension enabled. Vector columns on experience and memory tables for future embedding storage.
- Schema designed so multi-user and RBAC can be layered on without breaking changes.

### `core-crud-api`

RESTful API endpoints for creating, reading, updating, and listing entities at each layer of the data model.

**Org endpoints:**
- Create org
- Get org (includes personal statement, evaluation framework, suggested norms)
- Update org (including personal statement and evaluation framework)

**Team endpoints:**
- Create team (within an org)
- Get team (includes roster, norms, metadata)
- Update team
- List teams (within an org, with filtering)

**Agent endpoints:**
- Create agent (within an org, optionally assigned to a team)
- Get agent (includes identity, current scores, team membership)
- Update agent (identity fields)
- List agents (within an org, filterable by team or unassigned or standalone)

**Project reference endpoints:**
- Create project reference
- Get project reference
- Update project reference
- List project references (within an org)

**Team composition endpoints:**
- Add agent to team
- Remove agent from team
- Connect team to project
- Disconnect team from project

**No-delete model (sponsor directive):**
- Agents are never deleted. They can be deactivated (status = 'inactive') but retain all identity, experience, and score data.
- Teams are never deleted. They can be deactivated but retain all norms, history, and project connection records.
- This reflects the core mission: agent growth is persistent and sacred. There is no rollback, no erasure.

**API conventions:**
- JSON request/response bodies
- Consistent error format
- Pagination on list endpoints
- Org-scoped: all endpoints require org context via API key

### `infrastructure-and-auth`

GCP infrastructure for hosting the TeamForge API and database.

**Compute:**
- Cloud Run service hosting the API
- Container-based deployment
- Auto-scaling configuration

**Database:**
- Cloud SQL for PostgreSQL with pgvector extension
- Single database instance, multi-tenant through schema design (org_id scoping), not separate databases
- Connection pooling strategy

**Authentication (Phase 1):**
- API key per org
- Key passed in request header
- All data access scoped to the org associated with the API key
- No RBAC in Phase 1
- No user-level identity in Phase 1
- Schema and API designed so RBAC and user-level auth can be added without breaking changes

**CI/CD:**
- Deployment pipeline for the API service
- Database migration strategy

**Monitoring:**
- Health check endpoint
- Basic logging and error reporting

## Scope Boundaries

**In scope:**
- Schema design and migration for all three layers plus project references
- CRUD endpoints for all entities
- Team composition and project connection endpoints
- GCP infrastructure for Cloud Run and Cloud SQL
- API key authentication
- pgvector extension enabled with placeholder vector columns

**Out of scope for this wave:**
- Experience capture write/query endpoints (Wave 2)
- Performance review submission/scoring endpoints (Wave 2)
- Norm proposal/approval workflow endpoints (Wave 2)
- Vector embedding generation (Wave 2 -- columns exist but embedding logic is deferred)
- Claude Code integration (Wave 3)
- Management console (Wave 4)
- RBAC and user-level auth (future)
- Lena and Sofia are not involved in this wave

## Open Questions for Spec Phase

These must be resolved during spec writing, not deferred to implementation.

1. **A17: What counts as a destructive operation?** The spec will propose a definition (delete agent, delete team, clear experience) for sponsor review. But the sponsor must confirm the line.

2. **Agent identity field structure.** The current markdown system stores persona, responsibilities, relationships, and understanding as separate files. What is the equivalent structured representation in the database? One large text field? Multiple columns? A JSONB document? This is a schema design question that Dante and Chris should drive, but the spec must define what "agent identity" contains.

3. **Standalone specialist lifecycle.** The schema must support agents without team membership. But how are they discovered and assigned to projects? The CRUD API needs a way to list available specialists and connect them to a project context. The spec should define this interaction.

4. **Evaluation framework storage.** The eight dimensions are defined at the org level. Are they stored as a fixed set of rows? A JSONB array? Can the sponsor add or rename dimensions in the future? The spec must define the storage model and mutability rules.

5. **Migration strategy.** How do we seed the database with the existing Nautilus team's data? Is that a migration script, a manual process, or part of the Claude Code integration work in Wave 3? Needs to be decided during spec work so Chris knows whether to build seed tooling.

## Success Criteria

1. A running Cloud Run service with a PostgreSQL database responds to health checks.
2. CRUD operations for orgs, teams, and agents work end-to-end through the API.
3. An org can be created with a personal statement and evaluation framework.
4. A team can be created within an org, agents added to it, and a project reference connected.
5. An agent can be created without a team (hiring for growth) and later assigned.
6. A standalone specialist agent can be created at the org level without team membership.
7. All data is scoped to the org associated with the API key. No cross-org data leakage.
8. The schema includes pgvector columns ready for Wave 2 embedding work.
9. Frank can write and execute UAT cases against the deployed API (UAT test cases confirmed by sponsor before execution).

## Team Assignments

- **Maya (RA):** Owns the specs for this wave. Writes `org-team-agent-schema` and `core-crud-api` specs.
- **Dante (TL):** Reviews specs for feasibility. Writes design.md and tasks.md. Drives `infrastructure-and-auth` spec with Cloud Architect input. Owns architectural decisions.
- **Chris (Dev):** Implements. Consumes specs. Raises unknowns.
- **Frank (QA):** Writes UAT test cases from acceptance criteria. UAT cases confirmed by sponsor before execution.
- **Cloud Architect (Specialist):** Consulted on GCP infrastructure decisions.

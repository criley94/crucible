# Spec: org-team-agent-schema

**Parent Proposal:** wave1-foundation
**Author:** Maya (RA)
**Status:** Complete -- implemented and deployed. 35/35 UAT passed.

---

## What This Spec Covers

The PostgreSQL schema for the three-layer data model (Org, Team, Agent) plus project references. This is the foundational schema that all API endpoints and all future feature domains build on.

## Entities

### organizations

The top-level tenant entity. All data in the system is scoped to an org.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | System-generated |
| name | VARCHAR(255) | NOT NULL, UNIQUE | Display name |
| slug | VARCHAR(100) | NOT NULL, UNIQUE | URL-safe identifier |
| personal_statement | TEXT | NULLABLE | Sponsor's personal statement. One per org. |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Auto-updated on any change |

### evaluation_dimensions

The eight evaluation dimensions defined at the org level. Stored as individual rows rather than JSONB so they can be referenced by foreign key from score entries.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| org_id | UUID | FK -> organizations, NOT NULL | |
| name | VARCHAR(100) | NOT NULL | e.g., "Honesty & Transparency" |
| description | TEXT | NULLABLE | What this dimension measures |
| sort_order | INTEGER | NOT NULL | Display ordering |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Constraint:** UNIQUE(org_id, name) -- no duplicate dimension names within an org.

**Mutability:** Dimensions can be added or renamed by the sponsor. They cannot be deleted if scores reference them. This allows the framework to evolve without losing historical score data. The API must enforce this constraint.

### teams

A named collection of agents with its own identity and norms.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| org_id | UUID | FK -> organizations, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | Display name |
| slug | VARCHAR(100) | NOT NULL | URL-safe identifier |
| description | TEXT | NULLABLE | Team purpose or mission |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 'active' or 'inactive'. Teams are never deleted. |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Constraint:** UNIQUE(org_id, slug)

**No deletion:** Teams are never deleted. An inactive team retains all norms, history, and project connection records.

### team_norms

Living operating agreements for a team. Each norm is a separate row. Norms are mutable -- the current state is the only state (no version history, per sponsor direction).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| team_id | UUID | FK -> teams, NOT NULL | |
| title | VARCHAR(255) | NOT NULL | Short name for the norm |
| body | TEXT | NOT NULL | Full description of the norm |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 'active', 'proposed', 'rejected', 'retired' |
| promoted_to_org | BOOLEAN | NOT NULL, DEFAULT false | Whether this norm has been promoted as an org-level suggested norm |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Note:** The norm proposal/approval workflow (Wave 2) will use the status field. For Wave 1, norms can be created directly in 'active' status via the API.

### org_suggested_norms

Norms promoted from teams to the org level as suggestions for new teams.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| org_id | UUID | FK -> organizations, NOT NULL | |
| source_team_id | UUID | FK -> teams, NULLABLE | Which team this norm originated from |
| title | VARCHAR(255) | NOT NULL | |
| body | TEXT | NOT NULL | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### agents

A persistent identity with accumulated experience.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| org_id | UUID | FK -> organizations, NOT NULL | |
| team_id | UUID | FK -> teams, NULLABLE | NULL for standalone specialists and unassigned agents |
| name | VARCHAR(255) | NOT NULL | Display name (e.g., "Maya") |
| slug | VARCHAR(100) | NOT NULL | URL-safe identifier (e.g., "maya-ra") |
| agent_type | VARCHAR(20) | NOT NULL | 'team_member' or 'standalone_specialist' |
| role | VARCHAR(100) | NOT NULL | e.g., "Requirements Architect", "Backend Developer" |
| persona | TEXT | NOT NULL | Personality, communication style, pet peeves, what lights them up |
| responsibilities | TEXT | NOT NULL | What this agent does and does not do |
| understanding | TEXT | NULLABLE | Agent's own understanding of their role and the project |
| relationships | TEXT | NULLABLE | How this agent works with other team members (prose) |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 'active' or 'inactive'. Agents are never deleted. |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Constraint:** UNIQUE(org_id, slug)

**No deletion:** Agents are never deleted. An inactive agent retains all identity, experience, and score data. They are excluded from default listings but queryable with explicit filters.

**Design rationale for identity fields:** The current markdown system stores persona, responsibilities, understanding, and relationships as separate files per agent. This schema preserves that separation as distinct TEXT columns rather than collapsing into a single blob. Each field has a different authorship pattern (persona is sponsor-defined, understanding is agent-authored, relationships evolve through experience) and will be updated independently. Separate columns support targeted updates and clear API contracts.

**Standalone specialists:** Agents with agent_type = 'standalone_specialist' have team_id = NULL. They belong to the org directly. They can be listed, assigned to project contexts (through future Wave 2/3 endpoints), and reviewed by the sponsor.

**Unassigned agents:** Agents with agent_type = 'team_member' and team_id = NULL are "hired for growth" -- created but not yet assigned to a team. The API must support creating agents without team assignment and adding them to a team later.

### agent_scores

Current performance scores per evaluation dimension per agent.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| agent_id | UUID | FK -> agents, NOT NULL | |
| dimension_id | UUID | FK -> evaluation_dimensions, NOT NULL | |
| current_score | NUMERIC(3,1) | NULLABLE | 1.0 to 5.0. NULL means no score yet. |
| rolling_average | NUMERIC(3,1) | NULLABLE | Computed from review history |
| review_count | INTEGER | NOT NULL, DEFAULT 0 | Number of reviews contributing to the average |
| last_reviewed_at | TIMESTAMPTZ | NULLABLE | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Constraint:** UNIQUE(agent_id, dimension_id) -- one score record per agent per dimension.

**Cold start:** Agents start with NULL scores (no reviews yet). The API returns this as "not yet evaluated" rather than a default value. The display layer (console, Claude Code) decides how to present this. This is consistent with the sponsor's position that meaning emerges from accumulated feedback.

### project_references

Lightweight reference entities for projects. TeamForge does not manage project lifecycle.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| org_id | UUID | FK -> organizations, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | e.g., "TeamForge" |
| slug | VARCHAR(100) | NOT NULL | e.g., "crucible" |
| description | TEXT | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Constraint:** UNIQUE(org_id, slug)

### team_project_connections

Tracks which teams are connected to which projects, with history.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| team_id | UUID | FK -> teams, NOT NULL | |
| project_id | UUID | FK -> project_references, NOT NULL | |
| connected_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | When the team was connected |
| disconnected_at | TIMESTAMPTZ | NULLABLE | NULL means currently connected |

**Note:** A team can be connected to multiple projects over time. A team can be connected to the same project more than once (disconnected and reconnected). Active connections have disconnected_at = NULL.

### experience_entries (placeholder)

This table is created in Wave 1 with the hybrid structure defined by the sponsor, but the write/query endpoints and embedding logic are Wave 2.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| org_id | UUID | FK -> organizations, NOT NULL | |
| agent_id | UUID | FK -> agents, NOT NULL | Which agent authored this |
| team_id | UUID | FK -> teams, NULLABLE | Team context at time of writing |
| project_ref_id | UUID | FK -> project_references, NULLABLE | Project context at time of writing |
| observation_type | VARCHAR(50) | NOT NULL | e.g., 'lesson', 'pattern', 'relationship_note', 'heuristic', 'decision' |
| body | TEXT | NOT NULL | Free-text content |
| embedding | vector(768) | NULLABLE | Vector embedding of body via Vertex AI text-embedding-005. NULL until embedding is generated (Wave 2). |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Note:** This table exists in the Wave 1 schema so that the entity model is complete, but no API endpoints write to it in Wave 1. The embedding dimension was resolved to 768 in Wave 2 design (AD2, Vertex AI text-embedding-005). The initial migration created the column as vector(768).

### review_entries (placeholder)

Performance review submissions. Created in Wave 1 schema, endpoints in Wave 2.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| org_id | UUID | FK -> organizations, NOT NULL | |
| subject_agent_id | UUID | FK -> agents, NOT NULL | Agent being reviewed |
| reviewer_agent_id | UUID | FK -> agents, NULLABLE | NULL if reviewer is the sponsor (human) |
| reviewer_type | VARCHAR(20) | NOT NULL | 'sponsor', 'team_lead', 'peer' |
| project_ref_id | UUID | FK -> project_references, NULLABLE | Which project prompted this review |
| scores | JSONB | NOT NULL | {"dimension_id": score, ...} for each dimension scored |
| narrative | TEXT | NULLABLE | Free-text review feedback |
| narrative_embedding | vector(768) | NULLABLE | For pattern surfacing via vector search (768 dimensions per Vertex AI text-embedding-005) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

## Multi-Tenancy

All top-level entities (organizations, teams, agents, project_references) include org_id. Child entities (team_norms, agent_scores, experience_entries, review_entries) reach their org through foreign key chains.

The API layer enforces org scoping: the API key identifies the org, and all queries filter by org_id. There is no mechanism in Wave 1 for cross-org data access.

**Row-Level Security (RLS):** Whether to use PostgreSQL RLS as an additional enforcement layer is an architectural decision for Dante. The spec requires that cross-org data leakage is impossible through the API. The implementation mechanism is design-level.

---

## Indexing Strategy

Minimum required indexes (Dante and Chris may add more based on query patterns):

- organizations: index on slug
- teams: index on (org_id, slug)
- agents: index on (org_id, slug), index on (org_id, team_id), index on (org_id, agent_type)
- agent_scores: index on (agent_id)
- team_project_connections: index on (team_id, disconnected_at) for finding active connections
- experience_entries: index on (agent_id), index on (team_id), index on (project_ref_id), pgvector index on embedding (type TBD by Dante -- ivfflat vs hnsw)
- review_entries: index on (subject_agent_id), index on (reviewer_agent_id)

---

## What This Spec Does NOT Cover

- Experience capture write/query logic (Wave 2)
- Review submission workflow and score computation (Wave 2)
- Norm proposal/approval workflow (Wave 2)
- Embedding generation strategy (Wave 2)
- Relationship dynamics structured model (deferred pending A5 resolution -- placeholder covered by agents.relationships text field)
- Hiring practices definition (deferred pending A3 resolution)
- Migration of existing Nautilus markdown data (open question #5 from proposal)

---

## Acceptance Criteria

1. The schema can be applied to a fresh PostgreSQL database with pgvector extension without errors.
2. All foreign key relationships are valid and enforced.
3. All UNIQUE constraints are enforced.
4. An org can be created, and a team created within it, and an agent created within the team, with all foreign keys satisfied.
5. An agent can be created without a team_id (unassigned).
6. An agent can be created with agent_type = 'standalone_specialist' and team_id = NULL.
7. A project reference can be created and a team connected to it.
8. Evaluation dimensions can be created at the org level and agent_scores rows can reference them.
9. pgvector extension is enabled and vector columns accept data.
10. No table is missing org_id or a foreign key chain to organizations.
